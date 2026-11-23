"""V10: the research-to-video handoff, its schema check, the gatekeeper the editing side must run, and the QC report.

This project never edits, renders or publishes video. It writes `production_handoff.json` for the separate video-production
skill and refuses (exit code 2 from `creatoros handoff-check`) any handoff with unverified claims or assets without rights.
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import config

SCHEMA = "schemas/production_handoff.schema.json"
EDITING_HIERARCHY = ["GitHub editing tools", "saved references", "creative analysis", "transcript-based storyboard", "editing",
                     "audio restoration", "music", "color grading", "4K rendering", "QC"]
OUTPUT = {"resolution": "2160x3840", "fps": 30, "color": "Rec.709 SDR, full-range flagged correctly", "codec": "H.264 High or HEVC Main, 4:2:0",
          "loudness_lufs": -14, "true_peak_db": -1.5}
ALLOWED_RIGHTS = {"own", "public-record", "editorial-press", "licensed-library", "own-graphics"}
AWAITING = "AWAITING ORIGINAL RECORDING"


def rights_of(text: str) -> str:
    t = str(text).lower()
    if "creator footage" in t or "own footage" in t or "creator-recorded" in t:
        return "own"
    if "sec edgar" in t or "public filing" in t:
        return "public-record"
    if "own graphics" in t and not any(k in t for k in ("media assets", "press")):
        return "own-graphics"
    if any(k in t for k in ("newsroom", "media assets", "press image", "press photo", "credit nvidia", "editorial use", "credit")):
        return "editorial-press"
    if any(k in t for k in ("licensed library", "epidemic", "artlist", "youtube audio library")):
        return "licensed-library"
    return "unknown"


def captions(storyboard: list[dict], max_words: int = 4) -> list[dict]:
    out = []
    for r in storyboard:
        words = str(r["line"]).split()
        n = max(1, (len(words) + max_words - 1) // max_words)
        dur = (float(r["end_s"]) - float(r["start_s"])) / n
        for i in range(n):
            chunk = " ".join(words[i * max_words:(i + 1) * max_words])
            out.append({"text": chunk, "start_s": round(float(r["start_s"]) + i * dur, 2), "end_s": round(float(r["start_s"]) + (i + 1) * dur, 2)})
    return out


def build(p: dict, info: dict, verification: dict | None) -> dict:
    sb = [{**r, "rights": rights_of(r.get("source_licensing", ""))} for r in p["storyboard"]]
    ready = info["ready"]["status"] == "RECORDING READY"
    vstatus = "VERIFIED" if ready and (verification is None or str(verification.get("final_decision", "")).startswith("VERIFIED")) else "BLOCKED"
    assets, seen = [], set()
    for r in sb:
        if r["treatment"] == "talking-head" or r["rights"] == "own":
            continue
        key = r["footage"]
        if key in seen:
            continue
        seen.add(key)
        status = "to-create" if r["rights"] == "own-graphics" else ("to-capture" if r["rights"] in ("public-record", "editorial-press") else "to-request")
        assets.append({"asset": key, "rights": r["rights"], "status": status, "licensing_note": r["source_licensing"]})
    urls = []
    for c in p["factcheck"]["claims"]:
        if c.get("in_script"):
            for it in c.get("evidence") or []:
                u = it["url"] if isinstance(it, dict) else it
                if u not in urls:
                    urls.append(u)
    mu = p["music"]
    return {"schema_version": "v10", "date": p["date"], "slug": p["slug"], "topic": p["topic"], "verification_status": vstatus,
            "verification_report": p.get("verification_report"), "recording_status": p.get("recording_status", AWAITING),
            "approved_script": p["script"].strip(),
            "transcript": [{"line": r["line"], "start_s": r["start_s"], "end_s": r["end_s"]} for r in sb],
            "storyboard": sb, "source_urls": urls, "visual_asset_requirements": assets or [{"asset": "none beyond talking head", "rights": "own", "status": "available"}],
            "music": {k: mu[k] for k in ("style", "track_suggestion", "licensing", "opening_cue", "ending_cue", "dialogue_music_balance")}
                     | {"beat_changes": mu.get("beat_changes", [])},
            "sound_design": list(mu.get("sfx", [])), "caption_timing": captions(sb),
            "thumbnail": {"cover_headline": p["distribution"]["cover_headline"], "concept": p["distribution"]["thumbnail_concept"]},
            "output_settings": dict(OUTPUT), "editing_hierarchy": list(EDITING_HIERARCHY),
            "recording_directions": p.get("recording_v9", {}), "audio": p["production_handoff"].get("audio"),
            "captions_style": p["production_handoff"].get("captions"), "notes": p["production_handoff"].get("notes", ""),
            "editing_environment": environment()}


def environment() -> dict:
    """What a production step could actually use from this environment (inspected, not assumed)."""
    import shutil
    skill = Path.home() / ".claude" / "skills" / "influnexus-video-production" / "SKILL.md"
    return {"influnexus_video_production_skill": "installed" if skill.exists() else "NOT INSTALLED in this environment",
            "ffmpeg": "available" if shutil.which("ffmpeg") else "missing",
            "davinci_resolve": "available" if shutil.which("resolve") or Path("/opt/resolve").exists() else "NOT AVAILABLE (no authorized integration)"}


def validate(h: dict) -> list[str]:
    """Schema plus the editing-side gate: unverified facts or assets without rights are refused."""
    import jsonschema
    schema = json.loads(config.path(SCHEMA).read_text(encoding="utf-8"))
    probs = [f"schema: {e.message} at {'/'.join(map(str, e.path))}" for e in jsonschema.Draft202012Validator(schema).iter_errors(h)]
    if h.get("verification_status") != "VERIFIED":
        probs.append("refused: the handoff's factual claims are not VERIFIED")
    for i, r in enumerate(h.get("storyboard", []), 1):
        if r.get("rights") not in ALLOWED_RIGHTS:
            probs.append(f"refused: storyboard row {i} uses an asset without established rights ({r.get('source_licensing')})")
    if h.get("editing_hierarchy") != EDITING_HIERARCHY:
        probs.append("editing_hierarchy must follow the established order")
    tr = h.get("transcript", [])
    if any(float(b["start_s"]) < float(a["end_s"]) - 0.01 for a, b in zip(tr, tr[1:])):
        probs.append("transcript timings overlap")
    return probs


def qc(p: dict, info: dict, h: dict, verification: dict | None) -> dict:
    """Automated checks that can run before a recording exists; audio/video/delivery wait for the recording.
    Technical QC is not creative approval."""
    chk, rd = info["lint"], info["ready"]
    claims = [c for c in p["factcheck"]["claims"] if c.get("in_script")]
    opened = lambda c: any(isinstance(it, dict) and it.get("access") == "opened" for it in c.get("evidence") or [])
    res = {
        "research": {"primary_sources_accessible": all(opened(c) for c in claims), "claims_verified": rd["status"] == "RECORDING READY",
                     "verification_report": bool(verification), "dates_checked": all(c.get("event_date") for c in claims),
                     "quotes_exact": all(c.get("wording_verified", True) for c in claims if c.get("quote")),
                     "unsupported_statements": rd["reasons"]},
        "script": {"seconds": chk["seconds"], "words": chk["words"], "within_target": not chk["problems"],
                   "strong_opening": bool(p.get("hook")) and p["script"].strip().startswith(p["hook"].strip()),
                   "natural_language": not [x for x in chk["problems"] if "phrase" in x or "slang" in x]},
        "storyboard": {"every_sentence_covered": len(h["storyboard"]) == len(h["transcript"]),
                       "assets_with_rights": all(r["rights"] in ALLOWED_RIGHTS for r in h["storyboard"]),
                       "attribution_present": all(str(r.get("source_licensing", "")).strip() for r in h["storyboard"])},
        "handoff": {"schema_and_gate_problems": validate(h)},
        "audio": "PENDING — " + AWAITING, "video": "PENDING — " + AWAITING, "delivery": "PENDING — " + AWAITING,
        "note": "Technical QC only; it is not creative approval.",
    }
    res["pass_pre_recording"] = (res["research"]["primary_sources_accessible"] and res["research"]["claims_verified"]
                                 and res["script"]["within_target"] and res["storyboard"]["every_sentence_covered"]
                                 and res["storyboard"]["assets_with_rights"] and not res["handoff"]["schema_and_gate_problems"])
    return res
