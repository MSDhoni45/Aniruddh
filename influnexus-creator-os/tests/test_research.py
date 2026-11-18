"""Tests for the research-and-script workflow: package rules, content memory, script quality and weekly review."""
import copy
import json
from pathlib import Path

import pytest

from creatoros.analytics import store, weekly
from creatoros.research import candidates, content_db
from creatoros.scripts import lint, package

ROOT = Path(__file__).resolve().parents[1]
PKG = json.loads((ROOT / "daily" / "2026-11-18" / "package.json").read_text(encoding="utf-8"))


def problems(mod=None):
    p = copy.deepcopy(PKG)
    if mod:
        mod(p)
    return package.validate(p)[0]


def test_todays_package_is_valid():
    assert problems() == []


@pytest.mark.parametrize("mod,expect", [
    (lambda p: p["quality_scores"].update(fact=6), "below 90"),
    (lambda p: p.__setitem__("hooks", p["hooks"][:9]), "at least 10"),
    (lambda p: p.__setitem__("hook", p["hooks"][7]["text"]), "top-scoring"),
    (lambda p: p.__setitem__("topic", p["candidates"][4]["headline"]), "top eligible candidate"),
    (lambda p: p.__setitem__("script", p["script"].replace("Aarop hai ki", "Sach yeh hai ki")), "attribution phrase"),
    (lambda p: p.__setitem__("script", "Imagine a world where " + p["script"]), "banned phrase"),
    (lambda p: p.__setitem__("research_summary", "Too short."), "100-150"),
    (lambda p: p["instagram"].__setitem__("hashtags", ["#a", "#b"]), "3-5 hashtags"),
    (lambda p: p.__setitem__("candidates", p["candidates"][:5]), "candidate_shortfall_reason" if False else "credible candidates"),
    (lambda p: (p.__setitem__("keys", ["CVE-2026-114938"]), p.__setitem__("slug", "other")), "repeat of"),
    (lambda p: p.__setitem__("script", p["script"] + " " + p["script"]), "hard maximum"),
])
def test_package_rejects_rule_breaks(mod, expect):
    def m(p):
        mod(p)
        if expect == "credible candidates":
            p.pop("candidate_shortfall_reason", None)
    assert any(expect in x for x in problems(m)), problems(m)


def test_low_credibility_story_cannot_win():
    c = copy.deepcopy(PKG["candidates"][0])
    flashy = {**c, "headline": "Sensational unverified claim", "evidence_confidence": "LOW", "scores": {k: 10 for k in candidates.WEIGHTS}}
    r = candidates.rank([flashy, c])
    assert r[0]["headline"] == c["headline"] and not r[1]["eligible"]


def test_breaking_label_needs_the_24h_window():
    c = {**copy.deepcopy(PKG["candidates"][0]), "topic_type": "BREAKING", "outside_window": True}
    assert any("BREAKING" in x for x in candidates.validate(c))


def test_quality_measures_duration_itself():
    q = lint.quality({k: 10 for k in lint.QUALITY_CHECKS}, PKG["script"] + " " + PKG["script"])
    assert q["scores"]["duration"] == 0 and not q["approved"]


def test_content_db_lifecycle(tmp_path):
    db = tmp_path / "db.jsonl"
    content_db.add("2026-11-18", "California sues OpenAI over rogue agents", ["california-v-openai"], "ca", category="CONTROVERSY", path=db)
    assert content_db.add("2026-11-18", "x", [], "ca", path=db)["duplicate"]
    with pytest.raises(ValueError):
        content_db.add("2026-11-20", "OpenAI lawsuit update", ["california-v-openai"], "ca2", path=db)
    content_db.add("2026-11-20", "Judge rules in California v OpenAI", ["california-v-openai"], "ca-ruling", material_update_of="court ruling", path=db)
    content_db.update("2026-11-18", "ca", status="published", platforms=["instagram"], metrics={"views_7d": 1200}, path=db)
    content_db.update("2026-11-18", "ca", platforms=["x"], path=db)
    e = content_db.search("rogue", path=db)[0]
    assert e["status"] == "published" and e["platforms"] == ["instagram", "x"] and e["metrics"]["views_7d"] == 1200
    with pytest.raises(ValueError):
        content_db.update("2026-11-18", "ca", status="viral", path=db)
    content_db.update("2026-11-20", "ca-ruling", status="dropped", path=db)
    assert content_db.find_repeat("Judge rules in California v OpenAI", [], "2026-11-21", path=db, ignore_slug="ca") is None


def test_weekly_review_reports_unknowns_and_numbers(tmp_path):
    db, perf = tmp_path / "db.jsonl", tmp_path / "perf.csv"
    content_db.add("2026-11-18", "Topic one", ["k1"], "one", category="AI", hook="Hook one", path=db)
    text = weekly.build("2026-11-24", db, perf)
    assert "Topic one" in text and "UNKNOWN" in text
    store.upsert(dict(date="2026-11-18", video_id="2026-11-18_one", platform="instagram", checkpoint="7d", views="5000",
                      new_followers="40", shares="60", saves="90"), perf)
    text = weekly.build("2026-11-24", db, perf)
    assert "| 2026-11-18_one | instagram | 7d | 5000.0 | 8.0 | 12.0 | 18.0 |" in text and "Followers gained" in text and "anecdote" in text
