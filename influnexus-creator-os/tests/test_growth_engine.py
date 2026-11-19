"""v4 growth engine: source audit, cross-platform signals, v3 package rules, growth dashboard, weekly review."""
import copy
import datetime as dt
import json
from pathlib import Path

import pytest

from creatoros.analytics import growth, store, weekly
from creatoros.research import candidates, signals
from creatoros.scripts import lint, package
from test_production import WIN, _as_v3

ROOT = Path(__file__).resolve().parents[1]


def v3pkg():
    return _as_v3(json.loads((ROOT / "daily/2026-11-19/previous_als-brain-implant-home-use/package.json").read_text()))


# --- source audit ----------------------------------------------------------------------------------------------------

def fake_prober(open_hosts):
    return lambda h: {"host": h, "reachable": h in open_hosts, **({"http": 200} if h in open_hosts else {"error": "blocked"})}


def test_audit_classifies_groups_and_needs_data_hosts_not_just_api_hosts():
    r = signals.audit(fake_prober({"www.anthropic.com", "github.com", "www.googleapis.com", "www.reddit.com"}))
    g = r["groups"]
    assert g["primary"]["status"] == "PARTIAL" and g["x"]["status"] == "BLOCKED"
    assert g["youtube"]["status"] == "BLOCKED"            # only the keyed API host answers
    assert "YouTube Data API key" in g["youtube"]["needs_credentials"][0]
    assert g["reddit"]["status"] == "PARTIAL"
    all_open = signals.audit(fake_prober({h for hs in signals.GROUP_HOSTS.values() for h in hs}))
    assert all(v["status"] == "WORKING" for k, v in all_open["groups"].items() if k not in ("youtube", "x", "instagram", "reddit"))


def test_blocked_platform_cannot_be_directly_observed_and_engagement_needs_a_basis():
    sig = {"platform": "x", "url": "https://x.com/a/status/1", "title": "post", "retrieved_at": "2026-11-20T03:00:00+00:00",
           "access": "DIRECTLY OBSERVED", "engagement": {"basis": "observed", "likes": 1200}}
    assert any("BLOCKED" in p for p in signals.signal_problems(sig, 0, {"x"}))
    assert signals.signal_problems(sig, 0, set()) == []
    sig.update(access="SEARCH-INDEX")
    assert any("DIRECTLY OBSERVED" in p for p in signals.signal_problems(sig, 0, {"x"}))       # observed needs the page
    sig["engagement"] = {"basis": "reported", "likes": 1200}
    assert any("engagement.source" in p for p in signals.signal_problems(sig, 0, {"x"}))
    sig["engagement"]["source"] = "TechCrunch article"
    assert signals.signal_problems(sig, 0, {"x"}) == []
    sig["engagement"] = {"likes": 5}
    assert any("need a basis" in p for p in signals.signal_problems(sig, 0, set()))
    sig["engagement"] = {"basis": "unknown", "likes": "UNKNOWN"}
    assert signals.signal_problems(sig, 0, set()) == []


def test_signal_summary_counts_platforms():
    s = signals.summary([{"platform": "x", "access": "SEARCH-INDEX"}, {"platform": "news", "access": "SECONDARY"},
                         {"platform": "x", "access": "DIRECTLY OBSERVED"}])
    assert s["count"] == 2 and s["directly_observed"] == ["x"]


# --- v3 package rules ------------------------------------------------------------------------------------------------

def test_complete_v3_package_passes_and_renders_the_new_sections():
    p = v3pkg()
    p["quality_scores"].update({k: 10 for k in lint.QUALITY_CHECKS})
    probs, info = package.validate(p)
    assert probs == []
    today = package.render_today(p, info)
    for heading in ("CROSS-PLATFORM EVIDENCE", "BACKUP STORIES", "VISUAL PRODUCTION NOTES", "RESEARCH LIMITATIONS",
                    "RUN STATUS", "PILLAR / FORMAT", "WHY PEOPLE WILL CARE"):
        assert heading in today
    assert today.count(p["hook"]) >= 1 and "Hook candidates" not in today
    md = package.render(p, info)
    assert "only the winning hook is delivered" in md
    assert not any(h["text"] in md for h in p["hooks"] if h["text"] != p["hook"])


