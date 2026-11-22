"""v6 (creator-led editorial quality, from 2026-11-23): rubric, claim status, 25 hooks, variants, pacing, gate, learning."""
import csv
import json

import pytest

from creatoros import config
from creatoros.analytics import growth, learning, store
from creatoros.factcheck import claims as fcmod
from creatoros.research import candidates as cm
from creatoros.scripts import lint, package


def words(n, per_sentence=9):
    """A plain English script of n words in sentences of per_sentence words."""
    w = [("signal" if i % 3 else "phones") for i in range(n)]
    out = []
    for i in range(0, n, per_sentence):
        out.append(" ".join(w[i:i + per_sentence]).capitalize() + ".")
    return " ".join(out)


# --- pacing ----------------------------------------------------------------------------------------------------------

def test_v6_pacing_refuses_a_crammed_105_word_script():
    chk = lint.check(words(105), "english", "v6")
    assert chk["seconds"] > 45 and any("hard maximum" in p for p in chk["problems"])
    assert "natural moderate pace" in chk["pace_basis"]


def test_v6_pacing_accepts_about_90_words_and_v5_pace_is_unchanged():
    chk = lint.check(words(90), "english", "v6")
    assert 35 <= chk["seconds"] <= 45 and not chk["problems"]
    assert lint.check(words(105), "english", "v5")["seconds"] < chk["seconds"] + 10   # v5 keeps its own estimate


def test_v6_rejects_long_sentences_and_generic_openings():
    long = lint.check(words(90, per_sentence=30), "english", "v6")
    assert any("longer than 22 words" in p for p in long["problems"])
    gen = lint.check("Something crazy just happened. " + words(85), "english", "v6")
    assert any("generic opening" in p for p in gen["problems"])


# --- hooks -----------------------------------------------------------------------------------------------------------

def hook(text, approach, acc=9, base=8):
    return {"text": text, "approach": approach, "accuracy": acc, "curiosity": base, "clarity": base, "credibility": base,
            "emotional": base, "natural": base}


def five_hooks(prefix="Signal"):
    return [hook(f"{prefix} hook about {a}", a) for a in lint.HOOK_APPROACHES]


def test_five_hooks_one_per_approach_pass():
    assert lint.check_finalist_hooks(five_hooks(), "f") == []


@pytest.mark.parametrize("bad", ["Big news in AI today: Signal changed", "You won't believe what Signal did",
                                 "Stop scrolling, Signal did something", "This is insane, Signal blocked screenshots"])
def test_generic_hooks_are_rejected(bad):
    assert lint.hook_text_problems(bad)


def test_hook_must_land_in_two_seconds_and_cover_every_approach():
    assert lint.hook_text_problems("one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen")
    hs = five_hooks()
    hs[4]["approach"] = "surprising fact"
    assert any("each approach once" in p for p in lint.check_finalist_hooks(hs, "f"))
    assert any("exactly 5" in p for p in lint.check_finalist_hooks(hs[:4], "f"))


# --- creative gate ---------------------------------------------------------------------------------------------------

def gate(**fail):
    return {k: {"pass": k not in fail, "why": fail.get(k, "a concrete reason given here")} for k in lint.CREATIVE_GATE}


def test_creative_gate_all_yes_passes_and_any_no_fails():
    assert lint.creative_gate(gate()) == []
    probs = lint.creative_gate(gate(memorable_ending="the ending just repeats the facts"))
    assert probs and "Is the ending memorable?" in probs[0]
    g = gate()
    g["takeaway"] = {"pass": True, "why": "yes"}                  # a reason must be concrete
    assert lint.creative_gate(g)


# --- candidates: v6 rubric and claim status --------------------------------------------------------------------------

