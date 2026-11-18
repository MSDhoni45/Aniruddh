"""Performance storage and derived growth metrics. Only numbers that were actually collected are stored."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import median

from .. import config

FIELDS = ["date", "video_id", "platform", "checkpoint", "views", "reach", "watch_time_s", "avg_view_duration_s",
          "completion_rate", "shares", "saves", "comments", "likes", "profile_visits", "new_followers",
          "business_inquiries", "topic", "hook_type", "language", "format", "duration_s", "source", "collected_at",
          "viewed_rate", "top_countries"]
# viewed_rate: Instagram's "viewed vs swiped away" share (0-1). top_countries: as reported, e.g. "IN 41%; US 12%".
NUMERIC = FIELDS[4:16] + ["duration_s", "viewed_rate"]
CHECKPOINTS = ["24h", "72h", "7d"]
CSV = "analytics/performance.csv"


def _path(p: Path | None = None) -> Path:
    return p or config.path(CSV)


def load(p: Path | None = None) -> list[dict]:
    p = _path(p)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def upsert(row: dict, p: Path | None = None) -> dict:
    """Insert or replace the row for (video_id, platform, checkpoint). Blank means not collected."""
    p = _path(p)
    if row.get("checkpoint") not in CHECKPOINTS:
        raise ValueError(f"checkpoint must be one of {CHECKPOINTS}")
    for k in NUMERIC:
        v = row.get(k, "")
        if v not in ("", None):
            float(v)                       # raises on non-numeric input
            if float(v) < 0:
                raise ValueError(f"{k} cannot be negative")
    unknown = set(row) - set(FIELDS)
    if unknown:
        raise ValueError(f"unknown fields: {sorted(unknown)}")
    rows = [r for r in load(p) if (r["video_id"], r["platform"], r["checkpoint"]) != (row["video_id"], row["platform"], row["checkpoint"])]
    rows.append({k: "" if row.get(k) is None else row.get(k, "") for k in FIELDS})
    rows.sort(key=lambda r: (r["date"], r["video_id"], r["platform"], CHECKPOINTS.index(r["checkpoint"])))
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return derive(rows[-1] if rows[-1]["video_id"] == row["video_id"] else row)


def _f(r, k):
    try:
        return float(r[k])
    except (KeyError, ValueError, TypeError):
        return None


def derive(r: dict) -> dict:
    views = _f(r, "views")

    def per_k(k):
        v = _f(r, k)
        return round(v / views * 1000, 2) if v is not None and views else None

    dur, avd = _f(r, "duration_s"), _f(r, "avg_view_duration_s")
    return {"video_id": r["video_id"], "platform": r["platform"], "checkpoint": r["checkpoint"], "views": views,
            "follows_per_1k_views": per_k("new_followers"), "shares_per_1k_views": per_k("shares"),
            "saves_per_1k_views": per_k("saves"), "comments_per_1k_views": per_k("comments"),
            "likes_per_1k_views": per_k("likes"),
            "avg_retention": round(avd / dur, 3) if avd is not None and dur else None,
            "completion_rate": _f(r, "completion_rate"), "viewed_rate": _f(r, "viewed_rate"),
            "top_countries": r.get("top_countries") or None}


def by_dimension(dim: str, checkpoint: str = "7d", platform: str = "instagram", p: Path | None = None, min_n: int = 3) -> list[dict]:
    """Median outcomes per topic / hook_type / language / format. Groups under min_n are marked as too small to judge."""
    groups = defaultdict(list)
    for r in load(p):
        if r["checkpoint"] == checkpoint and r["platform"] == platform and r.get(dim):
            groups[r[dim]].append(derive(r))
    out = []
    for name, ds in groups.items():
        def med(k):
            vals = [d[k] for d in ds if d[k] is not None]
            return round(median(vals), 2) if vals else None
        out.append({dim: name, "videos": len(ds), "enough_data": len(ds) >= min_n, "median_views": med("views"),
                    "median_follows_per_1k": med("follows_per_1k_views"), "median_shares_per_1k": med("shares_per_1k_views"),
                    "median_saves_per_1k": med("saves_per_1k_views"), "median_retention": med("avg_retention")})
    return sorted(out, key=lambda g: (g["median_follows_per_1k"] is not None, g["median_follows_per_1k"] or 0), reverse=True)


def due_checkpoints(now_iso: str, published: list[dict], p: Path | None = None) -> list[dict]:
    """Which (video, platform, checkpoint) measurements are due but not yet stored."""
    from datetime import datetime, timedelta
    now = datetime.fromisoformat(now_iso)
    have = {(r["video_id"], r["platform"], r["checkpoint"]) for r in load(p)}
    hours = {"24h": 24, "72h": 72, "7d": 168}
    due = []
    for v in published:
        t0 = datetime.fromisoformat(v["published_at"])
        for cp, h in hours.items():
            if now >= t0 + timedelta(hours=h) and (v["video_id"], v["platform"], cp) not in have:
                due.append({"video_id": v["video_id"], "platform": v["platform"], "checkpoint": cp})
    return due


def review(p: Path | None = None, platform: str = "instagram") -> str:
    """Markdown review for the learning log. Called after every 10 videos."""
    rows = [r for r in load(p) if r["platform"] == platform and r["checkpoint"] == "7d"]
    lines = [f"## Review after {len(rows)} videos with 7-day data ({platform})", ""]
    if len(rows) < 10:
        lines.append(f"Only {len(rows)} videos have 7-day data. Patterns below are provisional; change nothing on the basis of one video.")
    for dim in ("topic", "hook_type", "language", "format"):
        lines += ["", f"### By {dim}", "", f"| {dim} | Videos | Enough data | Median views | Follows /1k | Shares /1k | Saves /1k | Retention |", "|---|---|---|---|---|---|---|---|"]
        for g in by_dimension(dim, "7d", platform, p):
            lines.append(f"| {g[dim]} | {g['videos']} | {'yes' if g['enough_data'] else 'no'} | {g['median_views']} | {g['median_follows_per_1k']} | {g['median_shares_per_1k']} | {g['median_saves_per_1k']} | {g['median_retention']} |")
    return "\n".join(lines) + "\n"
