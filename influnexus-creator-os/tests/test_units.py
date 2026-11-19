import json
from pathlib import Path

import pytest

from creatoros.analytics import store
from creatoros.editing import align, cuts
from creatoros.factcheck import claims
from creatoros.publishing import base, publish as pub
from creatoros.qc import checks
from creatoros.research import candidates, storylog
from creatoros.scripts import lint
from creatoros.subtitles import captions
from creatoros.transcription.asr import Transcript, Word
from creatoros.transcription.phonetic import key, tokenize

FIX = Path(__file__).parent / "fixtures"
SCRIPT = (FIX / "sample_script.txt").read_text(encoding="utf-8")


def transcript(segments):
    """segments: [(start, end, text)] -> Transcript with interpolated word times, like the sherpa backend."""
    from creatoros.transcription.asr import _spread
    t = Transcript(backend="test", vad="test", duration=segments[-1][1] + 1)
    for i, (a, b, text) in enumerate(segments):
        t.segments.append({"start": a, "end": b, "text": text})
        t.words += _spread(text, a, b, i)
    return t


# ---------- phonetic matching ----------
@pytest.mark.parametrize("roman,dev", [("critical", "क्रिटिकल"), ("bug", "बग"), ("ghante", "घंटे"), ("Oracle", "ओरेकल"),
                                        ("patch", "पैच"), ("kharcha", "खर्चा"), ("mushkil", "मुश्किल")])
def test_roman_and_devanagari_share_a_key(roman, dev):
    assert key(roman) == key(dev)


def test_numbers_are_wildcards_and_split_from_words():
    assert tokenize("Java4Shell costs $200") == ["Java", "4", "Shell", "costs", "200"]
    assert key("200") == "_"


def test_sentence_split_joins_one_word_fragments():
    s = align.script_sentences(SCRIPT)
    assert len(s) == 12 and s[1].startswith("Kharcha? Do sau")


# ---------- take selection ----------
def recording():
    return transcript([
        (0.8, 3.0, "एक एआई ने जावा में एक क्रिटिकल"),                       # false start
        (4.1, 5.4, "सॉरी फिर से"),                                         # aside
        (6.3, 10.4, "एक एआई ने जावा में एक क्रिटिकल बग सिर्फ एक घंटे में ढूंढ लिया"),
        (10.9, 12.9, "खर्चा दो सौ डॉलर से कम"),
        (13.4, 16.1, "यह क्लेम है सिक्योरिटी स्टार्टअप कैलिफ का"),
        (16.6, 18.3, "बग का नाम जावा फॉर शेल"),
        (19.0, 23.4, "जावा पर बैंक्स एयरलाइंस और शायद आपकी कंपनी का बैकएंड चलता है"),
        (25.9, 27.5, "ओरेकल का पैच आ गया"),                                 # bad take after a long pause
        (28.1, 29.9, "ओरेकल का पैच आ चुका है"),
        (30.5, 31.7, "लेकिन पैनिक नहीं"),
        (32.0, 37.7, "ओरेकल खुद कहता है एक्सप्लॉइट करना मुश्किल है और अभी तक कोई रियल अटैक कन्फर्म नहीं"),
        (38.3, 41.1, "असली सबक बग ढूंढना अब सस्ता हो गया है"),
        (41.5, 43.0, "पैच लेट करना महंगा"),
        (43.6, 46.1, "डेवलपर हो आज ही जावा अपडेट करो"),
    ])


def test_alignment_finds_every_sentence_and_drops_retakes():
    t = recording()
    r = align.align(SCRIPT, t)
    assert r["missing"] == []
    assert r["sentences"][0]["start"] > 6.0, "the complete second take of the opening must win over the false start"
    assert 28.0 < r["sentences"][5]["start"] < 28.5, "the later, complete take of the Oracle line must win"
    kinds = [x["kind"] for x in r["removed"]]
    assert "false_start" in kinds and len(r["removed"]) >= 2
    assert r["attempts_at_opening"] == 2
    assert any(p["seconds"] > 2 for p in r["long_pauses"])


def test_missing_sentence_is_reported_not_invented():
    t = recording()
    t2 = transcript([(s["start"], s["end"], s["text"]) for s in t.segments[:-1]])   # creator never said the ending
    r = align.align(SCRIPT, t2)
    assert 11 in r["missing"]


def test_garbled_sentence_is_located_by_position_and_flagged():
    segs = [(s["start"], s["end"], s["text"]) for s in recording().segments]
    segs[4] = (13.4, 16.1, "टटटट पपपप गगगग ममम")       # recogniser failure on "Yeh claim hai ..."
    r = align.align(SCRIPT, transcript(segs))
    assert r["missing"] == [] and 2 in r["inferred"] and 2 in r["weak"]


