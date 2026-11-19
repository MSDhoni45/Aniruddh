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


FIELDS_V2 = FIELDS + ["source_title", "supporting_evidence"]


def check_claim(c: dict, v2: bool = False) -> list[str]:
    cid = c.get("id", "?")
    need = FIELDS_V2 if v2 and c.get("in_script") else FIELDS
    p = [f"{cid}: missing {f}" for f in need if f not in c]
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


def check_claim_v5(c: dict) -> list[str]:
    """v5 claims: the level is computed from the evidence list (factcheck/evidence.py), never self-declared."""
    from . import evidence as ev
    cid = c.get("id", "?")
    p = [f"{cid}: missing {f}" for f in ("id", "text", "status", "evidence", "in_script") if f not in c]
    if p:
        return p
    if c["status"] not in STATUSES:
        p.append(f"{cid}: status must be one of {STATUSES}")
    if c.get("risk") not in ev.RISKS + [None]:
        p.append(f"{cid}: risk, if declared, must be 'high' (time-sensitive) or 'low' (historical)")
    for i, it in enumerate(c["evidence"]):
        p += [f"{cid}: {x}" for x in ev.item_problems(it, i)]
    if c["status"] in NEEDS_ATTRIBUTION and not c.get("attribution"):
        p.append(f"{cid}: {c['status']} needs an attribution")
    return p


def readiness_v5(claims: list[dict], script: str, unresolved: list[str], package_date: str) -> dict:
    from . import evidence as ev
    problems = [x for c in claims for x in check_claim_v5(c)]
    if problems:
        return {"status": HOLD, "problems": problems, "reasons": ["claim table incomplete"]}
    low, reasons = script.lower(), []
    for c in claims:
        c["level"] = ev.level(c)["level"]
        rk = ev.effective_risk(c, package_date)
        c["risk_effective"], c["risk_why"] = rk["risk"], rk["why"]
        if not c["in_script"]:
            continue
        if c["status"] in NOT_USABLE:
            reasons.append(f"{c['id']} is {c['status']} but used in the script")
        reasons += ev.gate(c, package_date)
        if c["status"] in NEEDS_ATTRIBUTION:
            phrase = c.get("script_attribution")
            if not phrase or phrase.lower() not in low:
                reasons.append(f"{c['id']} is a {c['status']} but the script does not attribute it (script_attribution)")
        if c.get("quote") and not c.get("wording_verified"):
            reasons.append(f"{c['id']} quotes a statement whose exact wording is not verified")
    reasons += [f"unresolved: {u}" for u in unresolved]
    return {"status": READY if not reasons else HOLD, "problems": [], "reasons": reasons}


def readiness(claims: list[dict], script: str, unresolved: list[str], v2: bool = False) -> dict:
    """Decide READY or HOLD. Problems are structural errors; reasons are what keeps the script from recording.
    v2 packages also require, for every script claim, the source title and the exact supporting evidence text."""
    problems, reasons = [], []
    low = script.lower()
    for c in claims:
        problems += check_claim(c, v2)
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


ACCESS_LABEL = {"opened": "page opened and read directly",
                "search-index": "verified from search-index excerpts of the primary site; page NOT opened directly",
                "secondary-only": "secondary sources only; primary not reached",
                "not found": "primary source not found"}


def is_tiered(claims: list[dict]) -> bool:
    return any(isinstance(c.get("evidence"), list) and c["evidence"] and isinstance(c["evidence"][0], dict) for c in claims)


def level_summary(claims: list[dict]) -> str:
    """Tiered policy: evidence level per script claim, and how many sources were opened directly."""
    from . import evidence as ev
    used = [c for c in claims if c.get("in_script")]
    if not used:
        return ""
    counts: dict[str, int] = {}
    for c in used:
        lv = ev.level(c)["level"]
        counts[lv] = counts.get(lv, 0) + 1
    opened = sum(1 for c in used if any(it.get("access") == "opened" for it in c.get("evidence") or []))
    order = [lv for lv in reversed(ev.LEVELS) if lv in counts]
    return ("Evidence levels: " + ", ".join(f"{counts[lv]} {lv}" for lv in order) +
            f". Claims with a source opened directly: {opened} of {len(used)}; the rest rely on search-index excerpts and independent reports.")


def table_v5(claims: list[dict]) -> str:
    from . import evidence as ev
    rows = ["| # | Claim | Risk | Evidence level | Why | Sources (kind, access, date) | In script |", "|---|---|---|---|---|---|---|"]
    for c in claims:
        lv = ev.level(c)
        src = "; ".join(f"[{ev.outlet(it)}]({it['url']}) ({it.get('kind')}, {it.get('access')}, {it.get('date', 'undated')}"
                        + (f", copy of {it['syndicated_from']}" if it.get("syndicated_from") else "") + ")" for it in c.get("evidence") or [])
        risk = c.get("risk_effective", c.get("risk") or "?") + (f" ({c['risk_why']})" if c.get("risk_why") else "")
        rows.append(f"| {c['id']} | {c['text']} | {risk} | {lv['level']} | {lv['why']} | {src or 'none'} | "
                    f"{'yes' if c.get('in_script') else 'no'} |")
    return "\n".join(rows) + "\n"


def access_summary(claims: list[dict]) -> str:
    """One plain line saying how the script's sources were actually reached."""
    if is_tiered(claims):
        return level_summary(claims)
    used = [c for c in claims if c.get("in_script")]
    kinds = sorted({c.get("access") or "not found" for c in used})
    if not used:
        return ""
    if kinds == ["opened"]:
        return "Source access: every script claim's primary page was opened and read directly."
    parts = [f"{sum(1 for c in used if (c.get('access') or 'not found') == k)} {ACCESS_LABEL.get(k, k)}" for k in kinds]
    return "Source access: " + "; ".join(parts) + "."


def table(claims: list[dict]) -> str:
    if is_tiered(claims):
        return table_v5(claims)
    return _table_v1(claims)


def _table_v1(claims: list[dict]) -> str:
    def link(u):
        return f"[link]({u})" if u else "NONE FOUND"
    rows = ["| # | Exact claim | Primary source | Supporting source | Status | Source date | Confidence | In script |",
            "|---|---|---|---|---|---|---|---|"]
    for c in claims:
        prim = link(c.get("primary_source")) + (f" ({c['access']})" if c.get("primary_source") else "")
        rows.append(f"| {c['id']} | {c['text']} | {prim} | {link(c.get('supporting_source'))} | {c['status']} | "
                    f"{c.get('source_date') or 'UNKNOWN'} | {c['confidence']} | {'yes' if c['in_script'] else 'no'} |")
    notes = [f"- **{c['id']}:** {c['note']}" for c in claims if c.get("note")]
    ev = [f"- **{c['id']}** — {c.get('source_title', '')}: \"{c['supporting_evidence']}\"" for c in claims if c.get("supporting_evidence")]
    if ev:
        notes = ["**Exact supporting evidence**", ""] + ev + ([""] + notes if notes else [])
    head = access_summary(claims)
    rows = ([head, ""] if head else []) + rows
    return "\n".join(rows) + ("\n\n" + "\n".join(notes) if notes else "") + "\n"