@pytest.mark.parametrize("mod,expect", [
    (lambda p: p.update(pillar="memes"), "pillar must be one of"),
    (lambda p: p.update(format="Z"), "format must be one of"),
    (lambda p: p.update(backups=p["backups"][:1]), "two backup stories"),
    (lambda p: p.update(backups=[p["topic"], p["backups"][0]]), "cannot be the selected story"),
    (lambda p: p["audience"].pop("follow"), "audience: answer ['follow']"),
    (lambda p: p["editing"].pop("sound"), "editing: missing ['sound']"),
    (lambda p: p["candidates"][0].pop("signals"), "cross-platform evidence"),
    (lambda p: p["hooks"][0].pop("specificity"), "lacks scores"),
])
def test_v3_package_rule_breaks(mod, expect):
    p = v3pkg()
    p["quality_scores"].update({k: 10 for k in lint.QUALITY_CHECKS})
    mod(p)
    assert any(expect in x for x in package.validate(p)[0]), package.validate(p)[0]


def test_backup_shortfall_can_be_explained():
    p = v3pkg()
    p["quality_scores"].update({k: 10 for k in lint.QUALITY_CHECKS})
    p.update(backups=p["backups"][:1], backup_shortfall_reason="only two stories passed verification today")
    assert package.validate(p)[0] == []


def test_repeated_opening_is_rejected(monkeypatch):
    from creatoros.research import content_db
    p = v3pkg()
    p["quality_scores"].update({k: 10 for k in lint.QUALITY_CHECKS})
    monkeypatch.setattr(content_db, "entries", lambda path=None: [
        {"date": "2026-11-15", "slug": "other", "topic": "Unrelated chip story", "status": "scripted", "hook": p["hook"].split(".")[0] + ". Something else entirely."}])
    assert any("opens like" in x for x in package.validate(p)[0])
    monkeypatch.setattr(content_db, "entries", lambda path=None: [
        {"date": "2026-10-01", "slug": "other", "topic": "Unrelated chip story", "status": "scripted", "hook": p["hook"]}])
    assert not any("opens like" in x for x in package.validate(p)[0])


def test_new_generic_phrases_and_claim_labels():
    assert any("groundbreaking" in x for x in lint.check("This groundbreaking chip is small. Only time will tell.")["problems"])
    from creatoros.factcheck import claims
    assert "REPORTED" in claims.NEEDS_ATTRIBUTION and "SPECULATIVE" in claims.NOT_USABLE


def test_v3_hook_scoring_uses_seven_criteria():
    hooks = [{"text": t, "mechanism": m, **{k: 8 for k in lint.HOOK_CRITERIA_V3}}
             for t, m in zip("abcdefghij", lint.HOOK_MECHANISMS)]
    hooks[3]["surprise"] = 10
    assert lint.score_hooks(hooks, lint.HOOK_CRITERIA_V3)[0]["text"] == "d"
    assert lint.check_hooks(hooks, "d", lint.HOOK_CRITERIA_V3) == []
    assert lint.check_hooks(hooks, "a", lint.HOOK_CRITERIA_V3)


# --- growth dashboard ------------------------------------------------------------------------------------------------

def test_dashboard_is_unknown_without_data(tmp_path):
    d = growth.dashboard("2026-11-25", tmp_path / "f.csv", tmp_path / "p.csv", tmp_path / "db.jsonl")
    assert d["day"] == 6 and d["phase"].startswith("Phase 1")
    assert d["current_followers"] == "UNKNOWN" and d["daily_net_growth_required"] == "UNKNOWN"
    assert d["conversion"]["followers_per_1k_views"] == "UNKNOWN"
    assert "UNKNOWN" in growth.render(d)


