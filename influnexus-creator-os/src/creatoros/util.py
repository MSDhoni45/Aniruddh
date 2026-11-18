"""Shared helpers: subprocess wrappers, JSON IO and a log that redacts secrets."""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path

from .config import ROOT

_SECRET_ENV = re.compile(r"(TOKEN|SECRET|KEY|PASSWORD)", re.I)


class _Redact(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        for k, v in os.environ.items():
            if _SECRET_ENV.search(k) and v and len(v) >= 8 and v in msg:
                msg = msg.replace(v, "<redacted>")
        record.msg, record.args = msg, ()
        return True


def logger(name: str = "creatoros") -> logging.Logger:
    log = logging.getLogger(name)
    if not log.handlers:
        log.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        (ROOT / "logs").mkdir(exist_ok=True)
        for h in (logging.StreamHandler(), logging.FileHandler(ROOT / "logs" / "creatoros.log", encoding="utf-8")):
            h.setFormatter(fmt)
            h.addFilter(_Redact())
            log.addHandler(h)
    return log


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, errors="replace")
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(map(str, cmd[:6]))} ...\n{proc.stderr[-2000:]}")
    return proc


def ffmpeg(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return run(["ffmpeg", "-hide_banner", "-nostdin", "-y", *args], check=check)


def read_json(p: str | Path):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(p: str | Path, data) -> Path:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    tmp.replace(p)
    return p
