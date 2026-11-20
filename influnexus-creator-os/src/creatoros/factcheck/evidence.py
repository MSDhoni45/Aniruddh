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


# --- risk classification from the claim's temporal meaning -----------------------------------------------------------
import re as _re

_MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
_NOW_FUTURE = [r"\btoday\b", r"\btonight\b", r"\btomorrow\b", r"\byesterday\b", r"\bright now\b", r"\bout now\b", r"\bnow\b",
               r"\bthis (week|weekend|month|year|morning|evening)\b", r"\bnext (week|month|year|quarter)\b", r"\blater this\b",
               r"\bcoming soon\b", r"\bupcoming\b", r"\bjust (launched|released|announced|dropped|went live)\b",
               r"\b(will|is going to|are going to|set to|scheduled to|expected to|plans to)\b", r"\bis launching\b",
               r"\b(currently|latest|still)\b", r"\bnew(ly)? (price|prices|pricing)\b", r"\bpre-?orders? (open|opened|are live)\b",
               # Hinglish time words (Roman script)
               r"\baaj\b", r"\babhi\b", r"\bkal\b", r"\bagle (hafte|mahine|saal)\b"]
_PAST = [r"\b\d+\s+(years|decades)\s+ago\b", r"\bback in\b", r"\boriginally\b", r"\bin the (19|20)\d0s\b",
         r"\b(19|20)\d0s\b", r"\bsaal pehle\b", r"\bhistorically\b", r"\bfirst (released|launched|came out)\b"]
_VOLATILE = [r"\bprice", r"\bcost", r"\$\s?\d", r"\b(rs|inr|usd|eur)\b", r"\bdiscount", r"\bsale\b", r"\blaunch",
             r"\brelease", r"\bavailab", r"\bpre-?order", r"\bpre-?load", r"\bin stock\b", r"\bout of stock\b", r"\bdelay",
             r"\bbreach", r"\bhack", r"\bvulnerab", r"\bexploit", r"\bcve-", r"\boutage", r"\bshares?\b", r"\bstock\b",
             r"\bvaluation", r"\brevenue", r"\bipo\b", r"\bfunding", r"\braised\b", r"\bacquir", r"\blayoffs?\b", r"\bbanned?\b"]
RECENT_DAYS, OLD_DAYS = 90, 365


def _dates_in(text: str, today: dt.date) -> list[dt.date]:
    """Explicit dates in the claim: full dates, 'Month Year', and bare years (taken as mid-year)."""
    out = []
    for m in _re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        try:
            out.append(dt.date(int(m[1]), int(m[2]), int(m[3])))
        except ValueError:
            pass
    for m in _re.finditer(rf"\b(\d{{1,2}})?\s*({_MONTHS})\.?\s*(\d{{1,2}})?,?\s*(\d{{4}})\b", text, _re.I):
        mon = [x[:3] for x in _MONTHS.split("|")].index(m[2][:3].lower()) % 12 + 1
        day = int(m[1] or m[3] or 15)
        try:
            out.append(dt.date(int(m[4]), mon, min(day, 28)))
        except ValueError:
            pass
    if not out:
        for m in _re.finditer(r"(?<![\d-])((?:19|20)\d{2})(?![\d-]|s\b)", text):
            out.append(dt.date(int(m[1]), 7, 1))
    return out


