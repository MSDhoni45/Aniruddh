"""Append-only log of stories already used, to stop repeats without a material new development."""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from .. import config

LOG = "research/story_log.jsonl"
_STOP = set("the a an of in on for to and is are was with by from at as its it this that says say new ai".split())


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-.]+", text.lower()) if w not in _STOP}


def entries(path: Path | None = None) -> list[dict]:
    p = path or config.path(LOG)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def find_repeat(headline: str, keys: list[str], today: str, days: int = 45, path: Path | None = None) -> dict | None:
    """A repeat shares an identifier (CVE, product name, event key) or most headline words with a recent story."""
    cutoff = date.fromisoformat(today) - timedelta(days=days)
    hk, ht = {k.lower() for k in keys}, _tokens(headline)
    for e in entries(path):
        if date.fromisoformat(e["date"]) < cutoff:
            continue
        et = _tokens(e["headline"])
        jac = len(ht & et) / max(len(ht | et), 1)
        if hk & {k.lower() for k in e.get("keys", [])} or jac >= 0.6:
            return e
    return None


def add(day: str, headline: str, keys: list[str], slug: str, material_update_of: str | None = None, path: Path | None = None) -> dict:
    p = path or config.path(LOG)
    if any(e["date"] == day and e["slug"] == slug for e in entries(p)):
        return {"date": day, "slug": slug, "duplicate": True}
    prior = find_repeat(headline, keys, day, path=p)
    if prior and not material_update_of:
        raise ValueError(f"repeat of {prior['date']} '{prior['headline']}'. Pass material_update_of with the new development to proceed.")
    rec = {"date": day, "slug": slug, "headline": headline, "keys": keys, "material_update_of": material_update_of}
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec
