"""Weekly strategy review data: what was covered, what the numbers say, and what is still unknown."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from .. import config
from ..research import content_db
from . import store


def build(end: str, db_path: Path | None = None, perf_path: Path | None = None) -> str:
    e = date.fromisoformat(end)
    start = e - timedelta(days=6)
    items = [x for x in content_db.entries(db_path) if start <= date.fromisoformat(x["date"]) <= e]
    rows = store.load(perf_path)
    L = [f"# Weekly strategy review: {start} to {e}", "", "## Topics covered", ""]
    if not items:
        L.append("Nothing was scripted this week.")
    else:
        L += ["| Date | Topic | Category | Status | Hook |", "|---|---|---|---|---|"]
        L += [f"| {x['date']} | {x['topic']} | {x.get('category', '')} | {x.get('status', '')} | {x.get('hook', '')} |" for x in items]
    vids = {f"{x['date']}_{x['slug']}" for x in items}
    perf = [store.derive(r) | {"row": r} for r in rows if r["video_id"] in vids]
    L += ["", "## Performance", ""]
    if not perf:
        L += ["No analytics have been recorded for this week's videos. Best and weakest content, audience growth and hook",
              "performance are UNKNOWN until real numbers are added with `creatoros metrics-add`."]
    else:
        L += ["| Video | Platform | Checkpoint | Views | Follows /1k | Shares /1k | Saves /1k | Retention |", "|---|---|---|---|---|---|---|---|"]
        for d in sorted(perf, key=lambda d: (d["follows_per_1k_views"] is None, -(d["follows_per_1k_views"] or 0))):
            L.append(f"| {d['video_id']} | {d['platform']} | {d['checkpoint']} | {d['views']} | {d['follows_per_1k_views']} | "
                     f"{d['shares_per_1k_views']} | {d['saves_per_1k_views']} | {d['avg_retention']} |")
        gained = [float(d["row"]["new_followers"]) for d in perf if d["checkpoint"] == "7d" and d["row"].get("new_followers")]
        L += ["", f"Followers gained from videos with 7-day data: {int(sum(gained)) if gained else 'UNKNOWN'}"]
        if len({d['video_id'] for d in perf}) < 3:
            L.append("Fewer than three videos have data: treat any pattern as anecdote, not evidence.")
    from . import growth
    g = growth.dashboard(end, perf_path=perf_path, db_path=db_path)
    L += ["", "## 60-day target", "", f"Day {g['day']} of {g['days_total']} ({g['phase']}). Current followers: {g['current_followers']}; "
          f"remaining: {g['remaining_followers']}; needed per day: {g['daily_net_growth_required']}; trajectory: "
          f"{g['trajectory'] if isinstance(g['trajectory'], str) else g['trajectory']['status']}. "
          f"Observed followers per 1,000 views: {g['conversion']['followers_per_1k_views']}."]
    week_items = [x for x in items if x.get("status") in ("scripted", "published")]
    L += ["", "## Content mix this week", "", "| Pillar | Scripts | Share | Starting target |", "|---|---|---|---|"]
    from ..scripts.package import PILLARS
    L += [f"| {m['pillar']} | {m['count']} | {m['share_pct']}% | {m['target_pct'] if m['target_pct'] is not None else '-'}% |"
          for m in growth.mix(week_items, "pillar", PILLARS) if m["count"] or m["target_pct"]]
    L += ["", "| Format | Scripts |", "|---|---|"] + [f"| {m['format']} | {m['count']} |" for m in growth.mix(week_items, "format")]
    L += ["", "## What the numbers say (7-day data, all videos so far)", ""]
    any_rows = False
    for dim in ("pillar", "format", "hook_type"):
        groups = store.by_dimension(dim, "7d", "instagram", perf_path)
        if not groups:
            continue
        any_rows = True
        L += [f"**By {dim}**", "", "| Group | Videos | Enough data | Follows /1k | Shares /1k | Saves /1k | Retention |", "|---|---|---|---|---|---|---|"]
        L += [f"| {x[dim]} | {x['videos']} | {'yes' if x['enough_data'] else 'no (under 3)'} | {x['median_follows_per_1k']} | "
              f"{x['median_shares_per_1k']} | {x['median_saves_per_1k']} | {x['median_retention']} |" for x in groups] + [""]
    if not any_rows:
        L.append("No 7-day Instagram data yet: no pattern can be claimed. Recommendations must wait for real numbers.")
    L += ["", "## Notes for the reviewer", "",
          "- Do not change the strategy on one unusually good or bad video; groups under three videos are anecdotes.",
          "- Rank content by follows, shares and saves per 1,000 views before raw views.",
          "- Name the evidence behind every recommendation. Correlation in a handful of videos is not causation.",
          "- Change one variable at a time."]
    return "\n".join(L) + "\n"


def save(end: str) -> Path:
    out = config.path("reports", "weekly", f"{end}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(end), encoding="utf-8")
    return out
