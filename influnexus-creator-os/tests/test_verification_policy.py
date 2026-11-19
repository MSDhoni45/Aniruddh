"""Permanent tiered, risk-based verification policy (19 Nov 2026): regression tests."""
import copy
import json
from pathlib import Path

import pytest

from creatoros.factcheck import evidence as ev
from creatoros.factcheck import verification as ver
from creatoros.research import holds
from creatoros.scripts import package

ROOT = Path(__file__).resolve().parents[1]
DAY = "2026-11-21"


def item(url, kind="news", access="secondary", date="2026-11-20", **kw):
    return {"url": url, "kind": kind, "access": access, "date": date, **kw}


def claim(risk, items, status="CONFIRMED", text="x", **kw):
    return {"id": "c1", "text": text, "status": status, "risk": risk, "evidence": items, "in_script": True, **kw}


OFFICIAL_IDX = item("https://www.rockstargames.com/newswire/launch", "primary", "search-index")
OFFICIAL_OPEN = item("https://www.rockstargames.com/newswire/launch", "primary", "opened")
FORBES = item("https://www.forbes.com/a")
VERGE = item("https://www.theverge.com/b")
OLD_NME = item("https://www.nme.com/feature", date="2022-10-29")
OLD_YAHOO = item("https://tech.yahoo.com/gaming/x", date="2023-05-01")


# --- breaking news / time-sensitive ----------------------------------------------------------------------------------

def test_breaking_claim_needs_official_text_plus_two_independent_current_reports():
    assert ev.gate(claim("high", [OFFICIAL_IDX, FORBES, VERGE]), DAY) == []
    assert ev.level(claim("high", [OFFICIAL_IDX, FORBES, VERGE]))["level"] == "MEDIUM-HIGH"
    weak = ev.gate(claim("high", [OFFICIAL_IDX, FORBES]), DAY)
    assert weak and "LOW" in weak[0] and "needs MEDIUM-HIGH" in weak[0]


def test_breaking_claim_without_a_current_report_is_held():
    stale = [OFFICIAL_IDX, item("https://www.forbes.com/a", date="2026-10-01"), item("https://www.theverge.com/b", date="2026-10-02")]
    reasons = ev.gate(claim("high", stale), DAY)
    assert any("dated within 7 days" in r for r in reasons)


def test_two_reports_without_official_text_are_not_enough_for_a_launch():
    assert ev.level(claim("high", [FORBES, VERGE]))["level"] == "MEDIUM"
    assert ev.gate(claim("high", [FORBES, VERGE]), DAY)


# --- historical / low risk ---------------------------------------------------------------------------------------------

def test_historical_claim_passes_on_two_independent_reputable_sources():
    c = claim("low", [OLD_NME, OLD_YAHOO, item("https://en.wikipedia.org/wiki/GTA_VC", "reference", date="2026-11-01")])
    assert ev.level(c)["level"] == "MEDIUM" and ev.gate(c, DAY) == []


def test_historical_claim_from_blogs_and_fan_wikis_is_low():
    c = claim("low", [item("https://gta.fandom.com/wiki/Radio", "news"), item("https://tvtropes.org/vc", "reference"),
                      item("https://someblog.example/vc", "blog")])
    assert ev.level(c)["level"] == "LOW" and ev.gate(c, DAY)


# --- syndication, conflicts, attribution -------------------------------------------------------------------------------

def test_syndicated_copies_of_one_report_count_once():
    orig = "https://www.reuters.com/story"
    c = claim("low", [item(orig), item("https://www.msn.com/copy", syndicated_from=orig),
                      item("https://news.yahoo.com/copy", syndicated_from=orig)])
    lv = ev.level(c)
    assert lv["level"] == "LOW" and lv["independent"] == ["reuters.com"] and "syndicated" in lv["why"]


def test_conflicting_sources_are_unverified():
    c = claim("high", [OFFICIAL_IDX, FORBES, VERGE], conflicts=["Forbes says 19 Nov, The Verge says 20 Nov"])
    assert ev.level(c)["level"] == "UNVERIFIED" and ev.gate(c, DAY)


def test_undated_or_unattributed_reports_do_not_count():
    c = claim("low", [item("https://www.nme.com/a", date=""), item("https://www.theverge.com/b", date="")])
    assert ev.level(c)["level"] == "LOW"


# --- search-index-only evidence ----------------------------------------------------------------------------------------

