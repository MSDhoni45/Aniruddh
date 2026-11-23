"""Automatic fallback: put today's selected story on HOLD, record why, and name the next-ranked story to try.

The held story is archived (never deleted) under daily/DATE/held_<slug>/, logged in daily/DATE/holds.json and marked
'held' in the content database. The validator then refuses any package that selects it again without its hold_reason,
so the next-ranked eligible candidate wins. Nothing is invented to fill an evidence gap.
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

FILES = ("package.json", "package.md", "today.md", "recording.md", "script.txt", "captions.txt", "claims.md", "sources.json", "creative.md", "production_handoff.json", "qc_report.json", "verification_report.json",
         "research.json")


def hold(day_dir: Path, reason: str, db_path: Path | None = None, now: dt.datetime | None = None) -> dict:
    from . import candidates, content_db
    if not reason.strip():
        raise ValueError("say why the story is on HOLD")
    f = day_dir / "package.json"
    if not f.exists():
        raise FileNotFoundError("no package to hold")
    p = json.loads(f.read_text(encoding="utf-8"))
    dst = day_dir / f"held_{p['slug']}"
    dst.mkdir(exist_ok=True)
    for name in FILES:
        if (day_dir / name).exists():
            shutil.move(str(day_dir / name), str(dst / name))
    log = day_dir / "holds.json"
    holds = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
    holds.append({"topic": p["topic"], "slug": p["slug"], "reason": reason.strip(), "archived": dst.name,
                  "at_utc": (now or dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds")})
    log.write_text(json.dumps(holds, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        content_db.update(p["date"], p["slug"], path=db_path, status="held", hold_reasons=[reason.strip()])
    except KeyError:
        pass
    held = {h["topic"] for h in holds}
    window = p.get("research_window")
    ranked = candidates.rank([{**c, **({"hold_reason": "held earlier today"} if c["headline"] in held and not c.get("hold_reason") else {})}
                              for c in p.get("candidates", [])], window)
    nxt = [{"headline": c["headline"], "score": c["trend_score"], "confidence": c.get("evidence_confidence")}
           for c in ranked if c["eligible"]]
    return {"held": p["topic"], "archived": str(dst), "reason": reason.strip(), "next_candidates": nxt[:3],
            "next": (f"verify '{nxt[0]['headline']}' to the same standard and write a new package.json (give the held story its "
                     "hold_reason)") if nxt else "no eligible candidate left: research more stories or deliver no script today"}