def test_growth_mathematics_and_trajectory(tmp_path):
    """The target counts Instagram only; other platforms are reported separately, never added in."""
    f, perf = tmp_path / "f.csv", tmp_path / "p.csv"
    growth.add_snapshot("2026-11-20", "instagram", 2000, "app", f)
    growth.add_snapshot("2026-11-20", "youtube", 1000, "studio", f)
    growth.add_snapshot("2026-11-30", "instagram", 6000, "app", f)
    store.upsert(dict(date="2026-11-21", video_id="v1", platform="instagram", checkpoint="7d", views="50000",
                      new_followers="400"), perf)
    store.upsert(dict(date="2026-11-21", video_id="v1", platform="instagram", checkpoint="24h", views="10000",
                      new_followers="50"), perf)
    d = growth.dashboard("2026-11-30", f, perf, tmp_path / "db.jsonl")
    assert d["current_followers"] == 6000 and d["followers_by_platform"]["youtube"] == 1000
    assert d["remaining_followers"] == 94000 and d["days_remaining"] == 49
    assert d["daily_net_growth_required"] == round(94000 / 49)
    assert d["average_daily_required_over_60"] == round(98000 / 60)
    assert d["net_gained"] == 4000 and d["daily_growth"] == 400.0 and d["growth_7d"] == 4000 and d["growth_30d"] == "UNKNOWN"
    t = d["trajectory"]
    assert t["expected_today"] == round(2000 + 98000 * 10 / 59) and t["status"] == "BEHIND"
    assert d["conversion"] == {"videos": 1, "views": 50000, "new_followers": 400, "followers_per_1k_views": 8.0}
    assert d["phase"].startswith("Phase 2")
    pr = d["projection"]
    assert pr["baseline"] == 6000 + 400 * 49 and pr["conservative"] == "UNKNOWN" and pr["on_track"] is False
    assert "not enough" in pr["warning"]


def test_scenarios_use_observed_rates_and_flag_a_shortfall():
    import datetime as dt
    D = lambda n: dt.date(2026, 11, 20) + dt.timedelta(days=n)
    series = [(D(0), 1000), (D(1), 1300), (D(2), 1500), (D(3), 2100)]
    pr = growth.scenarios(series, 56, 100000)
    assert pr["observed_avg_daily"] == round(1100 / 3, 1)
    assert pr["conservative"] == 2100 + 200 * 56 and pr["optimistic"] == 2100 + 600 * 56
    assert pr["baseline"] == round(2100 + (1100 / 3) * 56) and pr["on_track"] is False
    assert growth.scenarios(series[:1], 56, 100000)["status"] == "UNKNOWN"
    fast = [(D(0), 1000), (D(1), 3000), (D(2), 5000)]
    assert growth.scenarios(fast, 58, 100000)["on_track"] is True


def test_reel_rates_are_per_reach_and_compared_with_the_account_median(tmp_path):
    perf = tmp_path / "p.csv"
    for vid, reach, shares, follows in (("a", 10000, 100, 50), ("b", 20000, 100, 40), ("c", 5000, 150, 30)):
        store.upsert(dict(date="2026-11-21", video_id=vid, platform="instagram", checkpoint="48h", views=str(reach * 2),
                          reach=str(reach), shares=str(shares), new_followers=str(follows)), perf)
    store.upsert(dict(date="2026-11-21", video_id="a", platform="instagram", checkpoint="2h", reach="900"), perf)
    reels = {r["video_id"]: r for r in growth.reel_table(store.load(perf))}
    assert reels["a"]["checkpoint"] == "48h" and reels["a"]["share_rate"] == 0.01
    assert reels["c"]["share_rate"] == 0.03 and reels["c"]["share_rate_vs_median"] == 3.0
    assert reels["b"]["follows_per_1k_reach"] == 2.0 and reels["b"]["save_rate"] is None


