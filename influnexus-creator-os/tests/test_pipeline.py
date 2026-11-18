"""End-to-end test on synthetic footage. Needs ffmpeg, the speech models and piper-tts; skipped otherwise."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODELS = Path(os.environ.get("CREATOROS_MODELS", Path.home() / "models"))
needs = pytest.mark.skipif(not (MODELS / "sherpa-onnx-whisper-small").exists() or shutil.which("ffmpeg") is None,
                           reason="speech models or ffmpeg missing: run tools/setup_models.sh")


@pytest.fixture(scope="module")
def footage():
    out = ROOT / "footage" / "incoming" / "synthetic"
    if not (out / "sample_vertical_hevc.mov").exists():
        if not (MODELS / "vits-piper-hi_IN-pratham-medium").exists():
            pytest.skip("test voice missing: run tools/setup_models.sh --with-test-voice")
        subprocess.run([sys.executable, str(ROOT / "tools" / "make_test_footage.py"), str(out), str(MODELS)], check=True)
    return out


@needs
@pytest.mark.slow
def test_vertical_hevc_footage_becomes_a_passing_reel(footage):
    from creatoros.editing.pipeline import edit
    from creatoros.editing.probe import probe
    fx = ROOT / "tests" / "fixtures"
    r = edit(footage / "sample_vertical_hevc.mov", "test-e2e", fx / "sample_script.txt", fx / "sample_edit_plan.json",
             fx / "sample_factcheck.json", force=True)
    s, qc = r["summary"], r["qc"]
    assert s["input"]["video"]["codec"] == "hevc" and s["input"]["video"]["orientation"] == "vertical"
    assert qc["passed"], [c for c in qc["checks"] if c["status"] == "FAIL"]
    truth = json.loads((footage / "truth.json").read_text(encoding="utf-8"))
    bad = [m for m in truth if m["label"] in ("false_start", "aside", "s5_bad_take")]
    for m in bad:
        mid = (m["start"] + m["end"]) / 2
        assert not any(c["src_start"] <= mid <= c["src_end"] for c in s["cuts"]), f"{m['label']} survived the edit"
    assert 30 <= s["duration"] <= 40 and s["missing_sentences"] == []
    final = probe(Path(s["final"]["instagram"]))
    assert (final["video"]["width"], final["video"]["height"], final["video"]["codec"], final["audio"]["codec"]) == (1080, 1920, "h264", "aac")
    assert all(Path(p).exists() for p in s["final"].values()) and len(s["final"]) == 4
    assert footage.joinpath("sample_vertical_hevc.mov").exists(), "the source recording is never moved or deleted"
