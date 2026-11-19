"""Production reliability: v3 scoring, the 24-hour window, length limits, run IDs, duplicate guard, recovery, delivery."""
import copy
import datetime as dt
import json
from pathlib import Path

import pytest

from creatoros.factcheck.verification import access_summary
from creatoros.research import candidates, runs, runstatus
from creatoros.scripts import lint, package

ROOT = Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc
RUN_START = dt.datetime(2026, 11, 20, 3, 11, 30, tzinfo=UTC)          # 08:41:30 IST
WIN = package.research_window(RUN_START.isoformat())


def v3_candidate(**kw):
    c = {"headline": "Robot learns a task overnight", "category": "AI", "topic_type": "BREAKING",
         "published_at": "2026-11-19T18:00:00+00:00", "original_source": "https://example.org/a", "main_claim": "x",
         "verification_status": "VERIFIED", "why_it_matters": "x", "potential_hook": "x", "target_audience": "x",
         "uncertainty": "x", "evidence_confidence": "HIGH", "already_covered": False,
         "x_signal": {"status": "NOT VERIFIED", "posts": [], "discussion_evidence": []},
         "scores": {k: 6 for k in candidates.WEIGHTS_V3}}
    c["scores"]["public_discussion"] = 3
    c.update(kw)
    return c


def words(n):
    return " ".join(["Robots learn fast now."] * (n // 4)) + " " + " ".join(["word"] * (n % 4))


# --- v3 scoring and X signal -------------------------------------------------------------------------------------------

def test_v3_weights_sum_to_100_and_detect_scheme():
    assert sum(candidates.WEIGHTS_V3.values()) == 100
    c = v3_candidate()
    assert candidates.scheme(c) == "v3" and candidates.validate(c) == []
    assert candidates.trend_score(c)["total"] == pytest.approx(60 - 20 * 0.6 + 20 * 0.3)


def test_public_discussion_needs_evidence_and_high_needs_observed_x_posts():
    c = v3_candidate()
    c["scores"]["public_discussion"] = 6
    assert any("discussion_evidence" in p for p in candidates.validate(c))
    c["x_signal"]["discussion_evidence"] = ["covered by 4 outlets in 12 h (links in research.json)"]
    assert candidates.validate(c) == []
    c["scores"]["public_discussion"] = 9
    assert any("VERIFIED x_signal" in p for p in candidates.validate(c))


def test_x_metrics_must_be_observed_and_verified_needs_an_opened_post():
    post = {"url": "https://x.com/a/status/1", "account": "@a", "posted_at": "2026-11-19T10:00:00+00:00",
            "retrieved_at": "2026-11-20T03:20:00+00:00", "access": "search-index", "metrics": {"likes": "lots"}}
    c = v3_candidate(x_signal={"status": "VERIFIED", "posts": [post], "discussion_evidence": []})
    probs = candidates.validate(c)
    assert any("observed number or UNKNOWN" in p for p in probs)
    assert any("opened directly" in p for p in probs)
    post["metrics"] = {"likes": "UNKNOWN"}
    c["x_signal"]["status"] = "PARTLY VERIFIED"
    assert candidates.validate(c) == []


# --- 24-hour research window ------------------------------------------------------------------------------------------

def test_research_window_is_the_24_hours_before_the_run():
    assert WIN["end_utc"] == "2026-11-20T03:11:30+00:00" and WIN["start_utc"] == "2026-11-19T03:11:30+00:00"
    assert WIN["end_ist"].startswith("2026-11-20T08:41:30+05:30")
    assert package.window_problems(WIN) == []
    assert package.window_problems({**WIN, "start_utc": "2026-11-19T15:11:30+00:00"})
    assert runs.window(RUN_START) == {**WIN}


def test_old_story_needs_a_dated_new_development_inside_the_window():
    old = v3_candidate(published_at="2026-06-15T00:00:00+00:00")
    assert "before the 24-hour" in candidates.window_reason(old, WIN)
    old["new_development"] = {"what": "FDA clearance", "at": "2026-11-19T20:00:00+00:00"}
    assert candidates.window_reason(old, WIN) is None
    old["new_development"]["at"] = "2026-11-10T00:00:00+00:00"
    assert candidates.window_reason(old, WIN)
    ranked = candidates.rank([old, v3_candidate()], WIN)
    assert ranked[0]["headline"] == "Robot learns a task overnight" and not ranked[1]["eligible"]


def test_window_rule_does_not_touch_v2_candidates():
    v2 = json.loads((ROOT / "daily/2026-11-19/package.json").read_text())["candidates"][0]
    assert candidates.window_reason(v2, WIN) is None


# --- length and duration ----------------------------------------------------------------------------------------------

def test_v3_length_limits_and_v2_limits_are_kept_for_history():
    s95, s120 = words(95), words(120)
    assert lint.check(s95, scheme="v3")["seconds"] <= 45
    assert not any("hard maximum" in p for p in lint.check(s95, scheme="v3")["problems"])
    assert any("hard maximum" in p for p in lint.check(s95)["problems"])             # 40 s limit for v1/v2
    assert any("hard maximum" in p for p in lint.check(s120, scheme="v3")["problems"])
    assert any("90-105" in w for w in lint.check(words(70), scheme="v3")["warnings"])


def test_duration_score_is_measured_with_v3_limits():
    q = {k: 9 for k in lint.QUALITY_CHECKS}
    assert lint.quality(q, words(98), "v3")["scores"]["duration"] == 10
    assert lint.quality(q, words(130), "v3")["scores"]["duration"] == 0


# --- historical packages ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("date", ["2026-11-18", "2026-11-19"])
def test_historical_packages_still_validate(date):
    p = json.loads((ROOT / "daily" / date / "package.json").read_text())
    assert package.validate(p)[0] == []


def test_v3_package_requires_window_and_retrieval_times():
    p = json.loads((ROOT / "daily/2026-11-19/package.json").read_text())
    p["scoring"] = "v3"
    probs = package.validate(p)[0]
    assert "missing: research_window" in probs and "missing: generated_at" in probs and "missing: backups" in probs
    p.update(research_window=WIN, generated_at="2026-11-20T09:05:00+05:30", pillar="startups_science", format="C",
             backups=[], audience={}, editing={}, limitations=[])
    probs = package.validate(p)[0]
    assert any("retrieved_at" in x for x in probs) and any("v3 criteria" in x for x in probs)


# --- run records: IDs, duplicate guard, recovery, delivery, idempotency ------------------------------------------------

def test_run_start_records_id_window_budgets_and_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    monkeypatch.setenv("CLAUDE_CODE_MESSAGING_TOKEN", "secret-should-not-appear")
    rec = runs.start(tmp_path / "runs.jsonl", "scheduled", root=tmp_path, now=RUN_START)
    assert rec["run_id"] == "2026-11-20-scheduled-084130" and rec["ist_date"] == "2026-11-20"
    assert rec["research_window"] == WIN
    assert rec["budgets"]["deliver_by"] == "09:25" and rec["budgets"]["research"] == "09:03"
    assert rec["environment"]["cloud"] is True
    assert "secret" not in json.dumps(rec)


def test_duplicate_scheduled_run_is_refused_and_interrupted_run_is_recovered(tmp_path):
    log, daily = tmp_path / "runs.jsonl", tmp_path / "daily"
    first = runs.start(log, "scheduled", root=tmp_path, now=RUN_START)
    again = runs.start(log, "scheduled", root=tmp_path, now=RUN_START + dt.timedelta(minutes=5))
    assert again["duplicate"] == "IN_PROGRESS" and again["run_id"] == first["run_id"]
    later = runs.start(log, "scheduled", root=tmp_path, now=RUN_START + dt.timedelta(minutes=70))
    assert "duplicate" not in later and later["run_id"] != first["run_id"]
    assert any(r.get("status") == "INTERRUPTED" and r["run_id"] == first["run_id"] for r in runs.load(log))
    runs.end(log, daily, "READY", run_id=later["run_id"], delivery="requested", channel="push",
             now=RUN_START + dt.timedelta(minutes=80))
    done = runs.start(log, "scheduled", root=tmp_path, now=RUN_START + dt.timedelta(minutes=90))
    assert done["duplicate"] == "ALREADY_DONE"
    assert runs.start(log, "manual", root=tmp_path, now=RUN_START + dt.timedelta(minutes=91)).get("duplicate") is None


def test_run_report_is_idempotent_and_only_touches_its_own_date(tmp_path):
    log, daily = tmp_path / "runs.jsonl", tmp_path / "daily"
    (daily / "2026-11-19").mkdir(parents=True)
    (daily / "2026-11-19" / "today.md").write_text("yesterday")
    r = runs.start(log, "scheduled", root=tmp_path, now=RUN_START)
    runs.end(log, daily, "READY", run_id=r["run_id"], now=RUN_START + dt.timedelta(minutes=30))
    runs.delivery(log, daily, r["run_id"], "requested", "push", now=RUN_START + dt.timedelta(minutes=31))
    runs.delivery(log, daily, r["run_id"], "confirmed", "push", "creator replied", now=RUN_START + dt.timedelta(minutes=40))
    rep = json.loads((daily / "2026-11-20" / "run_report.json").read_text())
    assert list(rep["runs"]) == [r["run_id"]]
    entry = rep["runs"][r["run_id"]]
    assert entry["delivery"]["status"] == "confirmed" and entry["package_status"] == "MISSING"
    assert entry["research_window"] == WIN and entry["status"] == "READY"
    assert (daily / "2026-11-19" / "today.md").read_text() == "yesterday"


def test_delivery_failure_is_reported_even_when_the_package_is_ready(tmp_path):
    log, daily = tmp_path / "runs.jsonl", tmp_path / "daily"
    r = runs.start(log, "scheduled", root=tmp_path, now=RUN_START)
    runs.end(log, daily, "READY", run_id=r["run_id"], delivery="failed", channel="push",
             now=RUN_START + dt.timedelta(minutes=30))
    s = runstatus.status(log, "2026-11-20", RUN_START + dt.timedelta(minutes=60))
    assert s["verdict"] == "PACKAGE READY — DELIVERY FAILED" and s["problem"]
    runs.delivery(log, daily, r["run_id"], "requested", "push", now=RUN_START + dt.timedelta(minutes=35))
    assert runstatus.status(log, "2026-11-20", RUN_START + dt.timedelta(minutes=60))["verdict"] == "OK"


def test_end_without_start_and_bad_delivery_are_errors(tmp_path):
    with pytest.raises(ValueError):
        runs.end(tmp_path / "r.jsonl", tmp_path, "READY", run_id="nope")
    r = runs.start(tmp_path / "r.jsonl", "manual", root=tmp_path, now=RUN_START)
    with pytest.raises(ValueError):
        runs.end(tmp_path / "r.jsonl", tmp_path, "READY", run_id=r["run_id"], delivery="sent-by-pigeon")


def test_run_report_summarises_a_real_package(tmp_path):
    s = runs.summarise_package(ROOT / "daily/2026-11-19/package.json")
    assert s["package_status"] == "VALID" and s["readiness"] == "RECORDING READY" and s["fact_check"] == "PASS"
    assert s["word_count"] == 90 and s["quality_gate"] == "PASS"
    assert "search-index" in s["source_access"] and "NOT opened" in s["source_access"]


def test_missing_primary_source_is_labelled_not_found():
    assert "primary source not found" in access_summary([dict(in_script=True, access="not found")])


def _as_v3(p):
    p.update(scoring="v3", research_window=WIN, generated_at="2026-11-20T09:10:00+05:30")
    for c in p["factcheck"]["claims"]:
        c["retrieved_at"] = "2026-11-20T03:30:00+00:00"
    for i, c in enumerate(p["candidates"]):
        c.pop("announced_at", None)
        c["published_at"] = "2026-11-19T12:00:00+00:00"
        c["x_signal"] = {"status": "NOT VERIFIED", "posts": [], "discussion_evidence": ["covered by several outlets"]}
        c["scores"] = {k: 7 for k in candidates.WEIGHTS_V3}
        c["scores"].update(public_discussion=5, surprise=10 - min(i, 9))
    for h in p["hooks"]:
        h.setdefault("surprise", h["curiosity"])
        h.setdefault("specificity", h["clarity"])
    p["candidates"][0]["signals"] = [{"platform": "primary", "url": "https://www.nature.com/articles/s41591-026-04414-6",
                                      "title": "Nature Medicine paper", "retrieved_at": "2026-11-20T03:30:00+00:00",
                                      "access": "SEARCH-INDEX", "engagement": {"basis": "unknown"}}]
    others = [c["headline"] for c in candidates.rank(p["candidates"], WIN) if c["eligible"] and c["headline"] != p["topic"]]
    p.update(pillar="startups_science", format="C", backups=others[:2],
             audience={q: "because" for q in package.AUDIENCE_QUESTIONS},
             editing={k: ["x"] for k in package.EDITING_KEYS},
             limitations=["x.com and nature.com could not be opened; search-index only"])
    return p


def test_full_v3_package_end_to_end():
    """A complete v3 package validates; a 38 s script is penalised against the 40-45 s target, not rejected outright."""
    p = _as_v3(json.loads((ROOT / "daily/2026-11-19/package.json").read_text()))
    probs, info = package.validate(p)
    assert probs == ["quality: script quality 87/100 is below 90: revise the script"]
    assert info["quality"]["scores"]["duration"] == 7 and "40-45s target" in " ".join(info["lint"]["warnings"])
    p["quality_scores"].update({k: 10 for k in lint.QUALITY_CHECKS})
    probs, info = package.validate(p)
    assert probs == [] and info["ready"]["status"] == "RECORDING READY"
    p["candidates"][0]["published_at"] = "2026-06-15T00:00:00+00:00"          # winner falls outside the window
    assert any("top eligible candidate" in x for x in package.validate(p)[0])


def test_new_dates_must_use_v3_and_old_dates_keep_their_scheme():
    p = json.loads((ROOT / "daily/2026-11-19/package.json").read_text())
    p["date"] = "2026-11-20"
    assert "must use" in package.validate(p)[0][0]
    p["date"] = "2026-11-19"
    assert package.validate(p)[0] == []


def test_end_without_run_id_closes_the_open_run_whatever_trigger_was_typed(tmp_path):
    """The stored scheduled-task prompt calls `runlog end` with no --run-id; it must still close the scheduled run."""
    log, daily = tmp_path / "runs.jsonl", tmp_path / "daily"
    r = runs.start(log, "scheduled", root=tmp_path, now=RUN_START)
    rep = runs.end(log, daily, "READY", now=RUN_START + dt.timedelta(minutes=30))
    assert rep["run_id"] == r["run_id"] and rep["trigger"] == "scheduled"
    with pytest.raises(ValueError):
        runs.end(log, daily, "READY", now=RUN_START + dt.timedelta(minutes=31))     # nothing left open


def test_duplicate_guard_sees_runs_logged_before_run_ids_existed(tmp_path):
    log = tmp_path / "runs.jsonl"
    legacy = [{"event": "start", "trigger": "scheduled", "at_utc": "2026-11-19T03:12:16+00:00", "ist_date": "2026-11-19"},
              {"event": "end", "trigger": "scheduled", "status": "READY", "at_utc": "2026-11-19T03:12:31+00:00",
               "ist_date": "2026-11-19"}]
    log.write_text("".join(json.dumps(r) + "\n" for r in legacy))
    noon = dt.datetime(2026, 11, 19, 7, 0, tzinfo=UTC)
    rec = runs.start(log, "scheduled", root=tmp_path, now=noon)
    assert rec["duplicate"] == "ALREADY_DONE" and rec["run_id"] == "2026-11-19-scheduled-084216"


def test_early_scheduled_tagged_test_run_does_not_block_the_0841_run(tmp_path):
    log = tmp_path / "runs.jsonl"
    early = [{"event": "start", "trigger": "scheduled", "at_utc": "2026-11-19T19:30:00+00:00", "ist_date": "2026-11-20"},
             {"event": "end", "trigger": "scheduled", "status": "READY", "at_utc": "2026-11-19T19:31:00+00:00",
              "ist_date": "2026-11-20"}]
    log.write_text("".join(json.dumps(r) + "\n" for r in early))
    assert "duplicate" not in runs.start(log, "scheduled", root=tmp_path, now=RUN_START)
