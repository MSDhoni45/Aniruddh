"""Command-line entry point: `creatoros <command>`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config
from .util import read_json, write_json


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def ist_today() -> str:
    import datetime as dt
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=5, minutes=30)).date().isoformat()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="creatoros", description="Influnexus Creator OS")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe", help="inspect a raw recording"); p.add_argument("video")
    p = sub.add_parser("edit", help="raw footage -> finished reel + QC report")
    p.add_argument("video"); p.add_argument("--date", required=True); p.add_argument("--script"); p.add_argument("--plan")
    p.add_argument("--factcheck"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("script-check", help="lint a script and estimate its duration"); p.add_argument("script")
    p = sub.add_parser("factcheck", help="validate a fact-check file against its script"); p.add_argument("file"); p.add_argument("--script")
    p = sub.add_parser("score", help="rank candidate stories"); p.add_argument("candidates_json")
    p = sub.add_parser("story-check", help="has this story been covered?"); p.add_argument("headline"); p.add_argument("--keys", nargs="*", default=[]); p.add_argument("--date", required=True)
    p = sub.add_parser("story-add"); p.add_argument("headline"); p.add_argument("--keys", nargs="*", default=[]); p.add_argument("--date", required=True); p.add_argument("--slug", required=True); p.add_argument("--update-of")
    p = sub.add_parser("brief", help="(legacy format) validate and render daily/DATE/brief.json"); p.add_argument("--date", required=True)
    p = sub.add_parser("package", help="validate daily/DATE/package.json, render the recording package, log it"); p.add_argument("--date", required=True)
    p.add_argument("--file", help="package.json elsewhere (outputs are written beside it)")
    p = sub.add_parser("today", help="print today's deliverable (Script for today)"); p.add_argument("--date")
    p = sub.add_parser("topics", help="the strongest eligible topics from a day's research (Give me 5 topics)"); p.add_argument("--date")
    p.add_argument("-n", type=int, default=5)
    p = sub.add_parser("recording", help="script and delivery notes only (Prepare for recording)"); p.add_argument("--date")
    p = sub.add_parser("switch", help="archive today's package before replacing it (Different topic)"); p.add_argument("--date")
    p = sub.add_parser("runlog", help="run records: start (duplicate guard, window, budgets), end, delivery, status")
    p.add_argument("event", choices=["start", "end", "delivery", "status"]); p.add_argument("--date")
    p.add_argument("--trigger", default="manual"); p.add_argument("--status", default=""); p.add_argument("--note", default="")
    p.add_argument("--run-id"); p.add_argument("--delivery", default="not attempted", help="requested|confirmed|failed|not attempted")
    p.add_argument("--channel", default=""); p.add_argument("--receipt", default="")
    p.add_argument("--error", action="append", default=[]); p.add_argument("--warning", action="append", default=[])
    p = sub.add_parser("sources-audit", help="probe every source group from this environment; save daily/DATE/source_access.json")
    p.add_argument("--date")
    p = sub.add_parser("followers-add", help="record a follower count you actually saw")
    p.add_argument("--date", required=True); p.add_argument("--platform", required=True); p.add_argument("--followers", required=True)
    p.add_argument("--source", required=True)
    p = sub.add_parser("growth", help="60-day growth dashboard -> reports/growth/DATE.md"); p.add_argument("--date")
    p = sub.add_parser("content-search", help="search the content database"); p.add_argument("query", nargs="?", default="")
    p.add_argument("--status"); p.add_argument("--category")
    p = sub.add_parser("content-update", help="update a content entry: key=value ..."); p.add_argument("--date", required=True)
    p.add_argument("--slug", required=True); p.add_argument("pairs", nargs="+")
    p = sub.add_parser("weekly", help="write reports/weekly/END.md"); p.add_argument("--end", required=True)
    p = sub.add_parser("calibrate", help="record the creator's measured pace from a finished edit"); p.add_argument("--date", required=True)
    p = sub.add_parser("metrics-add", help="store one analytics row: key=value ..."); p.add_argument("pairs", nargs="+")
    p = sub.add_parser("metrics-report"); p.add_argument("--dim", default="topic"); p.add_argument("--checkpoint", default="7d"); p.add_argument("--platform", default="instagram")
    p = sub.add_parser("metrics-review", help="append a review to analytics/learning_log.md")
    p = sub.add_parser("publish"); p.add_argument("--date", required=True); p.add_argument("--platform", required=True)
    p.add_argument("--reviewed", action="store_true"); p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if getattr(a, "date", None) is None and a.cmd in ("today", "topics", "recording", "switch"):
        a.date = ist_today()

    if a.cmd == "probe":
        from .editing.probe import probe
        _print(probe(Path(a.video)))
    elif a.cmd == "edit":
        from .editing.pipeline import edit
        r = edit(Path(a.video), a.date, Path(a.script) if a.script else None, Path(a.plan) if a.plan else None,
                 Path(a.factcheck) if a.factcheck else None, a.force)
        s = r["summary"]
        _print({k: s[k] for k in ("status", "duration", "attempts_at_opening", "removed", "missing_sentences", "weak_sentences", "final")})
        _print([c for c in r["qc"]["checks"] if c["status"] != "PASS"])
        return 0 if s["status"] == "COMPLETE" else 2
    elif a.cmd == "script-check":
        from .scripts import lint
        r = lint.check(Path(a.script).read_text(encoding="utf-8"))
        _print(r)
        return 0 if r["ok"] else 2
    elif a.cmd == "factcheck":
        from .factcheck import claims
        problems = claims.validate(read_json(a.file), Path(a.script).read_text(encoding="utf-8") if a.script else None)
        _print({"ok": not problems, "problems": problems})
        return 0 if not problems else 2
    elif a.cmd == "score":
        from .research import candidates
        _print([{k: c[k] for k in ("headline", "trend_score", "unknown_criteria", "eligible", "problems")} for c in candidates.rank(read_json(a.candidates_json))])
    elif a.cmd == "story-check":
        from .research import storylog
        _print({"repeat_of": storylog.find_repeat(a.headline, a.keys, a.date)})
    elif a.cmd == "story-add":
        from .research import storylog
        _print(storylog.add(a.date, a.headline, a.keys, a.slug, a.update_of))
    elif a.cmd == "brief":
        from .scripts import brief
        r = brief.save(read_json(config.path("daily", a.date, "brief.json")))
        _print(r)
        return 0 if r["ok"] else 2
    elif a.cmd == "package":
        from .scripts import package
        src = Path(a.file) if a.file else config.path("daily", a.date, "package.json")
        r = package.save(read_json(src), src.parent)
        _print(r)
        return 0 if r["ok"] else 2
    elif a.cmd in ("today", "recording"):
        f = config.path("daily", a.date, "today.md" if a.cmd == "today" else "recording.md")
        if not f.exists():
            print(f"No package for {a.date} yet. Run the daily research (RUNBOOK.md), then `creatoros package --date {a.date}`.")
            return 3
        print(f.read_text(encoding="utf-8"))
    elif a.cmd == "topics":
        from .research import candidates
        f = config.path("daily", a.date, "package.json")
        if not f.exists():
            print(f"No research for {a.date} yet.")
            return 3
        elig = [c for c in candidates.rank(read_json(f)["candidates"]) if c["eligible"]]
        ranked = sorted(elig, key=lambda c: (c.get("verification_status", "VERIFIED") != "VERIFIED", -c["trend_score"]))[: a.n]
        for i, c in enumerate(ranked, 1):
            vs = c.get("verification_status", "n/a")
            flag = "" if vs == "VERIFIED" else "  <- needs verification before scripting"
            print(f"{i}. {c['headline']}  [{c['trend_score']}/100, {vs}, {c['evidence_confidence']}]{flag}")
            print(f"   Claim: {c.get('main_claim') or c.get('what_happened')}")
            if c.get("potential_hook"):
                print(f"   Hook: {c['potential_hook']}")
            print(f"   Source: {c['original_source']} ({c['announced_at']})")
    elif a.cmd == "switch":
        import shutil
        from .research import content_db
        d = config.path("daily", a.date)
        f = d / "package.json"
        if not f.exists():
            print("nothing to switch")
            return 3
        old = read_json(f)
        dst = d / f"previous_{old['slug']}"
        dst.mkdir(exist_ok=True)
        for name in ("package.json", "package.md", "today.md", "recording.md", "script.txt", "captions.txt", "claims.md", "sources.json"):
            if (d / name).exists():
                shutil.move(str(d / name), str(dst / name))
        try:
            content_db.update(a.date, old["slug"], status="superseded")
        except KeyError:
            pass
        _print({"archived": str(dst), "next": "pick the next eligible candidate, verify it, write a new package.json"})
    elif a.cmd == "runlog" and a.event == "status":
        from .research import runstatus
        res = runstatus.status(config.path("logs", "runs.jsonl"), a.date or ist_today())
        _print(res)
        return 4 if res["problem"] else 0
    elif a.cmd == "runlog":
        from .research import runs
        log, daily = config.path("logs", "runs.jsonl"), config.path("daily")
        try:
            if a.event == "start":
                rec = runs.start(log, a.trigger, a.note, root=config.path("."))
                _print(rec)
                return {"ALREADY_DONE": 5, "IN_PROGRESS": 6}.get(rec.get("duplicate"), 0)
            if a.event == "end":
                _print(runs.end(log, daily, a.status or "NONE", run_id=a.run_id, trigger=None,
                                note=a.note, delivery=a.delivery, channel=a.channel, receipt=a.receipt,
                                errors=a.error, warnings=a.warning))
            else:
                if not a.run_id:
                    print("runlog delivery needs --run-id", file=sys.stderr)
                    return 2
                _print(runs.delivery(log, daily, a.run_id, a.delivery, a.channel, a.receipt))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
    elif a.cmd == "sources-audit":
        from .research import signals
        res = signals.audit()
        d = a.date or ist_today()
        signals.save_audit(config.path("daily", d, "source_access.json"), res)
        signals.save_audit(config.path("logs", "source_access.json"), res)
        _print({g: v["status"] for g, v in res["groups"].items()} | {"saved": f"daily/{d}/source_access.json"})
    elif a.cmd == "followers-add":
        from .analytics import growth
        try:
            _print(growth.add_snapshot(a.date, a.platform, a.followers, a.source))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
    elif a.cmd == "growth":
        from .analytics import growth
        d = a.date or ist_today()
        path = growth.save(d)
        print(path.read_text(encoding="utf-8"))
    elif a.cmd == "content-search":
        from .research import content_db
        _print([{k: e.get(k) for k in ("date", "slug", "topic", "category", "status", "hook")}
                for e in content_db.search(a.query, status=a.status, category=a.category)])
    elif a.cmd == "content-update":
        from .research import content_db
        fields = {}
        for pair in a.pairs:
            k, v = pair.split("=", 1)
            fields[k] = v.split(",") if k == "platforms" else v
        _print(content_db.update(a.date, a.slug, **fields))
    elif a.cmd == "weekly":
        from .analytics import weekly
        print(weekly.save(a.end))
    elif a.cmd == "calibrate":
        from .scripts.lint import word_count
        rep = read_json(config.path("renders", a.date, "edit_report.json"))
        al = read_json(config.path("renders", a.date, "alignment.json"))
        spoken = sum(t["end"] - t["start"] for t in al["takes"] if t)
        words = sum(word_count(s["script"]) for s in al["sentences"] if s["found"])
        pf = config.path("analytics/pace.json")
        prev = read_json(pf) if pf.exists() else {"samples": 0, "words_per_minute": 0}
        n = prev["samples"] + 1
        wpm = (prev["words_per_minute"] * prev["samples"] + words / spoken * 60) / n
        _print(write_json(pf, {"words_per_minute": round(wpm, 1), "samples": n, "last": a.date, "note": "speech time only, pauses excluded"}) and read_json(pf))
    elif a.cmd == "metrics-add":
        from .analytics import store
        _print(store.upsert(dict(pair.split("=", 1) for pair in a.pairs)))
    elif a.cmd == "metrics-report":
        from .analytics import store
        _print(store.by_dimension(a.dim, a.checkpoint, a.platform))
    elif a.cmd == "metrics-review":
        from .analytics import store
        log = config.path("analytics/learning_log.md")
        text = store.review()
        with open(log, "a", encoding="utf-8") as fh:
            fh.write("\n" + text)
        print(text)
    elif a.cmd == "publish":
        from .publishing.publish import publish
        r = publish(a.date, a.platform, a.reviewed, a.dry_run)
        _print(r)
        return 0 if r["status"] in ("published", "dry_run_ok", "skipped_duplicate") else 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
