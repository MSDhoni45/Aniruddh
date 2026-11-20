"""V5 production hardening (20 Nov 2026): extraordinary financial claims, source audit before research, delivery stages."""
import datetime as dt
import json
from pathlib import Path

import pytest

from creatoros.factcheck import evidence as ev
from creatoros.research import runs, signals

DAY = "2026-11-20"
ANTH_OPEN = {"url": "https://www.anthropic.com/news/anthropic-prices-initial-public-offering", "kind": "primary", "access": "opened", "date": "2026-11-18"}
ANTH_IDX = {**ANTH_OPEN, "access": "search-index"}
NASDAQ_IDX = {"url": "https://www.nasdaq.com/newsroom/anthropic-marks-ipo-at-nasdaq", "kind": "primary", "access": "search-index", "date": "2026-11-19"}
FORBES = {"url": "https://www.forbes.com/sites/x/2026/11/19/anthropic-ipo", "kind": "news", "access": "secondary", "date": "2026-11-19"}
CNN = {"url": "https://www.cnn.com/2026/11/19/business/anthropic-ipo", "kind": "news", "access": "secondary", "date": "2026-11-19"}


def c(text, items):
    return {"id": "a", "text": text, "status": "CONFIRMED", "evidence": items, "in_script": True}


# --- extraordinary financial claims need the primary document opened -----------------------------------------------

@pytest.mark.parametrize("text", [
    "The IPO was priced at $83.00 per share",
    "The stock opened at $111.50, about 34% above the IPO price",
    "Shares jumped 34% on the first day of trading",
    "The offering raised about $81.3 billion",
    "Anthropic is now valued at $1.27 trillion",
    "980 million shares were sold in the IPO",
])
def test_financial_claims_are_detected(text):
    assert ev.is_extraordinary_financial(text)


@pytest.mark.parametrize("text", ["Genie 4 is live for Google AI Ultra subscribers", "Vice City is inspired by Miami",
                                  "Voyager 1 is one light-day from Earth"])
def test_ordinary_claims_are_not_financial(text):
    assert not ev.is_extraordinary_financial(text)


def test_search_index_financial_claim_is_held_even_with_independent_reports():
    claim = c("The stock opened at $111.50, about 34% above the IPO price", [NASDAQ_IDX, FORBES, CNN])
    assert ev.level(claim)["level"] == "MEDIUM-HIGH"
    reasons = ev.gate(claim, DAY)
    assert reasons and "needs HIGH" in reasons[0]


def test_financial_claim_passes_when_the_primary_document_was_opened():
    assert ev.gate(c("The IPO was priced at $83.00 per share, above the $70-78 range", [ANTH_OPEN, FORBES]), DAY) == []


def test_non_financial_time_sensitive_threshold_is_unchanged():
    claim = c("Genie 4 is now live for AI Ultra subscribers", [dict(ANTH_IDX, url="https://blog.google/genie-4"), FORBES, CNN])
    assert ev.gate(claim, DAY) == []


def test_historical_financial_fact_keeps_the_historical_threshold():
    claim = c("In 2004 Google's IPO was priced at $85 per share", [dict(FORBES, date="2014-08-19"), dict(CNN, date="2019-08-19")])
    assert ev.classify_risk(claim["text"], DAY)["risk"] == "low" and ev.gate(claim, DAY) == []


# --- the source audit runs before research ---------------------------------------------------------------------------

def fake_audit():
    return signals.audit(lambda h: {"host": h, "reachable": h == "www.anthropic.com"}, now=dt.datetime(2026, 11, 21, 3, 11, tzinfo=dt.timezone.utc))


def test_run_start_audits_sources_first_and_records_it(tmp_path):
    log, daily = tmp_path / "logs" / "runs.jsonl", tmp_path / "daily"
    now = dt.datetime(2026, 11, 21, 3, 11, 30, tzinfo=dt.timezone.utc)
    rec = runs.start(log, "scheduled", root=tmp_path, now=now, daily=daily, audit_fn=fake_audit)
    saved = json.loads((daily / "2026-11-21" / "source_access.json").read_text())
    assert saved["groups"]["primary"]["status"] == "PARTIAL" and saved["groups"]["x"]["status"] == "BLOCKED"
    assert rec["source_audit"]["x"] == "BLOCKED" and rec["source_audit"]["checked_at_utc"] <= rec["at_utc"]
    assert (log.parent / "source_access.json").exists()


