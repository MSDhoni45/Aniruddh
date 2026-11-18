"""Voice activity detection: Silero (via sherpa-onnx) with an energy-based fallback."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Speech:
    start: float
    end: float


def silero(samples: np.ndarray, sr: int, model: Path, min_silence=0.25, min_speech=0.12, threshold=0.5) -> list[Speech]:
    import sherpa_onnx

    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = str(model)
    cfg.silero_vad.min_silence_duration = min_silence
    cfg.silero_vad.min_speech_duration = min_speech
    cfg.silero_vad.threshold = threshold
    cfg.silero_vad.max_speech_duration = 20.0
    cfg.sample_rate = sr
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=600)
    win = cfg.silero_vad.window_size
    out: list[Speech] = []

    def drain():
        while not vad.empty():
            seg = vad.front
            out.append(Speech(seg.start / sr, (seg.start + len(seg.samples)) / sr))
            vad.pop()

    for i in range(0, len(samples) - win + 1, win):
        vad.accept_waveform(samples[i:i + win])
        drain()
    vad.flush()
    drain()
    return out


def energy(samples: np.ndarray, sr: int, min_silence=0.25, min_speech=0.12) -> list[Speech]:
    """Fallback: frames louder than the noise floor by a margin count as speech."""
    hop = int(0.01 * sr)
    n = len(samples) // hop
    if n == 0:
        return []
    rms = np.sqrt(np.mean(samples[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    floor = np.percentile(db, 10)
    active = db > max(floor + 12, -45)
    out, start, gap = [], None, 0
    for i, a in enumerate(active):
        if a:
            start = i if start is None else start
            gap = 0
        elif start is not None:
            gap += 1
            if gap * 0.01 >= min_silence:
                end = i - gap + 1
                if (end - start) * 0.01 >= min_speech:
                    out.append(Speech(start * 0.01, end * 0.01))
                start, gap = None, 0
    if start is not None:
        out.append(Speech(start * 0.01, n * 0.01))
    return out


def detect(samples: np.ndarray, sr: int, model: Path | None, **kw) -> tuple[list[Speech], str]:
    if model and Path(model).exists():
        try:
            return silero(samples, sr, Path(model), **kw), "silero"
        except Exception:  # fall through to the energy detector
            pass
    kw.pop("threshold", None)
    return energy(samples, sr, **kw), "energy"