def test_follower_snapshots_reject_bad_input_and_replace_same_day(tmp_path):
    f = tmp_path / "f.csv"
    with pytest.raises(ValueError):
        growth.add_snapshot("2026-11-20", "tiktok", 5, "app", f)
    with pytest.raises(ValueError):
        growth.add_snapshot("2026-11-20", "x", -1, "app", f)
    with pytest.raises(ValueError):
        growth.add_snapshot("2026-11-20", "x", 5, " ", f)
    growth.add_snapshot("2026-11-20", "x", 5, "app", f)
    growth.add_snapshot("2026-11-20", "x", 7, "app", f)
    assert [r["followers"] for r in growth.load(f)] == ["7"]


def test_content_mix_against_pillar_targets():
    m = growth.mix([{"pillar": "ai_breakthroughs"}, {"pillar": "ai_breakthroughs"}, {"pillar": "useful_ai_tools"}, {}],
                   "pillar", package.PILLARS)
    row = {x["pillar"]: x for x in m}
    assert row["ai_breakthroughs"]["share_pct"] == 50 and row["ai_breakthroughs"]["target_pct"] == 30
    assert row["unrecorded"]["count"] == 1 and sum(package.PILLARS.values()) == 100


def test_weekly_review_includes_target_and_refuses_patterns_without_data(tmp_path):
    db = tmp_path / "db.jsonl"
    db.write_text(json.dumps({"date": "2026-11-21", "slug": "s", "topic": "t", "status": "scripted", "pillar": "useful_ai_tools",
                              "format": "B", "hook": "h"}) + "\n")
    text = weekly.build("2026-11-26", db, tmp_path / "p.csv")
    assert "## 60-day target" in text and "useful_ai_tools | 1 | 100%" in text
    assert "no pattern can be claimed" in text


def test_real_v3_package_from_the_manual_test_run_validates():
    """MANUAL TEST output (19 Nov 2026, isolated clone, real research): the first genuine v3 package."""
    p = json.loads((ROOT / "tests/fixtures/manual_test_v3_2026-11-19/package.json").read_text())
    probs, info = package.validate(p)
    assert probs == [] and info["ready"]["status"] == "RECORDING READY"
    assert 90 <= info["lint"]["words"] <= 105 and info["lint"]["seconds"] <= 45
    ranked = {c["headline"]: c for c in info["ranked"]}
    assert ranked["Microsoft announces Maia 300 inference chip at Ignite"]["ineligible_reason"].startswith("published before")
    assert ranked["Anthropic prices record IPO at $83 a share"]["ineligible_reason"].startswith("on hold")
    rep = json.loads((ROOT / "tests/fixtures/manual_test_v3_2026-11-19/run_report.json").read_text())
    run = rep["runs"]["2026-11-19-manual-test-133203"]
    assert run["trigger"] == "manual-test" and run["quality_gate"] == "PASS" and run["delivery"]["status"] == "not attempted"


def test_run_status_line_shows_the_current_run_not_an_older_one(monkeypatch):
    from creatoros.research import runs
    recs = [{"event": "start", "run_id": "D-scheduled-084216", "ist_date": "D"},
            {"event": "end", "run_id": "D-scheduled-084216", "ist_date": "D", "status": "READY",
             "delivery": {"status": "requested", "channel": "push"}},
            {"event": "start", "run_id": "D-manual-133203", "ist_date": "D"}]
    monkeypatch.setattr(runs, "load", lambda path: recs)
    assert package.run_status_line("D") == "D-manual-133203: IN PROGRESS (delivery is recorded when the run ends)"
    recs.append({"event": "end", "run_id": "D-manual-133203", "ist_date": "D", "status": "READY",
                 "delivery": {"status": "failed", "channel": "push"}})
    assert package.run_status_line("D") == "D-manual-133203: READY, delivery failed via push"
    assert package.run_status_line("E").startswith("no run recorded")


# --- v4: the creator's Instagram growth rubric -----------------------------------------------------------------------

