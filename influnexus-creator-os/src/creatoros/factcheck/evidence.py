"""Tiered, risk-based source verification (permanent policy from 19 Nov 2026; applies to v5 packages).

A claim's evidence level is COMPUTED from its evidence list, never self-declared:
  HIGH         a primary source opened directly (or equivalent authenticated primary material)
  MEDIUM-HIGH  clearly attributable official text read through a search index, corroborated by at least two
               genuinely independent reputable sources
  MEDIUM       at least two independent reputable reports, consistent, each dated and attributed
  LOW          a single source, unclear attribution, syndicated repetition or incomplete evidence
  UNVERIFIED   rumours, conflicting sources, unsupported claims, nothing traceable
Search excerpts agreeing with each other never make a claim HIGH. Copies of one original report count once.

Gate (by risk):
  high-risk / time-sensitive (launches, release dates, prices, availability, security incidents, financial claims,
  breaking news): needs MEDIUM-HIGH or better, and at least one corroborating source dated within CURRENT_DAYS of the package.
  low-risk / historical (release history, historical events, documented milestones): needs MEDIUM or better.
"""
from __future__ import annotations

import datetime as dt
from urllib.parse import urlparse

LEVELS = ["UNVERIFIED", "LOW", "MEDIUM", "MEDIUM-HIGH", "HIGH"]
RISKS = ["high", "low"]
KINDS = ["primary", "news", "reference", "blog", "forum", "user-edited"]
ACCESS = ["opened", "search-index", "secondary"]
REPUTABLE = {"primary", "news", "reference"}       # blogs, forums and user-edited wikis never count as reputable
UNUSABLE_STATUS = {"RUMOR", "UNVERIFIED", "SPECULATION", "SPECULATIVE", "DISPUTED"}
REQUIRED_LEVEL = {"high": "MEDIUM-HIGH", "low": "MEDIUM"}
CURRENT_DAYS = 7
# Known user-edited or low-editorial hosts, treated as user-edited whatever kind is declared.
USER_EDITED_HOSTS = ("fandom.com", "tvtropes.org", "reddit.com", "quora.com", "gtaforums.com")


def outlet(item: dict) -> str:
    """The publisher: declared outlet, else the URL's host without 'www.' and mobile prefixes."""
    if item.get("outlet"):
        return str(item["outlet"]).lower().strip()
    host = urlparse(str(item.get("url", ""))).netloc.lower()
    for pre in ("www.", "m.", "amp."):
        host = host[len(pre):] if host.startswith(pre) else host
    return host


def _kind(item: dict) -> str:
    host = urlparse(str(item.get("url", ""))).netloc.lower()
    if any(host.endswith(h) for h in USER_EDITED_HOSTS):
        return "user-edited"
    return item.get("kind", "news")


def item_problems(item: dict, i: int) -> list[str]:
    p = []
    if not str(item.get("url", "")).startswith("http"):
        p.append(f"evidence[{i}].url must be a URL")
    if item.get("kind") not in KINDS:
        p.append(f"evidence[{i}].kind must be one of {KINDS}")
    if item.get("access") not in ACCESS:
        p.append(f"evidence[{i}].access must be one of {ACCESS}")
    return p


def independent_reputable(items: list[dict], exclude_primary: bool = True) -> list[str]:
    """Distinct reputable outlets. A copy of another report (syndicated_from) counts as its original, once."""
    seen = set()
    for it in items:
        k = _kind(it)
        if k not in REPUTABLE or (exclude_primary and k == "primary"):
            continue
        if not (it.get("date") and outlet(it)):
            continue                                    # undated or unattributed reports do not count
        origin = it.get("syndicated_from")
        key = outlet({"url": origin}) if origin else outlet(it)
        seen.add(key)
    return sorted(seen)


def level(claim: dict) -> dict:
    """Compute the evidence level and say why."""
    items = claim.get("evidence") or []
    if claim.get("status") in UNUSABLE_STATUS:
        return {"level": "UNVERIFIED", "why": f"status {claim['status']}"}
    if claim.get("conflicts"):
        return {"level": "UNVERIFIED", "why": "sources conflict: " + "; ".join(map(str, claim["conflicts"]))}
    if not items:
        return {"level": "UNVERIFIED", "why": "no traceable evidence"}
    prim = [it for it in items if _kind(it) == "primary"]
    indep = independent_reputable(items)
    if any(it.get("access") == "opened" or it.get("authenticated") for it in prim):
        return {"level": "HIGH", "why": "primary source opened directly", "independent": indep}
    if any(it.get("access") == "search-index" and it.get("date") for it in prim) and len(indep) >= 2:
        return {"level": "MEDIUM-HIGH", "why": f"official indexed text plus {len(indep)} independent sources: {', '.join(indep)}",
                "independent": indep}
    if len(indep) >= 2:
        return {"level": "MEDIUM", "why": f"{len(indep)} independent reputable reports: {', '.join(indep)}", "independent": indep}
    raw = len({outlet(it) for it in items})
    why = ("syndicated or repeated copies of one report" if raw > len(indep) and len(indep) <= 1 and len(items) > 1
           else "a single source or incomplete evidence")
    return {"level": "LOW", "why": why, "independent": indep}


def at_least(lv: str, need: str) -> bool:
    return LEVELS.index(lv) >= LEVELS.index(need)


def _current(items: list[dict], package_date: str) -> bool:
    d0 = dt.date.fromisoformat(package_date)
    for it in items:
        if _kind(it) not in REPUTABLE or _kind(it) == "primary":
            continue
        try:
            d = dt.date.fromisoformat(str(it.get("date", ""))[:10])
        except ValueError:
            continue
        if 0 <= (d0 - d).days <= CURRENT_DAYS:
            return True
    return False


def gate(claim: dict, package_date: str) -> list[str]:
    """Reasons this script claim blocks recording (empty = it passes)."""
    cid = claim.get("id", "?")
    risk = claim.get("risk")
    if risk not in RISKS:
        return [f"{cid}: set risk to 'high' (time-sensitive) or 'low' (historical)"]
    lv = level(claim)
    reasons = []
    need = REQUIRED_LEVEL[risk]
    if not at_least(lv["level"], need):
        reasons.append(f"{cid} ({risk}-risk) is {lv['level']} ({lv['why']}); needs {need}: {claim.get('text', '')}")
    if risk == "high" and at_least(lv["level"], need) and lv["level"] != "HIGH" and not _current(claim.get("evidence") or [], package_date):
        reasons.append(f"{cid} is time-sensitive but no corroborating report is dated within {CURRENT_DAYS} days of {package_date}")
    return reasons
