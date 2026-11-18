"""Render the daily brief from structured data, refusing to render an incomplete one."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ..factcheck import claims as fcmod
from ..research import candidates as candmod
from . import lint

REQUIRED = ["date", "selected_story", "why_it_won", "x_signals", "primary_sources", "uncertainties", "script",
            "recording_instructions", "visual_references", "instagram_caption", "linkedin_caption", "x_caption",
            "hashtags", "posting_time", "candidates", "hooks", "factcheck", "access_limits"]


def build(b: dict) -> tuple[str, list[str]]:
    problems = [f"missing: {k}" for k in REQUIRED if k not in b]
    if problems:
        return "", problems
    chk = lint.check(b["script"])
    problems += chk["problems"]
    problems += fcmod.validate(b["factcheck"], b["script"])
    ranked = candmod.rank(b["candidates"])
    for c in ranked:
        problems += [f"candidate '{c.get('headline', '?')[:40]}': {p}" for p in c["problems"]]
    if not 3 <= len(b["hashtags"]) <= 5:
        problems.append("use 3-5 hashtags")
    hooks = lint.score_hooks(b["hooks"])
    L = [f"# Daily brief: {b['date']}", "", f"## 1. Selected story", b["selected_story"], "", "## 2. Why it won", b["why_it_won"], "",
         "## 3. X signals", "Engagement counts are listed only where they were actually observed.", ""]
    L += ["| Time (UTC) | Account | Post | Likes | Reposts | Views |", "|---|---|---|---|---|---|"]
    for s in b["x_signals"]:
        L.append(f"| {s.get('time', 'UNKNOWN')} | {s['account']} | [{s['summary']}]({s['url']}) | {s.get('likes', 'UNKNOWN')} | {s.get('reposts', 'UNKNOWN')} | {s.get('views', 'UNKNOWN')} |")
    L += ["", "## 4. Primary sources"] + [f"- [{s['label']}]({s['url']})" for s in b["primary_sources"]]
    L += ["", "## 5. Important uncertainties"] + [f"- {u}" for u in b["uncertainties"]]
    L += ["", "## 6. Final script", "", "```", b["script"].strip(), "```", "",
          f"## 7. Word count\n{chk['words']}", "",
          f"## 8. Estimated duration\n{chk['seconds']}s at {chk['words_per_minute']:.0f} words per minute ({chk['pace_basis']})."]
    if chk["warnings"]:
        L += [""] + [f"- Note: {w}" for w in chk["warnings"]]
    L += ["", "## 9. Recording instructions"] + [f"- {r}" for r in b["recording_instructions"]]
    L += ["", "## 10. Visual references"] + [f"- {r}" for r in b["visual_references"]]
    L += ["", "## 11. Instagram caption", b["instagram_caption"], "", "## 12. LinkedIn caption", b["linkedin_caption"], "",
          "## 13. X caption", b["x_caption"], "", "## 14. Hashtags", " ".join(b["hashtags"]), "",
          "## 15. Suggested posting time", b["posting_time"], "", "---", "", "## Candidates considered", "",
          "| Rank | Story | Trend score | Unknown criteria | Eligible | Uncertainty |", "|---|---|---|---|---|---|"]
    for i, c in enumerate(ranked, 1):
        why = "yes" if c["eligible"] else ("already covered" if c.get("already_covered") else "outside 24h window")
        L.append(f"| {i} | {c['headline']} | {c['trend_score']} | {', '.join(c['unknown_criteria']) or 'none'} | {why} | {c['uncertainty']} |")
    L += ["", "## Hook candidates", "", "| Hook | Type | Total /50 | Eligible |", "|---|---|---|---|"]
    L += [f"| {h['text']} | {h['type']} | {h['total']} | {'yes' if h['eligible'] else 'no (accuracy)'} |" for h in hooks]
    L += ["", "## Fact-check", "", fcmod.to_markdown(b["factcheck"]).split("\n", 2)[2], "## Research access limits"]
    L += [f"- {a}" for a in b["access_limits"]]
    return "\n".join(L) + "\n", problems


def save(b: dict) -> dict:
    md, problems = build(b)
    if problems:
        return {"ok": False, "problems": problems}
    day = b["date"]
    out = config.path("daily", day, "brief.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    config.path("scripts", f"{day}_script.txt").write_text(b["script"].strip() + "\n", encoding="utf-8")
    config.path("scripts", f"{day}_factcheck.md").write_text(fcmod.to_markdown(b["factcheck"]), encoding="utf-8")
    from ..util import write_json
    write_json(config.path("scripts", f"{day}_factcheck.json"), b["factcheck"])
    write_json(config.path("scripts", f"{day}_sources.json"), {"date": day, "primary_sources": b["primary_sources"],
               "x_signals": b["x_signals"], "access_limits": b["access_limits"]})
    return {"ok": True, "brief": str(out)}
