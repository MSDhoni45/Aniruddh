"""Claim verification table and the recording-readiness gate.

Every factual claim in a package records: exact claim, primary source, supporting source, verification status,
source publication date, confidence and how the primary source was reached. A package is RECORDING READY only if
every claim the script relies on is resolved; otherwise it is HOLD — NOT RECORDING READY.
"""
from __future__ import annotations

from .claims import NEEDS_ATTRIBUTION, NOT_USABLE, STATUSES

CONFIDENCE = ["HIGH", "MEDIUM", "LOW"]
# How the primary source was reached. "opened" = the page itself was read. "search-index" = the primary domain's own
# indexed text was read through search, page not opened. "secondary-only" = only other outlets repeat it.
ACCESS = ["opened", "search-index", "secondary-only", "not found"]
FIELDS = ["id", "text", "status", "primary_source", "supporting_source", "source_date", "confidence", "access", "in_script"]
READY, HOLD = "RECORDING READY", "HOLD — NOT RECORDING READY"


def check_claim(c: dict) -> list[str]:
    cid = c.get("id", "?")
    p = [f"{cid}: missing {f}" for f in FIELDS if f not in c]
    if p:
        return p
    if c["status"] not in STATUSES:
        p.append(f"{cid}: status must be one of {STATUSES}")
    if c["confidence"] not in CONFIDENCE:
        p.append(f"{cid}: confidence must be one of {CONFIDENCE}")
    if c["access"] not in ACCESS:
        p.append(f"{cid}: access must be one of {ACCESS}")
    for k in ("primary_source", "supporting_source"):
        v = c.get(k)
        if v is not None and not str(v).startswith("http"):
            p.append(f"{cid}: {k} must be a URL or null (never a description)")
    if c["confidence"] == "HIGH":
        if not c.get("primary_source") or c["access"] in ("secondary-only", "not found"):
            p.append(f"{cid}: HIGH confidence needs a primary source reached directly or through its own indexed text; "
                     "repetition by secondary outlets is MEDIUM at most")
        if not c.get("supporting_source"):
            p.append(f"{cid}: HIGH confidence needs an independent supporting source")
    if c.get("quote") and c["confidence"] == "HIGH" and not c.get("wording_verified"):
        p.append(f"{cid}: a quotation can only be HIGH once its exact wording is verified against the primary source")
    if c["status"] in NEEDS_ATTRIBUTION and not c.get("attribution"):
        p.append(f"{cid}: {c['status']} needs an attribution")
    return p


def readiness(claims: list[dict], script: str, unresolved: list[str]) -> dict:
    """Decide READY or HOLD. Problems are structural errors; reasons are what keeps the script from recording."""
    problems, reasons = [], []
    low = script.lower()
    for c in claims:
        problems += check_claim(c)
    if problems:
        return {"status": HOLD, "problems": problems, "reasons": ["claim table incomplete"]}
    for c in claims:
        if not c["in_script"]:
            continue
        cid = c["id"]
        if c["status"] in NOT_USABLE:
            reasons.append(f"{cid} is {c['status']} but used in the script")
        if c["confidence"] != "HIGH" and c.get("central", True):
            reasons.append(f"{cid} is central to the script but only {c['confidence']} confidence: {c['text']}")
        if c["confidence"] == "LOW":
            reasons.append(f"{cid} is LOW confidence")
        if not c.get("primary_source") and c.get("central", True):
            reasons.append(f"{cid} has no primary source")
        if c["status"] in NEEDS_ATTRIBUTION:
            phrase = c.get("script_attribution")
            if not phrase or phrase.lower() not in low:
                reasons.append(f"{cid} is a {c['status']} but the script does not attribute it (script_attribution)")
        if c.get("quote") and not c.get("wording_verified"):
            reasons.append(f"{cid} quotes a statement whose exact wording is not verified")
    reasons += [f"unresolved: {u}" for u in unresolved]
    return {"status": READY if not reasons else HOLD, "problems": [], "reasons": reasons}


def story_confidence_ok(story_conf: str, claims: list[dict]) -> list[str]:
    used = [c for c in claims if c.get("in_script")]
    if story_conf == "HIGH" and any(c.get("confidence") != "HIGH" for c in used):
        return ["evidence_confidence cannot be HIGH while any claim in the script is below HIGH"]
    return []


def table(claims: list[dict]) -> str:
    def link(u):
        return f"[link]({u})" if u else "NONE FOUND"
    rows = ["| # | Exact claim | Primary source | Supporting source | Status | Source date | Confidence | In script |",
            "|---|---|---|---|---|---|---|---|"]
    for c in claims:
        prim = link(c.get("primary_source")) + (f" ({c['access']})" if c.get("primary_source") else "")
        rows.append(f"| {c['id']} | {c['text']} | {prim} | {link(c.get('supporting_source'))} | {c['status']} | "
                    f"{c.get('source_date') or 'UNKNOWN'} | {c['confidence']} | {'yes' if c['in_script'] else 'no'} |")
    notes = [f"- **{c['id']}:** {c['note']}" for c in claims if c.get("note")]
    return "\n".join(rows) + ("\n\n" + "\n".join(notes) if notes else "") + "\n"
