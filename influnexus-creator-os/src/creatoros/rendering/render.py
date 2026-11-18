"""One-pass video render: cut, reframe, overlays and captions, muxed with the finished audio."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ..util import ffmpeg

HDR_TO_SDR = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
              "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")


def _esc(p: Path) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def render(src: Path, audio: Path, intervals, dst: Path, *, info: dict, crop_left: int, overlays: list[dict],
           ass: Path | None, total: float) -> Path:
    ex = config.settings()["export"]
    W, H, fps = ex["width"], ex["height"], ex["fps"]
    n = len(intervals)
    hdr = HDR_TO_SDR if info["video"].get("hdr") else ""
    parts = [f"[0:v]{hdr}fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,"
             f"crop={W}:{H}:{crop_left}:(ih-{H})/2,setsar=1,format=yuv420p,split={n}" + "".join(f"[s{i}]" for i in range(n))]
    for i, iv in enumerate(intervals):
        zoom = ""
        if iv.zoom and abs(iv.zoom - 1) > 1e-3:
            zoom = (f",scale=trunc(iw*{iv.zoom}/2)*2:trunc(ih*{iv.zoom}/2)*2,"
                    f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*0.38,setsar=1")
        parts.append(f"[s{i}]trim=start={iv.start:.5f}:end={iv.end:.5f},setpts=PTS-STARTPTS{zoom}[v{i}]")
    parts.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[base0]")
    args = ["-i", src, "-i", audio]
    last, idx = "base0", 2
    for k, ov in enumerate(overlays):
        a, b = ov["start"], ov["end"]
        fade = min(0.18, (b - a) / 3)
        if ov.get("video"):
            args += ["-i", ov["video"]]
            x, y, w, h = ov["rect"]
            parts.append(f"[{idx}:v]fps={fps},trim=0:{b - a:.3f},scale={w}:{h}:force_original_aspect_ratio=decrease,"
                         f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setpts=PTS-STARTPTS+{a:.3f}/TB[o{k}]")
            parts.append(f"[{last}][o{k}]overlay={x}:{y}:enable='between(t,{a:.3f},{b:.3f})':eof_action=pass[b{k}]")
        else:
            args += ["-loop", "1", "-framerate", str(fps), "-t", f"{total:.3f}", "-i", ov["file"]]
            parts.append(f"[{idx}:v]format=rgba,fade=t=in:st={a:.3f}:d={fade:.3f}:alpha=1,"
                         f"fade=t=out:st={b - fade:.3f}:d={fade:.3f}:alpha=1[o{k}]")
            parts.append(f"[{last}][o{k}]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[b{k}]")
        last, idx = f"b{k}", idx + 1
    if ass:
        fonts = config.path(config.style()["font_dir"])
        parts.append(f"[{last}]ass='{_esc(ass)}':fontsdir='{_esc(fonts)}'[vout]")
        last = "vout"
    dst.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg([*args, "-filter_complex", ";".join(parts), "-map", f"[{last}]", "-map", "1:a",
            "-t", f"{total:.3f}", "-r", str(fps), "-c:v", "libx264", "-preset", ex["preset"], "-crf", str(ex["crf"]),
            "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-c:a", "aac", "-b:a", ex["audio_bitrate"], "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", "-map_metadata", "-1", "-fflags", "+bitexact", "-threads", "0", dst])
    return dst
