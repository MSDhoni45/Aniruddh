"""Searchable content memory: every topic scripted, its hook, script, sources, publishing status, results and lessons.

One JSON object per line in research/content_db.jsonl. Records are updated in place by (date, slug).
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from .. import config

DB = "research/content_db.jsonl"
STATUSES = ["scripted", "held", "recorded", "published", "dropped", "superseded"]
_STOP = set("the a an of in on for to and is are was with by from at as its it this that says say new ai".split())


def _path(p: Path | None) -> Path:
    return p or config.path(DB)


def entries(path: Path | None = None) -> list[dict]:
    p = _path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def _save(rows: list[dict], path: Path | None) -> None:
    p = _path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    tmp.replace(p)


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-.]+", text.lower()) if w not in _STOP}


def find_repeat(topic: str, keys: list[str], today: str, days: int = 45, path: Path | None = None,
                ignore_slug: str | None = None) -> dict | None:
    """A repeat shares an identifier (CVE, product, case, event key) or most topic words with a recent entry.
    Dropped and held entries never count (a held story may return once verified); superseded ones do."""
    cutoff = date.fromisoformat(today) - timedelta(days=days)
    hk, ht = {k.lower() for k in keys}, _tokens(topic)
    for e in entries(path):
        if e.get("status") in ("dropped", "held") or e.get("slug") == ignore_slug or date.fromisoformat(e["date"]) < cutoff:
            continue
        et = _tokens(e["topic"])
        jac = len(ht & et) / max(len(ht | et), 1)
        if hk & {k.lower() for k in e.get("keys", [])} or jac >= 0.6:
            return e
    return None


def add(day: str, topic: str, keys: list[str], slug: str, *, category: str = "", sources: list[str] | None = None,
        hook: str = "", script: str = "", material_update_of: str | None = None, path: Path | None = None) -> dict:
    rows = entries(path)
    if any(r["date"] == day and r["slug"] == slug for r in rows):
        return {"date": day, "slug": slug, "duplicate": True}
    prior = find_repeat(topic, keys, day, path=path)
    if prior and not material_update_of:
        raise ValueError(f"repeat of {prior['date']} '{prior['topic']}'. Pass material_update_of naming the new development.")
    rec = {"date": day, "slug": slug, "topic": topic, "category": category, "keys": keys, "sources": sources or [],
           "hook": hook, "script": script, "status": "scripted", "platforms": [], "metrics": {}, "audience_response": "",
           "lessons": "", "material_update_of": material_update_of}
    _save(rows + [rec], path)
    return rec


def update(day: str, slug: str, path: Path | None = None, **fields) -> dict:
    """Change status, platforms, metrics summary, audience response or lessons."""
    if "status" in fields and fields["status"] not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    rows = entries(path)
    for r in rows:
        if r["date"] == day and r["slug"] == slug:
            for k, v in fields.items():
                if k == "platforms":
                    r["platforms"] = sorted(set(r.get("platforms", [])) | set(v))
                elif k == "metrics":
                    r.setdefault("metrics", {}).update(v)
                else:
                    r[k] = v
            _save(rows, path)
            return r
    raise KeyError(f"no content entry {day}/{slug}")


def search(query: str = "", path: Path | None = None, **filters) -> list[dict]:
    q = query.lower()
    out = []
    for e in entries(path):
        hay = " ".join([e["topic"], e.get("hook", ""), e.get("script", ""), e.get("category", ""), " ".join(e.get("keys", []))]).lower()
        if q and q not in hay:
            continue
        if any(str(e.get(k, "")).lower() != str(v).lower() for k, v in filters.items() if v):
            continue
        out.append(e)
    return out