def _as_v4(p):
    """Convert the real 19 Nov MANUAL TEST package (v3) to v4, keeping its research."""
    p = copy.deepcopy(p)
    p["scoring"] = "v4"
    for c in p["candidates"]:
        sc = c["scores"]
        c["scores"] = {"social_traction": min(sc["public_discussion"], 6), "novelty": sc["surprise"], "consequence": sc["significance"],
                       "broad_appeal": sc["broad_appeal"], "visual": sc["visual"], "discussion": min(sc["discussion_potential"] * 2, 10),
                       "verified_significance": min(sc["verification_confidence"] * 2, 10), "freshness": 9}
        c.update(latest_development_at=c["published_at"], confirmed_facts=[c["main_claim"]], company_claims=[],
                 unverified_claims=[], why_share="x", visual_note="x")
    for h in p["hooks"]:
        h["retention"] = h.pop("specificity")
    p.pop("quality_scores")
    p.update(creative_scores={"hook": 9, "clarity": 9, "human_delivery": 9, "relevance": 9, "information": 9, "retention": 9,
                              "discussion": 9}, revisions=1,
             why_beats_alternatives="Verified by NASA plus independent outlets, awe plus a live twist; Genie 4 is company claims only.",
             posting_window={"window_ist": "19:00-21:00", "basis": "hypothesis", "rationale": "Untested starting slot; replace with the account's own best time once reels have data."},
             audience_hypothesis="High saves for the light-day explainer; comments on how to debug with a one-day delay.",
             candidate_shortfall_reason="Only 6 distinct candidates had dated primary sources in the window; most platforms are blocked.")
    return p


FIX = ROOT / "tests/fixtures/manual_test_v3_2026-11-19/package.json"


def test_v4_package_validates_and_delivers_the_morning_items():
    p = _as_v4(json.loads(FIX.read_text()))
    probs, info = package.validate(p)
    assert probs == [] and info["ready"]["status"] == "RECORDING READY"
    assert info["quality"]["total"] == 90.0 and info["quality"]["approved"]
    today = package.render_today(p, info)
    for heading in ("WHY IT BEATS THE ALTERNATIVES", "TOP FIVE RANKED CANDIDATES", "STRONGEST VERIFIED SOCIAL SIGNAL",
                    "RECOMMENDED POSTING WINDOW", "EXPECTED AUDIENCE RESPONSE (hypothesis)", "RESEARCH LIMITATIONS"):
        assert heading in today
    assert "provisional: traction not measured" in today and "(hypothesis)" in today
    assert "SOCIAL SIGNAL:** none observed" in today and "Strongest public evidence instead" in today
    p["candidates"][0]["signals"].append({"platform": "reddit", "url": "https://www.reddit.com/r/space/x", "title": "r/space thread",
                                          "retrieved_at": "2026-11-19T09:00:00+00:00", "access": "SEARCH-INDEX",
                                          "engagement": {"basis": "unknown"}})
    assert "SOCIAL SIGNAL:** [r/space thread]" in package.render_today(p, package.validate(p)[1])
    assert "Creative score" in package.render(p, info)


@pytest.mark.parametrize("mod,expect", [
    (lambda p: p["creative_scores"].update(hook=6), "below 90"),
    (lambda p: p["creative_scores"].pop("discussion"), "creative scores missing"),
    (lambda p: p.update(revisions=4), "revisions must be"),
    (lambda p: p.update(posting_window={"window_ist": "19:00", "basis": "best", "rationale": "x"}), "posting_window"),
    (lambda p: p.update(posting_window={"window_ist": "19:00", "basis": "observed", "rationale": "x"}), "needs evidence"),
    (lambda p: p.update(audience_hypothesis=" "), "audience_hypothesis"),
    (lambda p: p.pop("candidate_shortfall_reason"), "find 15"),
    (lambda p: p["candidates"][0]["scores"].update(social_traction=8), "measured engagement"),
    (lambda p: p["candidates"][0].pop("company_claims"), "missing field: company_claims"),
    (lambda p: p["hooks"][0].pop("retention"), "lacks scores"),
])
def test_v4_rule_breaks(mod, expect):
    p = _as_v4(json.loads(FIX.read_text()))
    mod(p)
    assert any(expect in x for x in package.validate(p)[0]), package.validate(p)[0]


