"""Persistent research memory beyond the content database:
research/topics_db.jsonl  every candidate ever researched (selected, eligible, held, rejected, covered) with its score
research/claims_db.jsonl  every fact-checked claim with source, evidence, status and confidence
Records are upserted, so re-rendering a package never duplicates them."""
from __future__ import annotations

import json
from pathlib import Path

from .. import config

TOPICS, CLAIMS = "research/topics_db.jsonl", "research/claims_db.jsonl"


def _load(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def _upsert(p: Path, rows: list[dict], key) -> None:
    existing = {key(r): r for r in _load(p)}
    for r in rows:
        existing[key(r)] = r
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in existing.values()), encoding="utf-8")
    tmp.replace(p)


def record(pkg: dict, ranked: list[dict], topics_path: Path | None = None, claims_path: Path | None = None) -> None:
    day = pkg["date"]
    topics = []
    for c in ranked:
        state = ("selected" if c["headline"] == pkg["topic"] and c["eligible"] else "rejected" if c.get("rejected")
                 else "covered" if c.get("already_covered") else "held" if c.get("hold_reason") else
                 "eligible" if c["eligible"] else "ineligible")
        topics.append({"date": day, "headline": c["headline"], "category": c.get("category"), "topic_type": c.get("topic_type"),
                       "source": c.get("original_source"), "published": c.get("announced_at"),
                       "main_claim": c.get("main_claim") or c.get("what_happened"), "verification_status": c.get("verification_status"),
                       "evidence_confidence": c.get("evidence_confidence"), "score": c["trend_score"], "scoring": "v2" if "curiosity" in c["scores"] else "v1",
                       "state": state, "reason": c.get("ineligible_reason"), "package_slug": pkg["slug"] if state == "selected" else None})
    _upsert(topics_path or config.path(TOPICS), topics, lambda r: (r["date"], r["headline"]))
    claims = [{"date": day, "slug": pkg["slug"], **c} for c in pkg["factcheck"]["claims"]]
    _upsert(claims_path or config.path(CLAIMS), claims, lambda r: (r["date"], r["slug"], r["id"]))


def topics(path: Path | None = None) -> list[dict]:
    return _load(path or config.path(TOPICS))


def claims(path: Path | None = None) -> list[dict]:
    return _load(path or config.path(CLAIMS))
