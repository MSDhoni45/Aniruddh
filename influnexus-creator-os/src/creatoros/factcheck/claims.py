"""Claim classification rules. A script cannot be approved while it leans on an unverified or unattributed claim."""
from __future__ import annotations

STATUSES = ["CONFIRMED", "COMPANY CLAIM", "THIRD-PARTY CLAIM", "PREDICTION", "OPINION", "DISPUTED", "UNVERIFIED", "RUMOR",
            "SPECULATION"]
# COMPANY CLAIM covers marketing claims; PREDICTION and OPINION must be attributed to the person who made them.
NEEDS_ATTRIBUTION = {"COMPANY CLAIM", "THIRD-PARTY CLAIM", "PREDICTION", "OPINION", "DISPUTED"}
NOT_USABLE = {"UNVERIFIED", "RUMOR", "SPECULATION"}


def validate(fc: dict, script_text: str | None = None) -> list[str]:
    problems, seen = [], set()
    low = (script_text or "").lower()
    for c in fc.get("claims", []):
        cid = c.get("id", "?")
        if cid in seen:
            problems.append(f"{cid}: duplicate id")
        seen.add(cid)
        st = c.get("status")
        if st not in STATUSES:
            problems.append(f"{cid}: status must be one of {STATUSES}")
            continue
        evidence = list(c.get("evidence") or []) + [u for u in (c.get("primary_source"), c.get("supporting_source")) if u]
        if st not in NOT_USABLE and not evidence:
            problems.append(f"{cid}: {st} needs at least one evidence URL")
        if any(not str(u).startswith("http") for u in evidence):
            problems.append(f"{cid}: evidence must be URLs")
        if not c.get("in_script"):
            continue
        if st in NOT_USABLE:
            problems.append(f"{cid}: {st} claim is used in the script; remove it or reject the story")
        if st in NEEDS_ATTRIBUTION:
            if not c.get("attribution"):
                problems.append(f"{cid}: {st} needs an attribution")
            phrase = c.get("script_attribution")
            if script_text is not None and (not phrase or phrase.lower() not in low):
                problems.append(f"{cid}: {st} is in the script but the script does not carry its attribution phrase "
                                f"({phrase!r}); set script_attribution to the exact words that attribute it")
    return problems


def to_markdown(fc: dict) -> str:
    lines = [f"# Fact-check: {fc.get('story', '')}", "", f"Date: {fc.get('date', '')}", "",
             "| ID | Claim | Status | Attribution | In script | Evidence | Note |", "|---|---|---|---|---|---|---|"]
    for c in fc.get("claims", []):
        urls = list(c.get("evidence") or []) + [u for u in (c.get("primary_source"), c.get("supporting_source")) if u]
        ev = " ".join(f"[{i + 1}]({u})" for i, u in enumerate(urls)) or "none"
        lines.append(f"| {c['id']} | {c['text']} | {c['status']} | {c.get('attribution', '')} | {'yes' if c.get('in_script') else 'no'} | {ev} | {c.get('note', '')} |")
    return "\n".join(lines) + "\n"