def cand(status="CONFIRMED", fc=8, **kw):
    sc = {k: 7 for k in cm.WEIGHTS_V6}
    sc["factual_confidence"] = fc
    return {"headline": "h", "category": "AI", "topic_type": "BREAKING", "published_at": "2026-11-22",
            "original_source": "https://example.org/a", "main_claim": "m", "verification_status": "VERIFIED",
            "why_it_matters": "w", "potential_hook": "p", "target_audience": "t", "uncertainty": "u",
            "evidence_confidence": "HIGH", "already_covered": False, "x_signal": {"status": "NOT VERIFIED", "posts": []},
            "claim_status": status, "why_share": "s", "visual_note": "v", "scores": sc, **kw}


def test_v6_weights_sum_to_100_and_scheme_is_detected():
    assert sum(cm.WEIGHTS_V6.values()) == 100
    assert cm.scheme(cand()) == "v6" and cm.validate(cand()) == []
    assert cm.trend_score(cand())["total"] == pytest.approx(0.7 * 92 + 0.8 * 8)


def test_v6_score_is_weighted():
    c = cand(fc=10)
    assert cm.trend_score(c)["total"] == pytest.approx(0.7 * 92 + 8)


@pytest.mark.parametrize("status", ["CLAIMED", "SPECULATIVE", "UNVERIFIED"])
def test_only_confirmed_or_reported_stories_can_be_selected(status):
    r = cm.rank([cand(status, fc=6)])[0]
    assert not r["eligible"] and "claim status" in r["ineligible_reason"]
    assert cm.rank([cand("REPORTED", fc=6)])[0]["eligible"]


def test_factual_confidence_must_match_the_evidence():
    assert any("needs claim_status CONFIRMED" in p for p in cm.validate(cand("REPORTED", fc=9)))
    assert "below 6" in cm.rank([cand(fc=5)])[0]["ineligible_reason"]


def test_claimed_statements_need_attribution_in_the_script():
    fc = {"claims": [{"id": "c1", "text": "Signal says X", "status": "CLAIMED", "evidence": ["https://signal.org/b"],
                      "in_script": True, "attribution": "Signal", "script_attribution": "Signal says"}]}
    assert fcmod.validate(fc, "Signal says it blocks screenshots.") == []
    assert fcmod.validate(fc, "It blocks screenshots.")


# --- package-level rules ---------------------------------------------------------------------------------------------

def test_packages_from_23_nov_must_be_v7():
    p = json.loads(config.path("daily", "2026-11-22", "previous_signal-blocks-screenshots-ai-assistants",
                               "package.json").read_text(encoding="utf-8"))
    probs, _ = package.validate({**p, "date": "2026-11-23"})
    assert probs and '"v7"' in probs[0]
    probs, _ = package.validate({**trial(), "date": "2026-11-23"})
    assert probs and '"v7"' in probs[0]


def test_22_nov_v5_package_still_validates():
    p = json.loads(config.path("daily", "2026-11-22", "previous_signal-blocks-screenshots-ai-assistants",
                               "package.json").read_text(encoding="utf-8"))
    probs, info = package.validate(p)
    assert probs == [] and info["ready"]["status"] == "RECORDING READY"


# --- performance learning --------------------------------------------------------------------------------------------

def test_learning_reports_missing_connection_and_no_data(tmp_path):
    d = learning.learn(tmp_path / "none.csv")
    assert d["status"] == "NO DATA" and "NOT CONNECTED" in d["connection"]
    assert "No Instagram performance data" in learning.summary_line(d)
    assert all(v is None for v in d["baseline"].values())


