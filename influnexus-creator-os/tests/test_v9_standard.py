"""V9 permanent production standard (from 2026-11-24): 40-45 s / 90-105 words, recording directions, sentence-by-sentence
storyboard, music plan, distribution kit and production handoff."""
import json
from pathlib import Path

from creatoros.scripts import lint, package


def v9():
    return json.loads((Path(__file__).parent / "fixtures" / "v9_2026-11-24" / "package.json").read_text(encoding="utf-8"))


def ok(monkeypatch):
    monkeypatch.setattr(package, "holds_for", lambda date: [])


def test_v10_length_limits_supersede_v9():
    lim = lint.limits("v9")          # the V9 layer now carries the V10 limits (35-45 s, 85-105 words; 45 s hard)
    assert lim["target_seconds"] == [35, 45] and lim["hard_max_seconds"] == 45 and lim["target_words"] == [85, 105]


def test_real_nvidia_package_passes_and_writes_the_handoff(tmp_path, monkeypatch):
    ok(monkeypatch)
    p = v9()
    assert package.is_v9(p)
    probs, info = package.validate(p)
    assert probs == [] and info["ready"]["status"] == "RECORDING READY"
    assert 35 <= info["lint"]["seconds"] <= 45 and 85 <= info["lint"]["words"] <= 105
    package.save(p, tmp_path, record=False)
    today = (tmp_path / "today.md").read_text(encoding="utf-8")
    for h in ["## 1. Why this story", "## 2. Final script", "## 3. Recording directions", "## 4. Visual storyboard",
              "## 5. Music and sound", "## 6. Caption and hashtags", "## 7. Cover headline", "## 8. Verified sources",
              "## 9. Production handoff"]:
        assert h in today
    ho = json.loads((tmp_path / "production_handoff.json").read_text(encoding="utf-8"))
    assert ho["output_settings"]["resolution"] == "2160x3840" and ho["editing_hierarchy"][0] == "GitHub editing tools"
    assert len(ho["storyboard"]) == 10 and ho["recording_status"] == "AWAITING ORIGINAL RECORDING"


def test_storyboard_must_follow_the_spoken_script(monkeypatch):
    ok(monkeypatch)
    p = v9()
    sb = [dict(r) for r in p["storyboard"]]
    sb[2]["line"] = "Something the creator does not say."
    assert any("exact spoken sentence" in x for x in package.validate({**p, "storyboard": sb})[0])
    assert any("one row per sentence" in x for x in package.validate({**p, "storyboard": p["storyboard"][:-1]})[0])
    sb = [dict(r) for r in p["storyboard"]]
    sb[3]["start_s"] = 0
    assert any("run forward" in x for x in package.validate({**p, "storyboard": sb})[0])
    sb = [dict(r) for r in p["storyboard"]]
    sb[5]["source_licensing"] = ""
    assert any("row 6: fill" in x for x in package.validate({**p, "storyboard": sb})[0])


def test_music_distribution_and_handoff_are_required(monkeypatch):
    ok(monkeypatch)
    p = v9()
    assert any(x.startswith("music:") for x in package.validate({**p, "music": {}})[0])
    assert any(x.startswith("distribution:") for x in package.validate({**p, "distribution": {"cover_headline": "x"}})[0])
    bad = {**p["production_handoff"], "output_resolution": "1080x1920"}
    assert any("2160x3840" in x for x in package.validate({**p, "production_handoff": bad})[0])
    bad = {**p["production_handoff"], "pipeline": list(reversed(p["production_handoff"]["pipeline"]))}
    assert any("established order" in x for x in package.validate({**p, "production_handoff": bad})[0])


def test_a_short_script_is_refused(monkeypatch):
    ok(monkeypatch)
    p = v9()
    short = p["script"].replace("And Harvey Jones became chair of the board.", "").replace("Huang said he can't wait to get back to work.", "")
    probs = package.validate({**p, "script": short})[0]
    assert any("words; write 85-105" in x or "one row per sentence" in x for x in probs)