def test_search_index_alone_is_low_and_agreeing_excerpts_never_make_high():
    assert ev.level(claim("high", [OFFICIAL_IDX]))["level"] == "LOW"
    many = [OFFICIAL_IDX] + [item(f"https://outlet{i}.example.com/x") for i in range(6)]
    assert ev.level(claim("high", many))["level"] == "MEDIUM-HIGH"           # never HIGH from excerpts
    assert ev.level(claim("high", [OFFICIAL_OPEN]))["level"] == "HIGH"        # only an opened primary source is HIGH


# --- unverified launch announcements -----------------------------------------------------------------------------------

def test_rumoured_or_single_excerpt_launch_is_held():
    assert ev.level(claim("high", [OFFICIAL_IDX, FORBES, VERGE], status="RUMOR"))["level"] == "UNVERIFIED"
    assert ev.gate(claim("high", [item("https://leaks.example.com/gta6")]), DAY)
    assert "if declared" in ev.gate({**claim("high", [FORBES, VERGE]), "risk": "medium"}, DAY)[0]


# --- the package gate and the automatic fallback -----------------------------------------------------------------------

def _tiered(p, risk_items):
    p = copy.deepcopy(p)
    p["verification"] = "tiered"
    for c in p["factcheck"]["claims"]:
        for k in ("confidence", "access", "primary_source", "supporting_source", "source_title", "supporting_evidence"):
            c.pop(k, None)
        c.update(risk="low", evidence=risk_items)
    return p


def _v5():
    from test_growth_engine import FIX, _as_v5
    return _as_v5(json.loads(FIX.read_text()))


NASA_IDX = item("https://science.nasa.gov/blogs/voyager/2026/11/18/x", "primary", "search-index", date="2026-11-18")
JUB = item("https://www.jubileecast.com/articles/41196", date="2026-11-19")
EARTHSKY = item("https://earthsky.org/space/voyager-1", date="2026-11-18")


def test_tiered_v5_package_is_ready_with_corroborated_evidence_and_held_without():
    ok = _tiered(_v5(), [NASA_IDX, JUB, EARTHSKY])
    probs, info = package.validate(ok)
    assert probs == [] and info["ready"]["status"] == ver.READY
    assert "MEDIUM-HIGH" in package.render_today(ok, info) and "Evidence levels:" in package.render_today(ok, info)
    for c in ok["factcheck"]["claims"]:
        c["risk"] = "high"
    assert package.validate(ok)[1]["ready"]["status"] == ver.READY          # dated 18-19 Nov: current for a 19 Nov package
    weak = _tiered(_v5(), [NASA_IDX])
    probs, info = package.validate(weak)
    assert probs == [] and info["ready"]["status"] == ver.HOLD
    assert any("needs MEDIUM" in r for r in info["ready"]["reasons"])


def test_tiered_claims_need_evidence_and_risk_is_classified_when_not_declared():
    p = _tiered(_v5(), [NASA_IDX, JUB, EARTHSKY])
    p["factcheck"]["claims"][0].pop("risk")
    probs, info = package.validate(p)
    assert probs == [] and "risk_effective" in p["factcheck"]["claims"][0]
    p["factcheck"]["claims"][0].pop("evidence")
    assert any("missing evidence" in x for x in package.validate(p)[0])


def test_hold_archives_the_story_and_names_the_next_one(tmp_path, monkeypatch):
    from creatoros.research import content_db
    monkeypatch.setattr(content_db, "update", lambda *a, **k: {})
    p = _v5()
    (tmp_path / "package.json").write_text(json.dumps(p))
    (tmp_path / "today.md").write_text("old")
    r = holds.hold(tmp_path, "launch date not corroborated by two current independent reports")
    assert r["held"] == p["topic"] and (tmp_path / f"held_{p['slug']}" / "package.json").exists()
    assert not (tmp_path / "today.md").exists()
    assert r["next_candidates"] and r["next_candidates"][0]["headline"] != p["topic"]
    log = json.loads((tmp_path / "holds.json").read_text())
    assert log[0]["reason"].startswith("launch date")
    with pytest.raises(ValueError):
        holds.hold(tmp_path, " ")


def test_validator_refuses_to_reselect_a_held_story(monkeypatch):
    p = _v5()
    monkeypatch.setattr(package, "holds_for", lambda d: [{"topic": p["topic"], "reason": "not corroborated"}])
    assert any("put on HOLD today" in x for x in package.validate(p)[0])
    p["candidates"][0]["hold_reason"] = "not corroborated"
    assert not any("put on HOLD today" in x for x in package.validate(p)[0])