def classify_risk(text: str, package_date: str, event_date: str | None = None) -> dict:
    """'high' (time-sensitive) or 'low' (historical) from the claim's temporal meaning, with the reason.
    Order: explicit present/future context, then the age of any date in the claim, then the topic as a tie-breaker."""
    t = f" {text.lower()} "
    today = dt.date.fromisoformat(package_date)
    dates = _dates_in(text, today)
    if event_date:
        try:
            dates.append(dt.date.fromisoformat(str(event_date)[:10]))
        except ValueError:
            pass
    now_hits = [p for p in _NOW_FUTURE if _re.search(p, t)]
    past_hits = [p for p in _PAST if _re.search(p, t)]
    if any(d > today for d in dates):
        return {"risk": "high", "why": "refers to a future date"}
    if now_hits and not (past_hits and not dates):
        return {"risk": "high", "why": "present or future time context"}
    if dates:
        newest = max(dates)
        age = (today - newest).days
        if age <= RECENT_DAYS:
            return {"risk": "high", "why": f"refers to a recent date ({newest.isoformat()})"}
        if age >= OLD_DAYS:
            return {"risk": "low", "why": f"refers to a past date ({newest.isoformat()})"}
    if past_hits:
        return {"risk": "low", "why": "explicitly in the past"}
    if any(_re.search(p, t) for p in _VOLATILE):
        return {"risk": "high", "why": "price, launch, availability, security or financial fact with no clear past date"}
    return {"risk": "low", "why": "stable descriptive fact with no time-sensitive content"}


def effective_risk(claim: dict, package_date: str) -> dict:
    """The stricter of the declared risk and the classified one: a writer can raise the risk, never lower it."""
    auto = classify_risk(claim.get("text", ""), package_date, claim.get("event_date"))
    declared = claim.get("risk")
    if declared == "high" or auto["risk"] == "high":
        why = auto["why"] if auto["risk"] == "high" else "declared high by the writer"
        return {"risk": "high", "why": why, "auto": auto["risk"], "declared": declared}
    return {"risk": "low", "why": auto["why"], "auto": auto["risk"], "declared": declared}


# Extraordinary financial claims: share-price moves, IPO pricing and proceeds, valuations, market caps, and amounts in the
# billions. When time-sensitive they need a primary source OPENED directly (HIGH); search excerpts are not enough.
_FINANCIAL = [r"\bipo\b", r"\bper share\b", r"\bshare price", r"\bstock price", r"\bmarket cap", r"\bvaluation",
              r"\bvalued at\b", r"\bpriced (at|its|the)\b", r"\b(opened|closed|traded|jumped|soared|fell|dropped|rose|surged|plunged)\b.{0,40}\b(\d+(\.\d+)?\s?%|percent|\$)",
              r"\b\d+(\.\d+)?\s?(%|percent)\s+(higher|lower|up|down|above|below)\b", r"\bshares? (opened|closed|rose|fell|jumped)\b",
              r"\$\s?\d[\d,.]*\s?(billion|trillion|bn|tn)\b", r"\b\d[\d,.]*\s?(billion|trillion) (dollars?|usd)\b",
              r"\b(revenue|proceeds|raised|funding round)\b.{0,30}\$?\d", r"\bshares? (sold|offered)\b", r"\bticker\b"]


def is_extraordinary_financial(text: str) -> bool:
    t = text.lower()
    return any(_re.search(p, t) for p in _FINANCIAL)


def gate(claim: dict, package_date: str) -> list[str]:
    """Reasons this script claim blocks recording (empty = it passes)."""
    cid = claim.get("id", "?")
    if claim.get("risk") not in RISKS + [None]:
        return [f"{cid}: risk, if declared, must be 'high' (time-sensitive) or 'low' (historical)"]
    risk = effective_risk(claim, package_date)["risk"]
    lv = level(claim)
    reasons = []
    need = REQUIRED_LEVEL[risk]
    if risk == "high" and (claim.get("financial") or is_extraordinary_financial(claim.get("text", ""))):
        need = "HIGH"                      # extraordinary financial claim: the primary document itself must be opened
    if not at_least(lv["level"], need):
        reasons.append(f"{cid} ({risk}-risk) is {lv['level']} ({lv['why']}); needs {need}: {claim.get('text', '')}")
    if risk == "high" and at_least(lv["level"], need) and lv["level"] != "HIGH" and not _current(claim.get("evidence") or [], package_date):
        reasons.append(f"{cid} is time-sensitive but no corroborating report is dated within {CURRENT_DAYS} days of {package_date}")
    return reasons
