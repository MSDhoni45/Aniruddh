"""Automated quality control for a finished render. Nothing is reported as passed unless it was measured."""
from __future__ import annotations

import re
from pathlib import Path

from .. import config
from ..audio import chain
from ..editing import align as alignmod
from ..editing.probe import probe
from ..transcription import asr
from ..util import ffmpeg, read_json
from ..util import run as run_cmd

ATTRIBUTION_NEEDED = {"COMPANY CLAIM", "THIRD-PARTY CLAIM", "DISPUTED"}
BLOCKED = {"UNVERIFIED", "SPECULATION"}
FACTUAL_TYPES = {"hook_title", "label", "stat_card", "split"}


def _c(name, ok, detail, warn=False):
    return {"check": name, "status": "PASS" if ok else ("WARN" if warn else "FAIL"), "detail": detail}


def overlay_claims(plan: dict, factcheck: dict | None) -> list[dict]:
    """Every factual overlay must point at a fact-checked claim, and attributed claims must show who said it."""
    out = []
    claims = {c["id"]: c for c in (factcheck or {}).get("claims", [])}
    for ov in plan.get("overlays", []):
        if ov["type"] not in FACTUAL_TYPES or ov.get("factual") is False:
            continue
        ids = ov.get("claim_ids", [])
        text = " ".join([ov.get("text", ""), ov.get("title", "")] + [r.get("title", "") + " " + r.get("text", "") for r in ov.get("rows", [])])
        if not ids:
            out.append(_c(f"overlay_claim:{ov['id']}", False, "factual overlay has no claim_ids (set factual:false if it states no fact)"))
            continue
        for cid in ids:
            c = claims.get(cid)
            if not c:
                out.append(_c(f"overlay_claim:{ov['id']}", False, f"claim {cid} not in fact-check file"))
            elif c["status"] in BLOCKED:
                out.append(_c(f"overlay_claim:{ov['id']}", False, f"claim {cid} is {c['status']} and may not be shown as fact"))
            elif c["status"] in ATTRIBUTION_NEEDED and not (ov.get("attribution") or (c.get("attribution") and c["attribution"].lower() in text.lower())):
                out.append(_c(f"overlay_claim:{ov['id']}", False, f"claim {cid} is {c['status']}: overlay must name the source ({c.get('attribution')})"))
            else:
                out.append(_c(f"overlay_claim:{ov['id']}", True, f"{cid}: {c['status']}"))
    return out


def licences(plan: dict, music: str | None) -> list[dict]:
    manifest = config.path("assets/licensed/manifest.json")
    known = read_json(manifest).get("files", {}) if manifest.exists() else {}
    used = [ov["file"] for ov in plan.get("overlays", []) if ov["type"] in ("image", "video")]
    used += [s["file"] for s in plan.get("sfx", [])] + ([music] if music else [])
    if not used:
        return [_c("asset_licences", True, "no third-party assets used; graphics are generated in-pipeline")]
    return [_c(f"asset_licence:{f}", f in known and bool(known[f].get("license")),
               known.get(f, {}).get("license", "not listed in assets/licensed/manifest.json")) for f in used]


