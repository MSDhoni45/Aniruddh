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
                   "revolutionise", "seamless", "unlock the power", "delve", "smash that like", "don't forget to subscribe",
                   "rapidly evolving", "technological landscape", "groundbreaking", "ground-breaking", "only time will tell",
                   "like and subscribe"]
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
    if not text:
        return []
    if language == "hinglish":
        # Hinglish is written in Roman script so it reads straight off a teleprompter.
        return ["contains Devanagari script; write Hinglish in Roman script"] if re.search(r"[\u0900-\u097f]", text) else []
    if language != "english":
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


def estimate_seconds(text: str, scheme: str | None = None) -> dict:
    wpm, basis = pace()
    words = word_count(text)
    sentences = len(script_sentences(text))
    pauses = min(0.2 * max(sentences - 1, 0), config.settings()["script"]["pause_allowance_seconds"] + 1)
    v6 = config.settings().get("script_v6", {})
    if scheme == "v6":
        # v6: a moderate, natural speaking pace with a real pause after every sentence (no cramming). A measured
        # calibration of the creator's voice still wins over the assumed pace; the pauses are always added.
        if not config.path("analytics/pace.json").exists():
            wpm = float(v6.get("words_per_minute", 140))
            basis = f"natural moderate pace, {wpm:g} wpm plus a pause after each sentence (assumed; not yet calibrated)"
        pauses = float(v6.get("pause_seconds_per_sentence", 0.35)) * max(sentences - 1, 0)
    return {"words": words, "sentences": sentences, "words_per_minute": wpm, "pace_basis": basis,
            "seconds": round(words / wpm * 60 + pauses, 1)}


def limits(scheme: str | None = None) -> dict:
    """Length limits: script_v3 for v3 packages, the original script limits otherwise."""
    st = config.settings()
    sc = dict(st["script"])
    if scheme in ("v3", "v5", "v6") and f"script_{scheme}" in st:
        sc.update(st[f"script_{scheme}"])
    return sc


def check(text: str, language: str | None = None, scheme: str | None = None) -> dict:
    sc = limits(scheme)
    est = estimate_seconds(text, scheme)
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
    if scheme == "v6":
        long = [i + 1 for i, x in enumerate(sents) if word_count(x) > MAX_SENTENCE_WORDS_V6]
        if long:
            problems.append(f"sentence(s) {long} longer than {MAX_SENTENCE_WORDS_V6} words: use short, spoken sentences")
        for g in GENERIC_HOOK_PHRASES:
            if low.startswith(g):
                problems.append(f"generic opening: '{g}'")
    return {**est, "ok": not problems, "problems": problems, "warnings": warnings, "sentences_indexed": list(enumerate(sents))}


MAX_SENTENCE_WORDS_V6 = 22
# Openings the creator named as generic (v6). Also checked on every hook candidate.
GENERIC_HOOK_PHRASES = ["big news in ai", "big news in tech", "big news today", "something crazy just happened",
                        "something crazy", "something huge just happened", "something big just happened", "you won't believe",
                        "you wont believe", "this is huge", "this is crazy", "this is insane", "ai just changed everything",
                        "breaking:", "breaking news", "hold on", "wait for it", "stop scrolling"]

HOOK_CRITERIA = ["accuracy", "clarity", "curiosity", "natural", "relevance", "comprehension"]
HOOK_MECHANISMS = ["unexpected fact", "contradiction", "surprising demonstration", "important consequence", "curiosity gap",
                   "relatable problem", "counterintuitive insight", "unexpected comparison", "strong factual statement",
                   "timely development"]
MIN_HOOKS = 10
# v3 (from 20 Nov 2026): seven criteria, total /70. Accuracy below 7 still disqualifies.
HOOK_CRITERIA_V3 = ["accuracy", "clarity", "curiosity", "surprise", "specificity", "natural", "relevance"]
# v4: the creator's hook criteria (natural = spoken delivery; retention = audience retention potential)
HOOK_CRITERIA_V4 = ["accuracy", "clarity", "curiosity", "surprise", "relevance", "natural", "retention"]


def score_hooks(hooks: list[dict], criteria: list[str] | None = None) -> list[dict]:
    """Rank hook candidates scored 0-10 on each criterion (HOOK_CRITERIA /60, or HOOK_CRITERIA_V3 /70).
    Accuracy below 7 disqualifies a hook regardless of its total."""
    criteria = criteria or HOOK_CRITERIA
    out = [{**h, "total": sum(h[k] for k in criteria), "eligible": h["accuracy"] >= 7} for h in hooks]
    return sorted(out, key=lambda h: (h["eligible"], h["total"]), reverse=True)


