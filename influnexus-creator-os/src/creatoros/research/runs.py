"""Run records: one ID per run, a duplicate-run guard, time budgets, and an idempotent daily/DATE/run_report.json.

State lives in the repository (logs/runs.jsonl and daily/DATE/run_report.json), never in a conversation, so every run
can start from a fresh session. Only non-secret environment markers are recorded.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
STALE_MINUTES = 60          # a scheduled start with no end after this long is treated as interrupted
DELIVER_BY = dt.time(9, 25)  # target, leaving 5 minutes before the 09:30 deadline
# Minutes after the run starts by which each phase should be finished (scheduled runs start 08:41).
BUDGET_MIN = {"research": 22, "verification": 32, "ranking_and_writing": 39, "quality_and_package": 42}
ENV_KEYS = ["CLAUDE_CODE_REMOTE", "CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE", "CLAUDE_CODE_REMOTE_SESSION_ID",
            "CLAUDE_CODE_CONTAINER_ID"]
# Notification stages, weakest to strongest. "requested" = we asked the notification tool; "accepted" = the provider
# acknowledged it (needs the provider's response as evidence); "received" = the creator saw it (needs their confirmation).
# "confirmed" is the older word for "received". Never record accepted or received without evidence.
DELIVERY = ["not attempted", "failed", "requested", "accepted", "received", "confirmed"]
NEEDS_EVIDENCE = {"accepted", "received", "confirmed"}


def _now(now: dt.datetime | None) -> dt.datetime:
    return (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)


def _iso(d: dt.datetime) -> str:
    return d.isoformat(timespec="seconds")


def load(log: Path) -> list[dict]:
    if not log.exists():
        return []
    out = []
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _append(log: Path, rec: dict) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def git_commit(root: Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True,
                              timeout=10).stdout.strip() or "UNKNOWN"
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"


def environment() -> dict:
    env = {k: os.environ.get(k, "") for k in ENV_KEYS if os.environ.get(k)}
    env["cloud"] = os.environ.get("CLAUDE_CODE_REMOTE") == "true"
    return env


def window(start: dt.datetime, hours: int = 24) -> dict:
    s = start - dt.timedelta(hours=hours)
    return {"start_utc": _iso(s), "end_utc": _iso(start), "start_ist": _iso(s.astimezone(IST)),
            "end_ist": _iso(start.astimezone(IST)), "hours": hours}


def budgets(start: dt.datetime, trigger: str) -> dict:
    """Phase deadlines in IST. Scheduled runs must deliver by 09:25 IST; the hard deadline is 09:30."""
    b = {k: (start + dt.timedelta(minutes=m)).astimezone(IST).strftime("%H:%M") for k, m in BUDGET_MIN.items()}
    if trigger == "scheduled":
        day = start.astimezone(IST).date()
        b["deliver_by"] = DELIVER_BY.strftime("%H:%M")
        b["hard_deadline"] = "09:30"
        if start.astimezone(IST) > dt.datetime.combine(day, DELIVER_BY, IST):
            b["late_start"] = True
    return b


def _runs_for(recs: list[dict], date: str, trigger: str) -> dict:
    """run_id -> {start, end} for one IST date and trigger. Records from before run IDs existed are grouped in order
    (an end belongs to the latest start). Scheduled-tagged records more than 15 minutes before 08:41 IST are ignored,
    so a test fire never counts as the day's scheduled run (same rule as `runlog status`)."""
    sched = dt.datetime.combine(dt.date.fromisoformat(date), dt.time(8, 26), IST)
    runs: dict[str, dict] = {}
    last_legacy = None
    for r in recs:
        if r.get("ist_date") != date or r.get("trigger") != trigger or r.get("event") not in ("start", "end"):
            continue
        if trigger == "scheduled" and dt.datetime.fromisoformat(r["at_utc"]) < sched:
            continue
        rid = r.get("run_id")
        if not rid:
            if r["event"] == "start":
                last_legacy = rid = f"{date}-{trigger}-{dt.datetime.fromisoformat(r['at_utc']).astimezone(IST):%H%M%S}"
            else:
                rid = last_legacy
            if rid is None:
                continue
        runs.setdefault(rid, {})[r["event"]] = r
    return runs


