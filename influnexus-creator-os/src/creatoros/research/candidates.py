"""Candidate topic records, the 100-point viral potential score and ranking rules."""
from __future__ import annotations

WEIGHTS = {"traction": 25, "surprise": 20, "relevance": 20, "practical": 15, "visual": 10, "credibility": 10}   # v1 (before 19 Nov 2026)
# v2 (current): editorial scores, not predictions of views. Each criterion is scored 0-10 and weighted.
WEIGHTS_V2 = {"curiosity": 20, "storytelling": 20, "shareability": 15, "global_relevance": 15, "freshness": 10, "visual": 10,
              "originality": 10}
REQUIRED_V2 = ["headline", "category", "topic_type", "announced_at", "original_source", "main_claim", "verification_status",
               "why_it_matters", "potential_hook", "target_audience", "uncertainty", "evidence_confidence", "already_covered", "scores"]
VERIFICATION = ["VERIFIED", "PARTLY VERIFIED", "UNVERIFIED", "REJECTED"]
REQUIRED = ["headline", "category", "topic_type", "announced_at", "original_source", "supporting_sources", "what_happened",
            "why_it_matters", "target_audience", "discussion_signals", "competing_coverage", "uncertainty", "novelty",
            "evidence_confidence", "already_covered", "scores", "secondary"]
CATEGORIES = ["AI", "CONSUMER TECH", "FUTURE TECH", "AI BUSINESS & STARTUPS", "CREATOR TECH", "CONTROVERSY", "TECH COMPANIES",
              "FOUNDERS & CEOS", "STARTUPS", "EMERGING TECH", "SCIENCE"]
TOPIC_TYPES = ["BREAKING", "EMERGING", "EVERGREEN", "EXPERIMENTAL"]
CONFIDENCE = ["HIGH", "MEDIUM", "LOW"]
SECONDARY = ["shareability", "comment_potential", "follower_conversion", "saturation", "freshness", "brand_alignment"]
UNKNOWN = "UNKNOWN"


def scheme(c: dict) -> str:
    return "v2" if "curiosity" in c.get("scores", {}) else "v1"


def weights(c: dict) -> dict:
    return WEIGHTS_V2 if scheme(c) == "v2" else WEIGHTS


def validate(c: dict) -> list[str]:
    if scheme(c) == "v2":
        return validate_v2(c)
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
    if c.get("category") not in CATEGORIES:
        problems.append(f"category must be one of {CATEGORIES}")
    if c.get("topic_type") not in TOPIC_TYPES:
        problems.append(f"topic_type must be one of {TOPIC_TYPES}")
    if c.get("evidence_confidence") not in CONFIDENCE:
        problems.append(f"evidence_confidence must be one of {CONFIDENCE}")
    sec = c.get("secondary", {})
    if not isinstance(sec, dict):
        sec = {}
    for k in SECONDARY:
        if sec.get(k) not in CONFIDENCE + [UNKNOWN]:
            problems.append(f"secondary.{k} must be HIGH, MEDIUM, LOW or UNKNOWN")
    if c.get("topic_type") == "BREAKING" and c.get("outside_window"):
        problems.append("a story outside the 24-hour window cannot be labelled BREAKING")
    return problems


def validate_v2(c: dict) -> list[str]:
    problems = [f"missing field: {f}" for f in REQUIRED_V2 if f not in c]
    for k in WEIGHTS_V2:
        v = c.get("scores", {}).get(k)
        if v != UNKNOWN and not (isinstance(v, (int, float)) and 0 <= v <= 10):
            problems.append(f"score {k} must be 0-10 or UNKNOWN")
    if c.get("category") not in CATEGORIES:
        problems.append(f"category must be one of {CATEGORIES}")
    if c.get("topic_type") not in TOPIC_TYPES:
        problems.append(f"topic_type must be one of {TOPIC_TYPES}")
    if c.get("evidence_confidence") not in CONFIDENCE:
        problems.append(f"evidence_confidence must be one of {CONFIDENCE}")
    if c.get("verification_status") not in VERIFICATION:
        problems.append(f"verification_status must be one of {VERIFICATION}")
    if c.get("original_source") and not str(c["original_source"]).startswith("http"):
        problems.append("original_source must be a URL")
    if c.get("topic_type") == "BREAKING" and c.get("outside_window"):
        problems.append("a story outside the 24-hour window cannot be labelled BREAKING")
    if isinstance(c.get("engagement"), dict):
        for k, v in c["engagement"].items():
            if v != UNKNOWN and not isinstance(v, (int, float)):
                problems.append(f"engagement.{k} must be a number that was observed, or UNKNOWN")
    return problems


def trend_score(c: dict) -> dict:
    """Weighted total. An UNKNOWN criterion scores zero and is listed, so missing data never inflates a story."""
    total, unknown = 0.0, []
    for k, w in weights(c).items():
        v = c["scores"].get(k, UNKNOWN)
        if v == UNKNOWN:
            unknown.append(k)
            continue
        total += w * float(v) / 10
    return {"total": round(total, 1), "unknown": unknown}


def ineligible_reason(c: dict) -> str | None:
    if c.get("rejected"):
        return f"rejected: {c['rejected']}"
    if c.get("already_covered"):
        return "already covered"
    if c.get("outside_window"):
        return "outside the 24-hour window (72 hours for EMERGING stories) with no new development"
    if c.get("hold_reason"):
        return f"on hold: {c['hold_reason']}"
    if c.get("evidence_confidence") == "LOW":
        return "evidence confidence LOW"
    if c.get("verification_status") in ("UNVERIFIED", "REJECTED"):
        return f"verification status {c['verification_status']}"
    cred = c["scores"].get("credibility")
    if isinstance(cred, (int, float)) and cred < 5:
        return "credibility below 5/10"
    return None


def rank(cands: list[dict]) -> list[dict]:
    """Eligible stories first, by score. Low-confidence or low-credibility stories can never outrank a verified one."""
    out = []
    for c in cands:
        s = trend_score(c)
        reason = ineligible_reason(c)
        out.append({**c, "trend_score": s["total"], "unknown_criteria": s["unknown"], "problems": validate(c),
                    "eligible": reason is None, "ineligible_reason": reason})
    return sorted(out, key=lambda c: (c["eligible"], c["trend_score"]), reverse=True)
