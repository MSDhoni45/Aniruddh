"""Speech-to-text with timestamps.

Backends:
  sherpa         Whisper ONNX through sherpa-onnx. Segment-level timing comes from
                 VAD; word times inside a segment are interpolated (approximate).
  faster_whisper True word-level timestamps. Used when the package and a model
                 are available (the model download needs Hugging Face access).
"""
from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import soundfile as sf

from .. import config
from ..util import ffmpeg, logger
from . import vad as vadmod
from .phonetic import key, tokenize

log = logger("asr")


@dataclass
class Word:
    text: str
    start: float
    end: float
    seg: int
    approx: bool = True


@dataclass
class Transcript:
    words: list[Word] = field(default_factory=list)
    segments: list[dict] = field(default_factory=list)   # {start, end, text}
    backend: str = ""
    vad: str = ""
    duration: float = 0.0

    def to_dict(self):
        return {"backend": self.backend, "vad": self.vad, "duration": self.duration,
                "segments": self.segments, "words": [asdict(w) for w in self.words]}

    @classmethod
    def from_dict(cls, d):
        return cls([Word(**w) for w in d["words"]], d["segments"], d["backend"], d["vad"], d["duration"])


def extract_audio(src: Path, dst: Path, sr: int = 16000) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg(["-i", src, "-vn", "-ac", "1", "-ar", sr, "-c:a", "pcm_s16le", dst])
    return dst


def _models_dir() -> Path:
    return Path(config.settings()["models_dir"])


def _spread(text: str, start: float, end: float, seg: int) -> list[Word]:
    toks = tokenize(text)
    if not toks:
        return []
    weights = np.array([max(len(key(t)), 1) + 1 for t in toks], dtype=float)
    edges = start + (end - start) * np.concatenate([[0], np.cumsum(weights) / weights.sum()])
    return [Word(t, float(edges[i]), float(edges[i + 1]), seg, True) for i, t in enumerate(toks)]


def _sherpa(samples, sr, speech, cfg) -> Transcript:
    import sherpa_onnx

    mdir = _models_dir() / cfg["whisper_model"]
    name = cfg["whisper_model"].rsplit("-", 1)[-1]
    enc = mdir / f"{name}-encoder.int8.onnx"
    if not enc.exists():
        raise FileNotFoundError(f"Whisper model not found at {mdir}. Run tools/setup_models.sh")
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(enc), decoder=str(mdir / f"{name}-decoder.int8.onnx"), tokens=str(mdir / f"{name}-tokens.txt"),
        language=cfg.get("whisper_language", "hi"), num_threads=int(cfg.get("threads", 4)))
    t = Transcript(backend=f"sherpa:{cfg['whisper_model']}")
    for i, sp in enumerate(speech):
        a, b = int(max(sp.start - 0.05, 0) * sr), int(min(sp.end + 0.05, len(samples) / sr) * sr)
        chunk = samples[a:b]
        # sherpa-onnx caps decoded tokens by audio length, and Devanagari needs several
        # tokens per character, so short clips get cut off unless padded with silence.
        pad = min(len(chunk) * 2, max(int(29 * sr) - len(chunk), 0))
        chunk = np.concatenate([chunk, np.zeros(pad, dtype=np.float32)])
        stream = rec.create_stream()
        stream.accept_waveform(sr, chunk)
        rec.decode_stream(stream)
        text = stream.result.text.strip()
        t.segments.append({"start": round(sp.start, 3), "end": round(sp.end, 3), "text": text})
        t.words += _spread(text, sp.start, sp.end, i)
    return t


def _faster_whisper(wav: Path, cfg) -> Transcript:
    from faster_whisper import WhisperModel

    model = WhisperModel(cfg.get("faster_whisper_model", "small"), device="auto", compute_type="int8")
    segs, _ = model.transcribe(str(wav), language=cfg.get("whisper_language", "hi"), word_timestamps=True, vad_filter=True)
    t = Transcript(backend="faster_whisper")
    for i, s in enumerate(segs):
        t.segments.append({"start": s.start, "end": s.end, "text": s.text.strip()})
        for w in s.words or []:
            for tok in tokenize(w.word):
                t.words.append(Word(tok, w.start, w.end, i, False))
    return t


def transcribe(wav: Path) -> Transcript:
    cfg = config.settings()["transcription"]
    samples, sr = sf.read(str(wav), dtype="float32")
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    backend = cfg.get("backend", "auto")
    if backend in ("auto", "faster_whisper"):
        try:
            t = _faster_whisper(wav, cfg)
            t.vad, t.duration = "faster_whisper", len(samples) / sr
            return t
        except Exception as exc:
            if backend == "faster_whisper":
                raise
            log.info("faster_whisper unavailable (%s); using sherpa-onnx", type(exc).__name__)
    v = cfg.get("vad", {})
    speech, vad_name = vadmod.detect(samples, sr, _models_dir() / "silero_vad.onnx",
                                     min_silence=v.get("min_silence", 0.25), min_speech=v.get("min_speech", 0.12),
                                     threshold=v.get("threshold", 0.5))
    t = _sherpa(samples, sr, speech, cfg)
    t.vad, t.duration = vad_name, len(samples) / sr
    return t
