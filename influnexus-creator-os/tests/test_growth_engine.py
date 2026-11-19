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
    return _as_v3(json.loads((ROOT / "daily/2026-11-19/package.json").read_text()))


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
    f, perf = tmp_path / "f.csv", tmp_path / "p.csv"
    growth.add_snapshot("2026-11-20", "instagram", 2000, "app", f)
    growth.add_snapshot("2026-11-20", "youtube", 1000, "studio", f)
    growth.add_snapshot("2026-11-30", "instagram", 6000, "app", f)
    growth.add_snapshot("2026-11-30", "youtube", 2000, "studio", f)
    store.upsert(dict(date="2026-11-21", video_id="v1", platform="instagram", checkpoint="7d", views="50000",
                      new_followers="400"), perf)
    store.upsert(dict(date="2026-11-21", video_id="v1", platform="instagram", checkpoint="24h", views="10000",
                      new_followers="50"), perf)
    d = growth.dashboard("2026-11-30", f, perf, tmp_path / "db.jsonl")
    assert d["current_followers"] == 8000 and d["remaining_followers"] == 92000
    assert d["days_remaining"] == 49 and d["daily_net_growth_required"] == round(92000 / 49)
    t = d["trajectory"]
    expected = 3000 + (100000 - 3000) * 10 / 59
    assert t["expected_today"] == round(expected) and t["status"] == "BEHIND"
    assert d["conversion"] == {"videos": 1, "views": 50000, "new_followers": 400, "followers_per_1k_views": 8.0}
    assert d["daily_views_needed_at_observed_conversion"] == round(d["daily_net_growth_required"] / 8.0 * 1000)
    assert d["phase"].startswith("Phase 2")


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