def test_cuts_remove_retakes_and_tighten_pauses():
    t = recording()
    r = align.align(SCRIPT, t)
    cfg = {"pad_before": 0.10, "pad_after": 0.16, "max_natural_pause": 0.45, "punch_in_scale": 1.06}
    iv, shift = cuts.build(t, r["takes"], cfg)
    total = iv[-1].out + iv[-1].end - iv[-1].start
    assert iv[0].start > 6.0 and 30 < total < 36
    assert all(not (i.start < 27.5 and i.end > 25.9) for i in iv), "the bad take must not be in the edit"
    assert all(abs(i.start * 30 - round(i.start * 30)) < 1e-6 for i in iv), "cuts sit on frame boundaries"
    assert {i.zoom for i in iv} == {1.0, 1.06}
    words = cuts.script_word_times(r["sentences"], r["takes"], t, shift)
    assert [w["text"] for w in words][:3] == ["Ek", "AI", "ne"]
    assert all(b["start"] >= a["start"] for a, b in zip(words, words[1:])) and words[-1]["end"] <= total + 0.01


# ---------- captions ----------
def test_caption_groups_respect_limits():
    t = recording()
    r = align.align(SCRIPT, t)
    iv, shift = cuts.build(t, r["takes"], {"pad_before": 0.1, "pad_after": 0.16, "max_natural_pause": 0.45})
    groups = captions.group(cuts.script_word_times(r["sentences"], r["takes"], t, shift))
    assert all(1 <= len(g["words"]) <= 5 and len(g["lines"]) <= 2 for g in groups)
    assert sum(len(g["words"]) for g in groups) == 88
    assert captions.check_layout(groups) == []
    assert all(b["start"] >= a["end"] - 1e-6 for a, b in zip(groups, groups[1:])), "captions never overlap"


def test_caption_layout_flags_overflow():
    g = [{"start": 0, "end": 1, "lines": ["X" * 40], "width": 2000.0, "words": ["X" * 40]}]
    assert captions.check_layout(g)


# ---------- research ----------
def cand(**kw):
    base_ = {f: "x" for f in candidates.REQUIRED}
    base_.update(already_covered=False, engagement={"likes": "UNKNOWN"}, category="AI", topic_type="BREAKING",
                 evidence_confidence="HIGH", secondary={k: "MEDIUM" for k in candidates.SECONDARY},
                 scores={"traction": 5, "surprise": 8, "relevance": 8, "practical": 8, "visual": 5, "credibility": 8})
    base_.update(kw)
    return base_


def test_trend_score_weights_and_unknowns():
    assert candidates.trend_score(cand())["total"] == 25 * .5 + 20 * .8 + 20 * .8 + 15 * .8 + 10 * .5 + 10 * .8
    s = candidates.trend_score(cand(scores={"traction": "UNKNOWN", "surprise": 10, "relevance": 10, "practical": 10, "visual": 10, "credibility": 10}))
    assert s == {"total": 75.0, "unknown": ["traction"]}


def test_high_traction_needs_evidence_and_no_invented_metrics():
    c = cand(scores={**cand()["scores"], "traction": 9})
    assert any("traction_evidence" in p for p in candidates.validate(c))
    assert any("engagement.likes" in p for p in candidates.validate(cand(engagement={"likes": "lots"})))


def test_covered_stories_are_not_eligible():
    r = candidates.rank([cand(headline="a", already_covered=True, scores={**cand()["scores"], "surprise": 10}), cand(headline="b")])
    assert r[0]["headline"] == "b"


def test_story_log_blocks_repeats(tmp_path):
    log = tmp_path / "log.jsonl"
    storylog.add("2026-11-18", "Java4Shell: AI found a critical Java flaw", ["CVE-2026-114938"], "java4shell", path=log)
    assert storylog.find_repeat("Oracle patches Java bug", ["cve-2026-114938"], "2026-11-25", path=log)
    with pytest.raises(ValueError):
        storylog.add("2026-11-25", "Java4Shell again", ["CVE-2026-114938"], "java4shell-2", path=log)
    storylog.add("2026-11-25", "Java4Shell exploited in the wild", ["CVE-2026-114938"], "java4shell-itw", "first confirmed exploitation", path=log)
    assert storylog.find_repeat("Something else entirely about robots", [], "2026-11-25", path=log) is None


# ---------- fact-check ----------
def test_real_factcheck_is_clean():
    assert claims.validate(json.loads((FIX / "sample_factcheck.json").read_text(encoding="utf-8")), SCRIPT) == []


def test_factcheck_rejects_unverified_and_unattributed_claims():
    fc = {"claims": [{"id": "a", "text": "t", "status": "UNVERIFIED", "in_script": True},
                     {"id": "b", "text": "t", "status": "COMPANY CLAIM", "attribution": "Acme", "script_attribution": "Acme says",
                      "in_script": True, "evidence": ["https://example.com"]},
                     {"id": "c", "text": "t", "status": "CONFIRMED", "in_script": True}]}
    p = claims.validate(fc, "The product is amazing.")
    assert any(x.startswith("a:") for x in p) and any(x.startswith("b:") for x in p) and any("evidence" in x for x in p)