def test_creator_requested_topic_is_exempt_from_the_window_and_top_score():
    from creatoros.research import candidates
    old = {"scores": {"public_discussion": 1}, "published_at": "2002-10-29", "creator_request": True}
    win = {"start_utc": "2026-11-18T12:00:00+00:00", "end_utc": "2026-11-19T12:00:00+00:00"}
    assert candidates.window_reason(old, win) is None
    assert candidates.window_reason({**old, "creator_request": False}, win)


def test_older_packages_keep_their_original_verification_and_today_uses_the_tiered_policy():
    for path in ("daily/2026-11-18/package.json", "daily/2026-11-19/previous_als-brain-implant-home-use/package.json"):
        p = json.loads((ROOT / path).read_text())
        assert not package.is_tiered(p) and package.validate(p)[0] == []
    today = json.loads((ROOT / "daily/2026-11-19/package.json").read_text())
    probs, info = package.validate(today)
    assert package.is_tiered(today) and probs == [] and info["ready"]["status"] == ver.READY
    held = json.loads((ROOT / "daily/2026-11-19/holds.json").read_text())
    assert held[0]["slug"] == "gta-vi-launch"



# --- semantic risk classification (temporal context, not keywords alone) ----------------------------------------------

@pytest.mark.parametrize("text,risk", [
    # the creator's examples
    ("GTA Vice City released in 2002", "low"),
    ("GTA VI launched today", "high"),
    ("GTA VI launches next month", "high"),
    ("A game released 20 years ago", "low"),
    ("Game prices changed today", "high"),
    # historical release dates
    ("GTA Vice City came out in 2002 (North America: 27 Oct 2002)", "low"),
    ("The original PlayStation launched in Japan on 3 December 1994", "low"),
    ("Back in the 1990s, Nintendo released the Game Boy Color", "low"),
    ("Voyager 1 launched in 1977", "low"),
    # current launches
    ("GTA 6 is out now on PS5 and Xbox Series X|S", "high"),
    ("Rockstar just launched GTA VI", "high"),
    ("GTA 6 finally aa gaya hai, aaj launch hua", "high"),
    ("GTA VI launches on 19 Nov 2026 on PlayStation 5", "high"),
    # future launches
    ("The PC version will release in 2027", "high"),
    ("Apple is set to launch the device on 2 December 2026", "high"),
    ("Pre-orders open next week", "high"),
    # price changes and prices
    ("The Standard Edition costs $79.99", "high"),
    ("Xbox raised console prices this week", "high"),
    ("In 2002 the game cost $49.99", "low"),
    # stable descriptive facts
    ("Vice City is a fictional city inspired by Miami", "low"),
    ("Tommy Vercetti was voiced by actor Ray Liotta", "low"),
    ("The soundtrack was mostly licensed real 1980s music", "low"),
])
def test_risk_is_classified_from_temporal_meaning(text, risk):
    assert ev.classify_risk(text, "2026-11-19")["risk"] == risk, ev.classify_risk(text, "2026-11-19")


def test_event_date_field_overrides_a_vague_claim():
    assert ev.classify_risk("The update rolled out", "2026-11-19", event_date="2026-11-18")["risk"] == "high"
    assert ev.classify_risk("The update rolled out", "2026-11-19", event_date="2019-03-01")["risk"] == "low"


def test_declared_risk_can_raise_but_never_lower_the_classified_risk():
    hist = claim("high", [OLD_NME, OLD_YAHOO], text="GTA Vice City released in 2002")
    assert ev.effective_risk(hist, DAY)["risk"] == "high"                        # writer chose the stricter gate
    launch = claim("low", [OFFICIAL_IDX], text="GTA VI launched today")
    eff = ev.effective_risk(launch, DAY)
    assert eff["risk"] == "high" and eff["declared"] == "low"
    assert ev.gate(launch, DAY) and "high-risk" in ev.gate(launch, DAY)[0]       # thresholds unchanged: needs MEDIUM-HIGH


def test_thresholds_are_unchanged_for_classified_claims():
    hist = claim(None, [OLD_NME, OLD_YAHOO], text="GTA Vice City released in 2002")
    assert ev.gate(hist, DAY) == []                                               # historical: MEDIUM is enough
    launch = claim(None, [OLD_NME, OLD_YAHOO], text="GTA VI launched today")
    assert ev.gate(launch, DAY)                                                   # time-sensitive: MEDIUM is not enough
    assert ev.gate(claim(None, [OFFICIAL_IDX, FORBES, VERGE], text="GTA VI launched today"), DAY) == []
