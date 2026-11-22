"""V7 (Viral AI & Technology Creator Engine, from 22 Nov 2026): virality model with a verification gate, extraordinary
claims, the V7 hook engine, 30-40 s scripts, ten script checks, story history and weekly growth checkpoints."""
import json
from pathlib import Path

import pytest

from creatoros.analytics import growth, learning, store
from creatoros.factcheck import evidence as ev
from creatoros.research import candidates as cm
from creatoros.scripts import lint, package


# --- extraordinary claims ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Levent Alpöge says he and Claude proved the Riemann Hypothesis",
    "The proof settles the Riemann Hypothesis",
    "The lab says its model has reached artificial general intelligence",
    "A new gene therapy cured sickle cell disease in all patients",
    "The AI discovered a new antibiotic on its own",
    "It is the world's first fully autonomous surgery",
    "The startup raised $2 billion",
    "Hackers breached the company and stole millions of records",
    "A zero-day is being actively exploited",
    "The humanoid robot does household chores without any teleoperation",
])
def test_extraordinary_claims_are_detected(text):
    assert ev.is_extraordinary(text)


@pytest.mark.parametrize("text", [
    "Signal blocks screenshots by default on iOS 27",
    "The Riemann Hypothesis was first posed in 1859",
    "Users can turn the protection off",
    "The app is free on iPhone and Android",
])
def test_ordinary_claims_are_not_extraordinary(text):
    assert not ev.is_extraordinary(text)


GH = {"url": "https://github.com/leanprover-community/riemann-hypothesis", "kind": "primary", "access": "opened",
      "date": "2026-11-20"}
SNIP = {"url": "https://www.scientificamerican.com/article/x", "kind": "news", "access": "search-index", "date": "2026-11-21"}
OPENED_NEWS = {"url": "https://www.science.org/content/article/y", "kind": "news", "access": "opened", "date": "2026-11-21"}
EXPERT = {"url": "https://terrytao.example.org/post", "kind": "expert", "access": "opened", "date": "2026-11-21",
          "outlet": "independent mathematician"}


def claim(items, text="Alpöge says he and Claude proved the Riemann Hypothesis"):
    return {"id": "c1", "text": text, "status": "CLAIMED", "evidence": items, "in_script": True}


def test_a_github_repository_and_snippets_never_confirm_an_extraordinary_claim():
    r = ev.gate(claim([GH, SNIP]), "2026-11-22", extraordinary_rule=True)
    assert any("independent confirmation opened directly" in x for x in r)
    gh_as_news = {**GH, "kind": "news"}
    assert ev.extraordinary_problems(claim([GH, gh_as_news]))          # GitHub never counts as independent


def test_extraordinary_claim_passes_with_primary_and_independent_confirmation_opened():
    assert ev.gate(claim([GH, OPENED_NEWS, SNIP]), "2026-11-22", extraordinary_rule=True) == []
    assert ev.gate(claim([GH, EXPERT]), "2026-11-22", extraordinary_rule=True) == []


def test_extraordinary_rule_needs_the_primary_opened():
    r = ev.extraordinary_problems(claim([{**GH, "access": "search-index"}, OPENED_NEWS]))
    assert any("open the primary source" in x for x in r)


def test_older_packages_keep_their_rule():
    assert ev.gate(claim([GH, SNIP]), "2026-11-22") == []                # without the V7 flag nothing changes


def test_the_22_nov_riemann_package_would_be_held_under_v7():
    f = Path(__file__).parent / "fixtures" / "v6_trial_2026-11-22" / "package.json"
    p = json.loads(f.read_text(encoding="utf-8"))
    from creatoros.factcheck import verification as ver
    r = ver.readiness_v5(p["factcheck"]["claims"], p["script"], [], p["date"], extraordinary_rule=True)
    assert r["status"] != "RECORDING READY" and any("extraordinary" in x for x in r["reasons"])


# --- candidates: V7 virality model and the verification gate ----------------------------------------------------------

def cand(status="CONFIRMED", sm=3, **kw):
    sc = {k: 7 for k in cm.WEIGHTS_V7}
    sc["social_momentum"] = sm
    return {"headline": "h", "category": "AI", "topic_type": "BREAKING", "published_at": "2026-11-22",
            "original_source": "https://example.org/a", "main_claim": "m", "verification_status": "VERIFIED",
            "why_it_matters": "w", "potential_hook": "p", "target_audience": "t", "uncertainty": "u",
            "evidence_confidence": "HIGH", "already_covered": False, "x_signal": {"status": "NOT VERIFIED", "posts": []},
            "claim_status": status, "latest_development": "l", "audience_relevance": "a", "practical_usefulness": "u",
            "visual_potential": "v", "potential_controversy": "c", "scores": sc, **kw}


