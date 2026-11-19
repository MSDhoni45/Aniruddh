"""Candidate topic records, the 100-point viral potential score and ranking rules."""
from __future__ import annotations

WEIGHTS = {"traction": 25, "surprise": 20, "relevance": 20, "practical": 15, "visual": 10, "credibility": 10}   # v1 (before 19 Nov 2026)
# v2 (current): editorial scores, not predictions of views. Each criterion is scored 0-10 and weighted.
WEIGHTS_V2 = {"curiosity": 20, "storytelling": 20, "shareability": 15, "global_relevance": 15, "freshness": 10, "visual": 10,
              "originality": 10}
REQUIRED_V2 = ["headline", "category", "topic_type", "announced_at", "original_source", "main_claim", "verification_status",
               "why_it_matters", "potential_hook", "target_audience", "uncertainty", "evidence_confidence", "already_covered", "scores"]
VERIFICATION = ["VERIFIED", "PARTLY VERIFIED", "UNVERIFIED", "REJECTED"]
# v3 (from 20 Nov 2026): public discussion counts, but only with evidence. Editorial judgements, not view predictions.
WEIGHTS_V3 = {"public_discussion": 20, "surprise": 15, "significance": 15, "usefulness": 15, "visual": 10,
              "broad_appeal": 10, "discussion_potential": 5, "longevity": 5, "verification_confidence": 5}
REQUIRED_V3 = ["headline", "category", "topic_type", "published_at", "original_source", "main_claim", "verification_status",
               "why_it_matters", "potential_hook", "target_audience", "uncertainty", "evidence_confidence", "already_covered",
               "scores", "x_signal"]
X_STATUS = ["VERIFIED", "PARTLY VERIFIED", "NOT VERIFIED"]
X_METRICS = ["likes", "reposts", "replies", "quotes", "views"]
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
    sc = c.get("scores", {})
    return "v3" if "public_discussion" in sc else ("v2" if "curiosity" in sc else "v1")


def weights(c: dict) -> dict:
    return {"v3": WEIGHTS_V3, "v2": WEIGHTS_V2}.get(scheme(c), WEIGHTS)


def validate(c: dict) -> list[str]:
    if scheme(c) == "v3":
        return validate_v3(c)
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


def _iso(v) -> "dt.datetime | None":
    import datetime as dt
    try:
        d = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else None


def x_signal_problems(x) -> list[str]:
    """X evidence: every metric is an observed number or UNKNOWN; the status must match what was actually seen."""
    if not isinstance(x, dict):
        return ["x_signal must be an object with status, posts and discussion_evidence"]
    problems = []
    if x.get("status") not in X_STATUS:
        problems.append(f"x_signal.status must be one of {X_STATUS}")
    posts = x.get("posts", [])
    for i, post in enumerate(posts):
        for f in ("url", "account", "posted_at", "retrieved_at", "access"):
            if not post.get(f):
                problems.append(f"x_signal.posts[{i}] needs {f}")
        if post.get("url") and not str(post["url"]).startswith("http"):
            problems.append(f"x_signal.posts[{i}].url must be a URL")
        if post.get("access") not in (None, "opened", "search-index", "secondary-only"):
            problems.append(f"x_signal.posts[{i}].access must be opened, search-index or secondary-only")
        for k, v in (post.get("metrics") or {}).items():
            if v != UNKNOWN and not isinstance(v, (int, float)):
                problems.append(f"x_signal.posts[{i}].metrics.{k} must be an observed number or UNKNOWN")
    observed = [p for p in posts if p.get("access") == "opened"
                and any(isinstance(v, (int, float)) for v in (p.get("metrics") or {}).values())]
    if x.get("status") == "VERIFIED" and not observed:
        problems.append("x_signal VERIFIED needs at least one post opened directly with observed metrics")
    if x.get("status") == "PARTLY VERIFIED" and not posts:
        problems.append("x_signal PARTLY VERIFIED needs at least one post URL")
    return problems


def validate_v3(c: dict) -> list[str]:
    problems = [f"missing field: {f}" for f in REQUIRED_V3 if f not in c]
    for k in WEIGHTS_V3:
        v = c.get("scores", {}).get(k)
        if v != UNKNOWN and not (isinstance(v, (int, float)) and 0 <= v <= 10):
            problems.append(f"score {k} must be 0-10 or UNKNOWN")
    for f, allowed in (("category", CATEGORIES), ("topic_type", TOPIC_TYPES), ("evidence_confidence", CONFIDENCE),
                       ("verification_status", VERIFICATION)):
        if c.get(f) not in allowed:
            problems.append(f"{f} must be one of {allowed}")
    if c.get("original_source") and not str(c["original_source"]).startswith("http"):
        problems.append("original_source must be a URL")
    if "published_at" in c and _iso(c["published_at"]) is None:
        problems.append("published_at must be an ISO timestamp with a timezone (e.g. 2026-11-19T14:05:00+00:00)")
    x = c.get("x_signal")
    problems += x_signal_problems(x) if "x_signal" in c else []
    pd_ = c.get("scores", {}).get("public_discussion")
    xs = x.get("status") if isinstance(x, dict) else None
    evidence = (x or {}).get("discussion_evidence") if isinstance(x, dict) else None
    if isinstance(pd_, (int, float)):
        if pd_ > 3 and xs == "NOT VERIFIED" and not evidence:
            problems.append("public_discussion above 3 needs X posts or other discussion_evidence; fame alone does not count")
        if pd_ > 7 and xs != "VERIFIED":
            problems.append("public_discussion above 7 needs a VERIFIED x_signal (posts opened, metrics observed)")
    return problems


def window_reason(c: dict, window: dict | None) -> str | None:
    """v3 freshness rule: published inside the 24-hour research window, or a dated new development inside it."""
    if not window or scheme(c) != "v3":
        return None
    start, end = _iso(window.get("start_utc")), _iso(window.get("end_utc"))
    pub = _iso(c.get("published_at"))
    if not (start and end and pub):
        return None
    if pub > end:
        return "published after the research window ended"
    if pub >= start:
        return None
    nd = c.get("new_development") or {}
    at = _iso(nd.get("at"))
    if nd.get("what") and at and start <= at <= end:
        return None
    return "published before the 24-hour research window with no dated new development inside it"


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


def rank(cands: list[dict], window: dict | None = None) -> list[dict]:
    """Eligible stories first, by score. Low-confidence or low-credibility stories can never outrank a verified one."""
    out = []
    for c in cands:
        s = trend_score(c)
        reason = ineligible_reason(c) or window_reason(c, window)
        out.append({**c, "trend_score": s["total"], "unknown_criteria": s["unknown"], "problems": validate(c),
                    "eligible": reason is None, "ineligible_reason": reason})
    return sorted(out, key=lambda c: (c["eligible"], c["trend_score"]), reverse=True)
