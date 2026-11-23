"""V10: verification report, schema-checked production handoff, editing-side gate, QC report, recording dependency and the
approved scheduled-task prompt."""
import copy
import json
from pathlib import Path

import pytest

from creatoros import config
from creatoros.production import handoff as hmod
from creatoros.scripts import package

FIX = Path(__file__).parent / "fixtures" / "v9_2026-11-24"


def pkg():
    return json.loads((FIX / "package.json").read_text(encoding="utf-8"))


@pytest.fixture
def saved(tmp_path, monkeypatch):
    monkeypatch.setattr(package, "holds_for", lambda date: [])
    (tmp_path / "verification_report.json").write_text((FIX / "verification_report.json").read_text(encoding="utf-8"))
    r = package.save(pkg(), tmp_path, record=False)
    assert r["ok"]
    return tmp_path


def test_handoff_matches_the_schema_and_passes_the_gate(saved):
    h = json.loads((saved / "production_handoff.json").read_text(encoding="utf-8"))
    assert hmod.validate(h) == []
    assert h["verification_status"] == "VERIFIED" and h["schema_version"] == "v10"
    assert h["output_settings"]["resolution"] == "2160x3840" and h["output_settings"]["fps"] == 30
    assert len(h["caption_timing"]) >= len(h["transcript"]) and all("https://" in u for u in h["source_urls"])
    assert any("sec.gov" in u for u in h["source_urls"])                  # regulatory filing in the evidence


def test_gate_refuses_unverified_claims_and_assets_without_rights(saved):
    h = json.loads((saved / "production_handoff.json").read_text(encoding="utf-8"))
    bad = copy.deepcopy(h); bad["verification_status"] = "BLOCKED"
    assert any("not VERIFIED" in x for x in hmod.validate(bad))
    bad = copy.deepcopy(h); bad["storyboard"][3]["rights"] = "unknown"
    assert any("without established rights" in x for x in hmod.validate(bad))
    bad = copy.deepcopy(h); bad["output_settings"]["resolution"] = "1080x1920"
    assert any(x.startswith("schema:") for x in hmod.validate(bad))
    bad = copy.deepcopy(h); del bad["music"]
    assert any("music" in x for x in hmod.validate(bad))


@pytest.mark.parametrize("text,expected", [("Creator footage (own)", "own"), ("SEC EDGAR screenshot (public filings)", "public-record"),
                                            ("NVIDIA media assets (editorial use; confirm terms)", "editorial-press"),
                                            ("Random YouTube clip", "unknown"), ("Track from Epidemic Sound", "licensed-library")])
def test_rights_classification(text, expected):
    assert hmod.rights_of(text) == expected


def test_qc_waits_for_the_recording_and_is_not_creative_approval(saved):
    q = json.loads((saved / "qc_report.json").read_text(encoding="utf-8"))
    assert q["pass_pre_recording"] is True
    assert q["audio"].endswith("AWAITING ORIGINAL RECORDING") and q["video"].endswith("AWAITING ORIGINAL RECORDING")
    assert "not creative approval" in q["note"]
    h = json.loads((saved / "production_handoff.json").read_text(encoding="utf-8"))
    assert h["recording_status"] == "AWAITING ORIGINAL RECORDING"


def test_unsupported_claim_blocks_the_handoff(tmp_path, monkeypatch):
    monkeypatch.setattr(package, "holds_for", lambda date: [])
    p = pkg()
    for c in p["factcheck"]["claims"]:
        if c["id"] == "c4":
            c["evidence"] = [dict(e, access="search-index") for e in c["evidence"] if e["kind"] != "primary"] or \
                            [dict(c["evidence"][0], access="search-index")]
    probs, info = package.validate(p)
    assert info["ready"]["status"] != "RECORDING READY"
    h = hmod.build(p, info, None)
    assert h["verification_status"] == "BLOCKED" and hmod.validate(h)


def test_v10_package_needs_a_verification_report(monkeypatch, tmp_path):
    monkeypatch.setattr(package, "holds_for", lambda date: [])
    monkeypatch.setattr(config, "path", lambda *a: tmp_path.joinpath(*[str(x) for x in a]))
    probs = package.validate({**pkg(), "date": "2026-11-25"})[0]
    assert any("verification_report.json" in x for x in probs)


def test_verification_report_for_24_nov_is_complete():
    r = json.loads((FIX / "verification_report.json").read_text(encoding="utf-8"))
    assert r["final_decision"].startswith("VERIFIED")
    for c in r["claims"]:
        for k in ("claim", "evidence", "sources", "event_date", "announcement_date", "status", "confidence", "contradictions", "decision"):
            assert k in c
    assert r["sources"]["sec_8k_resignation"]["opened"] and r["sources"]["cnn_independent"]["opened"]
    assert any("11 Nov" in x for x in r["corrections"])


def test_approved_scheduled_prompt_is_v10():
    t = config.path("config", "scheduled_task_prompt.md").read_text(encoding="utf-8")
    assert "V10" in t and "verification_report.json" in t and "handoff-check" in t and "AWAITING ORIGINAL RECORDING" in t
    assert "never create, change or delete scheduled tasks" in t