# ---------- script lint ----------
def test_script_passes_and_bad_scripts_fail():
    english = json.loads((Path(__file__).resolve().parents[1] / "daily" / "2026-11-18" / "package.json").read_text(encoding="utf-8"))["script"]
    r = lint.check(english)
    assert r["ok"] and 75 <= r["words"] <= 90 and 30 <= r["seconds"] <= 40
    assert not lint.check("Breaking news! " + english)["ok"]
    assert not lint.check(english + " " + english)["ok"], "a script over 40 seconds must be rejected"
    assert not lint.check(english + " What do you think?")["ok"]
    assert not lint.check(SCRIPT)["ok"], "a Hinglish script fails while English is the default"
    assert lint.check(SCRIPT, language="hinglish")["ok"], "the language rule is configurable"


def test_hook_scoring_disqualifies_inaccurate_hooks():
    full = lambda t, acc, v: {"text": t, "mechanism": "unexpected fact", "accuracy": acc, **{k: v for k in lint.HOOK_CRITERIA if k != "accuracy"}}
    h = lint.score_hooks([full("a", 4, 10), full("b", 9, 7)])
    assert h[0]["text"] == "b"


# ---------- QC rules ----------
def test_overlay_claim_rules():
    fc = json.loads((FIX / "sample_factcheck.json").read_text(encoding="utf-8"))
    plan = json.loads((FIX / "sample_edit_plan.json").read_text(encoding="utf-8"))
    assert all(c["status"] == "PASS" for c in checks.overlay_claims(plan, fc))
    bad = {"overlays": [{"id": "x", "type": "stat_card", "title": "CISA says patch now", "claim_ids": ["c8"]},
                        {"id": "y", "type": "stat_card", "title": "Found in 1 hour", "claim_ids": ["c1"]},
                        {"id": "z", "type": "hook_title", "text": "Hackers inside NSA"}]}
    assert [c["status"] for c in checks.overlay_claims(bad, fc)] == ["FAIL", "FAIL", "FAIL"]


# ---------- analytics ----------
def test_analytics_upsert_and_derived_metrics(tmp_path):
    p = tmp_path / "perf.csv"
    row = dict(date="2026-11-19", video_id="v1", platform="instagram", checkpoint="24h", views="2000", shares="30", saves="50",
               new_followers="12", avg_view_duration_s="21", duration_s="35", topic="security", hook_type="unexpected_result", source="manual")
    d = store.upsert(row, p)
    assert d["follows_per_1k_views"] == 6.0 and d["shares_per_1k_views"] == 15.0 and d["avg_retention"] == 0.6
    store.upsert({**row, "views": "4000"}, p)
    assert len(store.load(p)) == 1 and store.load(p)[0]["views"] == "4000"
    assert store.derive(store.load(p)[0])["likes_per_1k_views"] is None, "uncollected metrics stay empty, never zero"
    with pytest.raises(ValueError):
        store.upsert({**row, "views": "many"}, p)
    with pytest.raises(ValueError):
        store.upsert({**row, "checkpoint": "1h"}, p)
    store.upsert({**row, "checkpoint": "7d"}, p)
    g = store.by_dimension("topic", "7d", "instagram", p)
    assert g[0]["videos"] == 1 and g[0]["enough_data"] is False
    due = store.due_checkpoints("2026-11-23T12:00:00", [{"video_id": "v1", "platform": "instagram", "published_at": "2026-11-19T14:00:00"}], p)
    assert [d["checkpoint"] for d in due] == ["2h", "48h", "72h"]          # 24h and 7d are stored; 7d not yet due


# ---------- publishing safeguards ----------
def test_publish_is_blocked_without_qc_or_credentials(tmp_path, monkeypatch):
    for k in ("IG_USER_ID", "IG_ACCESS_TOKEN", "YT_ACCESS_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    led = tmp_path / "ledger.jsonl"
    r = pub.publish("1999-01-01", "instagram", ledger_path=led)
    assert r["status"] == "blocked" and "QC" in r["reason"]
    assert pub.publish("1999-01-01", "linkedin", ledger_path=led)["status"] == "blocked"
    assert [e["status"] for e in base.ledger(led)] == ["blocked", "blocked"]
    with pytest.raises(base.Blocked):
        base.credentials("instagram")


def test_duplicate_publish_is_detected(tmp_path):
    led = tmp_path / "ledger.jsonl"
    base.record({"platform": "instagram", "status": "published", "sha256": "abc", "date": "2026-11-18", "platform_id": "1"}, led)
    assert base.already_published("instagram", "abc", "2026-11-19", led)
    assert base.already_published("instagram", "zzz", "2026-11-18", led)
    assert base.already_published("youtube", "abc", "2026-11-18", led) is None


def test_secrets_are_redacted_from_logs(monkeypatch, caplog):
    monkeypatch.setenv("IG_ACCESS_TOKEN", "supersecretvalue123")
    from creatoros.util import _Redact
    import logging
    rec = logging.LogRecord("x", logging.INFO, "", 0, "token is supersecretvalue123", (), None)
    _Redact().filter(rec)
    assert "supersecretvalue123" not in rec.getMessage()