def test_learning_compares_groups_with_the_account_median_and_needs_three_reels(tmp_path):
    f = tmp_path / "p.csv"
    rows = [("a", "contrarian question", 1000, 20), ("b", "contrarian question", 1000, 18), ("c", "contrarian question", 1000, 22),
            ("d", "surprising fact", 1000, 5), ("e", "surprising fact", 1000, 6), ("f", "surprising fact", 1000, 4),
            ("g", "visual demonstration", 1000, 50)]
    for vid, ht, views, fol in rows:
        store.upsert(dict(date="2026-11-23", video_id=vid, platform="instagram", checkpoint="7d", views=str(views),
                          new_followers=str(fol), hook_type=ht), f)
    store.upsert(dict(date="2026-11-23", video_id="a", platform="instagram", checkpoint="24h", views="10",
                      new_followers="0", hook_type="contrarian question"), f)      # the 7d row wins over 24h
    d = learning.learn(f)
    assert d["reels_with_data"] == 7 and d["status"] == "PROVISIONAL"
    hooks = {g["name"]: g for g in d["dimensions"]["hook_type"]}
    assert hooks["visual demonstration"]["enough_data"] is False          # one reel is an anecdote
    assert hooks["contrarian question"]["follows_per_1k_views"] == 20.0
    assert any("strongest follower conversion 'contrarian question'" in x and "weakest 'surprising fact'" in x
               for x in d["lessons"])


def test_growth_goal_is_100k_in_60_days_from_22_nov():
    s = growth.settings()
    assert (s["target_followers"], s["days"], s["start_date"]) == (100000, 60, "2026-11-22")


# --- the real production-equivalent trial (22 Nov 2026, fresh-context subagent, v6 rules) -----------------------------



def trial():
    from pathlib import Path
    f = Path(__file__).parent / "fixtures" / "v6_trial_2026-11-22" / "package.json"
    return json.loads(f.read_text(encoding="utf-8"))


def test_trial_package_is_recording_ready_and_delivers_eight_items_only(tmp_path, monkeypatch):
    monkeypatch.setattr(package, "holds_for", lambda date: [])   # as it stood at trial time (the story was held later under V7)
    p = trial()
    probs, info = package.validate(p)
    assert probs == [] and info["ready"]["status"] == "RECORDING READY"
    r = package.save(p, tmp_path, record=False)
    assert r["ok"] and r["content_db"] == "not recorded (trial)"
    today = (tmp_path / "today.md").read_text(encoding="utf-8")
    for h in ["## 1. Today's story", "## 2. Why it was selected", "## 3. Verified facts and sources",
              "## 4. Recording-ready script", "## 5. Estimated speaking duration", "## 6. Opening visual", "## 7. Caption",
              "## 8. Hashtags"]:
        assert h in today
    assert "contrarian question" not in today and "Version B" not in today       # internal material stays internal
    creative = (tmp_path / "creative.md").read_text(encoding="utf-8")
    assert "(chosen)" in creative and "Version C" in creative and "Creative quality gate" in creative
    rj = json.loads((tmp_path / "research.json").read_text(encoding="utf-8"))
    assert sum(len(f["hooks"]) for f in rj["finalists"]) == 5 * len(p["finalists"]) and set(rj["variants"]) == {"A", "B", "C"}


def test_trial_mutations_are_refused(monkeypatch):
    monkeypatch.setattr(package, "holds_for", lambda date: [])
    base = trial()
    p = {**base, "script": base["variants"]["B"]["script"]}
    assert any("selected variant" in x or "chosen hook" in x or "open with" in x for x in package.validate(p)[0])
    vp = {**base["visual_plan"], "demonstrations": ["robot folds laundry"]}
    assert any("never describe a demonstration" in x for x in package.validate({**base, "visual_plan": vp})[0])
    fin = json.loads(json.dumps(base["finalists"]))
    fin[0]["hooks"][0]["text"] = "Big news in AI today: math changed"
    assert any("generic hook" in x for x in package.validate({**base, "finalists": fin})[0])
    g = {**base["creative_gate"], "memorable_ending": {"pass": False, "why": "the ending only repeats the facts"}}
    assert any("creative gate failed" in x for x in package.validate({**base, "creative_gate": g})[0])
    v = json.loads(json.dumps(base["variants"]))
    v["C"]["script"] = v["C"]["script"] + " " + " ".join(["And that is a very long extra sentence."] * 3)
    assert any(x.startswith("variant C") for x in package.validate({**base, "variants": v})[0])
