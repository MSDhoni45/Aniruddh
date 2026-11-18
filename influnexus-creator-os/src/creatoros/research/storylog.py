"""Backwards-compatible wrapper: the story log is now the content database (research/content_db.py)."""
from __future__ import annotations

from pathlib import Path

from . import content_db


def find_repeat(headline: str, keys: list[str], today: str, days: int = 45, path: Path | None = None) -> dict | None:
    return content_db.find_repeat(headline, keys, today, days, path)


def add(day: str, headline: str, keys: list[str], slug: str, material_update_of: str | None = None, path: Path | None = None) -> dict:
    return content_db.add(day, headline, keys, slug, material_update_of=material_update_of, path=path)
