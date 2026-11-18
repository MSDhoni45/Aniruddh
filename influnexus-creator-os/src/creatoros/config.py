"""Configuration loading. Secrets come from the environment only."""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

ROOT = Path(os.environ.get("CREATOROS_ROOT", Path(__file__).resolve().parents[2]))


def _expand(value):
    if isinstance(value, str):
        def sub(m):
            name, _, default = m.group(1).partition(":-")
            return os.environ.get(name, default)
        return os.path.expanduser(re.sub(r"\$\{([^}]+)\}", sub, value))
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def load(name: str) -> dict:
    with open(ROOT / "config" / f"{name}.yaml", encoding="utf-8") as fh:
        return _expand(yaml.safe_load(fh))


def settings() -> dict:
    return load("settings")


def style() -> dict:
    return load("style")


def platforms() -> dict:
    return load("platforms")


def path(*parts: str) -> Path:
    p = Path(*parts)
    return p if p.is_absolute() else ROOT / p
