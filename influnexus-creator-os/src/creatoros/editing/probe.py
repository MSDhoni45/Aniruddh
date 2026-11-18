"""Inspect a raw recording with ffprobe."""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..util import ffmpeg, run


def probe(src: Path) -> dict:
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", src]).stdout
    info = json.loads(out)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        raise ValueError(f"{src} has no video stream")
    rot = 0
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(round(float(sd["rotation"])))
    w, h = int(v["width"]), int(v["height"])
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    res = {
        "file": str(src), "container": info["format"].get("format_name"), "duration": float(info["format"].get("duration", 0)),
        "size_bytes": int(info["format"].get("size", 0)),
        "video": {"codec": v.get("codec_name"), "profile": v.get("profile"), "stored_width": int(v["width"]),
                  "stored_height": int(v["height"]), "rotation": rot, "width": w, "height": h, "fps": round(fps, 3),
                  "pix_fmt": v.get("pix_fmt"), "color_transfer": v.get("color_transfer"), "color_primaries": v.get("color_primaries"),
                  "orientation": "vertical" if h > w else "horizontal" if w > h else "square",
                  "hdr": v.get("color_transfer") in ("arib-std-b67", "smpte2084")},
        "audio": None,
    }
    if a:
        res["audio"] = {"codec": a.get("codec_name"), "sample_rate": int(a.get("sample_rate", 0)), "channels": a.get("channels")}
        res["audio"].update(audio_stats(src))
    return res


def audio_stats(src: Path) -> dict:
    """Peak/mean level, an estimated noise floor and clipping count."""
    err = ffmpeg(["-i", src, "-vn", "-af", "astats=metadata=0:measure_perchannel=none", "-f", "null", "-"]).stderr

    def grab(label):
        m = re.findall(rf"{label}:\s*(-?[\d.]+|-inf)", err)
        return float(m[-1]) if m and m[-1] != "-inf" else None

    peak, rms, floor = grab("Peak level dB"), grab("RMS level dB"), grab("Noise floor dB")
    quality = "good"
    notes = []
    if peak is not None and peak >= -0.1:
        quality, _ = "clipped", notes.append("peaks reach 0 dBFS: likely clipping")
    if rms is not None and rms < -35:
        quality, _ = "quiet", notes.append("very low recording level")
    if floor is not None and rms is not None and rms - floor < 20:
        quality, _ = "noisy", notes.append("small gap between speech level and noise floor")
    return {"peak_db": peak, "rms_db": rms, "noise_floor_db": floor, "quality": quality, "notes": notes}