def test_duplicate_scheduled_start_does_not_audit_again(tmp_path):
    log, daily = tmp_path / "runs.jsonl", tmp_path / "daily"
    now = dt.datetime(2026, 11, 21, 3, 11, 30, tzinfo=dt.timezone.utc)
    runs.start(log, "scheduled", root=tmp_path, now=now, daily=daily, audit_fn=fake_audit)
    calls = []
    again = runs.start(log, "scheduled", root=tmp_path, now=now + dt.timedelta(minutes=2), daily=daily,
                       audit_fn=lambda: calls.append(1) or fake_audit())
    assert again["duplicate"] == "IN_PROGRESS" and calls == []


def test_tiered_package_requires_a_source_audit_and_research_json_records_it(tmp_path, monkeypatch):
    from creatoros.scripts import package
    from creatoros.research import content_db, memory
    from test_verification_policy import _tiered, _v5, NASA_IDX, JUB, EARTHSKY
    p = _tiered(_v5(), [NASA_IDX, JUB, EARTHSKY])
    monkeypatch.setattr(package, "source_audit_for", lambda p: None)
    assert any("no source audit" in x for x in package.validate(p)[0])
    audit = fake_audit()
    monkeypatch.setattr(package, "source_audit_for", lambda p: audit)
    monkeypatch.setattr(content_db, "add", lambda *a, **k: {})
    monkeypatch.setattr(content_db, "update", lambda *a, **k: {})
    monkeypatch.setattr(memory, "record", lambda *a, **k: None)
    assert package.save(p, tmp_path)["ok"]
    assert json.loads((tmp_path / "research.json").read_text())["source_audit"]["groups"]["x"]["status"] == "BLOCKED"


# --- delivery stages ---------------------------------------------------------------------------------------------------

def test_accepted_or_received_needs_evidence(tmp_path):
    log, daily = tmp_path / "runs.jsonl", tmp_path / "daily"
    r = runs.start(log, "manual", root=tmp_path, now=dt.datetime(2026, 11, 21, 3, 11, tzinfo=dt.timezone.utc))
    with pytest.raises(ValueError):
        runs.end(log, daily, "READY", run_id=r["run_id"], delivery="received")
    with pytest.raises(ValueError):
        runs.end(log, daily, "READY", run_id=r["run_id"], delivery="accepted", receipt=" ")
    runs.end(log, daily, "READY", run_id=r["run_id"], delivery="requested", channel="push")
    with pytest.raises(ValueError):
        runs.delivery(log, daily, r["run_id"], "received", "push")


def test_delivery_stages_report_each_step_from_evidence(tmp_path):
    log, daily = tmp_path / "runs.jsonl", tmp_path / "daily"
    r = runs.start(log, "scheduled", root=tmp_path, now=dt.datetime(2026, 11, 21, 3, 11, tzinfo=dt.timezone.utc))
    runs.end(log, daily, "READY", run_id=r["run_id"], delivery="requested", channel="push")
    st = runs.delivery_stages(daily, "2026-11-21", log)
    assert st["package_generated"] == "NO" and st["notification_requested"] == "YES"
    assert st["notification_accepted"] == "UNKNOWN" and st["notification_received"] == "UNKNOWN"
    runs.delivery(log, daily, r["run_id"], "received", "push", receipt="creator replied 'got it' at 09:02 IST")
    st = runs.delivery_stages(daily, "2026-11-21", log)
    assert st["notification_received"].startswith("YES") and "09:02" in st["notification_received"]


def test_the_real_20_nov_hook_would_fail_the_financial_rule():
    """The delivered 20 Nov package: its +34% opening-price hook rested on Nasdaq search excerpts."""
    from creatoros.scripts import package
    root = Path(__file__).resolve().parents[1]
    held = json.loads((root / "daily/2026-11-20/held_anthropic-ipo-first-day/package.json").read_text())
    held["verification"] = "tiered"
    held["candidates"][0].pop("hold_reason", None)
    held["candidates"] = [c for c in held["candidates"]]
    import creatoros.scripts.package as pk
    reasons = pk.validate({**held, "date": "2026-11-20"})[1]["ready"]["reasons"]
    assert any("needs HIGH" in r for r in reasons)
    today = json.loads((root / "daily/2026-11-20/package.json").read_text())
    probs, info = package.validate(today)
    assert probs == [] and info["ready"]["status"] == "RECORDING READY"
    assert all(c["level"] == "HIGH" for c in today["factcheck"]["claims"] if c["in_script"])
