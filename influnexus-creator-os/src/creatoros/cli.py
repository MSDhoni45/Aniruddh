"""Command-line entry point: `creatoros <command>`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config
from .util import read_json, write_json


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="creatoros", description="Influnexus Creator OS")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe", help="inspect a raw recording"); p.add_argument("video")
    p = sub.add_parser("edit", help="raw footage -> finished reel + QC report")
    p.add_argument("video"); p.add_argument("--date", required=True); p.add_argument("--script"); p.add_argument("--plan")
    p.add_argument("--factcheck"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("script-check", help="lint a script and estimate its duration"); p.add_argument("script")
    p = sub.add_parser("factcheck", help="validate a fact-check file against its script"); p.add_argument("file"); p.add_argument("--script")
    p = sub.add_parser("score", help="rank candidate stories"); p.add_argument("candidates_json")
    p = sub.add_parser("story-check", help="has this story been covered?"); p.add_argument("headline"); p.add_argument("--keys", nargs="*", default=[]); p.add_argument("--date", required=True)
    p = sub.add_parser("story-add"); p.add_argument("headline"); p.add_argument("--keys", nargs="*", default=[]); p.add_argument("--date", required=True); p.add_argument("--slug", required=True); p.add_argument("--update-of")
    p = sub.add_parser("brief", help="validate and render daily/DATE/brief.json"); p.add_argument("--date", required=True)
    p = sub.add_parser("calibrate", help="record the creator's measured pace from a finished edit"); p.add_argument("--date", required=True)
    p = sub.add_parser("metrics-add", help="store one analytics row: key=value ..."); p.add_argument("pairs", nargs="+")
    p = sub.add_parser("metrics-report"); p.add_argument("--dim", default="topic"); p.add_argument("--checkpoint", default="7d"); p.add_argument("--platform", default="instagram")
    p = sub.add_parser("metrics-review", help="append a review to analytics/learning_log.md")
    p = sub.add_parser("publish"); p.add_argument("--date", required=True); p.add_argument("--platform", required=True)
    p.add_argument("--reviewed", action="store_true"); p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "probe":
        from .editing.probe import probe
        _print(probe(Path(a.video)))
    elif a.cmd == "edit":
        from .editing.pipeline import edit
        r = edit(Path(a.video), a.date, Path(a.script) if a.script else None, Path(a.plan) if a.plan else None,
                 Path(a.factcheck) if a.factcheck else None, a.force)
        s = r["summary"]
        _print({k: s[k] for k in ("status", "duration", "attempts_at_opening", "removed", "missing_sentences", "weak_sentences", "final")})
        _print([c for c in r["qc"]["checks"] if c["status"] != "PASS"])
        return 0 if s["status"] == "COMPLETE" else 2
    elif a.cmd == "script-check":
        from .scripts import lint
        r = lint.check(Path(a.script).read_text(encoding="utf-8"))
        _print(r)
        return 0 if r["ok"] else 2
    elif a.cmd == "factcheck":
        from .factcheck import claims
        problems = claims.validate(read_json(a.file), Path(a.script).read_text(encoding="utf-8") if a.script else None)
        _print({"ok": not problems, "problems": problems})
        return 0 if not problems else 2
    elif a.cmd == "score":
        from .research import candidates
        _print([{k: c[k] for k in ("headline", "trend_score", "unknown_criteria", "eligible", "problems")} for c in candidates.rank(read_json(a.candidates_json))])
    elif a.cmd == "story-check":
        from .research import storylog
        _print({"repeat_of": storylog.find_repeat(a.headline, a.keys, a.date)})
    elif a.cmd == "story-add":
        from .research import storylog
        _print(storylog.add(a.date, a.headline, a.keys, a.slug, a.update_of))
    elif a.cmd == "brief":
        from .scripts import brief
        r = brief.save(read_json(config.path("daily", a.date, "brief.json")))
        _print(r)
        return 0 if r["ok"] else 2
    elif a.cmd == "calibrate":
        from .scripts.lint import word_count
        rep = read_json(config.path("renders", a.date, "edit_report.json"))
        al = read_json(config.path("renders", a.date, "alignment.json"))
        spoken = sum(t["end"] - t["start"] for t in al["takes"] if t)
        words = sum(word_count(s["script"]) for s in al["sentences"] if s["found"])
        pf = config.path("analytics/pace.json")
        prev = read_json(pf) if pf.exists() else {"samples": 0, "words_per_minute": 0}
        n = prev["samples"] + 1
        wpm = (prev["words_per_minute"] * prev["samples"] + words / spoken * 60) / n
        _print(write_json(pf, {"words_per_minute": round(wpm, 1), "samples": n, "last": a.date, "note": "speech time only, pauses excluded"}) and read_json(pf))
    elif a.cmd == "metrics-add":
        from .analytics import store
        _print(store.upsert(dict(pair.split("=", 1) for pair in a.pairs)))
    elif a.cmd == "metrics-report":
        from .analytics import store
        _print(store.by_dimension(a.dim, a.checkpoint, a.platform))
    elif a.cmd == "metrics-review":
        from .analytics import store
        log = config.path("analytics/learning_log.md")
        text = store.review()
        with open(log, "a", encoding="utf-8") as fh:
            fh.write("\n" + text)
        print(text)
    elif a.cmd == "publish":
        from .publishing.publish import publish
        r = publish(a.date, a.platform, a.reviewed, a.dry_run)
        _print(r)
        return 0 if r["status"] in ("published", "dry_run_ok", "skipped_duplicate") else 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