def start(log: Path, trigger: str, note: str = "", root: Path | None = None, now: dt.datetime | None = None,
          daily: Path | None = None, audit_fn=None) -> dict:
    """Begin a run. For scheduled runs, refuse a duplicate: ALREADY_DONE if today's scheduled run already ended READY,
    IN_PROGRESS if one started under an hour ago and has not ended. A start older than that with no end is closed as
    INTERRUPTED and a new run proceeds (recovery)."""
    t = _now(now)
    date = t.astimezone(IST).date().isoformat()
    recs = load(log)
    if trigger == "scheduled":
        for rid, ev in _runs_for(recs, date, "scheduled").items():
            end = ev.get("end")
            if end and end.get("status") == "READY":
                return {"duplicate": "ALREADY_DONE", "run_id": rid, "ist_date": date,
                        "message": f"today's scheduled run {rid} already finished READY; deliver that package, do not rerun"}
            st = ev.get("start")
            if st and not end:
                age = (t - dt.datetime.fromisoformat(st["at_utc"])).total_seconds() / 60
                if age < STALE_MINUTES:
                    return {"duplicate": "IN_PROGRESS", "run_id": rid, "ist_date": date,
                            "message": f"scheduled run {rid} started {age:.0f} min ago and has not ended; do not start another"}
                _append(log, {"event": "end", "run_id": rid, "trigger": "scheduled", "status": "INTERRUPTED",
                              "note": f"no end recorded {age:.0f} min after start; closed by the next run",
                              "at_utc": _iso(t), "ist_date": date})
    audit_summary = None
    if daily is not None and audit_fn is not None:
        # The source audit runs BEFORE any research, so the run knows what it can reach; research.json records it.
        from . import signals
        res = audit_fn()
        signals.save_audit(daily / date / "source_access.json", res)
        signals.save_audit(log.parent / "source_access.json", res)
        audit_summary = {"checked_at_utc": res["checked_at_utc"], **{g: v["status"] for g, v in res["groups"].items()}}
    rid = f"{date}-{trigger}-{t.astimezone(IST).strftime('%H%M%S')}"
    rec = {"event": "start", "run_id": rid, "trigger": trigger, "status": "", "note": note, "at_utc": _iso(t),
           "at_ist": _iso(t.astimezone(IST)), "ist_date": date, "git_commit": git_commit(root or log.parent),
           "environment": environment(), "research_window": window(t), "budgets": budgets(t, trigger)}
    if audit_summary:
        rec["source_audit"] = audit_summary
    _append(log, rec)
    return rec


def summarise_package(pkg: Path) -> dict:
    """What the run produced, read from the package itself; missing data stays UNKNOWN."""
    if not pkg.exists():
        return {"package_status": "MISSING"}
    from ..scripts import lint, package as pk
    from ..factcheck.verification import access_summary
    p = json.loads(pkg.read_text(encoding="utf-8"))
    try:
        problems, info = pk.validate(p)
    except Exception as e:  # a malformed package must be reported, not crash the run log
        return {"package_status": "INVALID", "errors": [f"package could not be validated: {e}"]}
    claims = p.get("factcheck", {}).get("claims", [])
    chk = info.get("lint") or lint.estimate_seconds(p.get("script", ""))
    status = info["ready"]["status"] if info else "INVALID"
    return {"package_status": "VALID" if not problems else "INVALID", "readiness": status,
            "selected_story": p.get("topic"), "candidates": len(p.get("candidates", [])),
            "research_window": p.get("research_window", "UNKNOWN"),
            "source_access": access_summary(claims) or "UNKNOWN",
            "fact_check": "PASS" if info and not info["ready"]["reasons"] else "FAIL",
            "word_count": chk.get("words"), "estimated_seconds": chk.get("seconds"),
            "quality_gate": ("PASS" if info and info["quality"]["approved"] else "FAIL"),
            "quality_total": info["quality"]["total"] if info else None,
            "validation_problems": problems[:20]}


def _report_path(daily: Path, date: str) -> Path:
    return daily / date / "run_report.json"


def _upsert_report(daily: Path, date: str, run_id: str, fields: dict) -> dict:
    """daily/DATE/run_report.json holds one entry per run_id; re-running the same step updates it in place."""
    path = _report_path(daily, date)
    path.parent.mkdir(parents=True, exist_ok=True)
    rep = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"date": date, "runs": {}}
    rep["runs"].setdefault(run_id, {}).update(fields)
    path.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rep["runs"][run_id]


def _find_start(recs: list[dict], run_id: str | None, trigger: str | None) -> dict | None:
    """The named run, or else the most recent run that has started and not yet ended (optionally of one trigger)."""
    starts = [r for r in recs if r.get("event") == "start" and r.get("run_id")]
    if run_id:
        starts = [r for r in starts if r["run_id"] == run_id]
        return starts[-1] if starts else None
    ended = {r.get("run_id") for r in recs if r.get("event") == "end"}
    open_ = [r for r in starts if r["run_id"] not in ended and (trigger is None or r.get("trigger") == trigger)]
    return open_[-1] if open_ else None


