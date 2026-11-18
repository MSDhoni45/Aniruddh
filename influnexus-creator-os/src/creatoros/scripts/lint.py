"""Script checks: length, estimated duration, banned openings and endings."""
from __future__ import annotations

import re

from .. import config
from ..editing.align import script_sentences
from ..util import read_json

BANNED_OPENINGS = ["breaking news", "in a groundbreaking development", "the future is here", "this changes everything",
                   "ai is taking over", "you won't believe", "you wont believe", "technology is evolving rapidly",
                   "hello", "hi guys", "hey guys", "guys", "namaste", "namaskar", "dosto", "welcome back", "aaj hum baat karenge",
                   "imagine a world where", "technology ki duniya mein"]
BANNED_OPENINGS += ["hey everyone", "hey guys", "what's up", "whats up", "in this video", "in today's video", "so today", "let's talk about",
                    "let's dive", "did you know", "big news"]
BANNED_ANYWHERE = ["technology ki duniya mein", "ai is changing everything", "imagine a world where", "aaj hum baat karenge",
                   "you won't believe", "nobody is talking about", "no one is talking about", "shocking", "this changes everything",
                   "in today's fast-paced world", "cutting-edge", "cutting edge", "synergy", "leverage", "revolutionize",
                   "revolutionise", "seamless", "unlock the power", "delve", "smash that like", "don't forget to subscribe"]
# Forced slang that does not fit a global audience or a natural Indian-English delivery.
FORCED_SLANG = ["no cap", "bussin", "lowkey", "low-key", "highkey", "fr fr", "it's giving", "rizz", "y'all", "slaps", "sheesh",
                "on god", "deadass", "bestie", "periodt", "big yikes"]
# Common Hindi words written in Latin script. Two or more in English copy means it is not English.
HINGLISH_MARKERS = {"hai", "hain", "nahi", "nahin", "kya", "yeh", "woh", "aur", "toh", "bhi", "karo", "raha", "rahi", "rahe", "tha",
                    "thi", "matlab", "lekin", "mein", "ka", "ki", "ke", "ko", "se", "pe", "apna", "apni", "kaise", "kyun", "agar",
                    "sirf", "abhi", "dekho", "yaar", "bhai", "accha", "achha", "haan", "kuch", "sab", "bahut", "zyada", "liye"}


def language_problems(text: str, language: str | None = None) -> list[str]:
    """The default language is English. Devanagari or repeated Hindi words in Latin script fail the check."""
    language = language or config.settings().get("language", "english")
    if language != "english" or not text:
        return []
    if re.search(r"[\u0900-\u097f]", text):
        return ["contains Devanagari script; all copy must be in English"]
    hits = [w for w in re.findall(r"[a-z]+", text.lower()) if w in HINGLISH_MARKERS]
    if len(hits) >= 2:
        return [f"reads as Hinglish, not English (Hindi words: {', '.join(sorted(set(hits)))})"]
    return []
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


def check(text: str, language: str | None = None) -> dict:
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
    for b in BANNED_ANYWHERE:
        if b in low:
            problems.append(f"generic phrase: '{b}'")
    for sl in FORCED_SLANG:
        if re.search(rf"(?<![a-z]){re.escape(sl)}(?![a-z])", low):
            problems.append(f"forced slang: '{sl}'")
    problems += language_problems(text, language)
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


HOOK_CRITERIA = ["accuracy", "clarity", "curiosity", "natural", "relevance", "comprehension"]
HOOK_MECHANISMS = ["unexpected fact", "contradiction", "surprising demonstration", "important consequence", "curiosity gap",
                   "relatable problem", "counterintuitive insight", "unexpected comparison", "strong factual statement",
                   "timely development"]
MIN_HOOKS = 10


def score_hooks(hooks: list[dict]) -> list[dict]:
    """Rank hook candidates scored 0-10 on each of HOOK_CRITERIA (total /60).
    Accuracy below 7 disqualifies a hook regardless of its total."""
    out = [{**h, "total": sum(h[k] for k in HOOK_CRITERIA), "eligible": h["accuracy"] >= 7} for h in hooks]
    return sorted(out, key=lambda h: (h["eligible"], h["total"]), reverse=True)


def check_hooks(hooks: list[dict], chosen: str) -> list[str]:
    problems = []
    if len(hooks) < MIN_HOOKS:
        problems.append(f"only {len(hooks)} hook candidates; generate at least {MIN_HOOKS}")
    for h in hooks:
        missing = [k for k in HOOK_CRITERIA if not isinstance(h.get(k), (int, float))]
        if missing:
            problems.append(f"hook '{h.get('text', '')[:30]}' lacks scores for {missing}")
        if h.get("mechanism") not in HOOK_MECHANISMS:
            problems.append(f"hook '{h.get('text', '')[:30]}' needs a mechanism from {HOOK_MECHANISMS}")
    if len({h.get("mechanism") for h in hooks}) < 5:
        problems.append("explore at least five different hook mechanisms")
    if problems:
        return problems
    best = score_hooks(hooks)[0]
    if not best["eligible"]:
        return ["no hook candidate scored 7 or more on accuracy"]
    if best["text"].strip() != chosen.strip():
        problems.append(f"the chosen hook is not the top-scoring eligible hook ('{best['text']}')")
    return problems


QUALITY_CHECKS = ["fact", "hook", "clarity", "retention", "originality", "naturalness", "duration", "payoff", "brand", "virality"]


def quality(scores: dict, text: str) -> dict:
    """Script quality out of 100: ten checks scored 0-10. Duration is measured, not self-assessed.
    Approval needs 90+ overall and nothing below 7. A high score is a writing standard, not a forecast of views."""
    est = estimate_seconds(text)
    lo, hi = config.settings()["script"]["target_seconds"]
    hard = config.settings()["script"]["hard_max_seconds"]
    s = dict(scores)
    s["duration"] = 10 if lo - 2 <= est["seconds"] <= hi + 2 else (7 if est["seconds"] <= hard else 0)
    missing = [k for k in QUALITY_CHECKS if not isinstance(s.get(k), (int, float))]
    total = sum(s.get(k, 0) for k in QUALITY_CHECKS)
    weak = [k for k in QUALITY_CHECKS if isinstance(s.get(k), (int, float)) and s[k] < 7]
    problems = [f"missing quality scores: {missing}"] if missing else []
    if total < 90:
        problems.append(f"script quality {total}/100 is below 90: revise the script")
    if weak:
        problems.append(f"checks below 7/10: {weak}")
    return {"scores": s, "total": total, "approved": not problems, "problems": problems}
