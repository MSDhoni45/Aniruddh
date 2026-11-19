"""60-day growth dashboard: follower snapshots, the target trajectory, observed conversion and the content mix.

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
            "start_date": str(g.get("start_date", "2026-11-20"))}


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
    return ("Before day 1", "The 60 days have not started.") if day < 1 else ("After day 60", "The 60-day window has ended.")


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


def dashboard(date: str, followers_path: Path | None = None, perf_path: Path | None = None,
              db_path: Path | None = None) -> dict:
    from ..scripts.package import PILLARS
    s = settings()
    start = dt.date.fromisoformat(s["start_date"])
    end = start + dt.timedelta(days=s["days"] - 1)
    today = dt.date.fromisoformat(date)
    day = (today - start).days + 1
    days_left = max((end - today).days, 0)
    rows = load(followers_path)
    latest, first = _latest(rows, date), _earliest(rows)
    current = sum(int(r["followers"]) for r in latest.values()) if latest else None
    missing = [pl for pl in PLATFORMS if pl not in latest]
    out = {"date": date, "day": day, "days_total": s["days"], "start_date": str(start), "end_date": str(end),
           "days_remaining": days_left, "target_followers": s["target_followers"],
           "phase": phase(day)[0], "phase_focus": phase(day)[1],
           "followers_by_platform": {pl: (int(latest[pl]["followers"]) if pl in latest else UNKNOWN) for pl in PLATFORMS},
           "platforms_without_data": missing,
           "current_followers": current if current is not None else UNKNOWN}
    if current is None:
        out.update(remaining_followers=UNKNOWN, daily_net_growth_required=UNKNOWN, trajectory=UNKNOWN)
    else:
        remaining = max(s["target_followers"] - current, 0)
        out["remaining_followers"] = remaining
        out["daily_net_growth_required"] = round(remaining / days_left) if days_left else (0 if remaining == 0 else UNKNOWN)
        base_date = min(r["date"] for r in first.values())
        base = sum(int(r["followers"]) for r in first.values())
        b = dt.date.fromisoformat(base_date)
        if b < today and set(first) == set(latest) and end > b:
            expected = base + (s["target_followers"] - base) * (today - b).days / (end - b).days
            gap = current - expected
            out["trajectory"] = {"baseline_date": base_date, "baseline_followers": base, "expected_today": round(expected),
                                 "gap": round(gap), "status": "AHEAD" if gap >= 0 else "BEHIND"}
        else:
            out["trajectory"] = "UNKNOWN (needs follower counts on at least two dates for the same platforms)"
    conv = conversion(store.load(perf_path))
    out["conversion"] = conv
    fpk = conv["followers_per_1k_views"]
    need = out["daily_net_growth_required"]
    if isinstance(fpk, float) and fpk > 0 and isinstance(need, int):
        out["daily_views_needed_at_observed_conversion"] = round(need / fpk * 1000)
    else:
        out["daily_views_needed_at_observed_conversion"] = UNKNOWN
    window = [e for e in content_db.entries(db_path) if start <= dt.date.fromisoformat(e["date"]) <= today
              and e.get("status") in ("scripted", "published")]
    out["scripted"] = len(window)
    out["published"] = sum(1 for e in window if e.get("status") == "published")
    out["pillar_mix"] = mix(window, "pillar", PILLARS)
    out["format_mix"] = mix(window, "format")
    return out


def render(d: dict) -> str:
    def v(x):
        return f"{x:,}" if isinstance(x, int) else str(x)
    L = [f"# 60-day growth dashboard: {d['date']} (day {d['day']} of {d['days_total']})", "",
         f"Target: {v(d['target_followers'])} followers by {d['end_date']}. This is a goal, not a forecast; nothing here predicts views.", "",
         f"**{d['phase']}.** {d['phase_focus']}", "",
         "| Measure | Value |", "|---|---|",
         f"| Current followers (all platforms recorded) | {v(d['current_followers'])} |",
         f"| Remaining to target | {v(d['remaining_followers'])} |",
         f"| Days remaining | {d['days_remaining']} |",
         f"| Net followers needed per day | {v(d['daily_net_growth_required'])} |"]
    t = d["trajectory"]
    traj = t if isinstance(t, str) else f"{t['status']} by {abs(t['gap']):,} (expected {t['expected_today']:,} today)"
    L.append(f"| Trajectory | {traj} |")
    c = d["conversion"]
    L += [f"| Observed followers per 1,000 views | {c['followers_per_1k_views']} ({c['videos']} videos) |",
          f"| Daily views needed at that rate | {v(d['daily_views_needed_at_observed_conversion'])} |",
          f"| Scripts since day 1 / published | {d['scripted']} / {d['published']} |", "",
          "**Followers by platform:** " + ", ".join(f"{k} {v(x)}" for k, x in d["followers_by_platform"].items())]
    if d["platforms_without_data"]:
        L += ["", f"No follower count recorded yet for: {', '.join(d['platforms_without_data'])}. Add one with "
              "`creatoros followers-add --date DATE --platform P --followers N --source \"where you read it\"`."]
    L += ["", "## Content mix since day 1", "", "| Pillar | Scripts | Share | Starting target |", "|---|---|---|---|"]
    L += [f"| {m['pillar']} | {m['count']} | {m['share_pct']}% | {m['target_pct'] if m['target_pct'] is not None else '-'}% |" for m in d["pillar_mix"]]
    L += ["", "| Format | Scripts | Share |", "|---|---|---|"]
    L += [f"| {m['format']} | {m['count']} | {m['share_pct']}% |" for m in d["format_mix"]] or ["| none yet | 0 | 0% |"]
    L += ["", "Pillar targets are starting hypotheses. Change them only after several videos with real numbers; one video is an anecdote."]
    return "\n".join(L) + "\n"


def save(date: str) -> Path:
    out = config.path("reports", "growth", f"{date}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(dashboard(date)), encoding="utf-8")
    return out
