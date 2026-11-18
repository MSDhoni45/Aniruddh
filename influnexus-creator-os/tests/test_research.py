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
    (lambda p: p.__setitem__("topic", [c for c in candidates.rank(p["candidates"]) if c["eligible"]][1]["headline"]), "top eligible candidate"),
    (lambda p: p.__setitem__("script", p["script"].replace("Vals AI", "ek tester")), "attribution phrase"),
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
    c = copy.deepcopy(next(x for x in PKG["candidates"] if x["headline"] == PKG["topic"]))
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


# ---------- claim verification table and readiness gate ----------
from creatoros.factcheck import verification as ver

HELD = json.loads((ROOT / "daily" / "2026-11-18" / "held_ca-v-openai" / "package.json").read_text(encoding="utf-8"))


def test_todays_package_is_recording_ready():
    r = ver.readiness(PKG["factcheck"]["claims"], PKG["script"], PKG.get("unresolved", []))
    assert r["status"] == ver.READY and r["reasons"] == []


def test_held_california_package_stays_on_hold():
    r = ver.readiness(HELD["factcheck"]["claims"], HELD["script"], HELD.get("unresolved", []))
    assert r["status"] == ver.HOLD
    assert any("case number" in x for x in r["reasons"]) and any("c4" in x for x in r["reasons"])


def test_secondary_repetition_cannot_be_high_confidence():
    c = {**PKG["factcheck"]["claims"][1], "access": "secondary-only"}
    assert any("HIGH confidence" in x for x in ver.check_claim(c))
    c = {**PKG["factcheck"]["claims"][1], "primary_source": None}
    assert any("HIGH confidence" in x for x in ver.check_claim(c))


def test_unverified_quote_or_unresolved_item_forces_hold():
    claims = copy.deepcopy(PKG["factcheck"]["claims"])
    claims[1].update(quote=True, wording_verified=False, confidence="MEDIUM")
    assert ver.readiness(claims, PKG["script"], [])["status"] == ver.HOLD
    assert ver.readiness(PKG["factcheck"]["claims"], PKG["script"], ["case number missing"])["status"] == ver.HOLD


def test_claim_table_fields_are_required_and_sources_must_be_urls():
    c = {k: v for k, v in PKG["factcheck"]["claims"][0].items() if k != "source_date"}
    assert any("source_date" in x for x in ver.check_claim(c))
    c = {**PKG["factcheck"]["claims"][0], "primary_source": "OpenAI blog"}
    assert any("must be a URL" in x for x in ver.check_claim(c))


def test_story_cannot_be_high_when_a_script_claim_is_not():
    claims = copy.deepcopy(PKG["factcheck"]["claims"])
    claims[0]["confidence"] = "MEDIUM"
    assert ver.story_confidence_ok("HIGH", claims)


def test_rendered_package_shows_status_and_claim_table():
    md = (ROOT / "daily" / "2026-11-18" / "package.md").read_text(encoding="utf-8")
    held = (ROOT / "daily" / "2026-11-18" / "held_ca-v-openai" / "package.md").read_text(encoding="utf-8")
    assert "## STATUS: RECORDING READY" in md and "## Claim verification table" in md
    assert "## STATUS: HOLD — NOT RECORDING READY" in held and "Do not record this script" in held


# ---------- English by default ----------
@pytest.mark.parametrize("text,bad", [
    ("OpenAI says its new AI helps build AI.", False),
    ("OpenAI ka naya AI, AI banane mein madad karne laga hai.", True),
    ("यह एक टेस्ट है", True),
    ("Kar Bank and Sab Inc. reported results.", False),
])
def test_language_detector(text, bad):
    assert bool(lint.language_problems(text, "english")) is bad


def test_package_rejects_hinglish_copy_slang_and_corporate_phrasing():
    assert any("instagram caption" in x for x in problems(lambda p: p["instagram"].__setitem__("caption", "Yeh dekho, OpenAI ka naya model hai.")))
    assert any("forced slang" in x for x in problems(lambda p: p.__setitem__("script", p["script"].replace("So no,", "No cap,"))))
    assert any("cutting-edge" in x for x in problems(lambda p: p.__setitem__("script", p["script"].replace("new AI", "cutting-edge AI"))))
    assert any("language" in x for x in problems(lambda p: p.__setitem__("language", "hinglish")))
    assert any("280" in x for x in problems(lambda p: p["x"].__setitem__("post", "x" * 281)))


def test_caption_lines_keep_exact_words_in_short_groups():
    lines = package.caption_lines(PKG["script"])
    assert " ".join(lines).split() == PKG["script"].split()
    assert all(1 <= len(l.split()) <= 5 for l in lines)
    assert not any(l.split()[-1].lower() in package._WEAK_END for l in lines)


# ---------- v2 scoring, claim evidence, memory and commands (19 Nov 2026) ----------
from creatoros import cli
from creatoros.research import memory

PKG19 = json.loads((ROOT / "daily" / "2026-11-19" / "package.json").read_text(encoding="utf-8"))


def v2(**kw):
    c = copy.deepcopy(PKG19["candidates"][0])
    c.update(kw)
    return c


def test_v2_weights_sum_to_100_and_score_correctly():
    assert sum(candidates.WEIGHTS_V2.values()) == 100
    c = v2(scores={"curiosity": 10, "storytelling": 10, "shareability": 9, "global_relevance": 9, "freshness": 5, "visual": 8, "originality": 7})
    assert candidates.trend_score(c)["total"] == 87.0
    assert candidates.trend_score(v2(scores={**c["scores"], "curiosity": "UNKNOWN"}))["unknown"] == ["curiosity"]


