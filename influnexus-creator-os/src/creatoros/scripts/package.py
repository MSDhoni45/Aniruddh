"""Daily recording package (sections A-F). Validates everything first and refuses to render a package that breaks a rule."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ..factcheck import claims as fcmod
from ..factcheck import evidence as ev
from ..factcheck import verification as ver
from ..research import candidates as candmod
from ..research import content_db
from ..util import write_json
from . import lint

REQUIRED = ["date", "language", "slug", "keys", "topic", "category", "topic_type", "announced_at", "why_selected", "evidence_confidence",
            "research_summary", "primary_sources", "supporting_sources", "key_facts", "uncertainties", "context",
            "script", "hook", "hooks", "quality_scores", "recording", "instagram", "linkedin", "x", "youtube", "growth",
            "x_signals", "candidates", "factcheck", "access_limits"]
MIN_CANDIDATES = 15
ENGLISH_DEFAULT_FROM = "2026-11-21"   # creator's instruction: English by default again from this IST date
MIN_CANDIDATES_V3 = 5              # v3: a shortlist of about 5-10 credible, verified candidates
REQUIRED_V2 = ["visuals"]          # v2 packages (scoring "v2", from 19 Nov 2026) also need visual suggestions for the editor
REQUIRED_V3 = ["visuals", "research_window", "generated_at", "pillar", "format", "backups", "audience", "editing",
               "limitations"]   # v3 packages (from 20 Nov 2026)
# Content pillars with their starting share of output (hypotheses; adjust only on observed performance).
PILLARS = {"ai_breakthroughs": 30, "future_tech_robotics": 20, "useful_ai_tools": 15, "big_tech_leaders": 15,
           "consumer_hardware": 10, "startups_science": 10}
FORMATS = {"A": "Something important just happened", "B": "This technology is actually useful",
           "C": "The future is already here", "D": "Everyone is talking about this, but...",
           "E": "Here's what most people missed", "F": "This changes how we use technology",
           "G": "Watch what this technology can do", "H": "The real story behind this announcement"}
AUDIENCE_QUESTIONS = ["stop_scroll", "watch_to_end", "share", "save", "comment", "follow"]
EDITING_KEYS = ["opening_visual", "key_moments", "broll", "on_screen_text", "demonstrations", "stats", "rhythm",
                "caption_emphasis", "sound"]
OPENING_WORDS, OPENING_DAYS = 3, 14
WINDOW_HOURS = 24
V3_FROM = "2026-11-20"             # from this IST date every package must use the v3 rules (v4 counts)
V4_FROM = "2026-11-21"             # (superseded by V5_FROM: from this date packages must be v5)
V5_FROM = "2026-11-21"             # from this IST date every package must use v5 (Master Prompt V5)
REQUIRED_V5 = ["verified_development", "confidence", "thumbnail_text", "pinned_comment", "edit_beats", "quality_v5",
               "revisions", "why_beats_alternatives"]
TIERED_FROM = V5_FROM = "2026-11-21"   # the tiered, risk-based verification policy is mandatory from this date
EDIT_BEATS = ["0-3", "3-10", "10-25", "25-45"]
RELEASE_TYPES = ["original release", "re-release", "remaster", "remake", "fan-made modification", "rumor", "official announcement",
                 "launch"]
MIN_CANDIDATES_V4 = 15             # v4: 15 distinct verified candidates, or say why fewer (never pad)
REQUIRED_V4 = ["why_beats_alternatives", "posting_window", "audience_hypothesis", "creative_scores", "revisions"]
POSTING_BASIS = ["hypothesis", "observed"]
# v6 (from 23 Nov 2026; the creator's daily-quality brief): 15-25 candidates scored on the v6 rubric, five finalists with five
# hooks each, three script variants, a visual plan, a creative quality gate and the performance lessons applied.
V6_FROM = "2026-11-23"
REQUIRED_V6 = ["verified_development", "confidence", "quality_v5", "revisions", "why_beats_alternatives", "finalists",
               "variants", "selected_variant", "variant_rationale", "visual_plan", "creative_gate", "learning_applied"]
VISUAL_KEYS = ["opening_visual", "broll", "screen_recordings", "demonstrations", "motion_graphics", "on_screen_text",
               "transitions"]
MAX_CAPTION_WORDS = 60
# V7 (the creator's "Viral AI & Technology Creator Engine V7", 22 Nov 2026): accepted from 22 Nov, required from 23 Nov.
# One story, 30-40 s, a seven-section brief, extraordinary claims under heightened scrutiny, persistent story history.
V7_ACCEPTED_FROM, V7_FROM = "2026-11-22", "2026-11-23"
REQUIRED_V7 = ["verified_development", "confidence", "why_beats_alternatives", "why_this_story", "story_id", "company",
               "event_date", "practical_takeaway", "audience_check", "script_checks", "recording_guidance",
               "learning_applied", "revisions"]
TAKEAWAY_KEYS = ["who_can_use", "what_it_does", "availability", "price", "difference", "limitations", "why_it_matters"]
SCRUTINY_KEYS = ["who_claimed", "what_demonstrated", "independent_confirmation", "uncertainty", "reproduced", "preliminary"]
GUIDANCE_KEYS = ["hook_emphasis", "important_pause", "final_tone"]
MAX_WHY_WORDS = 100
MIN_CANDIDATES_V7 = 20             # 20-30 credible developments when the news supports it; never filler


def is_v2(p: dict) -> bool:
    """v2 rules (claim table, visuals, hook reuse) also apply to v3 packages."""
    return p.get("scoring") in ("v2", "v3")


def is_v3(p: dict) -> bool:
    """v3 rules (window, signals, backups...) also apply to v4 packages."""
    return p.get("scoring") in ("v3", "v4", "v5", "v6", "v7")


def is_v6(p: dict) -> bool:
    return p.get("scoring") == "v6"


def is_v7(p: dict) -> bool:
    return p.get("scoring") == "v7"


def is_v4(p: dict) -> bool:
    return p.get("scoring") == "v4"


def is_v5(p: dict) -> bool:
    """v5 rules (tiered verification, quality score, window up to 72 h, language) also apply to v6 packages."""
    return p.get("scoring") in ("v5", "v6", "v7")


def is_tiered(p: dict) -> bool:
    """Tiered verification: every v5 package from 2026-11-21, or an earlier v5 package that opts in."""
    return is_v5(p) and (p.get("verification") == "tiered" or str(p.get("date", "")) >= TIERED_FROM)


def holds_for(date: str) -> list[dict]:
    """Stories already put on HOLD today (creatoros hold); they can never be selected again for this date."""
    import json
    f = config.path("daily", date, "holds.json")
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def hook_criteria_for(p: dict) -> list[str]:
    return (lint.HOOK_CRITERIA_V5 if is_v5(p) else lint.HOOK_CRITERIA_V4 if is_v4(p) else lint.HOOK_CRITERIA_V3 if is_v3(p)
            else lint.HOOK_CRITERIA)


def v5_problems(p: dict) -> list[str]:
    probs = []
    v6 = is_v6(p) or is_v7(p)   # v6/v7 replace thumbnail, pinned comment and edit beats with the visual plan (optional extras)
    for f in ("verified_development", "why_beats_alternatives") + (() if v6 else ("thumbnail_text", "pinned_comment")):
        if not str(p.get(f, "")).strip():
            probs.append(f"{f} is empty")
    if p.get("confidence") not in candmod.CONFIDENCE:
        probs.append(f"confidence must be one of {candmod.CONFIDENCE}")
    beats = p.get("edit_beats") if isinstance(p.get("edit_beats"), dict) else {}
    missing = [b for b in EDIT_BEATS if not str(beats.get(b, "")).strip()]
    if missing and not (v6 and not beats):
        probs.append(f"edit_beats: missing {missing} (editing directions per beat)")
    if len(str(p.get("thumbnail_text", "")).split()) > 6:
        probs.append("thumbnail_text: keep it to six words or fewer")
    if p.get("category") == "GAMING" and p.get("release_type") not in RELEASE_TYPES:
        probs.append(f"gaming story: release_type must be one of {RELEASE_TYPES} (never call a re-release or rumour a launch)")
    w = p.get("research_window") or {}
    if w.get("hours", 24) > 24 and not str(p.get("window_expansion_reason", "")).strip():
        probs.append("research window beyond 24 hours needs window_expansion_reason (no strong verified story in 24 hours)")
    return probs


def _items(v) -> list:
    return v if isinstance(v, list) else ([v] if isinstance(v, (str, dict)) and v else [])


def v6_problems(p: dict, ranked: list[dict], ready: dict) -> list[str]:
    """Finalists, 25 hooks, three variants, visual plan, creative gate, learning (RUNBOOK "v6")."""
    probs = []
    eligible = [c for c in ranked if c["eligible"]]
    fin = p["finalists"] if isinstance(p["finalists"], list) else []
    names = [f.get("headline") for f in fin]
    want = min(lint.FINALISTS_V6, len(eligible))
    if len(fin) != want:
        probs.append(f"finalists: {len(fin)} listed; select the strongest {want} eligible candidates")
    if want < lint.FINALISTS_V6 and not str(p.get("finalist_shortfall_reason", "")).strip():
        probs.append(f"only {want} eligible candidates: explain in finalist_shortfall_reason (never pad with weak stories)")
    top = [c["headline"] for c in eligible[:want]]
    if not p.get("creator_request") and sorted(map(str, names)) != sorted(top):
        probs.append(f"finalists must be the {want} highest-scoring eligible candidates: {top}")
    if p["topic"] not in names:
        probs.append("the selected story must be one of the finalists")
    for f in fin:
        nm = f"finalist '{str(f.get('headline'))[:30]}'"
        probs += lint.check_finalist_hooks(f.get("hooks") or [], nm)
        if f.get("headline") != p["topic"] and len(str(f.get("why_not", "")).split()) < 5:
            probs.append(f"{nm}: say in why_not why it lost to the winner")
    win = next((f for f in fin if f.get("headline") == p["topic"]), None)
    if win and not any("lacks" in x for x in lint.check_finalist_hooks(win.get("hooks") or [], "")):
        best = lint.score_hooks(win["hooks"], lint.HOOK_CRITERIA_V5)[0]
        if not best["eligible"]:
            probs.append("no hook for the winner scores 7+ on accuracy")
        elif best["text"].strip() != p["hook"].strip():
            probs.append(f"the chosen hook must be the winner's top-scoring accurate hook ('{best['text']}')")
    var = p["variants"] if isinstance(p["variants"], dict) else {}
    texts = []
    for k, angle in lint.VARIANTS.items():
        v = var.get(k) if isinstance(var.get(k), dict) else {}
        t = str(v.get("script", "")).strip()
        if not t:
            probs.append(f"variant {k} ({angle}) is missing its script")
            continue
        texts.append(t)
        chk = lint.check(t, p["language"], "v6")
        probs += [f"variant {k}: {x}" for x in chk["problems"]]
        lo, hi = lint.limits("v6")["target_words"]
        if not lo <= chk["words"] <= hi:
            probs.append(f"variant {k}: {chk['words']} words; write {lo}-{hi}")
        if chk["seconds"] < lint.limits("v6")["target_seconds"][0]:
            probs.append(f"variant {k}: about {chk['seconds']} s; under the 35 s minimum")
    if len(set(texts)) < len(texts):
        probs.append("variants must be genuinely different scripts")
    sel = p["selected_variant"]
    if sel not in lint.VARIANTS:
        probs.append(f"selected_variant must be one of {list(lint.VARIANTS)}")
    elif str((var.get(sel) or {}).get("script", "")).strip() != p["script"].strip():
        probs.append(f"script must be the selected variant {sel}'s text, word for word")
    if len(str(p["variant_rationale"]).split()) < 6:
        probs.append("variant_rationale: say why this variant beat the other two")
    vp = p["visual_plan"] if isinstance(p["visual_plan"], dict) else {}
    for k in ("opening_visual", "on_screen_text", "transitions"):
        if not _items(vp.get(k)):
            probs.append(f"visual_plan.{k} is empty")
    shown = [k for k in ("broll", "screen_recordings", "demonstrations", "motion_graphics") if _items(vp.get(k))]
    if len(shown) < 2:
        probs.append("visual_plan: give at least two of broll, screen_recordings, demonstrations, motion_graphics")
    for k in ("demonstrations", "screen_recordings"):
        for it in _items(vp.get(k)):
            src = str(it.get("source", "")) if isinstance(it, dict) else ""
            if not (isinstance(it, dict) and it.get("what") and (src.startswith("http") or src == "creator-recorded")):
                probs.append(f"visual_plan.{k}: each item needs what and source (a URL of real footage, or "
                             "'creator-recorded'); never describe a demonstration that does not exist")
    probs += lint.creative_gate(p["creative_gate"])
    cv = (p["creative_gate"] or {}).get("claims_verified") if isinstance(p["creative_gate"], dict) else None
    if isinstance(cv, dict) and cv.get("pass") and ready.get("status") != ver.READY:
        probs.append("creative gate says the claims are verified, but the claim table is not RECORDING READY")
    if len(str(p["learning_applied"]).split()) < 5:
        probs.append("learning_applied: say what the performance data changed today, or that no data is connected yet")
    if len(str(p["instagram"].get("caption", "")).split()) > MAX_CAPTION_WORDS:
        probs.append(f"instagram caption: keep it concise ({MAX_CAPTION_WORDS} words or fewer)")
    return probs


def _filled(v) -> bool:
    return bool(str(v if v is not None else "").strip())


def v7_problems(p: dict, ready: dict) -> list[str]:
    probs = []
    if len(str(p["why_this_story"]).split()) > MAX_WHY_WORDS or not _filled(p["why_this_story"]):
        probs.append(f"why_this_story: 1-{MAX_WHY_WORDS} words (why it matters, what is interesting, the X signal, why it won)")
    if "x" not in str(p["why_this_story"]).lower() and "social" not in str(p["why_this_story"]).lower():
        probs.append("why_this_story must state the observable X/social signal (or that it is unverified)")
    for k in ("story_id", "company", "event_date"):
        if not _filled(p[k]):
            probs.append(f"{k} is empty (story history)")
    tk = p["practical_takeaway"] if isinstance(p["practical_takeaway"], dict) else {}
    missing = [k for k in TAKEAWAY_KEYS if not _filled(tk.get(k))]
    if missing:
        probs.append(f"practical_takeaway: fill {missing} (use UNKNOWN or 'not applicable'; never invent availability or price)")
    ac = p["audience_check"] if isinstance(p["audience_check"], dict) else {}
    missing = [k for k in lint.AUDIENCE_CHECK_V7 if len(str(ac.get(k, "")).split()) < 3]
    if missing:
        probs.append(f"audience_check: answer {missing} in a sentence each")
    rg = p["recording_guidance"] if isinstance(p["recording_guidance"], dict) else {}
    missing = [k for k in GUIDANCE_KEYS if not _filled(rg.get(k))]
    if missing:
        probs.append(f"recording_guidance: fill {missing} (only these three)")
    sc = p["script_checks"].get("factual_accuracy") if isinstance(p["script_checks"], dict) else None
    if isinstance(sc, dict) and sc.get("pass") and ready.get("status") != ver.READY:
        probs.append("script check says the facts are accurate, but the claim table is not RECORDING READY")
    ex = [c for c in p["factcheck"]["claims"] if c.get("in_script")
          and (c.get("extraordinary") or ev.is_extraordinary(c.get("text", "")))]
    if ex:
        sc = p.get("scrutiny") if isinstance(p.get("scrutiny"), dict) else {}
        missing = [k for k in SCRUTINY_KEYS if not _filled(sc.get(k))]
        if missing:
            probs.append(f"extraordinary claim in the script ({ex[0]['id']}): fill scrutiny {missing}")
    if len(str(p["learning_applied"]).split()) < 5:
        probs.append("learning_applied: say what the performance data changed today, or that none is connected")
    if len(str(p["instagram"].get("caption", "")).split()) > MAX_CAPTION_WORDS:
        probs.append(f"instagram caption: keep it concise ({MAX_CAPTION_WORDS} words or fewer)")
    return probs


def v4_problems(p: dict) -> list[str]:
    probs = []
    if not str(p["why_beats_alternatives"]).strip():
        probs.append("why_beats_alternatives: say why this story beats the runners-up")
    pw = p["posting_window"] if isinstance(p["posting_window"], dict) else {}
    if not pw.get("window_ist") or pw.get("basis") not in POSTING_BASIS or not pw.get("rationale"):
        probs.append(f"posting_window needs window_ist, rationale and basis {POSTING_BASIS} (hypothesis until the "
                     "account's own data shows a better time)")
    if pw.get("basis") == "observed" and not pw.get("evidence"):
        probs.append("posting_window basis 'observed' needs evidence (which reels' numbers)")
    if not str(p["audience_hypothesis"]).strip():
        probs.append("audience_hypothesis: the expected response, stated as a hypothesis to check against real numbers")
    return probs


def research_window(run_start_utc: str) -> dict:
    """The 24 hours ending at the run's start, in UTC and IST."""
    import datetime as dt
    end = dt.datetime.fromisoformat(run_start_utc.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    start = end - dt.timedelta(hours=WINDOW_HOURS)
    ist = dt.timezone(dt.timedelta(hours=5, minutes=30))
    f = lambda d: d.isoformat(timespec="seconds")
    return {"start_utc": f(start), "end_utc": f(end), "start_ist": f(start.astimezone(ist)), "end_ist": f(end.astimezone(ist)),
            "hours": WINDOW_HOURS}


def source_audit_for(p: dict) -> dict | None:
    """The source audit recorded for this package's day (daily/DATE/source_access.json), if any."""
    from ..research import signals
    return signals.load_audit(config.path("daily", p["date"], "source_access.json"))


def opening_repeat(hook: str, date: str, slug: str, days: int = OPENING_DAYS) -> dict | None:
    """Same first three words as a hook used in the last two weeks: an opening the audience has heard recently."""
    import datetime as dt
    import re
    first = lambda t: " ".join(re.findall(r"[a-z0-9']+", t.lower())[:OPENING_WORDS])
    d0 = dt.date.fromisoformat(date)
    for e in content_db.entries():
        if e.get("slug") == slug or not e.get("hook"):
            continue
        age = (d0 - dt.date.fromisoformat(e["date"])).days
        if 0 <= age <= days and first(e["hook"]) == first(hook):
            return e
    return None


def v3_problems(p: dict, ranked: list[dict]) -> list[str]:
    """The v3 package rules: pillar, format, backups, audience questions, editing notes, cross-platform signals."""
    from ..research import signals
    problems = []
    if p["pillar"] not in PILLARS:
        problems.append(f"pillar must be one of {list(PILLARS)}")
    if p["format"] not in FORMATS:
        problems.append(f"format must be one of {list(FORMATS)} ({'; '.join(f'{k}: {v}' for k, v in FORMATS.items())})")
    eligible = [c["headline"] for c in ranked if c["eligible"]]
    backups = p["backups"] if isinstance(p["backups"], list) else []
    for b in backups:
        if b == p["topic"]:
            problems.append("a backup story cannot be the selected story")
        elif b not in eligible:
            problems.append(f"backup '{b[:40]}' must be an eligible candidate")
    if len(set(backups)) < 2 and not p.get("backup_shortfall_reason"):
        problems.append(f"name two backup stories (eligible candidates) or explain in backup_shortfall_reason "
                        f"({max(len(eligible) - 1, 0)} other eligible)")
    aud = p["audience"] if isinstance(p["audience"], dict) else {}
    missing = [q for q in AUDIENCE_QUESTIONS if not str(aud.get(q, "")).strip()]
    if missing:
        problems.append(f"audience: answer {missing} (why would someone stop, finish, share, save, comment, follow?)")
    ed = p["editing"] if isinstance(p["editing"], dict) else {}
    missing = [k for k in EDITING_KEYS if not ed.get(k)]
    if missing:
        problems.append(f"editing: missing {missing}")
    if not isinstance(p["limitations"], list):
        problems.append("limitations must be a list (research limits for today; empty only if nothing was blocked)")
    blocked = signals.blocked_platforms(source_audit_for(p))
    win = next((c for c in ranked if c["headline"] == p["topic"]), None)
    for c in ranked:
        for i, sig in enumerate(c.get("signals") or []):
            problems += [f"candidate '{c['headline'][:30]}': {x}" for x in signals.signal_problems(sig, i, blocked)]
    if win is not None and not win.get("signals"):
        problems.append("the selected story needs cross-platform evidence in candidate.signals (at least one source)")
    if blocked and not p["limitations"]:
        problems.append(f"limitations: the source audit found {sorted(blocked)} blocked; say so")
    old = opening_repeat(p["hook"], p["date"], p["slug"])
    if old:
        problems.append(f"the hook opens like the {old['date']} hook ('{old['hook']}'); vary the opening")
    return problems


def window_problems(w, allowed_hours: tuple = (WINDOW_HOURS,)) -> list[str]:
    import datetime as dt
    if not isinstance(w, dict):
        return ["research_window must be an object (use `creatoros runlog start`, which prints it)"]
    try:
        a = dt.datetime.fromisoformat(str(w["start_utc"]).replace("Z", "+00:00"))
        b = dt.datetime.fromisoformat(str(w["end_utc"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return ["research_window needs ISO start_utc and end_utc"]
    if not any(abs((b - a).total_seconds() - h * 3600) <= 300 for h in allowed_hours):
        return [f"research_window must span {' or '.join(map(str, allowed_hours))} hours (it spans {(b - a).total_seconds() / 3600:.1f})"]
    return []


def _hook_tokens(t: str) -> set[str]:
    import re
    return {w for w in re.findall(r"[a-z0-9']+", t.lower()) if len(w) > 2}


def reused_hook(hook: str, slug: str, path=None) -> dict | None:
    """A hook is reused if it shares most of its words with a hook already used for another topic."""
    a = _hook_tokens(hook)
    for e in content_db.entries(path):
        if e.get("slug") == slug or not e.get("hook"):
            continue
        b = _hook_tokens(e["hook"])
        if a and b and len(a & b) / len(a | b) >= 0.6:
            return e
    return None


def _words(text: str) -> int:
    return len(text.split())


def with_winner_hooks(p: dict) -> dict:
    """v6: the winner's five hooks are the package's hook list (no need to repeat them)."""
    if is_v6(p) and "hooks" not in p and isinstance(p.get("finalists"), list):
        win = next((f for f in p["finalists"] if f.get("headline") == p.get("topic")), {})
        return {**p, "hooks": list(win.get("hooks") or [])}
    return p


def validate(p: dict) -> tuple[list[str], dict]:
    if str(p.get("date", "")) >= V7_FROM and not is_v7(p):
        return [f"packages dated {V7_FROM} or later must use \"scoring\": \"v7\" (RUNBOOK.md \"V7\"); this one is "
                f"'{p.get('scoring', 'v1')}'"], {}
    if is_v7(p) and str(p.get("date", "")) < V7_ACCEPTED_FROM:
        return [f"v7 packages start on {V7_ACCEPTED_FROM}"], {}
    p = with_winner_hooks(p)
    if str(p.get("date", "")) >= V5_FROM and not is_v5(p):
        return [f"packages dated {V5_FROM} or later must use \"scoring\": \"v5\" (RUNBOOK.md); this one is "
                f"'{p.get('scoring', 'v1')}'"], {}
    if str(p.get("date", "")) >= V3_FROM and not is_v3(p):
        return [f"packages dated {V3_FROM} or later must use \"scoring\": \"v3\" (RUNBOOK.md); this one is "
                f"'{p.get('scoring', 'v1')}'"], {}
    extra = REQUIRED_V3 + (REQUIRED_V4 if is_v4(p) else []) + (REQUIRED_V7 if is_v7(p) else REQUIRED_V6 if is_v6(p) else REQUIRED_V5 if is_v5(p) else []) \
        if is_v3(p) else (REQUIRED_V2 if is_v2(p) else [])
    base = [k for k in REQUIRED if not ((is_v4(p) or is_v5(p)) and k == "quality_scores")]
    problems = [f"missing: {k}" for k in base + extra if k not in p]
    if problems:
        return problems, {}
    scheme = "v7" if is_v7(p) else "v6" if is_v6(p) else "v5" if is_v5(p) else ("v3" if is_v3(p) else None)   # length: v5 85-105 words / 35-45 s; v3 and v4 90-105 / 40-45
    window = p.get("research_window") if is_v3(p) else None
    if is_v3(p):
        problems += window_problems(window, (24, 48, 72) if is_v5(p) else (WINDOW_HOURS,))
        for c in p["factcheck"]["claims"]:
            if c.get("in_script") and not c.get("retrieved_at"):
                problems.append(f"claim {c.get('id')}: v3 claims in the script need retrieved_at (when the source was read)")
    if is_v2(p):
        if not p["visuals"] or not all(isinstance(v, str) and v.strip() for v in p["visuals"]):
            problems.append("visuals: list at least one B-roll or graphic suggestion for the editor")
        want = "v7" if is_v7(p) else "v6" if is_v6(p) else "v4" if is_v4(p) else ("v3" if is_v3(p) else "v2")      # v5 packages score candidates with the v3 rubric
        if any(candmod.scheme(c) != want for c in p["candidates"]):
            problems.append(f"a {p['scoring']} package must score every candidate with the {want} criteria")
        old = reused_hook(p["hook"], p["slug"])
        if old:
            problems.append(f"hook too similar to the hook used on {old['date']} ('{old['hook']}')")
    allowed = config.settings().get("languages_allowed", ["english"])
    if p["language"] not in allowed:
        problems.append(f"package language is '{p['language']}'; allowed: {allowed}")
    # Packages written while Hinglish was the default (before 21 Nov 2026) stay valid as historical records.
    if (is_v5(p) and p["date"] >= ENGLISH_DEFAULT_FROM and p["language"] != config.settings().get("language", "english")
            and not p.get("language_requested_by_creator")):
        problems.append(f"v5 packages use the configured language '{config.settings().get('language')}'; another language needs "
                        "language_requested_by_creator: true (the creator asked for it)")
    chk = lint.check(p["script"], p["language"], scheme)
    problems += [f"script: {x}" for x in chk["problems"]]
    copy_fields = {"instagram caption": p["instagram"].get("caption", ""), "instagram cover": p["instagram"].get("cover_headline", ""),
                   "linkedin": " ".join(str(p["linkedin"].get(k, "")) for k in ("caption", "business_relevance", "discussion_prompt")),
                   "x": p["x"].get("post", ""), "youtube": " ".join([p["youtube"].get("title", ""), p["youtube"].get("description", "")]),
                   "hooks": " / ".join(h.get("text", "") for h in p["hooks"])}
    for name, text in copy_fields.items():
        problems += [f"{name}: {x}" for x in lint.language_problems(text, p["language"])]
    if len(p["x"].get("post", "")) > 280:
        problems.append(f"X post is {len(p['x']['post'])} characters; keep it within 280")
    if not p["script"].strip().startswith(p["hook"].strip()):
        problems.append("script must open with the chosen hook")
    if is_v7(p):
        problems += [f"hooks: {x}" for x in lint.check_hooks_v7(p["hooks"], p["hook"])]
    elif is_v6(p):
        pass                                             # v6: five hooks per finalist, checked in v6_problems
    elif is_v5(p):
        problems += [f"hooks: {x}" for x in lint.check_hooks(p["hooks"], p["hook"], lint.HOOK_CRITERIA_V5,
                                                             lint.MIN_HOOKS_V5, min_mechanisms=3)]
    else:
        hook_criteria = lint.HOOK_CRITERIA_V4 if is_v4(p) else (lint.HOOK_CRITERIA_V3 if is_v3(p) else None)
        problems += [f"hooks: {x}" for x in lint.check_hooks(p["hooks"], p["hook"], hook_criteria)]
    if is_v7(p):
        q = lint.script_checks_v7(p["script_checks"])
        cr = q
        problems += v5_problems(p)
        if not isinstance(p["revisions"], int) or not 0 <= p["revisions"] <= lint.MAX_REVISIONS:
            problems.append(f"revisions must be 0-{lint.MAX_REVISIONS}")
    elif is_v5(p):
        cr = lint.quality_v5(p["quality_v5"], p["revisions"], p.get("quality_limitation", ""))
        q = {**cr, "scores": dict(p["quality_v5"])}
        problems += v5_problems(p)
    elif is_v4(p):
        cr = lint.creative(p["creative_scores"], p["revisions"], p.get("quality_limitation", ""))
        q = {**cr, "scores": dict(p["creative_scores"])}
        problems += v4_problems(p)
    else:
        q = lint.quality(p["quality_scores"], p["script"], scheme)
    problems += [f"quality: {x}" for x in q["problems"]]
    problems += [f"fact-check: {x}" for x in fcmod.validate(p["factcheck"], p["script"])]
    if is_tiered(p) and source_audit_for(p) is None:
        problems.append("no source audit for this date: run `creatoros runlog start` (it audits sources before research) "
                        "or `creatoros sources-audit --date DATE`")
    if is_tiered(p):
        ready = ver.readiness_v5(p["factcheck"]["claims"], p["script"], p.get("unresolved", []), p["date"],
                                 extraordinary_rule=is_v7(p))
    else:
        ready = ver.readiness(p["factcheck"]["claims"], p["script"], p.get("unresolved", []), v2=is_v2(p))
    problems += [f"claim table: {x}" for x in ready["problems"]]
    if not is_tiered(p):
        problems += ver.story_confidence_ok(p["evidence_confidence"], p["factcheck"]["claims"])
    held = {h["topic"]: h for h in holds_for(p["date"])}
    for c in p["candidates"]:
        if c.get("headline") in held and not c.get("hold_reason"):
            problems.append(f"candidate '{c['headline'][:40]}' was put on HOLD today ({held[c['headline']]['reason']}); "
                            "copy that into its hold_reason so the next-ranked story is chosen")
    ranked = candmod.rank(p["candidates"], window)
    if is_v3(p):
        problems += v3_problems(p, ranked)
    for c in ranked:
        problems += [f"candidate '{c.get('headline', '?')[:40]}': {x}" for x in c["problems"]]
    eligible = [c for c in ranked if c["eligible"]]
    if not eligible:
        problems.append("no eligible candidate")
    elif p.get("creator_request") and any(c["headline"] == p["topic"] for c in eligible):
        pass                                             # REEL SCRIPT: [TOPIC] - the creator chose the story
    elif eligible[0]["headline"] != p["topic"]:
        problems.append(f"topic must be the top eligible candidate ('{eligible[0]['headline']}')")
    credible = [c for c in ranked if not c.get("rejected") and c.get("evidence_confidence") != "LOW"]
    need = MIN_CANDIDATES_V7 if is_v7(p) else MIN_CANDIDATES_V4 if (is_v4(p) or is_v6(p)) else (MIN_CANDIDATES_V3 if is_v3(p) else MIN_CANDIDATES)
    if len(credible) < need and not p.get("candidate_shortfall_reason"):
        problems.append(f"{len(credible)} credible candidates; find {need} or explain in candidate_shortfall_reason")
    n = _words(p["research_summary"])
    if not 100 <= n <= 150:
        problems.append(f"research summary is {n} words; keep it to 100-150")
    if not 3 <= len(p["instagram"].get("hashtags", [])) <= 5:
        problems.append("Instagram needs 3-5 hashtags")
    if p["evidence_confidence"] not in candmod.CONFIDENCE:
        problems.append("evidence_confidence must be HIGH, MEDIUM or LOW")
    for s in p["primary_sources"] + p["supporting_sources"]:
        if not str(s.get("url", "")).startswith("http"):
            problems.append(f"source '{s.get('label')}' needs a URL")
    prior = content_db.find_repeat(p["topic"], p["keys"], p["date"], ignore_slug=p["slug"])
    if prior and not p.get("material_update_of"):
        problems.append(f"repeat of {prior['date']} '{prior['topic']}'; set material_update_of to the new development")
    if is_v7(p):
        problems += v7_problems(p, ready)
    if is_v6(p) or is_v7(p):
        if is_v6(p):
            problems += v6_problems(p, ranked, ready)
        wlo, whi = lint.limits(scheme)["target_words"]
        if not wlo <= chk["words"] <= whi:
            problems.append(f"script: {chk['words']} words; write {wlo}-{whi} at a natural pace")
    return problems, {"lint": chk, "quality": q, "ranked": ranked, "ready": ready, "hooks": p["hooks"]}


def render(p: dict, info: dict) -> str:
    chk, q, ranked = info["lint"], info["quality"], info["ranked"]
    win = next(c for c in ranked if c["eligible"])
    r, ig, li, xx, yt, g = p["recording"], p["instagram"], p["linkedin"], p["x"], p["youtube"], p["growth"]
    rd = info["ready"]
    L = [f"# Recording package: {p['date']}", "", f"## STATUS: {rd['status']}", ""]
    if rd["reasons"]:
        L += ["Do not record this script. Unresolved:", ""] + [f"- {x}" for x in rd["reasons"]] + [""]
    if p.get("disclosure"):
        L += [f"> {p['disclosure']}", ""]
    L += ["## A. Today's winning topic", "",
          f"- **Topic:** {p['topic']}", f"- **Language:** {p['language'].capitalize()}", f"- **Category:** {p['category']} ({p['topic_type']})",
          f"- **Original announcement date:** {p['announced_at']}",
          f"- **Viral potential score:** {win['trend_score']}/100" + (f" (unknown: {', '.join(win['unknown_criteria'])})" if win["unknown_criteria"] else ""),
          f"- **Evidence confidence:** {p['evidence_confidence']}", f"- **Why selected:** {p['why_selected']}", "",
          "## B. Verified research", "", p["research_summary"], "", "**Key verified facts**", ""]
    L += [f"- {f}" for f in p["key_facts"]]
    L += ["", "**Uncertainties**", ""] + [f"- {u}" for u in p["uncertainties"]]
    L += ["", "**Context**", "", p["context"], "", "**Primary sources**", ""] + [f"- [{s['label']}]({s['url']})" for s in p["primary_sources"]]
    L += ["", "**Supporting sources**", ""] + [f"- [{s['label']}]({s['url']})" for s in p["supporting_sources"]]
    L += ["", "## C. Final recording script", "", "```", p["script"].strip(), "```", "",
          f"{chk['words']} words · about {chk['seconds']} s at {chk['words_per_minute']:.0f} words per minute ({chk['pace_basis']}) · script quality {q['total']}/100", "",
          "## Claim verification table", "",
          "Access: *opened* = page read directly; *search-index* = the primary site's own text read through search, page not opened; "
          "*secondary-only* = only other outlets report it.", "", ver.table(p["factcheck"]["claims"]),
          "## D. Recording direction", "", "Delivery only. Keep your natural accent; no editing instructions.", "", f"- **Tone:** {r['tone']}", f"- **Opening expression:** {r['opening_expression']}",
          f"- **Emphasise:** {', '.join(r['emphasis'])}", f"- **Pauses:** {'; '.join(r['pauses'])}",
          f"- **Pronunciation:** {'; '.join(r['pronunciation'])}", f"- **Estimated duration:** {chk['seconds']} s", "",
          "## E. Platform content", "", "**Instagram**", "", f"Cover headline: {ig['cover_headline']}", "", ig["caption"], "",
          " ".join(ig["hashtags"]), "", "**LinkedIn**", "", li["caption"], "", f"Business relevance: {li['business_relevance']}", "",
          f"Discussion prompt: {li['discussion_prompt']}", "", "**X**", "", xx["post"], "", "**YouTube Shorts**", "",
          f"Title: {yt['title']}", "", yt["description"], "", f"Keywords: {', '.join(yt['keywords'])}", "",
          "## F. Growth reasoning", "", f"- **Why they may watch:** {g['watch']}", f"- **Why they may share:** {g['share']}",
          f"- **Why they may follow:** {g['follow']}", f"- **Audience segment:** {g['segment']}",
          f"- **What could make it underperform:** {g['underperform']}", "",
          "A high internal score is a writing standard, not a forecast. No view counts are promised.", "", "---", "",
          "## Appendix 1: X signals", "", "Engagement counts appear only where they were actually observed.", "",
          "| Time (UTC) | Account | Post | Likes | Reposts | Views |", "|---|---|---|---|---|---|"]
    for s in p["x_signals"]:
        L.append(f"| {s.get('time', 'UNKNOWN')} | {s['account']} | [{s['summary']}]({s['url']}) | {s.get('likes', 'UNKNOWN')} | {s.get('reposts', 'UNKNOWN')} | {s.get('views', 'UNKNOWN')} |")
    L += ["", "## Appendix 2: Candidates ranked", "", "| # | Topic | Type | Score | Confidence | Status |", "|---|---|---|---|---|---|"]
    for i, c in enumerate(ranked, 1):
        L.append(f"| {i} | {c['headline']} | {c['topic_type']} | {c['trend_score']} | {c['evidence_confidence']} | {'eligible' if c['eligible'] else c['ineligible_reason']} |")
    if is_v3(p):
        L += ["", "## Appendix 3: Hook candidates", "", "Scored internally; only the winning hook is delivered. All candidates are in `research.json`."]
    else:
        L += ["", "## Appendix 3: Hook candidates", "", "| Hook | Mechanism | Score /60 | Usable |", "|---|---|---|---|"]
        L += [f"| {h['text']} | {h['mechanism']} | {h['total']} | {'yes' if h['eligible'] else 'no (accuracy)'} |" for h in lint.score_hooks(p["hooks"])]
    if is_v4(p):
        L += ["", "## Appendix 4: Creative score (facts are a separate gate)", "", "| Criterion | Weight | Score /10 |", "|---|---|---|"]
        L += [f"| {k} | {w} | {q['scores'].get(k)} |" for k, w in lint.CREATIVE_V4.items()]
        L += ["", f"Total {q['total']}/100 after {p['revisions']} revision(s)" + (f". Limitation: {p['quality_limitation']}" if p.get("quality_limitation") else "")]
    else:
        L += ["", "## Appendix 4: Script quality", "", "| Check | Score /10 |", "|---|---|"]
        L += [f"| {k} | {v} |" for k, v in q["scores"].items() if k in lint.QUALITY_CHECKS]
    L += ["", "## Appendix 5: Research access limits", ""]
    L += [f"- {a}" for a in p["access_limits"]]
    return "\n".join(L) + "\n"


_WEAK_END = {"a", "an", "the", "its", "it's", "of", "to", "for", "and", "but", "or", "in", "on", "at", "by", "with", "that", "their",
             "his", "her", "my", "your", "our", "is", "are", "was", "be", "it"}


def render_today_v5(p: dict, info: dict) -> str:
    """Master Prompt V5 format: A-G, script near the top, ready for a teleprompter."""
    from ..factcheck.verification import access_summary
    chk, rd, r, ig, yt = info["lint"], info["ready"], p["recording"], p["instagram"], p["youtube"]
    claims = [c for c in p["factcheck"]["claims"] if c.get("in_script")]
    q = info["quality"]
    L = [f"# Today's reel: {p['date']}", "", f"**STATUS: {rd['status']}**", ""]
    if rd["reasons"]:
        L += ["Do not record. Unresolved:"] + [f"- {x}" for x in rd["reasons"]] + [""]
    L += ["## A. TODAY'S SELECTED TOPIC", "", f"**Story title:** {p['topic']}", f"**Why selected:** {p['why_beats_alternatives']}",
          f"**Verified development:** {p['verified_development']}", f"**Publication date:** {p['announced_at']}",
          f"**Confidence:** {p['confidence']}" + (f" | **Release type:** {p['release_type']}" if p.get("release_type") else ""), "",
          "## B. FINAL RECORDING SCRIPT", "", "```", p["script"].strip(), "```", "",
          f"About {chk['seconds']} seconds ({chk['words']} words, {chk['pace_basis']}).", "",
          "## C. RECORDING DIRECTIONS", "", f"- **Tone:** {r['tone']}", f"- **Pacing:** {r.get('pacing', r['opening_expression'])}",
          f"- **Emphasis:** {', '.join(r['emphasis'])}", f"- **Pauses:** {'; '.join(r['pauses'])}",
          f"- **Pronunciation:** {'; '.join(r['pronunciation'])}", "- Keep your natural accent.", "",
          "## D. EDITING DIRECTIONS", ""] + [f"- **{b} s:** {p['edit_beats'][b]}" for b in EDIT_BEATS] + [
          "- Use only footage you are licensed to use; label illustrations as illustrations.", "",
          "## E. POSTING PACKAGE", "", f"**Instagram caption:** {ig['caption']}", "", f"**YouTube Shorts title:** {yt['title']}", "",
          f"**Hashtags:** {' '.join(ig['hashtags'])}", "", f"**Thumbnail text:** {p['thumbnail_text']}", "",
          f"**Pinned comment:** {p['pinned_comment']}", "", "## F. FACT-CHECK", "", f"*{access_summary(claims)}*"]
    if ver.is_tiered(claims):
        from ..factcheck import evidence as ev
        for c in claims:
            lv = ev.level(c)
            srcs = ", ".join(f"[{ev.outlet(it)}]({it['url']})" for it in c.get("evidence") or [])
            L.append(f"- {c['text']}: **{lv['level']}** ({c.get('risk_effective', c.get('risk'))}-risk: {c.get('risk_why', 'declared')}; "
                     f"{lv['why']}). {c['status']}. Sources: {srcs}"
                     + (f". Note: {c['note']}" if c.get("note") else ""))
    else:
        for c in claims:
            L.append(f"- {c['text']} — [{c.get('source_title') or 'source'}]({c['primary_source']}) ({c['status']}, {c['confidence']}, "
                     f"{c.get('source_date') or 'date unknown'}; supporting: {c.get('supporting_source') or 'none'})" + (f". Note: {c['note']}" if c.get("note") else ""))
    if p.get("uncertainties"):
        L += ["", "**Uncertain or left out:**"] + [f"- {u}" for u in p["uncertainties"]]
    L += ["", "## G. INTERNAL QUALITY SCORE", ""] + [f"- {k.replace('_', ' ').capitalize()}: {v}/10" for k, v in q["scores"].items()]
    L += [f"- **Total: {q['total']}/100** after {p['revisions']} revision(s). An editorial assessment, not a prediction of virality."]
    if p.get("quality_limitation"):
        L.append(f"- Limitation: {p['quality_limitation']}")
    L += ["", f"**Backups (DIFFERENT TOPIC):** {'; '.join(p['backups'])}", "", f"**RUN STATUS:** {run_status_line(p['date'])}",
          "", "Full research, candidates and the claim table: `package.md` and `research.json`."]
    return "\n".join(L) + "\n"


def render_today_v6(p: dict, info: dict) -> str:
    """v6 daily delivery: the eight items the creator asked for, nothing more. Finalists, the 25 hooks, the three variants,
    the full visual plan and the quality gate stay in creative.md (internal)."""
    from ..factcheck import evidence as ev
    chk, rd, ig, r = info["lint"], info["ready"], p["instagram"], p["recording"]
    claims = [c for c in p["factcheck"]["claims"] if c.get("in_script")]
    L = [f"# Today's reel: {p['date']}", "", f"**STATUS: {rd['status']}**", ""]
    if rd["reasons"]:
        L += ["Do not record. Unresolved:"] + [f"- {x}" for x in rd["reasons"]] + [""]
    L += ["## 1. Today's story", "", f"**{p['topic']}**", "", p["verified_development"], "",
          f"Published: {p['announced_at']} · Confidence: {p['confidence']}", "",
          "## 2. Why it was selected", "", p["why_beats_alternatives"], "",
          "## 3. Verified facts and sources", ""]
    for c in claims:
        lv = ev.level(c)["level"] if ver.is_tiered(claims) else c.get("confidence", "")
        items = c.get("evidence") or [{"url": c.get("primary_source", "")}]
        srcs = ", ".join(f"[{ev.outlet(it) if isinstance(it, dict) else 'source'}]({it['url'] if isinstance(it, dict) else it})"
                         for it in items)
        L.append(f"- {c['text']} — **{c['status']}** ({lv}). {srcs}")
    if p.get("uncertainties"):
        L += ["", "Not in the script / uncertain: " + "; ".join(p["uncertainties"][:4])]
    L += ["", "## 4. Recording-ready script", "", "```", p["script"].strip(), "```", "",
          "## 5. Estimated speaking duration", "",
          f"About {chk['seconds']} seconds ({chk['words']} words; {chk['pace_basis']}).",
          f"Delivery: {r['tone']} Pauses: {'; '.join(r['pauses'])}.", "",
          "## 6. Opening visual", "", str(p["visual_plan"]["opening_visual"]), "",
          "## 7. Caption", "", ig["caption"], "", "## 8. Hashtags", "", " ".join(ig["hashtags"]), "", "---", "",
          f"Backups (DIFFERENT TOPIC): {'; '.join(p['backups'])}", "", f"RUN STATUS: {run_status_line(p['date'])}", "",
          "Internal: `creative.md` (finalists, 25 hooks, 3 variants, visual plan, quality gate), `package.md`, `research.json`."]
    return "\n".join(L) + "\n"


def _fmt(it) -> str:
    if isinstance(it, dict):
        return f"{it.get('what')} (source: {it.get('source')})"
    return str(it)


def render_creative(p: dict, info: dict) -> str:
    """Internal editorial record (v6): why the winner won, every hook, every variant, the visual plan and the gate."""
    ranked = {c["headline"]: c for c in info["ranked"]}
    L = [f"# Creative record: {p['date']}", "", "Internal. The creator receives only `today.md`.", "",
         "## Finalists (v6 rubric, editorial estimates, not view predictions)", "",
         "| # | Story | Score /100 | Claim status | Result |", "|---|---|---|---|---|"]
    for i, f in enumerate(p["finalists"], 1):
        c = ranked.get(f.get("headline"), {})
        res = "WINNER" if f.get("headline") == p["topic"] else f"lost: {f.get('why_not', '')}"
        L.append(f"| {i} | {f.get('headline')} | {c.get('trend_score', '?')} | {c.get('claim_status', '?')} | {res} |")
    L += ["", f"**Why the winner beats the alternatives:** {p['why_beats_alternatives']}", "", "## Hooks (5 per finalist)", ""]
    for f in p["finalists"]:
        L += [f"### {f.get('headline')}", "", "| Hook | Approach | Total /60 | Accurate |", "|---|---|---|---|"]
        for h in lint.score_hooks(f.get("hooks") or [], lint.HOOK_CRITERIA_V5):
            mark = " **(chosen)**" if h["text"].strip() == p["hook"].strip() else ""
            L.append(f"| {h['text']}{mark} | {h.get('approach')} | {h['total']} | {'yes' if h['eligible'] else 'no'} |")
        L.append("")
    L += ["## Script variants", ""]
    for k, angle in lint.VARIANTS.items():
        v = p["variants"].get(k, {})
        chk = lint.check(v.get("script", ""), p["language"], "v6")
        L += [f"### Version {k}: {angle}" + (" (SELECTED)" if k == p["selected_variant"] else ""), "",
              f"{chk['words']} words, about {chk['seconds']} s", "", "```", v.get("script", "").strip(), "```", ""]
    L += [f"**Why {p['selected_variant']}:** {p['variant_rationale']}", "", "## Visual plan", ""]
    for k in VISUAL_KEYS:
        items = _items(p["visual_plan"].get(k))
        if items:
            L += [f"**{k.replace('_', ' ').capitalize()}**"] + [f"- {_fmt(it)}" for it in items] + [""]
    L += ["## Creative quality gate", ""]
    for k, q in lint.CREATIVE_GATE.items():
        a = p["creative_gate"].get(k, {})
        L.append(f"- {q} **{'YES' if a.get('pass') else 'NO'}**: {a.get('why')}")
    q = info["quality"]
    L += ["", f"Quality score {q['total']}/100 after {p['revisions']} revision(s) (editorial assessment, not a forecast)."]
    if p.get("rejected_drafts"):
        L += ["", "## Rejected drafts", ""] + [f"- {d}" for d in p["rejected_drafts"]]
    L += ["", "## Performance learning applied", "", str(p["learning_applied"])]
    return "\n".join(L) + "\n"


def render_today_v7(p: dict, info: dict) -> str:
    """V7 daily brief: seven sections, one story, no editing plan."""
    chk, rd, ig = info["lint"], info["ready"], p["instagram"]
    claims = p["factcheck"]["claims"]
    used = [c for c in claims if c.get("in_script")]
    L = [f"# Today's reel: {p['date']}", "", f"**STATUS: {rd['status']}**", ""]
    if rd["reasons"]:
        L += ["Do not record. Unresolved:"] + [f"- {x}" for x in rd["reasons"]] + [""]
    L += ["## 1. Today's story", "", f"- **Headline:** {p['topic']}", f"- **Date:** {p['announced_at']}"
          + (f" (event: {p['event_date']})" if str(p["event_date"]) not in str(p["announced_at"]) else ""),
          f"- **Category:** {p['category']}", f"- **Confidence:** {p['confidence']}", "",
          "## 2. Why this story", "", p["why_this_story"], "",
          "## 3. Final recording script", "", "```", p["script"].strip(), "```", "",
          f"{chk['words']} words, about {chk['seconds']} s ({chk['pace_basis']}).", "",
          "## 4. Caption", "", ig["caption"], "", " ".join(ig["hashtags"]), "", "## 5. Sources", ""]
    seen = set()
    for c in used:
        for it in c.get("evidence") or []:
            if isinstance(it, dict) and it["url"] not in seen:
                seen.add(it["url"])
                L.append(f"- [{ev.outlet(it)}]({it['url']}) ({it.get('kind', 'source')}, {it.get('date') or 'date unknown'}, "
                         f"{'opened' if it.get('access') == 'opened' else 'not opened: ' + str(it.get('access'))})")
    L += ["", "## 6. Fact-check notes", "", "**Confirmed in the script:**"]
    for c in used:
        lv = ev.level(c)["level"] if ver.is_tiered(used) else c.get("confidence", "")
        L.append(f"- {c['text']} ({c['status']}, {lv})")
    if p.get("uncertainties"):
        L += ["", "**Important uncertainties:**"] + [f"- {u}" for u in p["uncertainties"]]
    left = [c for c in claims if not c.get("in_script")] + [{"text": x} for x in p.get("excluded_claims", [])]
    if left:
        L += ["", "**Excluded from the script:**"] + [f"- {c['text']}" for c in left]
    rg = p["recording_guidance"]
    L += ["", "## 7. Recording guidance", "", f"- **Hook emphasis:** {rg['hook_emphasis']}",
          f"- **Important pause:** {rg['important_pause']}", f"- **Final delivery tone:** {rg['final_tone']}", "", "---", "",
          f"RUN STATUS: {run_status_line(p['date'])}", "",
          "Internal: `package.md` (all candidates, scores, hooks, script checks) and `research.json`."]
    return "\n".join(L) + "\n"


def render_today(p: dict, info: dict) -> str:
    """The daily deliverable, in the order the creator asked for. Concise; full detail stays in package.md."""
    if is_v7(p):
        return render_today_v7(p, info)
    if is_v6(p):
        return render_today_v6(p, info)
    if is_v5(p):
        return render_today_v5(p, info)
    chk, rd = info["lint"], info["ready"]
    win = next((c for c in info["ranked"] if c["eligible"] and c["headline"] == p["topic"]), None)
    score = f"{win['trend_score']}/100 (editorial score, not a view prediction)" if win else "n/a"
    r, ig, li, xx, yt = p["recording"], p["instagram"], p["linkedin"], p["x"], p["youtube"]
    claims = [c for c in p["factcheck"]["claims"] if c.get("in_script")]
    L = [f"# Script for today: {p['date']}", "", f"**STATUS: {rd['status']}**", ""]
    if rd["reasons"]:
        L += ["Do not record. Unresolved:"] + [f"- {x}" for x in rd["reasons"]] + [""]
    L += ["**DATE:** " + p["date"], "", "**SELECTED TOPIC:** " + p["topic"], "", "**WHY THIS TOPIC:** " + p.get("why_short", p["why_selected"]), "",
          "**VIRAL POTENTIAL:** " + score, "", "**BEST HOOK:** " + p["hook"], "", "**FINAL SCRIPT:**", "", "```", p["script"].strip(), "```", "",
          f"**ESTIMATED DURATION:** about {chk['seconds']} seconds ({chk['words']} words at {chk['words_per_minute']:.0f} wpm, {chk['pace_basis']})", "",
          "**RECORDING DIRECTIONS:**", f"- Tone: {r['tone']}", f"- Pauses: {'; '.join(r['pauses'])}", f"- Emphasise: {', '.join(r['emphasis'])}",
          f"- Pronunciation: {'; '.join(r['pronunciation'])}", "- Keep your natural accent.", ""]
    if p.get("visuals"):
        L += ["**VISUAL SUGGESTIONS (for your editor):**"] + [f"- {v}" for v in p["visuals"]] + [""]
    from ..factcheck.verification import access_summary
    L += ["**FACT-CHECK:**"] + ([f"*{access_summary(claims)}*"] if access_summary(claims) else [])
    for c in claims:
        L.append(f"- {c['text']} — [{c.get('source_title') or 'primary source'}]({c['primary_source']}) ({c['status']}, {c['confidence']}, {c.get('source_date') or 'date unknown'}, {c.get('access') or 'access unknown'})"
                 if c.get("primary_source") else f"- {c['text']} — no primary source ({c['status']}, {c['confidence']})")
    if is_v4(p):
        L += v4_today_sections(p, info)
    if is_v3(p):
        L += v3_today_sections(p, info)
    L += ["", "**ENGLISH CAPTIONS:**", "", "```"] + caption_lines(p["script"]) + ["```", "", "**PLATFORM CONTENT:**", "",
          "*Instagram*", "", ig["caption"], "", " ".join(ig["hashtags"]), "", "*YouTube Shorts*", "", f"Title: {yt['title']}", "",
          yt["description"], "", "*LinkedIn*", "", li["caption"], "", "*X*", "", xx["post"], "",
          "Full research, all candidates, hooks and the claim table: `package.md`."]
    return "\n".join(L) + "\n"


ACCESS_RANK = {"DIRECTLY OBSERVED": 0, "SEARCH-INDEX": 1, "SECONDARY": 2, "NOT VERIFIED": 3}


def v4_today_sections(p: dict, info: dict) -> list[str]:
    """The creator's v4 morning items: why it wins, top five, strongest verified signal, posting window, hypothesis."""
    ranked = info["ranked"]
    win = next(c for c in ranked if c["headline"] == p["topic"])
    L = ["", f"**WHY IT BEATS THE ALTERNATIVES:** {p['why_beats_alternatives']}", "", "**TOP FIVE RANKED CANDIDATES:**"]
    for i, c in enumerate(ranked[:5], 1):
        tag = "eligible" if c["eligible"] else c["ineligible_reason"]
        L.append(f"{i}. {c['headline']}: {c['trend_score']}/100{' (provisional: traction not measured)' if c.get('provisional') else ''}, "
                 f"{c['evidence_confidence']} confidence, {tag}")
    social = {"x", "reddit", "youtube", "instagram", "linkedin", "google_trends"}
    rank = lambda s: ACCESS_RANK.get(s.get("access"), 9)
    sigs = win.get("signals") or []
    soc = sorted([s_ for s_ in sigs if s_.get("platform") in social and s_.get("access") != "NOT VERIFIED"], key=rank)

    def describe(s0):
        eng = s0.get("engagement") or {}
        nums = ", ".join(f"{k} {v}" for k, v in eng.items() if k not in ("basis", "source") and v != "UNKNOWN")
        return (f"[{s0['title']}]({s0['url']}) ({s0['platform']}, {s0['access']}; engagement {eng.get('basis', 'unknown')}"
                f"{': ' + nums if nums else ''})")
    if soc:
        L += ["", f"**STRONGEST VERIFIED SOCIAL SIGNAL:** {describe(soc[0])}"]
    else:
        pub = sorted(sigs, key=rank)
        L += ["", "**STRONGEST VERIFIED SOCIAL SIGNAL:** none observed (no social-platform post could be verified)."
              + (f" Strongest public evidence instead: {describe(pub[0])}" if pub else "")]
    if not candmod.traction_measured(win):
        L.append("No engagement was measured for this story; its traction score is provisional.")
    pw = p["posting_window"]
    L += ["", f"**RECOMMENDED POSTING WINDOW:** {pw['window_ist']} IST ({pw['basis']}): {pw['rationale']}",
          "", f"**EXPECTED AUDIENCE RESPONSE (hypothesis):** {p['audience_hypothesis']}"]
    if p.get("quality_limitation"):
        L += ["", f"**CREATIVE SCORE BELOW TARGET:** {info['quality']['total']}/100 after {p['revisions']} revisions. {p['quality_limitation']}"]
    return L


def run_status_line(date: str) -> str:
    """The latest run for this date from logs/runs.jsonl (never an older run's report)."""
    from ..research import runs
    recs = [r for r in runs.load(config.path("logs", "runs.jsonl")) if r.get("ist_date") == date and r.get("run_id")]
    starts = [r for r in recs if r.get("event") == "start"]
    if not starts:
        return "no run recorded for this date (built outside a logged run)"
    rid = starts[-1]["run_id"]
    end = next((r for r in reversed(recs) if r.get("run_id") == rid and r.get("event") == "end"), None)
    dels = [r["delivery"] for r in recs if r.get("run_id") == rid and isinstance(r.get("delivery"), dict)]
    if end is None:
        return f"{rid}: IN PROGRESS (delivery is recorded when the run ends)"
    d = dels[-1] if dels else {}
    return f"{rid}: {end.get('status') or 'UNKNOWN'}, delivery {d.get('status', 'UNKNOWN')}" + (
        f" via {d['channel']}" if d.get("channel") else "")


def v3_today_sections(p: dict, info: dict) -> list[str]:
    """Creator-facing extras for v3: evidence across platforms, backups, editing notes, limitations, run status."""
    import json
    from ..research import signals
    win = next(c for c in info["ranked"] if c["headline"] == p["topic"])
    L = ["", f"**PILLAR / FORMAT:** {p['pillar'].replace('_', ' ')} / {p['format']}: \"{FORMATS.get(p['format'], '')}\"", "",
         "**CROSS-PLATFORM EVIDENCE:**"]
    sigs = win.get("signals") or []
    sm = signals.summary(sigs)
    L.append(f"*Seen on {sm['count']} source type(s): {', '.join(sm['platforms']) or 'none'}. "
             f"Directly observed: {', '.join(sm['directly_observed']) or 'none'}.*")
    for s_ in sigs:
        eng = s_.get("engagement") or {}
        nums = ", ".join(f"{k} {v}" for k, v in eng.items() if k not in ("basis", "source") and v != "UNKNOWN")
        L.append(f"- {s_['platform']}: [{s_['title']}]({s_['url']}) ({s_['access']}; engagement "
                 f"{eng.get('basis', 'unknown')}{': ' + nums if nums else ''})")
    xs = win.get("x_signal") or {}
    L.append(f"- X signal: {xs.get('status', 'NOT VERIFIED')}")
    a = p["audience"]
    L += ["", "**WHY PEOPLE WILL CARE:**", f"- Stop scrolling: {a['stop_scroll']}", f"- Share: {a['share']}",
          f"- Save: {a['save']}", f"- Follow: {a['follow']}", "", "**VISUAL PRODUCTION NOTES (for your editor):**"]
    ed = p["editing"]
    lst = lambda v: "; ".join(v) if isinstance(v, list) else str(v)
    L += [f"- Opening visual: {lst(ed['opening_visual'])}", f"- Key moments: {lst(ed['key_moments'])}",
          f"- B-roll: {lst(ed['broll'])}", f"- On-screen text: {lst(ed['on_screen_text'])}",
          f"- Demonstrations: {lst(ed['demonstrations'])}", f"- Stats on screen: {lst(ed['stats'])}",
          f"- Rhythm: {lst(ed['rhythm'])}", f"- Caption emphasis: {lst(ed['caption_emphasis'])}", f"- Sound: {lst(ed['sound'])}",
          "", "**BACKUP STORIES (recovery only):**"] + [f"- {b}" for b in p["backups"]]
    if p.get("backup_shortfall_reason"):
        L.append(f"- Fewer than two: {p['backup_shortfall_reason']}")
    L += ["", "**RESEARCH LIMITATIONS:**"] + ([f"- {x}" for x in p["limitations"]] or ["- None recorded."])
    status = run_status_line(p["date"])
    L += ["", f"**RUN STATUS:** {status}"]
    return L


def render_recording(p: dict, info: dict) -> str:
    """'Prepare for recording': only the script and delivery notes."""
    chk, r = info["lint"], p["recording"]
    return "\n".join([f"# Recording: {p['date']} ({info['ready']['status']})", "", p["script"].strip(), "",
                       f"About {chk['seconds']} seconds.", "", f"- Tone: {r['tone']}", f"- Opening: {r['opening_expression']}",
                       f"- Pauses: {'; '.join(r['pauses'])}", f"- Emphasise: {', '.join(r['emphasis'])}",
                       f"- Pronunciation: {'; '.join(r['pronunciation'])}", "- Keep your natural accent."]) + "\n"


def caption_lines(script: str, max_words: int = 5) -> list[str]:
    """On-screen caption text: the script's exact words in groups of 2-5, never crossing a sentence, split at commas first,
    evenly sized, and never ending a line on a dangling word like 'the' or 'its'. Text only, no timing."""
    import math
    import re
    lines: list[list[str]] = []
    for sentence in re.split(r"(?<=[.?!])\s+|\n+", script.strip()):
        for phrase in re.split(r"(?<=,)\s+", sentence.strip()):
            words = phrase.split()
            if not words:
                continue
            if len(words) == 1 and lines and len(lines[-1]) < max_words and not re.search(r"[.?!]$", lines[-1][-1]):
                lines[-1].append(words[0])
                continue
            k = math.ceil(len(words) / max_words)
            sizes = [len(words) // k + (1 if i < len(words) % k else 0) for i in range(k)]
            chunks, i = [], 0
            for n in sizes:
                chunks.append(words[i:i + n])
                i += n
            for j in range(len(chunks) - 1):
                while (chunks[j][-1].lower().strip(",") in _WEAK_END and len(chunks[j]) > 2 and len(chunks[j + 1]) < max_words):
                    chunks[j + 1].insert(0, chunks[j].pop())
            lines += chunks
    return [" ".join(l) for l in lines if l]


def research_record(p: dict, info: dict) -> dict:
    rec = {"date": p["date"], "generated_at": p["generated_at"], "research_window": p["research_window"],
           "candidates": [{k: c.get(k) for k in ("headline", "published_at", "original_source", "trend_score", "eligible",
                                                 "ineligible_reason", "scores", "x_signal", "signals", "verification_status",
                                                 "evidence_confidence", "new_development", "claim_status")} for c in info["ranked"]],
           "hooks": lint.score_hooks(p["hooks"], hook_criteria_for(p)), "backups": p["backups"],
           "limitations": p["limitations"], "source_audit": source_audit_for(p)}
    if is_v7(p):
        rec.update(hooks=lint.score_hooks(p["hooks"], lint.HOOK_CRITERIA_V7), script_checks=p["script_checks"],
                   audience_check=p["audience_check"], practical_takeaway=p["practical_takeaway"],
                   scrutiny=p.get("scrutiny"), learning_applied=p["learning_applied"],
                   story={k: p[k] for k in ("story_id", "company", "event_date", "announced_at")})
    if is_v6(p):
        rec["finalists"] = [{"headline": f.get("headline"), "why_not": f.get("why_not"),
                             "hooks": lint.score_hooks(f.get("hooks") or [], lint.HOOK_CRITERIA_V5)} for f in p["finalists"]]
        rec["variants"] = {k: {**v, **{x: lint.check(v.get("script", ""), p["language"], "v6")[x] for x in ("words", "seconds")}}
                           for k, v in p["variants"].items()}
        rec.update(selected_variant=p["selected_variant"], creative_gate=p["creative_gate"], visual_plan=p["visual_plan"],
                   learning_applied=p["learning_applied"])
    return rec


def save(p: dict, out: Path | None = None, record: bool = True) -> dict:
    """Validate, render and record. record=False (a trial) writes the files but leaves the content and memory databases
    untouched, so a production-equivalent test never pollutes the real history."""
    p = with_winner_hooks(p)
    problems, info = validate(p)
    if problems:
        return {"ok": False, "problems": problems}
    out = out or config.path("daily", p["date"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "package.md").write_text(render(p, info), encoding="utf-8")
    (out / "script.txt").write_text(p["script"].strip() + "\n", encoding="utf-8")
    (out / "captions.txt").write_text("\n".join(caption_lines(p["script"])) + "\n", encoding="utf-8")
    (out / "today.md").write_text(render_today(p, info), encoding="utf-8")
    (out / "recording.md").write_text(render_recording(p, info), encoding="utf-8")
    (out / "claims.md").write_text(ver.table(p["factcheck"]["claims"]), encoding="utf-8")
    (out / "factcheck.md").unlink(missing_ok=True)
    if is_v6(p):
        (out / "creative.md").write_text(render_creative(p, info), encoding="utf-8")
    write_json(out / "sources.json", {"primary": p["primary_sources"], "supporting": p["supporting_sources"],
                                      "x_signals": p["x_signals"], "access_limits": p["access_limits"]})
    if not record:
        if is_v3(p):
            write_json(out / "research.json", research_record(p, info))
        return {"ok": True, "status": info["ready"]["status"], "reasons": info["ready"]["reasons"],
                "package": str(out / "package.md"), "content_db": "not recorded (trial)"}
    rec = content_db.add(p["date"], p["topic"], p["keys"], p["slug"], category=p["category"],
                         sources=[s["url"] for s in p["primary_sources"] + p["supporting_sources"]], hook=p["hook"],
                         script=p["script"].strip(), material_update_of=p.get("material_update_of"))
    status = info["ready"]["status"]
    content_db.update(p["date"], p["slug"], status="scripted" if status == ver.READY else "held",
                      hold_reasons=info["ready"]["reasons"], language=p["language"], hook=p["hook"], script=p["script"].strip())
    if is_v3(p):
        content_db.update(p["date"], p["slug"], pillar=p["pillar"], format=p["format"])
        write_json(out / "research.json", research_record(p, info))
    if is_v7(p):                                     # V7 story history: ID, company, event and publication dates
        content_db.update(p["date"], p["slug"], story_id=p["story_id"], company=p["company"], event_date=p["event_date"],
                          published_at=p["announced_at"], selected_on=p["date"])
    from ..research import memory
    memory.record(p, info["ranked"])
    return {"ok": True, "status": status, "reasons": info["ready"]["reasons"], "package": str(out / "package.md"),
            "content_db": "added" if not rec.get("duplicate") else "already present"}