def check_hooks(hooks: list[dict], chosen: str, criteria: list[str] | None = None, min_hooks: int = MIN_HOOKS,
                min_mechanisms: int = 5) -> list[str]:
    criteria = criteria or HOOK_CRITERIA
    problems = []
    if len(hooks) < min_hooks:
        problems.append(f"only {len(hooks)} hook candidates; generate at least {min_hooks}")
    for h in hooks:
        missing = [k for k in criteria if not isinstance(h.get(k), (int, float))]
        if missing:
            problems.append(f"hook '{h.get('text', '')[:30]}' lacks scores for {missing}")
        if h.get("mechanism") not in HOOK_MECHANISMS:
            problems.append(f"hook '{h.get('text', '')[:30]}' needs a mechanism from {HOOK_MECHANISMS}")
    if len({h.get("mechanism") for h in hooks}) < min_mechanisms:
        problems.append(f"explore at least {min_mechanisms} different hook mechanisms")
    if problems:
        return problems
    best = score_hooks(hooks, criteria)[0]
    if not best["eligible"]:
        return ["no hook candidate scored 7 or more on accuracy"]
    if best["text"].strip() != chosen.strip():
        problems.append(f"the chosen hook is not the top-scoring eligible hook ('{best['text']}')")
    return problems


QUALITY_CHECKS = ["fact", "hook", "clarity", "retention", "originality", "naturalness", "duration", "payoff", "brand", "virality"]


def quality(scores: dict, text: str, scheme: str | None = None) -> dict:
    """Script quality out of 100: ten checks scored 0-10. Duration is measured, not self-assessed.
    Approval needs 90+ overall and nothing below 7. A high score is a writing standard, not a forecast of views."""
    est = estimate_seconds(text)
    sc = limits(scheme)
    lo, hi = sc["target_seconds"]
    hard = sc["hard_max_seconds"]
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


# v4 creative score (the creator's rubric). Each criterion scored 0-10 and weighted to 100. Facts are a separate hard gate.
CREATIVE_V4 = {"hook": 20, "clarity": 15, "human_delivery": 15, "relevance": 15, "information": 15, "retention": 10,
               "discussion": 10}
CREATIVE_TARGET, MAX_REVISIONS = 90, 3


def creative(scores: dict, revisions: int = 0, limitation: str = "") -> dict:
    """Weighted creative total. Below 90 is allowed only after the third revision and with the limitation stated."""
    missing = [k for k in CREATIVE_V4 if not isinstance(scores.get(k), (int, float)) or not 0 <= scores[k] <= 10]
    total = round(sum(w * float(scores.get(k, 0)) / 10 for k, w in CREATIVE_V4.items()), 1)
    problems = [f"creative scores missing or out of 0-10: {missing}"] if missing else []
    if not isinstance(revisions, int) or not 0 <= revisions <= MAX_REVISIONS:
        problems.append(f"revisions must be 0-{MAX_REVISIONS}")
    below = total < CREATIVE_TARGET
    if below and not (revisions == MAX_REVISIONS and limitation.strip()):
        problems.append(f"creative score {total}/100 is below {CREATIVE_TARGET}: revise (attempt {revisions} of {MAX_REVISIONS}), "
                        "or after the third revision state quality_limitation")
    return {"total": total, "approved": not problems, "below_target": below, "problems": problems}


# v5 (Master Prompt V5): at least five hooks, judged on curiosity, clarity, credibility, emotional impact and natural delivery;
# accuracy stays the disqualifying gate. Quality score: six criteria weighted to 100.
HOOK_CRITERIA_V5 = ["accuracy", "curiosity", "clarity", "credibility", "emotional", "natural"]
MIN_HOOKS_V5 = 5
QUALITY_V5 = {"hook": 20, "clarity": 15, "storytelling": 20, "retention": 15, "shareability": 15, "factual_confidence": 15}