def test_v2_candidate_fields_and_verification_gate():
    assert candidates.validate(v2()) == []
    assert any("main_claim" in x for x in candidates.validate({k: v for k, v in v2().items() if k != "main_claim"}))
    assert any("verification_status" in x for x in candidates.validate(v2(verification_status="maybe")))
    assert candidates.ineligible_reason(v2(verification_status="UNVERIFIED"))
    assert candidates.ineligible_reason(v2(verification_status="PARTLY VERIFIED")) is None


def test_old_v1_packages_still_validate():
    assert package.validate(PKG)[0] == []


def test_todays_v2_package_is_recording_ready():
    problems_, info = package.validate(PKG19)
    assert problems_ == [] and info["ready"]["status"] == ver.READY


def test_v2_package_needs_visuals_evidence_and_v2_scores():
    def p19(mod):
        p = copy.deepcopy(PKG19)
        mod(p)
        return package.validate(p)[0]
    assert any("visuals" in x for x in p19(lambda p: p.__setitem__("visuals", [])))
    assert any("supporting_evidence" in x for x in p19(lambda p: p["factcheck"]["claims"][0].pop("supporting_evidence")))
    assert any("source_title" in x for x in p19(lambda p: p["factcheck"]["claims"][0].pop("source_title")))
    assert any("v2 criteria" in x for x in p19(lambda p: p["candidates"].append(copy.deepcopy(PKG["candidates"][0]))))


def test_new_claim_types_rumour_and_prediction():
    from creatoros.factcheck import claims as fc
    base = {"id": "z", "text": "t", "evidence": ["https://example.com"], "in_script": True}
    assert any("RUMOR" in x for x in fc.validate({"claims": [{**base, "status": "RUMOR"}]}, "x"))
    assert any("attribution" in x for x in fc.validate({"claims": [{**base, "status": "PREDICTION"}]}, "x"))


def test_hook_reuse_is_detected():
    assert package.reused_hook(PKG["hook"], "some-other-slug")
    assert package.reused_hook("A completely different opening about rockets.", "x") is None


def test_today_and_recording_views():
    d = ROOT / "daily" / "2026-11-19"
    today = (d / "today.md").read_text(encoding="utf-8")
    for heading in ("DATE:", "SELECTED TOPIC:", "WHY THIS TOPIC:", "VIRAL POTENTIAL:", "BEST HOOK:", "FINAL SCRIPT:", "ESTIMATED DURATION:",
                    "RECORDING DIRECTIONS:", "VISUAL SUGGESTIONS", "FACT-CHECK:", "ENGLISH CAPTIONS:", "PLATFORM CONTENT:"):
        assert heading in today, heading
    rec = (d / "recording.md").read_text(encoding="utf-8")
    assert PKG19["script"].splitlines()[0] in rec and "PLATFORM" not in rec


def test_memory_upserts_without_duplicates(tmp_path):
    t, c = tmp_path / "t.jsonl", tmp_path / "c.jsonl"
    ranked = candidates.rank(PKG19["candidates"])
    memory.record(PKG19, ranked, t, c)
    memory.record(PKG19, ranked, t, c)
    rows = memory.topics(t)
    assert len(rows) == len(PKG19["candidates"])
    assert [r["state"] for r in rows if r["headline"] == PKG19["topic"]] == ["selected"]
    assert {r["state"] for r in rows} >= {"selected", "rejected", "held", "covered"}
    assert len(memory.claims(c)) == len(PKG19["factcheck"]["claims"])


def test_analytics_new_fields(tmp_path):
    d = store.upsert(dict(date="2026-11-20", video_id="v", platform="instagram", checkpoint="24h", views="1000", viewed_rate="0.62",
                          top_countries="IN 40%; US 12%"), tmp_path / "p.csv")
    assert d["viewed_rate"] == 0.62 and d["top_countries"] == "IN 40%; US 12%"


def test_cli_runlog_and_ist_date(tmp_path, monkeypatch, capsys):
    assert len(cli.ist_today()) == 10
    assert cli.main(["recording", "--date", "2026-11-19"]) == 0
    assert "Harrell" in capsys.readouterr().out
    assert cli.main(["today", "--date", "1999-01-01"]) == 3


def test_runstatus_verdicts(tmp_path):
    import datetime as dt
    import json
    from creatoros.research import runstatus
    log = tmp_path / "runs.jsonl"
    utc = lambda h, m: dt.datetime(2026, 11, 20, h, m, tzinfo=dt.timezone.utc)
    st = lambda now: runstatus.status(log, "2026-11-20", now)["verdict"]
    assert st(utc(3, 0)) == "PENDING"          # 08:30 IST, not due
    assert st(utc(3, 40)) == "MISSED"          # 09:10 IST, nothing logged
    def add(ev, h, m, status="", trigger="scheduled"):
        with open(log, "a") as fh:
            fh.write(json.dumps({"event": ev, "trigger": trigger, "status": status, "ist_date": "2026-11-20",
                                 "at_utc": utc(h, m).isoformat()}) + "\n")
    add("start", 3, 12)
    assert st(utc(3, 30)) == "RUNNING"
    assert st(utc(4, 5)) == "FAILED"           # no end after 09:30 IST
    add("end", 3, 50, "READY")
    r = runstatus.status(log, "2026-11-20", utc(4, 5))
    assert r["verdict"] == "OK" and not r["problem"] and r["started_ist"] == "08:42"
    add("end", 4, 10, "READY")
    assert st(utc(4, 20)) == "LATE"
