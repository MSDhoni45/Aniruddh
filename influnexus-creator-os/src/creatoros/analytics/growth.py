"""Growth dashboard (V7: 100K followers in 60 days from 22 Nov 2026): follower snapshots, the target trajectory, observed conversion and the content mix.

Only numbers the creator recorded (or a connected analytics source returned) are used. Anything missing is UNKNOWN, and
no projection is shown as a prediction. A target is not a guarantee.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from .. import config
from ..research import content_db
from . import store

CSV = "analytics/followers.csv"
FIELDS = ["date", "platform", "followers", "source", "collected_at"]
PLATFORMS = ["instagram", "youtube", "x", "linkedin"]
UNKNOWN = "UNKNOWN"
PHASES = [(1, 7, "Phase 1: baseline", "Test hook structures, categories, story types, delivery and visual formats; record results."),
          (8, 21, "Phase 2: find what works", "Lean into topics with strong retention, shares, saves and follows per 1k views; cut consistently weak formats."),
          (22, 40, "Phase 3: scale", "Scale proven patterns; try recurring series, follow-up explainers, audience questions, demonstrations."),
          (41, 60, "Phase 4: concentrate", "Concentrate on the most effective formats; review often; keep repeatable audience value.")]


def settings() -> dict:
    g = config.settings().get("growth", {})
    return {"target_followers": int(g.get("target_followers", 100000)), "days": int(g.get("days", 60)),
            "start_date": str(g.get("start_date", "2026-11-20")), "platform": str(g.get("platform", "instagram"))}


def _path(p: Path | None = None) -> Path:
    return p or config.path(CSV)


def load(p: Path | None = None) -> list[dict]:
    p = _path(p)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def add_snapshot(date: str, platform: str, followers: int | str, source: str, p: Path | None = None,
                 now: dt.datetime | None = None) -> dict:
    """Record a follower count the creator actually saw (one row per date and platform; re-entry replaces it)."""
    dt.date.fromisoformat(date)
    if platform not in PLATFORMS:
        raise ValueError(f"platform must be one of {PLATFORMS}")
    n = int(followers)
    if n < 0:
        raise ValueError("followers cannot be negative")
    if not source.strip():
        raise ValueError("say where the number came from (e.g. 'Instagram app, profile page')")
    row = {"date": date, "platform": platform, "followers": str(n), "source": source.strip(),
           "collected_at": (now or dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds")}
    rows = [r for r in load(p) if (r["date"], r["platform"]) != (date, platform)] + [row]
    rows.sort(key=lambda r: (r["date"], r["platform"]))
    path = _path(p)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return row


def _latest(rows: list[dict], on: str) -> dict[str, dict]:
    out = {}
    for r in sorted(rows, key=lambda r: r["date"]):
        if r["date"] <= on:
            out[r["platform"]] = r
    return out


def _earliest(rows: list[dict]) -> dict[str, dict]:
    out = {}
    for r in sorted(rows, key=lambda r: r["date"]):
        out.setdefault(r["platform"], r)
    return out


def phase(day: int) -> tuple[str, str]:
    for lo, hi, name, focus in PHASES:
        if lo <= day <= hi:
            return name, focus
    last = settings()["days"]
    return ("Before day 1", "The plan has not started.") if day < 1 else (f"After day {last}", "The plan window has ended.")


def conversion(perf_rows: list[dict]) -> dict:
    """Observed followers per 1,000 views, from videos with both numbers (7-day checkpoint preferred)."""
    best: dict[tuple, dict] = {}
    rank = {"24h": 0, "72h": 1, "7d": 2}
    for r in perf_rows:
        if not (r.get("views") and r.get("new_followers")):
            continue
        key = (r["video_id"], r["platform"])
        if key not in best or rank.get(r["checkpoint"], -1) > rank.get(best[key]["checkpoint"], -1):
            best[key] = r
    views = sum(float(r["views"]) for r in best.values())
    follows = sum(float(r["new_followers"]) for r in best.values())
    if not best or views <= 0:
        return {"videos": 0, "followers_per_1k_views": UNKNOWN}
    return {"videos": len(best), "views": int(views), "new_followers": int(follows),
            "followers_per_1k_views": round(follows / views * 1000, 3)}


def mix(entries: list[dict], key: str, targets: dict | None = None) -> list[dict]:
    counts: dict[str, int] = {}
    for e in entries:
        counts[e.get(key) or "unrecorded"] = counts.get(e.get(key) or "unrecorded", 0) + 1
    total = sum(counts.values())
    names = list(targets or {}) + [k for k in counts if k not in (targets or {})]
    return [{key: n, "count": counts.get(n, 0), "share_pct": round(100 * counts.get(n, 0) / total) if total else 0,
             "target_pct": (targets or {}).get(n)} for n in names]


def _series(rows: list[dict], platform: str, on: str) -> list[tuple]:
    """(date, followers) for one platform up to a date, one point per day."""
    return [(dt.date.fromisoformat(r["date"]), int(r["followers"])) for r in sorted(rows, key=lambda r: r["date"])
            if r["platform"] == platform and r["date"] <= on]


def _growth_over(series: list[tuple], today: dt.date, days: int):
    """Net growth over the last `days`: latest minus the latest snapshot at least `days` old (None if none that old)."""
    if not series:
        return None
    past = [(d, n) for d, n in series if (today - d).days >= days]
    return series[-1][1] - past[-1][1] if past else None


def scenarios(series: list[tuple], days_left: int, target: int) -> dict:
    """End-of-plan projections from the account's own observed growth. Assumptions are stated; nothing is guaranteed.
    baseline     = average daily net growth since the first snapshot, continued
    conservative = the slowest daily rate between consecutive snapshots in the last 14 days, continued
    optimistic   = the fastest daily rate between consecutive snapshots in the last 14 days, continued"""
    if len(series) < 2 or series[-1][0] == series[0][0]:
        return {"status": UNKNOWN, "note": "needs follower counts on at least two different dates"}
    cur_d, cur = series[-1]
    avg = (cur - series[0][1]) / (cur_d - series[0][0]).days
    recent = [p for p in series if (cur_d - p[0]).days <= 14]
    rates = [(b[1] - a[1]) / (b[0] - a[0]).days for a, b in zip(recent, recent[1:]) if (b[0] - a[0]).days > 0]
    proj = lambda r: round(cur + r * days_left)
    out = {"assumptions": scenarios.__doc__.split("\n", 1)[1].strip(),
           "observed_avg_daily": round(avg, 1), "baseline": proj(avg)}
    if len(rates) >= 2:
        out.update(conservative=proj(min(rates)), optimistic=proj(max(rates)))
    else:
        out.update(conservative=UNKNOWN, optimistic=UNKNOWN,
                   note="conservative/optimistic need at least three snapshots in the last 14 days")
    out["on_track"] = out["baseline"] >= target
    if not out["on_track"]:
        out["warning"] = (f"At the observed rate ({round(avg, 1)}/day) the account reaches about {out['baseline']:,} by the last day, "
                          f"short of {target:,}. The current strategy is not enough on its own.")
    return out


def dashboard(date: str, followers_path: Path | None = None, perf_path: Path | None = None,
              db_path: Path | None = None) -> dict:
    from ..scripts.package import PILLARS
    s = settings()
    target_pl = s["platform"]
    start = dt.date.fromisoformat(s["start_date"])
    end = start + dt.timedelta(days=s["days"] - 1)
    today = dt.date.fromisoformat(date)
    day = (today - start).days + 1
    days_left = max((end - today).days, 0)
    rows = load(followers_path)
    latest = _latest(rows, date)
    series = _series(rows, target_pl, date)
    current = series[-1][1] if series else None
    out = {"date": date, "day": day, "days_total": s["days"], "start_date": str(start), "end_date": str(end),
           "days_remaining": days_left, "target_followers": s["target_followers"], "target_platform": target_pl,
           "phase": phase(day)[0], "phase_focus": phase(day)[1],
           "followers_by_platform": {pl: (int(latest[pl]["followers"]) if pl in latest else UNKNOWN) for pl in PLATFORMS},
           "platforms_without_data": [pl for pl in PLATFORMS if pl not in latest],
           "current_followers": current if current is not None else UNKNOWN}
    if current is None:
        out.update(remaining_followers=UNKNOWN, daily_net_growth_required=UNKNOWN, average_daily_required_over_plan=UNKNOWN,
                   trajectory=UNKNOWN, net_gained=UNKNOWN, daily_growth=UNKNOWN, growth_7d=UNKNOWN, growth_30d=UNKNOWN,
                   projection={"status": UNKNOWN, "note": f"no {target_pl} follower count recorded"})
    else:
        remaining = max(s["target_followers"] - current, 0)
        base_d, base = series[0]
        out["baseline"] = {"date": str(base_d), "followers": base}
        out["remaining_followers"] = remaining
        out["average_daily_required_over_plan"] = round(max(s["target_followers"] - base, 0) / s["days"])
        out["daily_net_growth_required"] = round(remaining / days_left) if days_left else (0 if remaining == 0 else UNKNOWN)
        out["net_gained"] = current - base
        prev = series[-2] if len(series) >= 2 else None
        out["daily_growth"] = round((current - prev[1]) / (series[-1][0] - prev[0]).days, 1) if prev else UNKNOWN
        g7, g30 = _growth_over(series, series[-1][0], 7), _growth_over(series, series[-1][0], 30)
        out["growth_7d"] = g7 if g7 is not None else UNKNOWN
        out["growth_30d"] = g30 if g30 is not None else UNKNOWN
        if base_d < today and end > base_d and len(series) >= 2:
            expected = base + (s["target_followers"] - base) * (today - base_d).days / (end - base_d).days
            gap = current - expected
            out["trajectory"] = {"baseline_date": str(base_d), "baseline_followers": base, "expected_today": round(expected),
                                 "gap": round(gap), "status": "AHEAD" if gap >= 0 else "BEHIND"}
        else:
            out["trajectory"] = "UNKNOWN (needs follower counts on at least two dates)"
        out["projection"] = scenarios(series, days_left, s["target_followers"])
    conv = conversion([r for r in store.load(perf_path) if r.get("platform") == target_pl])
    out["conversion"] = conv
    fpk = conv["followers_per_1k_views"]
    need = out["daily_net_growth_required"]
    out["daily_views_needed_at_observed_conversion"] = (round(need / fpk * 1000) if isinstance(fpk, float) and fpk > 0
                                                        and isinstance(need, int) else UNKNOWN)
    window = [e for e in content_db.entries(db_path) if start <= dt.date.fromisoformat(e["date"]) <= today
              and e.get("status") in ("scripted", "published")]
    out["scripted"] = len(window)
    out["published"] = sum(1 for e in window if e.get("status") == "published")
    out["pillar_mix"] = mix(window, "pillar", PILLARS)
    out["format_mix"] = mix(window, "format")
    out["reels"] = reel_table([r for r in store.load(perf_path) if r.get("platform") == target_pl])
    out["weekly_checkpoints"] = weekly_checkpoints(s, out.get("baseline"), series)
    return out


def weekly_checkpoints(s: dict, baseline: dict | None, series: list[tuple]) -> list[dict]:
    """End-of-week targets on a straight line from the baseline to the target, with the actual count where recorded.
    Without a baseline the targets are UNKNOWN (the starting follower count has to come from the creator)."""
    start = dt.date.fromisoformat(s["start_date"])
    end = start + dt.timedelta(days=s["days"] - 1)
    out, week = [], 1
    while True:
        d = min(start + dt.timedelta(days=7 * week - 1), end)
        if baseline:
            b_d, b = dt.date.fromisoformat(baseline["date"]), baseline["followers"]
            span = max((end - b_d).days, 1)
            tgt = round(b + (s["target_followers"] - b) * max((d - b_d).days, 0) / span)
        else:
            tgt = UNKNOWN
        actual = [n for sd, n in series if sd <= d and (d - sd).days < 7]
        out.append({"week": week, "date": str(d), "target": tgt, "actual": actual[-1] if actual else UNKNOWN})
        if d >= end:
            return out
        week += 1


def reel_table(rows: list[dict]) -> list[dict]:
    """Latest checkpoint per reel, with each rate compared with the account's own median (never a universal benchmark)."""
    from statistics import median
    order = {c: i for i, c in enumerate(store.CHECKPOINTS)}
    best: dict[str, dict] = {}
    for r in rows:
        if r["video_id"] not in best or order.get(r["checkpoint"], -1) > order.get(best[r["video_id"]]["checkpoint"], -1):
            best[r["video_id"]] = r
    reels = [{**store.derive(r), "date": r["date"], "topic": r.get("topic") or "", "reach": store._f(r, "reach")} for r in best.values()]
    for k in ("share_rate", "save_rate", "follower_conversion", "views"):
        vals = [x[k] for x in reels if x[k] is not None]
        med = median(vals) if vals else None
        for x in reels:
            x[f"{k}_vs_median"] = round(x[k] / med, 2) if med and x[k] is not None else None
    return sorted(reels, key=lambda x: x["date"])


