"""Did today's scheduled run happen, finish, and deliver by the deadline? Read from logs/runs.jsonl only."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
SCHEDULED = dt.time(8, 41)
DEADLINE = dt.time(9, 30)
GRACE_MIN = 15  # the scheduler may start a few minutes late


def _load(log: Path) -> list[dict]:
    if not log.exists():
        return []
    out = []
    for line in log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def status(log: Path, date: str, now: dt.datetime | None = None) -> dict:
    """Verdict for the scheduled run of IST `date`:
    PENDING (not due yet), RUNNING, OK (READY by 09:30), LATE (READY after 09:30), HOLD/NONE (ran, nothing recordable),
    FAILED (started, no end by the deadline), MISSED (no scheduled start at all)."""
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(IST)
    day = dt.date.fromisoformat(date)
    sched = dt.datetime.combine(day, SCHEDULED, IST)
    deadline = dt.datetime.combine(day, DEADLINE, IST)
    recs = [r for r in _load(log) if r.get("trigger") == "scheduled" and r.get("ist_date") == date]
    for r in recs:
        r["_at"] = dt.datetime.fromisoformat(r["at_utc"]).astimezone(IST)
    # Only runs from 15 minutes before the scheduled time count; an earlier test fire must not stand in for the 08:41 run.
    recs = [r for r in recs if r["_at"] >= sched - dt.timedelta(minutes=GRACE_MIN)]
    starts = [r for r in recs if r.get("event") == "start"]
    ends = [r for r in recs if r.get("event") == "end"]
    manual_ready = any(r.get("trigger") != "scheduled" and r.get("ist_date") == date and r.get("event") == "end"
                       and r.get("status") == "READY" for r in _load(log))
    res = {"date": date, "scheduled_ist": sched.strftime("%H:%M"), "deadline_ist": deadline.strftime("%H:%M"),
           "started_ist": starts[0]["_at"].strftime("%H:%M") if starts else None,
           "ended_ist": ends[-1]["_at"].strftime("%H:%M") if ends else None,
           "end_status": ends[-1].get("status") if ends else None,
           "manual_package_ready": manual_ready}
    if not starts:
        if now < sched + dt.timedelta(minutes=GRACE_MIN):
            v = "PENDING"
        else:
            v = "MISSED"
    elif not ends:
        v = "RUNNING" if now < deadline else "FAILED"
    else:
        st = ends[-1].get("status")
        if st == "READY":
            v = "OK" if ends[-1]["_at"] <= deadline else "LATE"
        else:
            v = st or "FAILED"
    res["verdict"] = v
    res["problem"] = v in ("MISSED", "FAILED", "LATE", "HOLD", "NONE")
    return res
