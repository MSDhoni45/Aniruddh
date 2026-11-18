"""Daily recording package (sections A-F). Validates everything first and refuses to render a package that breaks a rule."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ..factcheck import claims as fcmod
from ..research import candidates as candmod
from ..research import content_db
from ..util import write_json
from . import lint

REQUIRED = ["date", "slug", "keys", "topic", "category", "topic_type", "announced_at", "why_selected", "evidence_confidence",
            "research_summary", "primary_sources", "supporting_sources", "key_facts", "uncertainties", "context",
            "script", "hook", "hooks", "quality_scores", "recording", "instagram", "linkedin", "x", "youtube", "growth",
            "x_signals", "candidates", "factcheck", "access_limits"]
MIN_CANDIDATES = 15


def _words(text: str) -> int:
    return len(text.split())


def validate(p: dict) -> tuple[list[str], dict]:
    problems = [f"missing: {k}" for k in REQUIRED if k not in p]
    if problems:
        return problems, {}
    chk = lint.check(p["script"])
    problems += [f"script: {x}" for x in chk["problems"]]
    if not p["script"].strip().startswith(p["hook"].strip()):
        problems.append("script must open with the chosen hook")
    problems += [f"hooks: {x}" for x in lint.check_hooks(p["hooks"], p["hook"])]
    q = lint.quality(p["quality_scores"], p["script"])
    problems += [f"quality: {x}" for x in q["problems"]]
    problems += [f"fact-check: {x}" for x in fcmod.validate(p["factcheck"], p["script"])]
    ranked = candmod.rank(p["candidates"])
    for c in ranked:
        problems += [f"candidate '{c.get('headline', '?')[:40]}': {x}" for x in c["problems"]]
    eligible = [c for c in ranked if c["eligible"]]
    if not eligible:
        problems.append("no eligible candidate")
    elif eligible[0]["headline"] != p["topic"]:
        problems.append(f"topic must be the top eligible candidate ('{eligible[0]['headline']}')")
    credible = [c for c in ranked if not c.get("rejected") and c.get("evidence_confidence") != "LOW"]
    if len(credible) < MIN_CANDIDATES and not p.get("candidate_shortfall_reason"):
        problems.append(f"{len(credible)} credible candidates; find {MIN_CANDIDATES} or explain in candidate_shortfall_reason")
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
    return problems, {"lint": chk, "quality": q, "ranked": ranked}


def render(p: dict, info: dict) -> str:
    chk, q, ranked = info["lint"], info["quality"], info["ranked"]
    win = next(c for c in ranked if c["eligible"])
    r, ig, li, xx, yt, g = p["recording"], p["instagram"], p["linkedin"], p["x"], p["youtube"], p["growth"]
    L = [f"# Recording package: {p['date']}", ""]
    if p.get("disclosure"):
        L += [f"> {p['disclosure']}", ""]
    L += ["## A. Today's winning topic", "",
          f"- **Topic:** {p['topic']}", f"- **Category:** {p['category']} ({p['topic_type']})",
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
          "## D. Recording direction", "", f"- **Tone:** {r['tone']}", f"- **Opening expression:** {r['opening_expression']}",
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
    L += ["", "## Appendix 3: Hook candidates", "", "| Hook | Mechanism | Score /60 | Usable |", "|---|---|---|---|"]
    L += [f"| {h['text']} | {h['mechanism']} | {h['total']} | {'yes' if h['eligible'] else 'no (accuracy)'} |" for h in lint.score_hooks(p["hooks"])]
    L += ["", "## Appendix 4: Script quality", "", "| Check | Score /10 |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in q["scores"].items() if k in lint.QUALITY_CHECKS]
    L += ["", "## Appendix 5: Fact-check", "", fcmod.to_markdown(p["factcheck"]).split("\n", 2)[2], "## Appendix 6: Research access limits", ""]
    L += [f"- {a}" for a in p["access_limits"]]
    return "\n".join(L) + "\n"


def save(p: dict) -> dict:
    problems, info = validate(p)
    if problems:
        return {"ok": False, "problems": problems}
    out = config.path("daily", p["date"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "package.md").write_text(render(p, info), encoding="utf-8")
    (out / "script.txt").write_text(p["script"].strip() + "\n", encoding="utf-8")
    (out / "factcheck.md").write_text(fcmod.to_markdown(p["factcheck"]), encoding="utf-8")
    write_json(out / "sources.json", {"primary": p["primary_sources"], "supporting": p["supporting_sources"],
                                      "x_signals": p["x_signals"], "access_limits": p["access_limits"]})
    rec = content_db.add(p["date"], p["topic"], p["keys"], p["slug"], category=p["category"],
                         sources=[s["url"] for s in p["primary_sources"] + p["supporting_sources"]], hook=p["hook"],
                         script=p["script"].strip(), material_update_of=p.get("material_update_of"))
    return {"ok": True, "package": str(out / "package.md"), "content_db": "added" if not rec.get("duplicate") else "already present"}
