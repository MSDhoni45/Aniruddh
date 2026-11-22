"""Performance learning: what the account's own reels say about hooks, topics and formats.

Only numbers that were actually collected are used (analytics/performance.csv, filled by `creatoros metrics-add` or a
connected analytics source). Every comparison is against the account's own median, and a group with fewer than MIN_N reels
is reported as "not enough data" instead of a lesson. With no data the report says so; nothing is ever estimated.
"""
from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

from .. import config
from . import store

MIN_N = 3
CHECKPOINT_PREFERENCE = ["7d", "72h", "48h", "24h", "2h"]
METRICS = ["views", "avg_retention", "completion_rate", "shares_per_1k_views", "saves_per_1k_views",
           "comments_per_1k_views", "profile_visit_rate", "follows_per_1k_views"]
DIMENSIONS = ["hook_type", "topic", "pillar", "format"]
CONNECTION_NOTE = ("Instagram analytics: NOT CONNECTED. This environment has no authorized Instagram Graph API access, so "
                   "only numbers the creator enters with `creatoros metrics-add` are used.")


def _latest_per_reel(rows: list[dict], platform: str) -> list[dict]:
    """One row per reel: the most mature checkpoint recorded (7d if present)."""
    best: dict[str, dict] = {}
    for r in rows:
        if r.get("platform") != platform or r.get("checkpoint") not in CHECKPOINT_PREFERENCE:
            continue
        cur = best.get(r["video_id"])
        if cur is None or CHECKPOINT_PREFERENCE.index(r["checkpoint"]) < CHECKPOINT_PREFERENCE.index(cur["checkpoint"]):
            best[r["video_id"]] = r
    return list(best.values())


def _median(vals):
    vals = [v for v in vals if v is not None]
    return round(median(vals), 3) if vals else None


def learn(perf_path: Path | None = None, platform: str = "instagram", connected: bool = False) -> dict:
    reels = _latest_per_reel(store.load(perf_path), platform)
    derived = [{**store.derive(r), **{d: r.get(d) for d in DIMENSIONS}} for r in reels]
    out = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "platform": platform,
           "connection": "connected" if connected else CONNECTION_NOTE, "reels_with_data": len(derived),
           "baseline": {m: _median(d[m] for d in derived) for m in METRICS}, "dimensions": {}, "lessons": [],
           "status": "NO DATA" if not derived else ("PROVISIONAL" if len(derived) < 10 else "OK")}
    for dim in DIMENSIONS:
        groups = defaultdict(list)
        for d in derived:
            if d.get(dim):
                groups[d[dim]].append(d)
        rows = []
        for name, ds in groups.items():
            g = {"name": name, "reels": len(ds), "enough_data": len(ds) >= MIN_N}
            for m in ("follows_per_1k_views", "shares_per_1k_views", "saves_per_1k_views", "avg_retention"):
                med, base = _median(d[m] for d in ds), out["baseline"][m]
                g[m] = med
                g[f"{m}_vs_baseline"] = round(med / base, 2) if med is not None and base else None
            rows.append(g)
        rows.sort(key=lambda g: (g["enough_data"], g["follows_per_1k_views_vs_baseline"] or 0), reverse=True)
        out["dimensions"][dim] = rows
        judged = [g for g in rows if g["enough_data"] and g["follows_per_1k_views_vs_baseline"] is not None]
        if len(judged) >= 2:
            out["lessons"].append(f"{dim}: strongest follower conversion '{judged[0]['name']}' "
                                  f"({judged[0]['follows_per_1k_views_vs_baseline']}x the account median); weakest "
                                  f"'{judged[-1]['name']}' ({judged[-1]['follows_per_1k_views_vs_baseline']}x)")
    if not derived:
        out["lessons"].append("No reel performance recorded yet: keep the documented rubric unchanged and record the 24h and "
                              "7d numbers for each reel.")
    elif not out["lessons"]:
        out["lessons"].append(f"Fewer than {MIN_N} reels per group: patterns are not reliable yet; change nothing on one reel.")
    return out


def summary_line(d: dict) -> str:
    """One sentence for a package's learning_applied field."""
    if d["status"] == "NO DATA":
        return ("No Instagram performance data is connected or recorded yet, so today's choice uses the documented v6 rubric "
                "unchanged.")
    return f"{d['reels_with_data']} reels with data ({d['status']}): " + "; ".join(d["lessons"])


def render(d: dict) -> str:
    L = [f"# Performance learning ({d['platform']})", "", f"- {d['connection']}",
         f"- Reels with data: {d['reels_with_data']} ({d['status']})", ""]
    if d["reels_with_data"]:
        L += ["## Account baseline (median)", ""] + [f"- {m}: {v if v is not None else 'UNKNOWN'}" for m, v in d["baseline"].items()]
        for dim, rows in d["dimensions"].items():
            L += ["", f"## By {dim}", "", "| Group | Reels | Enough data | Follows/1k vs median | Shares/1k vs median | Saves/1k vs median |",
                  "|---|---|---|---|---|---|"]
            L += [f"| {g['name']} | {g['reels']} | {'yes' if g['enough_data'] else 'no'} | {g['follows_per_1k_views_vs_baseline']} | "
                  f"{g['shares_per_1k_views_vs_baseline']} | {g['saves_per_1k_views_vs_baseline']} |" for g in rows]
    L += ["", "## Lessons", ""] + [f"- {x}" for x in d["lessons"]]
    return "\n".join(L) + "\n"


def save(perf_path: Path | None = None) -> dict:
    d = learn(perf_path)
    out = config.path("analytics")
    out.mkdir(parents=True, exist_ok=True)
    (out / "learning.json").write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    (out / "learning.md").write_text(render(d), encoding="utf-8")
    return d
