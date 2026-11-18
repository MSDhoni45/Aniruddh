"""Script checks: length, estimated duration, banned openings and endings."""
from __future__ import annotations

import re

from .. import config
from ..editing.align import script_sentences
from ..util import read_json

BANNED_OPENINGS = ["breaking news", "in a groundbreaking development", "the future is here", "this changes everything",
                   "ai is taking over", "you won't believe", "you wont believe", "technology is evolving rapidly",
                   "hello", "hi guys", "hey guys", "namaste", "namaskar", "dosto", "welcome back", "aaj hum baat karenge"]
BANNED_ENDINGS = ["what do you think", "aapko kya lagta hai", "like share subscribe", "follow for more"]
HYPE = ["revolutionary", "game changer", "game-changer", "mind blowing", "mind-blowing", "insane", "guaranteed", "100% viral"]


def pace() -> tuple[float, str]:
    """Words per minute: the creator's measured pace if a calibration exists, else the configured assumption."""
    p = config.path("analytics/pace.json")
    if p.exists():
        d = read_json(p)
        return float(d["words_per_minute"]), f"measured from {d['samples']} recording(s)"
    return float(config.settings()["script"]["words_per_minute"]), "assumed default; not yet calibrated on the creator's voice"


def word_count(text: str) -> int:
    return len(re.findall(r"[^\s]+", re.sub(r"\s[—–-]\s", " ", text)))


def estimate_seconds(text: str) -> dict:
    wpm, basis = pace()
    words = word_count(text)
    sentences = len(script_sentences(text))
    pauses = min(0.2 * max(sentences - 1, 0), config.settings()["script"]["pause_allowance_seconds"] + 1)
    return {"words": words, "sentences": sentences, "words_per_minute": wpm, "pace_basis": basis,
            "seconds": round(words / wpm * 60 + pauses, 1)}


def check(text: str) -> dict:
    sc = config.settings()["script"]
    est = estimate_seconds(text)
    low = re.sub(r"\s+", " ", text.lower()).strip()
    sents = script_sentences(text)
    problems, warnings = [], []
    for b in BANNED_OPENINGS:
        if low.startswith(b) or low[:60].find(b) == 0:
            problems.append(f"opens with banned phrase: '{b}'")
    for b in BANNED_ENDINGS:
        if b in low[-80:]:
            problems.append(f"ends with generic call to action: '{b}'")
    for h in HYPE:
        if h in low:
            problems.append(f"unsupported hype word: '{h}'")
    if est["seconds"] > sc["hard_max_seconds"]:
        problems.append(f"estimated {est['seconds']}s is over the {sc['hard_max_seconds']}s hard maximum: shorten the script")
    lo, hi = sc["target_seconds"]
    if not lo <= est["seconds"] <= hi:
        warnings.append(f"estimated {est['seconds']}s is outside the {lo}-{hi}s target")
    wlo, whi = sc["target_words"]
    if not wlo <= est["words"] <= whi:
        warnings.append(f"{est['words']} words is outside the {wlo}-{whi} word target")
    if sents and word_count(sents[0]) > 16:
        warnings.append("first sentence is longer than 16 words: the hook should land within two seconds")
    return {**est, "ok": not problems, "problems": problems, "warnings": warnings, "sentences_indexed": list(enumerate(sents))}


def score_hooks(hooks: list[dict]) -> list[dict]:
    """Rank hook candidates scored 0-10 on clarity, curiosity, accuracy, natural delivery and visual potential.
    Accuracy below 7 disqualifies a hook regardless of its total."""
    keys = ["clarity", "curiosity", "accuracy", "natural", "visual"]
    out = [{**h, "total": sum(h[k] for k in keys), "eligible": h["accuracy"] >= 7} for h in hooks]
    return sorted(out, key=lambda h: (h["eligible"], h["total"]), reverse=True)