def test_v7_weights_and_scheme():
    assert sum(cm.WEIGHTS_V7.values()) == 100 and cm.WEIGHTS_V7["broad_relevance"] == 20
    assert cm.scheme(cand()) == "v7" and cm.validate(cand()) == []
    assert cm.trend_score(cand())["total"] == pytest.approx(0.7 * 85 + 0.3 * 15)


@pytest.mark.parametrize("status", ["COMPANY-CLAIMED", "PRELIMINARY", "SPECULATIVE", "DISPUTED"])
def test_verification_is_a_gate_not_a_bonus(status):
    hi = cand(status)
    hi["scores"] = {k: 10 for k in cm.WEIGHTS_V7}
    hi["scores"]["social_momentum"] = 3
    r = cm.rank([hi, cand("INDEPENDENTLY REPORTED")])
    assert r[0]["claim_status"] == "INDEPENDENTLY REPORTED" and r[0]["eligible"]
    assert not r[1]["eligible"] and "verification gate" in r[1]["ineligible_reason"]


def test_social_momentum_needs_observed_evidence():
    assert any("social_momentum above 3" in x for x in cm.validate(cand(sm=5)))
    with_ev = cand(sm=6)
    with_ev["x_signal"] = {"status": "NOT VERIFIED", "posts": [], "discussion_evidence": ["https://news.example/x"]}
    assert cm.validate(with_ev) == []
    assert any("above 6" in x for x in cm.validate({**with_ev, "scores": {**with_ev["scores"], "social_momentum": 8}}))


# --- hooks, length and script checks ----------------------------------------------------------------------------------

def hook(text, approach, acc=9, base=8):
    return {"text": text, "approach": approach, **{k: base for k in lint.HOOK_CRITERIA_V7}, "accuracy": acc}


def test_v7_hooks():
    hs = [hook("A free app now edits your video for you", "practical discovery", base=9),
          hook("This robot folded laundry on stage", "unusual demonstration"),
          hook("Your phone's AI can read your chats", "important warning"),
          hook("Google just shipped a feature nobody asked for", "contradiction"),
          hook("OpenAI's new tool lands today", "major product reveal")]
    assert lint.check_hooks_v7(hs, hs[0]["text"]) == []
    assert any("top-scoring" in x for x in lint.check_hooks_v7(hs, hs[1]["text"]))
    assert any("at least 5" in x for x in lint.check_hooks_v7(hs[:4], hs[0]["text"]))
    bad = hs[:4] + [hook("AI is getting crazy, look at this", "contradiction")]
    assert any("generic hook" in x for x in lint.check_hooks_v7(bad, hs[0]["text"]))
    same = [hook(f"Hook number {i} about phones", "important warning") for i in range(5)]
    assert any("3 different" in x for x in lint.check_hooks_v7(same, same[0]["text"]))


def words(n, per=8):
    w = ["phones" if i % 3 else "signal" for i in range(n)]
    return " ".join(" ".join(w[i:i + per]).capitalize() + "." for i in range(0, n, per))


def test_v7_length_is_30_to_40_seconds_at_a_natural_pace():
    assert lint.limits("v7")["hard_max_seconds"] == 40 and lint.limits("v7")["target_words"] == [70, 90]
    ok = lint.check(words(78), "english", "v7")
    assert 30 <= ok["seconds"] <= 40 and not ok["problems"]
    long = lint.check(words(92), "english", "v7")
    assert long["seconds"] > 40 and any("hard maximum" in x for x in long["problems"])


def checks(**fail):
    return {k: {"pass": k not in fail, "why": fail.get(k, "a concrete reason stated here")} for k in lint.SCRIPT_CHECKS_V7}


def test_script_checks():
    r = lint.script_checks_v7(checks())
    assert r["approved"] and r["total"] == 100
    r = lint.script_checks_v7(checks(no_redundancy="sentence four repeats the headline"))
    assert not r["approved"] and r["total"] == 90 and "revise" in r["problems"][0]


# --- growth and learning ------------------------------------------------------------------------------------------

def test_weekly_checkpoints_follow_a_straight_line_from_the_baseline(tmp_path, monkeypatch):
    monkeypatch.setattr(growth, "settings", lambda: {"target_followers": 100000, "days": 60, "start_date": "2026-11-22",
                                                     "platform": "instagram"})
    f = tmp_path / "f.csv"
    growth.add_snapshot("2026-11-22", "instagram", 4000, "creator", f)
    growth.add_snapshot("2026-11-28", "instagram", 5000, "creator", f)
    d = growth.dashboard("2026-11-28", f, tmp_path / "p.csv", tmp_path / "db.jsonl")
    wk = d["weekly_checkpoints"]
    assert len(wk) == 9 and wk[-1]["date"] == "2027-01-20" and wk[-1]["target"] == 100000
    assert wk[0] == {"week": 1, "date": "2026-11-28", "target": round(4000 + 96000 * 6 / 59), "actual": 5000}
    assert "Week 1 (2026-11-28)" in growth.render(d)
    none = growth.dashboard("2026-11-28", tmp_path / "none.csv", tmp_path / "p.csv", tmp_path / "db.jsonl")
    assert none["weekly_checkpoints"][0]["target"] == "UNKNOWN"


