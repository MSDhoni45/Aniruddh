"""Daily recording package (sections A-F). Validates everything first and refuses to render a package that breaks a rule."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ..factcheck import claims as fcmod
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
V3_FROM = "2026-11-20"             # from this IST date every package must use the v3 rules


def is_v2(p: dict) -> bool:
    """v2 rules (claim table, visuals, hook reuse) also apply to v3 packages."""
    return p.get("scoring") in ("v2", "v3")


def is_v3(p: dict) -> bool:
    return p.get("scoring") == "v3"


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


def window_problems(w) -> list[str]:
    import datetime as dt
    if not isinstance(w, dict):
        return ["research_window must be an object (use `creatoros runlog start`, which prints it)"]
    try:
        a = dt.datetime.fromisoformat(str(w["start_utc"]).replace("Z", "+00:00"))
        b = dt.datetime.fromisoformat(str(w["end_utc"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return ["research_window needs ISO start_utc and end_utc"]
    if abs((b - a).total_seconds() - WINDOW_HOURS * 3600) > 300:
        return [f"research_window must span {WINDOW_HOURS} hours (it spans {(b - a).total_seconds() / 3600:.1f})"]
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


def validate(p: dict) -> tuple[list[str], dict]:
    if str(p.get("date", "")) >= V3_FROM and not is_v3(p):
        return [f"packages dated {V3_FROM} or later must use \"scoring\": \"v3\" (RUNBOOK.md); this one is "
                f"'{p.get('scoring', 'v1')}'"], {}
    extra = REQUIRED_V3 if is_v3(p) else (REQUIRED_V2 if is_v2(p) else [])
    problems = [f"missing: {k}" for k in REQUIRED + extra if k not in p]
    if problems:
        return problems, {}
    scheme = "v3" if is_v3(p) else None
    window = p.get("research_window") if is_v3(p) else None
    if is_v3(p):
        problems += window_problems(window)
        for c in p["factcheck"]["claims"]:
            if c.get("in_script") and not c.get("retrieved_at"):
                problems.append(f"claim {c.get('id')}: v3 claims in the script need retrieved_at (when the source was read)")
    if is_v2(p):
        if not p["visuals"] or not all(isinstance(v, str) and v.strip() for v in p["visuals"]):
            problems.append("visuals: list at least one B-roll or graphic suggestion for the editor")
        want = "v3" if is_v3(p) else "v2"
        if any(candmod.scheme(c) != want for c in p["candidates"]):
            problems.append(f"a {want} package must score every candidate with the {want} criteria")
        old = reused_hook(p["hook"], p["slug"])
        if old:
            problems.append(f"hook too similar to the hook used on {old['date']} ('{old['hook']}')")
    language = config.settings().get("language", "english")
    if p["language"] != language:
        problems.append(f"package language is '{p['language']}' but the configured default is '{language}'")
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
    hook_criteria = lint.HOOK_CRITERIA_V3 if is_v3(p) else None
    problems += [f"hooks: {x}" for x in lint.check_hooks(p["hooks"], p["hook"], hook_criteria)]
    q = lint.quality(p["quality_scores"], p["script"], scheme)
    problems += [f"quality: {x}" for x in q["problems"]]
    problems += [f"fact-check: {x}" for x in fcmod.validate(p["factcheck"], p["script"])]
    ready = ver.readiness(p["factcheck"]["claims"], p["script"], p.get("unresolved", []), v2=is_v2(p))
    problems += [f"claim table: {x}" for x in ready["problems"]]
    problems += ver.story_confidence_ok(p["evidence_confidence"], p["factcheck"]["claims"])
    ranked = candmod.rank(p["candidates"], window)
    if is_v3(p):
        problems += v3_problems(p, ranked)
    for c in ranked:
        problems += [f"candidate '{c.get('headline', '?')[:40]}': {x}" for x in c["problems"]]
    eligible = [c for c in ranked if c["eligible"]]
    if not eligible:
        problems.append("no eligible candidate")
    elif eligible[0]["headline"] != p["topic"]:
        problems.append(f"topic must be the top eligible candidate ('{eligible[0]['headline']}')")
    credible = [c for c in ranked if not c.get("rejected") and c.get("evidence_confidence") != "LOW"]
    need = MIN_CANDIDATES_V3 if is_v3(p) else MIN_CANDIDATES
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
    return problems, {"lint": chk, "quality": q, "ranked": ranked, "ready": ready}


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
    L += ["", "## Appendix 4: Script quality", "", "| Check | Score /10 |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in q["scores"].items() if k in lint.QUALITY_CHECKS]
    L += ["", "## Appendix 5: Research access limits", ""]
    L += [f"- {a}" for a in p["access_limits"]]
    return "\n".join(L) + "\n"


_WEAK_END = {"a", "an", "the", "its", "it's", "of", "to", "for", "and", "but", "or", "in", "on", "at", "by", "with", "that", "their",
             "his", "her", "my", "your", "our", "is", "are", "was", "be", "it"}


def render_today(p: dict, info: dict) -> str:
    """The daily deliverable, in the order the creator asked for. Concise; full detail stays in package.md."""
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
    if is_v3(p):
        L += v3_today_sections(p, info)
    L += ["", "**ENGLISH CAPTIONS:**", "", "```"] + caption_lines(p["script"]) + ["```", "", "**PLATFORM CONTENT:**", "",
          "*Instagram*", "", ig["caption"], "", " ".join(ig["hashtags"]), "", "*YouTube Shorts*", "", f"Title: {yt['title']}", "",
          yt["description"], "", "*LinkedIn*", "", li["caption"], "", "*X*", "", xx["post"], "",
          "Full research, all candidates, hooks and the claim table: `package.md`."]
    return "\n".join(L) + "\n"


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


def save(p: dict, out: Path | None = None) -> dict:
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
    write_json(out / "sources.json", {"primary": p["primary_sources"], "supporting": p["supporting_sources"],
                                      "x_signals": p["x_signals"], "access_limits": p["access_limits"]})
    rec = content_db.add(p["date"], p["topic"], p["keys"], p["slug"], category=p["category"],
                         sources=[s["url"] for s in p["primary_sources"] + p["supporting_sources"]], hook=p["hook"],
                         script=p["script"].strip(), material_update_of=p.get("material_update_of"))
    status = info["ready"]["status"]
    content_db.update(p["date"], p["slug"], status="scripted" if status == ver.READY else "held",
                      hold_reasons=info["ready"]["reasons"], language=p["language"], hook=p["hook"], script=p["script"].strip())
    if is_v3(p):
        content_db.update(p["date"], p["slug"], pillar=p["pillar"], format=p["format"])
        write_json(out / "research.json", {
            "date": p["date"], "generated_at": p["generated_at"], "research_window": p["research_window"],
            "candidates": [{k: c.get(k) for k in ("headline", "published_at", "original_source", "trend_score", "eligible",
                                                  "ineligible_reason", "scores", "x_signal", "signals", "verification_status",
                                                  "evidence_confidence", "new_development")} for c in info["ranked"]],
            "hooks": lint.score_hooks(p["hooks"], lint.HOOK_CRITERIA_V3), "backups": p["backups"],
            "limitations": p["limitations"], "source_audit": source_audit_for(p)})
    from ..research import memory
    memory.record(p, info["ranked"])
    return {"ok": True, "status": status, "reasons": info["ready"]["reasons"], "package": str(out / "package.md"),
            "content_db": "added" if not rec.get("duplicate") else "already present"}
