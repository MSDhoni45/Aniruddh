"""Cross-platform signals and the source-access audit.

A signal is one observation of a story on one platform (an X post, a Reddit thread, a YouTube video, a news article...).
Every signal says how it was reached and what kind of engagement number it carries, so estimates are never shown as
measurements. The audit probes each source group from the run's own environment; a platform the audit found BLOCKED can
never be claimed as DIRECTLY OBSERVED.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import json
import urllib.error
import urllib.request
from pathlib import Path

PLATFORMS = ["x", "reddit", "youtube", "instagram", "linkedin", "google_trends", "primary", "news"]
ACCESS = ["DIRECTLY OBSERVED", "SEARCH-INDEX", "SECONDARY", "NOT VERIFIED"]
BASIS = ["observed", "reported", "estimated", "unknown"]
UNKNOWN = "UNKNOWN"

# Hosts probed per source group. A group is WORKING if every host answers, PARTIAL if some do, BLOCKED if none do.
GROUP_HOSTS = {
    "x": ["x.com", "api.twitter.com"],
    "reddit": ["www.reddit.com", "oauth.reddit.com"],
    "youtube": ["www.youtube.com", "www.googleapis.com"],
    "instagram": ["www.instagram.com", "graph.instagram.com"],
    "linkedin": ["www.linkedin.com"],
    "google_trends": ["trends.google.com"],
    "primary": ["openai.com", "www.anthropic.com", "blog.google", "nvidianews.nvidia.com", "arxiv.org", "www.nature.com",
                "huggingface.co", "github.com"],
    "news": ["www.reuters.com", "apnews.com", "www.theverge.com", "techcrunch.com", "arstechnica.com", "www.wired.com",
             "www.technologyreview.com", "spectrum.ieee.org"],
}
# Hosts that answer but need credentials before they return data (an API host reachable without a key is not data).
NEEDS_CREDENTIALS = {"www.googleapis.com": "YouTube Data API key", "oauth.reddit.com": "Reddit API app credentials",
                     "graph.instagram.com": "Instagram Graph API token", "api.twitter.com": "X API bearer token"}


def probe(host: str, timeout: float = 6.0) -> dict:
    """One HEAD request through the environment's own proxy settings. Any HTTP answer means the host is reachable."""
    req = urllib.request.Request(f"https://{host}/", method="HEAD", headers={"User-Agent": "creatoros-source-audit"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"host": host, "reachable": True, "http": r.status}
    except urllib.error.HTTPError as e:
        return {"host": host, "reachable": True, "http": e.code}      # the host itself answered
    except (urllib.error.URLError, OSError, ValueError) as e:
        return {"host": host, "reachable": False, "error": type(e).__name__ + ": " + str(getattr(e, "reason", e))[:120]}


def audit(prober=probe, now: dt.datetime | None = None) -> dict:
    """Probe every group in parallel (bounded: one attempt per host, a few seconds each)."""
    hosts = sorted({h for hs in GROUP_HOSTS.values() for h in hs})
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        results = dict(zip(hosts, ex.map(prober, hosts)))
    groups = {}
    for g, hs in GROUP_HOSTS.items():
        ok = [h for h in hs if results[h]["reachable"]]
        status = "WORKING" if len(ok) == len(hs) else ("PARTIAL" if ok else "BLOCKED")
        creds = [f"{h}: needs {NEEDS_CREDENTIALS[h]}" for h in ok if h in NEEDS_CREDENTIALS]
        data_hosts = [h for h in ok if h not in NEEDS_CREDENTIALS]
        if status != "BLOCKED" and not data_hosts:
            status = "BLOCKED"          # only credentialed API hosts answer; without credentials there is no data
        groups[g] = {"status": status, "reachable": ok, "blocked": [h for h in hs if h not in ok], "needs_credentials": creds}
    t = (now or dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds")
    return {"checked_at_utc": t, "groups": groups, "hosts": results,
            "note": "Reachability from this cloud environment. BLOCKED groups can only be researched through web-search "
                    "excerpts (SEARCH-INDEX) or secondary reporting; their engagement numbers are UNKNOWN."}


def save_audit(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def load_audit(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def blocked_platforms(audit_result: dict | None) -> set[str]:
    if not audit_result:
        return set()
    return {g for g, v in audit_result.get("groups", {}).items() if v.get("status") == "BLOCKED"}


def signal_problems(sig: dict, i: int, blocked: set[str] | None = None) -> list[str]:
    p, where = [], f"signals[{i}]"
    if sig.get("platform") not in PLATFORMS:
        p.append(f"{where}.platform must be one of {PLATFORMS}")
    for f in ("url", "title", "retrieved_at"):
        if not sig.get(f):
            p.append(f"{where} needs {f}")
    if sig.get("url") and not str(sig["url"]).startswith("http"):
        p.append(f"{where}.url must be a URL")
    if sig.get("access") not in ACCESS:
        p.append(f"{where}.access must be one of {ACCESS}")
    if sig.get("access") == "DIRECTLY OBSERVED" and blocked and sig.get("platform") in blocked:
        p.append(f"{where}: {sig['platform']} was BLOCKED in this run's source audit, so it cannot be DIRECTLY OBSERVED")
    eng = sig.get("engagement") or {}
    basis = eng.get("basis", "unknown")
    if basis not in BASIS:
        p.append(f"{where}.engagement.basis must be one of {BASIS}")
    metrics = {k: v for k, v in eng.items() if k not in ("basis", "source")}
    numeric = {k: v for k, v in metrics.items() if v != UNKNOWN}
    for k, v in numeric.items():
        if not isinstance(v, (int, float)):
            p.append(f"{where}.engagement.{k} must be a number or UNKNOWN")
    if numeric and basis == "unknown":
        p.append(f"{where}: engagement numbers need a basis (observed, reported or estimated)")
    if numeric and basis == "observed" and sig.get("access") != "DIRECTLY OBSERVED":
        p.append(f"{where}: 'observed' engagement needs the page DIRECTLY OBSERVED; use 'reported' with a source otherwise")
    if numeric and basis == "reported" and not eng.get("source"):
        p.append(f"{where}: reported engagement needs engagement.source (who reported the number)")
    return p


def summary(signals: list[dict]) -> dict:
    """Platforms a story appears on, and how each was reached."""
    by = {}
    for s in signals:
        by.setdefault(s.get("platform"), set()).add(s.get("access"))
    return {"platforms": sorted(k for k in by if k), "count": len([k for k in by if k]),
            "directly_observed": sorted(k for k, v in by.items() if "DIRECTLY OBSERVED" in v)}