def test_learning_compares_script_length_and_posting_time(tmp_path):
    f = tmp_path / "p.csv"
    for i, (dur, at) in enumerate([(33, "2026-11-23T19:00:00+05:30")] * 3 + [(44, "2026-11-23T09:00:00+05:30")] * 3):
        store.upsert(dict(date="2026-11-23", video_id=f"v{i}", platform="instagram", checkpoint="7d", views="1000",
                          new_followers=str(20 if dur == 33 else 5), duration_s=str(dur), posted_at=at), f)
    d = learning.learn(f)
    bands = {g["name"]: g for g in d["dimensions"]["length_band"]}
    assert bands["30-35s"]["follows_per_1k_views"] == 20.0 and bands["40-45s"]["enough_data"]
    assert {g["name"] for g in d["dimensions"]["posting_hour_ist"]} == {"19:00 IST", "09:00 IST"}
    assert any(x.startswith("length_band: strongest follower conversion '30-35s'") for x in d["lessons"])


# --- the real V7 package for 22 Nov 2026 (controlled production test) -------------------------------------------------

def v7pkg():
    return json.loads((Path(__file__).parent / "fixtures" / "v7_2026-11-22" / "package.json").read_text(encoding="utf-8"))


def test_the_tesla_package_is_held_because_every_source_was_a_search_excerpt(monkeypatch):
    monkeypatch.setattr(package, "holds_for", lambda date: [])
    probs, info = package.validate(v7pkg())
    assert info["ready"]["status"] != "RECORDING READY"
    assert sum("supported only by search excerpts" in r for r in info["ready"]["reasons"]) == 4


def opened_copy():
    """Synthetic: the same package as if every source had been opened (tests rendering only, not a real record)."""
    p = json.loads(json.dumps(v7pkg()))
    for c in p["factcheck"]["claims"]:
        for it in c["evidence"]:
            it["access"] = "opened"
    return p


def test_search_excerpts_never_raise_a_v7_level():
    c = v7pkg()["factcheck"]["claims"][0]
    assert ev.level(c)["level"] == "MEDIUM-HIGH" and ev.level(c, strict=True)["level"] == "LOW"


def test_v7_package_is_ready_and_renders_seven_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(package, "holds_for", lambda date: [])   # independent of today's real holds
    p = opened_copy()
    probs, info = package.validate(p)
    assert probs == [] and info["ready"]["status"] == "RECORDING READY"
    assert 30 <= info["lint"]["seconds"] <= 40 and 70 <= info["lint"]["words"] <= 90
    r = package.save(p, tmp_path, record=False)               # regression: saving a v7 package once crashed on hook criteria
    assert r["ok"]
    today = (tmp_path / "today.md").read_text(encoding="utf-8")
    for h in ["## 1. Today's story", "## 2. Why this story", "## 3. Final recording script", "## 4. Caption", "## 5. Sources",
              "## 6. Fact-check notes", "## 7. Recording guidance"]:
        assert h in today
    assert "Editing" not in today and "edit beats" not in today.lower()
    rj = json.loads((tmp_path / "research.json").read_text(encoding="utf-8"))
    assert rj["story"]["company"] == "Tesla" and len(rj["hooks"]) >= 5


def test_v7_package_rules_refuse_bad_changes(monkeypatch):
    monkeypatch.setattr(package, "holds_for", lambda date: [])
    base = opened_copy()
    long = base["script"].replace("Would seeing", "Honestly, after all of that, and thinking about it carefully, would seeing")
    assert any("hard maximum" in x for x in package.validate({**base, "script": long})[0])
    assert any("why_this_story" in x for x in package.validate({**base, "why_this_story": "word " * 120})[0])
    tk = {**base["practical_takeaway"], "price": ""}
    assert any("practical_takeaway" in x for x in package.validate({**base, "practical_takeaway": tk})[0])
    ch = {**base["script_checks"], "no_jargon": {"pass": False, "why": "critical interventions is unexplained jargon"}}
    assert any("script check failed" in x for x in package.validate({**base, "script_checks": ch})[0])
    cands = [dict(c) for c in base["candidates"]]
    for c in cands:
        if c["headline"].startswith("OpenRouter"):
            c.pop("hold_reason")                               # without the hold, the higher-scoring story must win
    assert any("topic must be the top eligible candidate" in x for x in package.validate({**base, "candidates": cands})[0])
