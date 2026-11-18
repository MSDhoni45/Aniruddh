"""Candidate story records and the 100-point trend score."""
from __future__ import annotations

WEIGHTS = {"traction": 25, "surprise": 20, "relevance": 20, "practical": 15, "visual": 10, "credibility": 10}
REQUIRED = ["headline", "original_source", "published_at", "first_discussed_at", "primary_x_post", "independent_discussion",
            "engagement", "geo_relevance", "audience_relevance", "visual_availability", "practical_value", "credibility_note",
            "uncertainty", "already_covered", "scores"]
UNKNOWN = "UNKNOWN"


def validate(c: dict) -> list[str]:
    problems = [f"missing field: {f}" for f in REQUIRED if f not in c]
    scores = c.get("scores", {})
    for k in WEIGHTS:
        v = scores.get(k)
        if v != UNKNOWN and not (isinstance(v, (int, float)) and 0 <= v <= 10):
            problems.append(f"score {k} must be 0-10 or UNKNOWN")
    t = scores.get("traction")
    if isinstance(t, (int, float)) and t > 5 and not c.get("traction_evidence"):
        problems.append("traction above 5 needs traction_evidence (what was actually observed); fame alone does not count")
    if isinstance(c.get("engagement"), dict):
        for k, v in c["engagement"].items():
            if v != UNKNOWN and not isinstance(v, (int, float)):
                problems.append(f"engagement.{k} must be a number that was observed, or UNKNOWN")
    return problems


def trend_score(c: dict) -> dict:
    """Weighted total. An UNKNOWN criterion scores zero and is listed, so missing data never inflates a story."""
    total, unknown = 0.0, []
    for k, w in WEIGHTS.items():
        v = c["scores"].get(k, UNKNOWN)
        if v == UNKNOWN:
            unknown.append(k)
            continue
        total += w * float(v) / 10
    return {"total": round(total, 1), "unknown": unknown}


def rank(cands: list[dict]) -> list[dict]:
    out = []
    for c in cands:
        s = trend_score(c)
        out.append({**c, "trend_score": s["total"], "unknown_criteria": s["unknown"], "problems": validate(c)})
    eligible = [c for c in out if not c.get("already_covered") and not c.get("outside_window")]
    for c in out:
        c["eligible"] = c in eligible
    return sorted(out, key=lambda c: (c["eligible"], c["trend_score"]), reverse=True)
