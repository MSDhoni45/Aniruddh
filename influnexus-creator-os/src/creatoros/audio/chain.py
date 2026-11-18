"""Voice-first audio post: cut, clean, level, optional ducked music, limit."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf

from ..util import ffmpeg


def cut_and_clean(src: Path, intervals, dst: Path, cfg: dict) -> Path:
    """Cut the kept intervals (8 ms fades at each edit to avoid clicks) and apply gentle voice cleanup."""
    n = len(intervals)
    parts = [f"[0:a]aresample=48000,aformat=channel_layouts=mono,asplit={n}" + "".join(f"[s{i}]" for i in range(n))]
    for i, iv in enumerate(intervals):
        dur = iv.end - iv.start
        parts.append(f"[s{i}]atrim=start={iv.start:.5f}:end={iv.end:.5f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.008,afade=t=out:st={max(dur - 0.008, 0):.5f}:d=0.008[a{i}]")
    chain = [f"highpass=f={cfg['highpass_hz']}"]
    if cfg.get("denoise_db", 0) > 0:
        chain.append(f"afftdn=nr={cfg['denoise_db']}:nf=-45:tn=1")
    if cfg.get("presence_db", 0):
        chain.append(f"equalizer=f=3500:t=q:w=1.2:g={cfg['presence_db']}")
    chain.append(f"acompressor=threshold=-20dB:ratio={cfg['compressor_ratio']}:attack=15:release=180:makeup=1")
    parts.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1," + ",".join(chain) + "[out]")
    dst.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg(["-i", src, "-filter_complex", ";".join(parts), "-map", "[out]", "-c:a", "pcm_s24le", dst])
    return dst


def normalize(src: Path, dst: Path, target_lufs: float, true_peak: float) -> dict:
    """Two-pass EBU R128 normalisation followed by a peak limiter."""
    base = f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11"
    err = ffmpeg(["-i", src, "-af", base + ":print_format=json", "-f", "null", "-"]).stderr
    m = json.loads(err[err.rindex("{"): err.rindex("}") + 1])
    second = (f"{base}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
              f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    limit = 10 ** ((true_peak - 0.5) / 20)      # sample-peak ceiling a little under the true-peak target
    tmp = dst.with_name(dst.stem + "_pass.wav")
    ffmpeg(["-i", src, "-af", f"{second},aresample=48000", "-ac", "2", "-c:a", "pcm_s24le", tmp])
    # loudnorm undershoots when peaks would exceed the ceiling, so trim the remaining gap and limit.
    gain = 0.0
    for _ in range(3):
        ffmpeg(["-i", tmp, "-af", f"volume={gain:.2f}dB,alimiter=limit={limit:.4f}:level=disabled:attack=3:release=60",
                "-c:a", "pcm_s24le", dst])
        got = measure(dst)["integrated_lufs"]
        if got is None or abs(got - target_lufs) <= 0.4:
            break
        gain += target_lufs - got
    tmp.unlink(missing_ok=True)
    out = measure(dst)
    return {"input_lufs": float(m["input_i"]), "input_true_peak": float(m["input_tp"]),
            "output_lufs": out["integrated_lufs"], "output_true_peak": out["true_peak_db"]}


def mix(voice: Path, dst: Path, music: Path | None = None, music_gain_db: float = -27, sfx: list[dict] | None = None,
        true_peak: float = -1.5) -> Path:
    """Add music ducked under the voice and any placed sound effects. Voice level is left untouched."""
    sfx = sfx or []
    if not music and not sfx:
        ffmpeg(["-i", voice, "-c:a", "pcm_s24le", dst])
        return dst
    dur = sf.info(str(voice)).duration
    args, parts, mixin = ["-i", voice], ["[0:a]asplit=2[v][key]"], ["[v]"]
    idx = 1
    if music:
        args += ["-stream_loop", "-1", "-i", music]
        parts.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{dur:.3f},volume={music_gain_db}dB,"
                     f"afade=t=in:d=0.6,afade=t=out:st={max(dur - 1.2, 0):.3f}:d=1.2[m0];"
                     f"[m0][key]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=350[m]")
        mixin.append("[m]")
        idx += 1
    else:
        parts.append("[key]anullsink")
    for k, fx in enumerate(sfx):
        args += ["-i", fx["file"]]
        ms = int(fx["at"] * 1000)
        parts.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,volume={fx.get('gain_db', -14)}dB,adelay={ms}|{ms}[x{k}]")
        mixin.append(f"[x{k}]")
        idx += 1
    limit = 10 ** ((true_peak - 0.5) / 20)
    parts.append("".join(mixin) + f"amix=inputs={len(mixin)}:normalize=0:duration=first,alimiter=limit={limit:.4f}:level=disabled[out]")
    ffmpeg([*args, "-filter_complex", ";".join(parts), "-map", "[out]", "-t", f"{dur:.3f}", "-c:a", "pcm_s24le", dst])
    return dst


def measure(src: Path) -> dict:
    err = ffmpeg(["-i", src, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    tail = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s*(-?[\d.]+) LUFS", tail)
    tp = re.search(r"Peak:\s*(-?[\d.]+) dBFS", tail)
    lra = re.search(r"LRA:\s*(-?[\d.]+) LU", tail)
    return {"integrated_lufs": float(i.group(1)) if i else None, "true_peak_db": float(tp.group(1)) if tp else None,
            "lra": float(lra.group(1)) if lra else None}


def generate_pad(dst: Path, seconds: float = 48.0, sr: int = 48000, seed: int = 11) -> Path:
    """Synthesise an original, royalty-free ambient bed (slow chord pad). No samples or third-party audio."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * sr)) / sr
    chords = [(110.0, 164.81, 220.0, 277.18), (98.0, 146.83, 196.0, 246.94), (87.31, 130.81, 174.61, 220.0), (98.0, 146.83, 196.0, 293.66)]
    bar = seconds / 8
    out = np.zeros((len(t), 2))
    for k in range(8):
        env = np.clip(1 - np.abs((t - (k + 0.5) * bar) / (bar * 0.75)), 0, 1) ** 1.5
        for f in chords[k % 4]:
            for ch, det in ((0, 0.997), (1, 1.003)):
                ph = rng.uniform(0, 2 * np.pi)
                out[:, ch] += env * (np.sin(2 * np.pi * f * det * t + ph) + 0.3 * np.sin(2 * np.pi * 2 * f * det * t + ph))
    out *= (1 + 0.15 * np.sin(2 * np.pi * 0.2 * t))[:, None]
    out = out / np.max(np.abs(out)) * 0.5
    dst.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(dst), out.astype(np.float32), sr, subtype="PCM_16")
    return dst
