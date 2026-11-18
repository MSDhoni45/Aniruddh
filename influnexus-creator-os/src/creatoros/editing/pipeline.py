"""Raw footage -> finished reel. Steps are cached in a work directory so a failed run can resume."""
from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .. import config
from ..audio import chain
from ..graphics import overlays as gfx
from ..qc import checks as qc
from ..rendering.render import render
from ..subtitles import captions
from ..transcription import asr
from ..util import logger, read_json, write_json
from . import align as alignmod
from . import cuts, framing
from .probe import probe

log = logger("edit")
PLATFORMS = ["instagram", "linkedin", "x", "youtube"]


def _fingerprint(*paths: Path) -> str:
    h = hashlib.sha256()
    for p in paths:
        if p and Path(p).exists():
            st = Path(p).stat()
            h.update(f"{p}:{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()[:16]


def edit(raw: Path, date: str, script: Path | None = None, plan_path: Path | None = None,
         factcheck_path: Path | None = None, force: bool = False) -> dict:
    cfg = config.settings()
    raw = Path(raw).resolve()
    script = script or config.path("scripts", f"{date}_script.txt")
    plan_path = plan_path or config.path("scripts", f"{date}_edit_plan.json")
    factcheck_path = factcheck_path or config.path("scripts", f"{date}_factcheck.json")
    script_text = script.read_text(encoding="utf-8") if script.exists() else None
    plan = read_json(plan_path) if plan_path.exists() else {"overlays": []}
    factcheck = read_json(factcheck_path) if factcheck_path.exists() else None

    work = config.path("renders", date)
    work.mkdir(parents=True, exist_ok=True)
    state_file = work / "state.json"
    fp = _fingerprint(raw, script, plan_path)
    state = read_json(state_file) if state_file.exists() and not force else {}
    if state.get("fingerprint") != fp:
        state = {"fingerprint": fp, "raw": str(raw), "steps": {}}

    def step(name, fn, outputs: list[Path] = ()):  # run once; reuse on resume
        if name in state["steps"] and all(Path(o).exists() for o in outputs):
            log.info("step %s: cached", name)
            return state["steps"][name]
        log.info("step %s: running", name)
        result = fn()
        state["steps"][name] = result
        write_json(state_file, state)
        return result

    # 1. inspect
    info = step("probe", lambda: probe(raw))
    # 2. transcribe
    wav = work / "audio16k.wav"
    tr_file = work / "transcript.json"

    def do_transcribe():
        asr.extract_audio(raw, wav)
        t = asr.transcribe(wav)
        write_json(tr_file, t.to_dict())
        return {"backend": t.backend, "vad": t.vad, "words": len(t.words), "segments": len(t.segments)}
    step("transcribe", do_transcribe, [tr_file])
    t = asr.Transcript.from_dict(read_json(tr_file))
    if not t.words:
        raise RuntimeError("no speech found in the recording")

    # 3-4. compare with script, choose takes
    ed = cfg["editing"]
    if script_text:
        al = alignmod.align(script_text, t, ed["match_threshold"], ed["weak_match"])
    else:                                   # no approved script: keep everything spoken, caption from the recogniser
        sents = [{"index": i, "script": s["text"], "found": True, "score": 0.0, "weak": True, "takes_heard": 1,
                  "heard": s["text"], "start": s["start"], "end": s["end"]} for i, s in enumerate(t.segments) if s["text"]]
        takes, wi = [], 0
        for i, s in enumerate(t.segments):
            idx = [k for k, w in enumerate(t.words) if w.seg == i]
            if s["text"] and idx:
                takes.append({"sentence": len(takes), "w0": idx[0], "w1": idx[-1], "score": 0.0, "start": s["start"], "end": s["end"]})
        al = {"sentences": sents, "takes": takes, "removed": [], "long_pauses": [], "missing": [], "weak": list(range(len(sents))),
              "attempts_at_opening": 1, "word_timing": "approximate"}
    write_json(work / "alignment.json", al)

    # 5. cut list
    fps = cfg["export"]["fps"]
    intervals, shift = cuts.build(t, al["takes"], ed, fps)
    if not intervals:
        raise RuntimeError("nothing usable matched the script; check the script file or the recording")
    total = round(intervals[-1].out + (intervals[-1].end - intervals[-1].start), 3)
    words = cuts.script_word_times(al["sentences"], al["takes"], t, shift)
    sent_times = cuts.sentence_times(words)

    # 8. sound
    aud = cfg["audio"]
    voice_cut, voice, mix = work / "voice_cut.wav", work / "voice.wav", work / "mix.wav"
    chain.cut_and_clean(raw, intervals, voice_cut, aud)
    norm = chain.normalize(voice_cut, voice, aud["target_lufs"], aud["true_peak_db"])
    music_cfg = aud.get("music", {})
    use_music = plan.get("music", music_cfg.get("enabled", False))
    music = music_cfg.get("file") if use_music else None
    if music and not config.path(music).exists():
        log.warning("music file %s missing; rendering without music", music)
        music = None
    sfx = [{**s, "file": str(config.path(s["file"])), "at": gfx.resolve_time(s["at"], sent_times, total)} for s in plan.get("sfx", [])]
    chain.mix(voice, mix, config.path(music) if music else None, music_cfg.get("gain_db", -27), sfx, aud["true_peak_db"])

    # 6. subtitles
    groups = captions.group(words)
    ass = captions.write_ass(groups, work / "captions.ass", plan.get("emphasis"))
    srt = captions.write_srt(groups, config.path("subtitles", f"{date}.srt"))
    caption_problems = captions.check_layout(groups)

    # 7. visuals
    rendered = []
    for i, ov in enumerate(plan.get("overlays", [])):
        try:
            a = gfx.resolve_time(ov.get("from", 0), sent_times, total)
            b = gfx.resolve_time(ov.get("to", total), sent_times, total)
        except KeyError as exc:
            log.warning("overlay %s skipped: %s", ov.get("id", i), exc)
            continue
        if b - a < 0.3:
            continue
        if ov["type"] == "video":
            st = config.style()["safe_area"]
            rect = ov.get("rect", [st["left"], st["top"] + 40, 1080 - st["left"] - st["right"], 495])
            rendered.append({"id": ov.get("id", f"ov{i}"), "video": str(config.path(ov["file"])), "rect": rect, "start": a, "end": b,
                             "box": [rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3]]})
        else:
            r = gfx.render(ov, work / "overlays" / f"{i:02d}_{ov.get('id', ov['type'])}.png")
            rendered.append({"id": ov.get("id", f"ov{i}"), **r, "start": a, "end": b})
    overlay_problems = gfx.check_boxes(rendered)

    # 9. render
    crop_left = 0
    v = info["video"]
    if v["orientation"] != "vertical" or v["width"] / v["height"] > 9 / 16 + 0.01:
        fx = framing.face_center_x(raw) if ed.get("face_crop", True) else None
        crop_left = framing.crop_x(v["width"], v["height"], cfg["export"]["width"], cfg["export"]["height"], fx)
        info["framing"] = {"face_x": fx, "crop_left": crop_left}
    master = work / f"{date}_master.mp4"
    render(raw, mix, intervals, master, info=info, crop_left=crop_left, overlays=rendered, ass=ass, total=total)

    # 10. QC, then publish-ready copies only if it passed
    report = qc.run(master, script_text=script_text, plan=plan, factcheck=factcheck, caption_problems=caption_problems,
                    overlay_problems=overlay_problems, music=music, work=work,
                    weak_sentences=al["weak"] if script_text else [], missing=al["missing"])
    finals = {}
    if report["passed"]:
        for p in PLATFORMS:
            dst = config.path("final", f"{date}_{p}.mp4")
            dst.parent.mkdir(exist_ok=True)
            shutil.copyfile(master, dst)
            finals[p] = str(dst)
    summary = {
        "date": date, "raw": str(raw), "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input": info, "transcription": state["steps"]["transcribe"], "word_timing": al["word_timing"],
        "attempts_at_opening": al["attempts_at_opening"], "removed": al["removed"], "long_pauses": al["long_pauses"],
        "missing_sentences": al["missing"], "weak_sentences": al["weak"] if script_text else "no script supplied",
        "cuts": [{"src_start": round(i.start, 3), "src_end": round(i.end, 3), "out": round(i.out, 3), "zoom": i.zoom} for i in intervals],
        "duration": total, "captions": len(groups), "overlays": [r["id"] for r in rendered], "music": music,
        "voice_before": norm, "subtitles": str(srt), "master": str(master), "final": finals, "qc_passed": report["passed"],
        "status": "COMPLETE" if report["passed"] else "FAILED_QC",
    }
    write_json(work / "edit_report.json", summary)
    write_json(work / "qc_report.json", report)
    (work / "qc_report.md").write_text(qc.to_markdown(report), encoding="utf-8")
    write_json(config.path("footage", "processed", f"{date}.json"), {"raw": str(raw), "status": summary["status"], "master": str(master)})
    return {"summary": summary, "qc": report}