def render(d: dict) -> str:
    def v(x):
        return f"{x:,}" if isinstance(x, int) else str(x)
    pl = d["target_platform"].capitalize()
    L = [f"# Growth dashboard: {d['date']} (day {d['day']} of {d['days_total']})", "",
         f"Target: {v(d['target_followers'])} {pl} followers by {d['end_date']}. This is a goal, not a forecast.", "",
         f"**{d['phase']}.** {d['phase_focus']}", "",
         "| Measure | Value |", "|---|---|",
         f"| Current {pl} followers | {v(d['current_followers'])} |",
         f"| Net gained since baseline | {v(d['net_gained'])} |",
         f"| Latest daily growth | {v(d['daily_growth'])} |",
         f"| 7-day growth | {v(d['growth_7d'])} |", f"| 30-day growth | {v(d['growth_30d'])} |",
         f"| Followers remaining | {v(d['remaining_followers'])} |", f"| Days remaining | {d['days_remaining']} |",
         f"| Net followers needed per day from now | {v(d['daily_net_growth_required'])} |",
         f"| Average needed per day over the plan (from baseline) | {v(d['average_daily_required_over_plan'])} |"]
    t = d["trajectory"]
    wk = d.get("weekly_checkpoints") or []
    traj_rows = [f"| Week {w['week']} ({w['date']}) target / actual | {v(w['target'])} / {v(w['actual'])} |" for w in wk]
    traj = t if isinstance(t, str) else f"{t['status']} by {abs(t['gap']):,} (expected {t['expected_today']:,} today)"
    L.append(f"| Actual vs target trajectory | {traj} |")
    L += traj_rows
    pr = d["projection"]
    if pr.get("status") == UNKNOWN:
        L.append(f"| Projected followers on the last day | UNKNOWN ({pr['note']}) |")
    else:
        L.append(f"| Projected on the last day (conservative / baseline / optimistic) | {v(pr['conservative'])} / {v(pr['baseline'])} / {v(pr['optimistic'])} |")
    c = d["conversion"]
    L += [f"| Observed followers per 1,000 views | {c['followers_per_1k_views']} ({c['videos']} reels) |",
          f"| Daily views needed at that rate | {v(d['daily_views_needed_at_observed_conversion'])} |",
          f"| Scripts since day 1 / published | {d['scripted']} / {d['published']} |", ""]
    if pr.get("warning"):
        L += [f"**Warning:** {pr['warning']}", ""]
    if pr.get("assumptions"):
        L += ["Projection assumptions: " + " ".join(pr["assumptions"].split()), ""]
    L += ["**Other platforms (not counted toward the target):** " + ", ".join(f"{k} {v(x)}" for k, x in d["followers_by_platform"].items() if k != d["target_platform"])]
    if d["target_platform"] in d["platforms_without_data"]:
        L += ["", f"No {pl} follower count recorded yet. Add one with "
              f"`creatoros followers-add --date DATE --platform {d['target_platform']} --followers N --source \"where you read it\"`."]
    L += ["", "## Reels (latest checkpoint; rates per account reached; x = vs this account's median)", ""]
    if not d["reels"]:
        L.append("No reel metrics yet. Record them with `creatoros metrics-add` at 2h, 24h, 48h and 7d.")
    else:
        L += ["| Date | Reel | Checkpoint | Views | Reach | Share rate | Save rate | Follower conversion | Follows /1k reach |", "|---|---|---|---|---|---|---|---|---|"]
        for r in d["reels"]:
            f = lambda k: "UNKNOWN" if r[k] is None else (f"{r[k]:.2%}" + (f" ({r[k + '_vs_median']}x)" if r.get(k + "_vs_median") else ""))
            L.append(f"| {r['date']} | {r['video_id']} | {r['checkpoint']} | {r['views'] if r['views'] is not None else 'UNKNOWN'} | "
                     f"{r['reach'] if r['reach'] is not None else 'UNKNOWN'} | {f('share_rate')} | {f('save_rate')} | {f('follower_conversion')} | "
                     f"{r['follows_per_1k_reach'] if r['follows_per_1k_reach'] is not None else 'UNKNOWN'} |")
    L += ["", "## Content mix since day 1", "", "| Pillar | Scripts | Share | Starting target |", "|---|---|---|---|"]
    L += [f"| {m['pillar']} | {m['count']} | {m['share_pct']}% | {m['target_pct'] if m['target_pct'] is not None else '-'}% |" for m in d["pillar_mix"]]
    L += ["", "| Format | Scripts | Share |", "|---|---|---|"]
    L += [f"| {m['format']} | {m['count']} | {m['share_pct']}% |" for m in d["format_mix"]] or ["| none yet | 0 | 0% |"]
    L += ["", "Small samples are anecdotes, and correlation is not causation. Change one variable at a time."]
    return "\n".join(L) + "\n"


def save(date: str) -> Path:
    out = config.path("reports", "growth", f"{date}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(dashboard(date)), encoding="utf-8")
    return out