def quality_v5(scores: dict, revisions: int = 0, limitation: str = "") -> dict:
    """Editorial assessment, not a prediction of virality. Below 90: revise (max 3), then state the limitation."""
    missing = [k for k in QUALITY_V5 if not isinstance(scores.get(k), (int, float)) or not 0 <= scores[k] <= 10]
    total = round(sum(w * float(scores.get(k, 0)) / 10 for k, w in QUALITY_V5.items()), 1)
    problems = [f"quality scores missing or out of 0-10: {missing}"] if missing else []
    if not isinstance(revisions, int) or not 0 <= revisions <= MAX_REVISIONS:
        problems.append(f"revisions must be 0-{MAX_REVISIONS}")
    if isinstance(scores.get("factual_confidence"), (int, float)) and scores["factual_confidence"] < 8:
        problems.append("factual confidence below 8/10: fix the facts before anything else")
    if total < CREATIVE_TARGET and not (revisions == MAX_REVISIONS and limitation.strip()):
        problems.append(f"quality score {total}/100 is below {CREATIVE_TARGET}: revise (attempt {revisions} of {MAX_REVISIONS}), "
                        "or after the third revision state quality_limitation")
    return {"total": total, "approved": not problems, "below_target": total < CREATIVE_TARGET, "problems": problems}


# v6 (from 23 Nov 2026): five hooks for each of five finalists, one per approach; a creative quality gate; three variants.
HOOK_APPROACHES = ["surprising fact", "unexpected consequence", "direct relevance", "contrarian question", "visual demonstration"]
HOOKS_PER_FINALIST, FINALISTS_V6 = 5, 5
MAX_HOOK_WORDS = 14            # a hook has to land in the first 1-2 seconds
VARIANTS = {"A": "curiosity storytelling", "B": "practical usefulness", "C": "surprising consequences"}
CREATIVE_GATE = {
    "nontechnical_viewer_cares": "Would a nontechnical viewer care?",
    "hook_compelling": "Is the hook genuinely compelling?",
    "delivers_on_hook": "Does the story deliver on the hook?",
    "takeaway": "Is there a surprising or useful takeaway?",
    "natural_language": "Is the language natural?",
    "visualizable": "Can the story be visualized?",
    "claims_verified": "Are the claims verified?",
    "memorable_ending": "Is the ending memorable?",
    "sounds_like_creator": "Does the script sound like a real creator?",
}


def hook_text_problems(text: str) -> list[str]:
    low = re.sub(r"\s+", " ", text.lower()).strip()
    p = [f"generic hook: '{g}'" for g in GENERIC_HOOK_PHRASES if g in low]
    p += [f"banned opening: '{b}'" for b in BANNED_OPENINGS if low.startswith(b)]
    p += [f"hype word: '{h}'" for h in HYPE if h in low]
    if word_count(text) > MAX_HOOK_WORDS:
        p.append(f"{word_count(text)} words; a hook must land in 1-2 seconds (max {MAX_HOOK_WORDS})")
    return p


def check_finalist_hooks(hooks: list[dict], name: str) -> list[str]:
    """Exactly five hooks, one per approach, each scored on the v5 hook criteria and free of generic openings."""
    probs = []
    if len(hooks) != HOOKS_PER_FINALIST:
        probs.append(f"{name}: {len(hooks)} hooks; write exactly {HOOKS_PER_FINALIST} (one per approach)")
    got = sorted(h.get("approach", "?") for h in hooks)
    if sorted(got) != sorted(HOOK_APPROACHES):
        probs.append(f"{name}: hooks must use each approach once {HOOK_APPROACHES}; got {got}")
    for h in hooks:
        t = h.get("text", "")
        missing = [k for k in HOOK_CRITERIA_V5 if not isinstance(h.get(k), (int, float)) or not 0 <= h[k] <= 10]
        if missing:
            probs.append(f"{name}: hook '{t[:30]}' lacks 0-10 scores for {missing}")
        probs += [f"{name}: hook '{t[:30]}': {x}" for x in hook_text_problems(t)]
    return probs


def creative_gate(gate: dict) -> list[str]:
    """Every question answered yes, with a concrete reason. A 'no' means rewrite or choose another story."""
    probs = []
    for k, q in CREATIVE_GATE.items():
        a = gate.get(k) if isinstance(gate, dict) else None
        if not isinstance(a, dict) or not isinstance(a.get("pass"), bool) or len(str(a.get("why", "")).split()) < 4:
            probs.append(f"creative gate '{q}' needs {{pass: true/false, why: a concrete reason}}")
        elif not a["pass"]:
            probs.append(f"creative gate failed: {q} ({a['why']}); rewrite or choose another story")
    return probs