def run(final: Path, *, script_text: str | None, plan: dict, factcheck: dict | None, caption_problems: list[str],
        overlay_problems: list[str], music: str | None, work: Path, weak_sentences: list[int], missing: list[int]) -> dict:
    ex = config.settings()
    exp, aud = ex["export"], ex["audio"]
    checks = []
    try:
        info = probe(final)
    except Exception as exc:
        return {"file": str(final), "passed": False, "checks": [_c("file_opens", False, str(exc))]}
    v, a = info["video"], info["audio"]
    checks.append(_c("file_opens", True, f"{info['container']}, {info['size_bytes'] / 1e6:.1f} MB"))
    checks.append(_c("resolution", (v["width"], v["height"]) == (exp["width"], exp["height"]), f"{v['width']}x{v['height']}"))
    checks.append(_c("aspect_ratio", abs(v["width"] / v["height"] - 9 / 16) < 1e-3, f"{v['width']}:{v['height']}"))
    checks.append(_c("video_codec", v["codec"] == "h264" and v["pix_fmt"] == "yuv420p", f"{v['codec']} {v['pix_fmt']}"))
    checks.append(_c("frame_rate", abs(v["fps"] - exp["fps"]) < 0.01, f"{v['fps']} fps"))
    checks.append(_c("duration", exp["min_seconds"] <= info["duration"] <= exp["max_seconds"],
                     f"{info['duration']:.2f}s (target {exp['min_seconds']}-{exp['max_seconds']}s)"))
    checks.append(_c("audio_present", bool(a) and a["codec"] == "aac", f"{a['codec']} {a['sample_rate']} Hz" if a else "no audio stream"))
    if a:
        loud = chain.measure(final)
        checks.append(_c("loudness", loud["integrated_lufs"] is not None and abs(loud["integrated_lufs"] - aud["target_lufs"]) <= 1.5,
                         f"{loud['integrated_lufs']} LUFS (target {aud['target_lufs']})"))
        checks.append(_c("no_clipping", loud["true_peak_db"] is not None and loud["true_peak_db"] <= -0.5, f"true peak {loud['true_peak_db']} dBFS"))
    err = ffmpeg(["-i", final, "-vf", "blackdetect=d=0.3:pix_th=0.10,freezedetect=n=0.001:d=2", "-af", "silencedetect=n=-50dB:d=1.5",
                  "-f", "null", "-"]).stderr
    black = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)
    freeze = re.findall(r"freeze_start: ([\d.]+)", err)
    silence = re.findall(r"silence_start: ([\d.]+)", err)
    checks.append(_c("no_black_frames", not black, f"black at {black}" if black else "none detected"))
    checks.append(_c("no_frozen_frames", not freeze, f"freeze at {freeze}s" if freeze else "no freeze of 2s or longer"))
    checks.append(_c("no_blank_audio", not silence, f"silence of 1.5s+ at {silence}s" if silence else "no silence of 1.5s or longer"))
    dur = run_cmd(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,start_time,duration", "-of", "csv=p=0", final]).stdout
    rows = {r.split(",")[0]: r.split(",") for r in dur.strip().splitlines() if r}
    vdur = float(rows["video"][2]) if "video" in rows else None
    adur = float(rows["audio"][2]) if "audio" in rows else None
    offset = abs(float(rows["video"][1]) - float(rows["audio"][1])) if vdur is not None and adur is not None else None
    ok = vdur is not None and adur is not None and abs(vdur - adur) <= 0.08 and offset <= 0.04
    checks.append(_c("av_stream_alignment", ok, f"video {vdur}s vs audio {adur}s, start offset {offset}s. Picture and sound are cut from identical "
                     "intervals; true lip-sync is not measured"))
    checks.append(_c("captions_layout", not caption_problems, "; ".join(caption_problems) or "all caption groups fit two lines inside the safe area"))
    checks.append(_c("overlays_safe_area", not overlay_problems, "; ".join(overlay_problems) or "all overlays inside the safe area"))
    checks += overlay_claims(plan, factcheck)
    checks += licences(plan, music)
    if script_text:
        wav = asr.extract_audio(final, work / "qc_final16k.wav")
        t = asr.transcribe(wav)
        res = alignmod.align(script_text, t, config.settings()["editing"]["match_threshold"], config.settings()["editing"]["weak_match"])
        sents = res["sentences"]
        found = [s for s in sents if s["found"]]
        checks.append(_c("speech_matches_script", len(found) == len(sents),
                         f"{len(found)}/{len(sents)} script sentences heard in the final audio; missing {res['missing']}"))
        checks.append(_c("ending_present", sents[-1]["found"], f"last sentence match {sents[-1]['score']}"))
        dup = [r["heard"] for r in res["removed"] if r["kind"] in ("repeated_take", "false_start") and r.get("score", 0) >= 0.8]
        checks.append(_c("no_duplicated_segments", not dup, f"possible repeats: {dup}" if dup else "each sentence heard once"))
        order = [s["start"] for s in found]
        checks.append(_c("sentence_order", order == sorted(order), "sentences are in script order"))
        mean = sum(s["score"] for s in found) / max(len(found), 1)
        checks.append(_c("voice_understandable", mean >= 0.7, f"mean recogniser match to script {mean:.2f} "
                         "(proxy for intelligibility; a person should still listen once)", warn=True))
    if weak_sentences:
        checks.append(_c("caption_confidence", False, f"sentences {weak_sentences} matched the script weakly; "
                         "captions there use script wording and need a human check", warn=True))
    if missing:
        checks.append(_c("script_complete_in_recording", False, f"script sentences {missing} were not found in the recording"))
    return {"file": str(final), "passed": all(c["status"] != "FAIL" for c in checks),
            "needs_human": [c for c in checks if c["status"] == "WARN"], "checks": checks}


def to_markdown(rep: dict) -> str:
    lines = [f"# QC report: {Path(rep['file']).name}", "", f"**Result: {'PASS' if rep['passed'] else 'FAIL'}**", "",
             "| Check | Status | Detail |", "|---|---|---|"]
    lines += [f"| {c['check']} | {c['status']} | {c['detail']} |" for c in rep["checks"]]
    return "\n".join(lines) + "\n"