def test_below_target_after_three_revisions_is_reported_not_hidden():
    p = _as_v4(json.loads(FIX.read_text()))
    p["creative_scores"].update(hook=7, discussion=7)
    assert any("below 90" in x for x in package.validate(p)[0])
    p.update(revisions=3, quality_limitation="Hook stays literal to remain accurate; no stronger accurate hook found.")
    probs, info = package.validate(p)
    assert probs == [] and "CREATIVE SCORE BELOW TARGET" in package.render_today(p, info)


def _as_v5(p):
    """The real 19 Nov research package (v3 candidates) in the V5 format: Hinglish, 85-105 words, six-part quality score."""
    p = copy.deepcopy(p)
    p.update(scoring="v5", language="hinglish")
    p.pop("quality_scores", None)
    p["hooks"] = [{"text": h["text"], "mechanism": h["mechanism"], "accuracy": h["accuracy"], "curiosity": h["curiosity"],
                   "clarity": h["clarity"], "credibility": h["accuracy"], "emotional": h["surprise"], "natural": h["natural"]}
                  for h in p["hooks"][:6]]
    p.update(verified_development="NASA: Voyager 1 one light-day from Earth; no science data since 14 Nov", confidence="HIGH",
             thumbnail_text="1 message = 1 day", pinned_comment="How would you debug a computer 25.9 billion km away?",
             edit_beats={"0-3": "NASA image + 24h timer", "3-10": "light-day graphic", "10-25": "data stops 14 Nov",
                         "25-45": "two-day round trip; 1977 launch photo"},
             quality_v5={"hook": 9, "clarity": 9, "storytelling": 9, "retention": 9, "shareability": 9, "factual_confidence": 10},
             revisions=0, why_beats_alternatives="Only story with a primary source plus independent reporting in the window.")
    return p


def test_v5_package_validates_with_hinglish_and_the_six_part_score():
    p = _as_v5(json.loads(FIX.read_text()))
    probs, info = package.validate(p)
    assert probs == [] and info["ready"]["status"] == "RECORDING READY"
    assert info["quality"]["total"] == 91.5 and 85 <= info["lint"]["words"] <= 105 and info["lint"]["seconds"] <= 45
    today = package.render_today(p, info)
    heads = ["## A. TODAY'S SELECTED TOPIC", "## B. FINAL RECORDING SCRIPT", "## C. RECORDING DIRECTIONS", "## D. EDITING DIRECTIONS",
             "## E. POSTING PACKAGE", "## F. FACT-CHECK", "## G. INTERNAL QUALITY SCORE"]
    pos = [today.index(h) for h in heads]
    assert pos == sorted(pos) and today.index(p["script"].splitlines()[0]) < today.index("## C.")
    assert "Thumbnail text:" in today and "Pinned comment:" in today and "0-3 s:" in today


@pytest.mark.parametrize("mod,expect", [
    (lambda p: p.update(language="english"), "v5 packages use the configured language"),
    (lambda p: p.update(script=p["script"] + " यह"), "Devanagari"),
    (lambda p: p["quality_v5"].update(hook=5), "below 90"),
    (lambda p: p["quality_v5"].update(factual_confidence=7), "factual confidence below 8"),
    (lambda p: p["edit_beats"].pop("25-45"), "edit_beats: missing"),
    (lambda p: p.update(thumbnail_text="far too many words for any thumbnail at all"), "six words"),
    (lambda p: p.update(category="GAMING"), "release_type"),
    (lambda p: p.update(hooks=p["hooks"][:4]), "at least 5"),
    (lambda p: p.update(confidence="SURE"), "confidence must be"),
])
def test_v5_rule_breaks(mod, expect):
    p = _as_v5(json.loads(FIX.read_text()))
    mod(p)
    assert any(expect in x for x in package.validate(p)[0]), package.validate(p)[0]


