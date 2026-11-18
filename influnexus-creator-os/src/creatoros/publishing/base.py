"""Publishing safeguards shared by every platform: review gate, duplicate prevention, retries and logging."""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from .. import config
from ..util import logger, read_json

log = logger("publish")
LEDGER = "logs/publish_ledger.jsonl"


class Blocked(Exception):
    """Publishing cannot proceed; the message says exactly what is missing."""


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ledger(path: Path | None = None) -> list[dict]:
    p = path or config.path(LEDGER)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def record(entry: dict, path: Path | None = None) -> None:
    p = path or config.path(LEDGER)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({**entry, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}, ensure_ascii=False) + "\n")


def already_published(platform: str, file_hash: str, date: str, path: Path | None = None) -> dict | None:
    for e in ledger(path):
        if e.get("platform") == platform and e.get("status") == "published" and (e.get("sha256") == file_hash or e.get("date") == date):
            return e
    return None


def gate(date: str, reviewed: bool) -> None:
    """Refuse unless QC passed, the fact-check is clean, and a human has reviewed any disputed material."""
    qc = config.path("renders", date, "qc_report.json")
    if not qc.exists() or not read_json(qc).get("passed"):
        raise Blocked(f"no passing QC report for {date}")
    fc_path = config.path("scripts", f"{date}_factcheck.json")
    if not fc_path.exists():
        raise Blocked(f"no fact-check file for {date}")
    from ..factcheck.claims import validate
    script = config.path("scripts", f"{date}_script.txt")
    problems = validate(read_json(fc_path), script.read_text(encoding="utf-8") if script.exists() else None)
    if problems:
        raise Blocked("fact-check problems: " + "; ".join(problems))
    disputed = [c["id"] for c in read_json(fc_path)["claims"] if c["status"] == "DISPUTED" and c.get("in_script")]
    if (disputed or read_json(qc).get("needs_human")) and not reviewed:
        raise Blocked("human review required before publishing (disputed claims or QC warnings). Re-run with --reviewed after checking.")


def credentials(platform: str) -> dict:
    need = config.platforms()[platform].get("env", [])
    missing = [k for k in need if not os.environ.get(k)]
    if missing:
        raise Blocked(f"{platform}: missing credentials in environment: {', '.join(missing)}")
    return {k: os.environ[k] for k in need}


def request(method: str, url: str, *, attempts: int = 4, **kw) -> requests.Response:
    """HTTP with backoff on network errors, 429 and 5xx. Tokens are never logged."""
    last = None
    for i in range(attempts):
        try:
            r = requests.request(method, url, timeout=kw.pop("timeout", 60), **kw)
            if r.status_code < 500 and r.status_code != 429:
                return r
            last = RuntimeError(f"HTTP {r.status_code}")
        except requests.RequestException as exc:
            last = exc
        log.warning("%s %s failed (%s); retry %d/%d", method, url.split("?")[0], type(last).__name__, i + 1, attempts)
        time.sleep(min(2 ** i, 30))
    raise RuntimeError(f"{method} {url.split('?')[0]} failed after {attempts} attempts: {last}")