def end(log: Path, daily: Path, status: str, run_id: str | None = None, trigger: str | None = None, note: str = "",
        delivery: str = "not attempted", channel: str = "", receipt: str = "", errors: list[str] | None = None,
        warnings: list[str] | None = None, now: dt.datetime | None = None) -> dict:
    t = _now(now)
    recs = load(log)
    st = _find_start(recs, run_id, trigger)
    if st is None:
        raise ValueError("no matching run start; run `creatoros runlog start` first")
    if delivery not in DELIVERY:
        raise ValueError(f"delivery must be one of {DELIVERY}")
    if delivery in NEEDS_EVIDENCE and not receipt.strip():
        raise ValueError(f"delivery '{delivery}' needs --receipt with the evidence (provider response or the creator's confirmation)")
    date = st["ist_date"]
    summary = summarise_package(daily / date / "package.json")
    rec = {"event": "end", "run_id": st["run_id"], "trigger": st["trigger"], "status": status, "note": note,
           "at_utc": _iso(t), "at_ist": _iso(t.astimezone(IST)), "ist_date": date,
           "delivery": {"status": delivery, "channel": channel, "receipt": receipt or "none available",
                        "at_ist": _iso(t.astimezone(IST)) if delivery != "not attempted" else None},
           "errors": errors or [], "warnings": warnings or []}
    _append(log, rec)
    report = {"run_id": st["run_id"], "trigger": st["trigger"], "start_ist": st.get("at_ist"), "end_ist": rec["at_ist"],
              "environment": st.get("environment", {}), "git_commit": st.get("git_commit", "UNKNOWN"),
              "research_window": st.get("research_window"), "status": status, "delivery": rec["delivery"],
              "errors": rec["errors"], "warnings": rec["warnings"], "note": note, **summary}
    _upsert_report(daily, date, st["run_id"], report)
    _rerender_today(daily, date)
    return report


def _rerender_today(daily: Path, date: str) -> None:
    """Refresh today.md so its RUN STATUS line shows this run's final status and delivery."""
    pkg = daily / date / "package.json"
    if not pkg.exists():
        return
    from ..scripts import package as pk
    try:
        p = json.loads(pkg.read_text(encoding="utf-8"))
        problems, info = pk.validate(p)
        if not problems and pk.is_v3(p):
            (daily / date / "today.md").write_text(pk.render_today(p, info), encoding="utf-8")
    except Exception:  # never let a re-render failure lose the run record
        return


def delivery(log: Path, daily: Path, run_id: str, status: str, channel: str = "", receipt: str = "",
             now: dt.datetime | None = None) -> dict:
    """Record (or correct) a run's delivery after the fact, e.g. a confirmed receipt or a failure."""
    if status not in DELIVERY:
        raise ValueError(f"delivery must be one of {DELIVERY}")
    if status in NEEDS_EVIDENCE and not receipt.strip():
        raise ValueError(f"delivery '{status}' needs --receipt with the evidence (provider response or the creator's confirmation)")
    t = _now(now)
    st = _find_start(load(log), run_id, None)
    if st is None:
        raise ValueError(f"unknown run_id {run_id}")
    d = {"status": status, "channel": channel, "receipt": receipt or "none available", "at_ist": _iso(t.astimezone(IST))}
    _append(log, {"event": "delivery", "run_id": run_id, "trigger": st["trigger"], "status": status, "delivery": d,
                  "at_utc": _iso(t), "ist_date": st["ist_date"]})
    rep = _upsert_report(daily, st["ist_date"], run_id, {"delivery": d})
    _rerender_today(daily, st["ist_date"])
    return rep


def delivery_stages(daily: Path, date: str, log: Path, repo: Path | None = None, branch: str | None = None) -> dict:
    """Each delivery stage separately, from evidence only: generated, saved, pushed, notification requested,
    accepted by the provider, received by the creator."""
    pkg = daily / date / "package.json"
    out = {"package_generated": "NO", "package_saved": "NO", "pushed": "UNKNOWN", "notification_requested": "NO",
           "notification_accepted": "UNKNOWN", "notification_received": "UNKNOWN"}
    if pkg.exists():
        s = summarise_package(pkg)
        out["package_generated"] = "YES" if s.get("package_status") == "VALID" else f"INVALID ({s.get('package_status')})"
        out["readiness"] = s.get("readiness")
        out["package_saved"] = "YES" if (daily / date / "today.md").exists() else "PARTIAL (no today.md)"
    if repo is not None and branch:
        try:
            h = subprocess.run(["git", "log", "-1", "--format=%h %cI", f"origin/{branch}", "--", str(daily / date)], cwd=repo,
                               capture_output=True, text=True, timeout=10).stdout.strip()
            out["pushed"] = f"YES ({h})" if h else "NO"
        except (OSError, subprocess.SubprocessError):
            pass
    recs = [r for r in load(log) if r.get("ist_date") == date and isinstance(r.get("delivery"), dict)]
    states = {r["delivery"].get("status") for r in recs}
    receipts = [r["delivery"].get("receipt") for r in recs if r["delivery"].get("status") in NEEDS_EVIDENCE]
    if states & {"requested", "accepted", "received", "confirmed"}:
        out["notification_requested"] = "YES"
    if "failed" in states and not states & {"requested", "accepted", "received", "confirmed"}:
        out["notification_requested"] = "FAILED"
    if states & {"accepted", "received", "confirmed"}:
        out["notification_accepted"] = f"YES ({receipts[0]})"
    if states & {"received", "confirmed"}:
        out["notification_received"] = f"YES ({receipts[-1]})"
    return out