def test_v5_window_may_expand_to_72_hours_only_with_a_reason():
    import datetime as dt
    p = _as_v5(json.loads(FIX.read_text()))
    end = dt.datetime.fromisoformat(p["research_window"]["end_utc"])
    p["research_window"] = {**p["research_window"], "start_utc": (end - dt.timedelta(hours=72)).isoformat(), "hours": 72}
    assert any("window_expansion_reason" in x for x in package.validate(p)[0])
    p["window_expansion_reason"] = "No verified story in the first 24 hours."
    assert package.validate(p)[0] == []


def test_scheme_dates_v3_v4_v5_on_the_20th_and_v5_from_the_21st():
    v3 = json.loads(FIX.read_text())
    v4, v5 = _as_v4(v3), _as_v5(v3)
    cases = [("2026-11-20", v3, True), ("2026-11-20", v4, True), ("2026-11-20", v5, True),
             ("2026-11-21", v3, False), ("2026-11-21", v4, False), ("2026-11-21", v5, True)]
    for d, p, ok in cases:
        q = copy.deepcopy(p)
        q["date"] = d
        first = package.validate(q)[0][:1]
        assert (not first or "must use" not in first[0]) == ok, (d, q["scoring"], first)


def test_hinglish_reads_fine_for_hinglish_and_fails_for_english():
    line = "Yeh dekho, GTA 6 finally aa gaya hai, aur download 212 GB ka hai."
    assert lint.language_problems(line, "hinglish") == []
    assert lint.language_problems(line, "english")


def test_measured_traction_comes_only_from_observed_engagement():
    c = {"x_signal": {"status": "NOT VERIFIED"}, "signals": [{"engagement": {"basis": "reported", "likes": 5, "source": "x"}}]}
    assert not candidates.traction_measured(c)
    c["signals"].append({"engagement": {"basis": "observed", "views": 1200}})
    assert candidates.traction_measured(c)
    assert sum(candidates.WEIGHTS_V4.values()) == 100 and sum(lint.CREATIVE_V4.values()) == 100


def test_real_v4_package_from_the_afternoon_manual_test_validates():
    """MANUAL TEST v4 (19 Nov 2026 16:27 IST, isolated copy, fresh research): 13 candidates, honest shortfall, 0 revisions."""
    d = ROOT / "tests/fixtures/manual_test_v4_2026-11-19"
    p = json.loads((d / "package.json").read_text())
    probs, info = package.validate(p)
    assert probs == [] and info["ready"]["status"] == "RECORDING READY" and info["quality"]["total"] >= 90
    assert len(p["candidates"]) == 13 and p["revisions"] == 0 and "candidate_shortfall_reason" in p
    assert all(c["provisional"] for c in info["ranked"])                         # no engagement could be observed
    run = json.loads((d / "run_report.json").read_text())["runs"]["2026-11-19-manual-test-162657"]
    assert run["trigger"] == "manual-test" and run["delivery"]["status"] == "not attempted"


def test_v5_package_saves_all_files(tmp_path, monkeypatch):
    """Regression: saving a v5 package crashed while writing research.json (hook criteria)."""
    from creatoros.research import content_db, memory
    monkeypatch.setattr(content_db, "add", lambda *a, **k: {})
    monkeypatch.setattr(content_db, "update", lambda *a, **k: {})
    monkeypatch.setattr(memory, "record", lambda *a, **k: None)
    p = _as_v5(json.loads(FIX.read_text()))
    r = package.save(p, tmp_path)
    assert r["ok"] and r["status"] == "RECORDING READY"
    rj = json.loads((tmp_path / "research.json").read_text())
    assert "credibility" in rj["hooks"][0] and "## B. FINAL RECORDING SCRIPT" in (tmp_path / "today.md").read_text()
