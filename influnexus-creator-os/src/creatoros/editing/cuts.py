"""Turn chosen takes into keep-intervals and map script words onto the output timeline."""
from __future__ import annotations

from dataclasses import dataclass

from ..transcription.asr import Transcript
from ..transcription.phonetic import key, tokenize


@dataclass
class Interval:
    start: float
    end: float
    out: float = 0.0     # position on the output timeline
    zoom: float = 1.0


def _snap(x: float, fps: int) -> float:
    return round(x * fps) / fps


def build(t: Transcript, takes: list[dict | None], cfg: dict, fps: int = 30) -> tuple[list[Interval], dict[int, float]]:
    """Returns keep-intervals and, for every kept transcript word index, the source->output time shift."""
    kept = sorted({i for c in takes if c for i in range(c["w0"], c["w1"] + 1)})
    if not kept:
        return [], {}
    seg_first, seg_last = {}, {}
    for i, w in enumerate(t.words):
        seg_first.setdefault(w.seg, i)
        seg_last[w.seg] = i
    kept_set = set(kept)

    def w_start(i):
        w = t.words[i]
        return t.segments[w.seg]["start"] if seg_first[w.seg] == i else w.start

    def w_end(i):
        w = t.words[i]
        return t.segments[w.seg]["end"] if seg_last[w.seg] == i else w.end

    groups, cur = [], [kept[0]]
    for a, b in zip(kept, kept[1:]):
        if b == a + 1 and w_start(b) - w_end(a) <= cfg["max_natural_pause"]:
            cur.append(b)
        else:
            groups.append(cur)
            cur = [b]
    groups.append(cur)

    intervals: list[Interval] = []
    shift: dict[int, float] = {}
    out = 0.0
    punched = False
    for gi, g in enumerate(groups):
        s, e = w_start(g[0]) - cfg["pad_before"], w_end(g[-1]) + cfg["pad_after"]
        if g[0] > 0:                                   # never run back into the previous spoken word
            s = max(s, w_end(g[0] - 1) + 0.02)
        if g[-1] + 1 < len(t.words):
            e = min(e, w_start(g[-1] + 1) - 0.02)
        s, e = _snap(max(s, 0.0), fps), _snap(min(e, t.duration), fps)
        if e - s < 2 / fps:
            continue
        # Change framing only across a real jump (half a second or more removed), not every tightened pause.
        if intervals and s - intervals[-1].end >= 0.5:
            punched = not punched
        zoom = cfg.get("punch_in_scale", 1.0) if punched else 1.0
        intervals.append(Interval(s, e, out, zoom))
        for i in g:
            shift[i] = out - s
        out = _snap(out + (e - s), fps)
    return intervals, shift


def script_word_times(sentences: list[dict], takes: list[dict | None], t: Transcript, shift: dict[int, float]) -> list[dict]:
    """Spread each script sentence's words over the time its chosen take was actually spoken."""
    words = []
    for rep, take in zip(sentences, takes):
        if not take:
            continue
        spoken = [(t.words[i].start + shift[i], t.words[i].end + shift[i]) for i in range(take["w0"], take["w1"] + 1) if i in shift]
        if not spoken:
            continue
        total = sum(b - a for a, b in spoken)
        toks = rep["script"].split()
        weights = [max(sum(len(key(x)) for x in tokenize(tok)), 1) + 1 for tok in toks]
        wsum = float(sum(weights))

        def at(frac: float) -> float:
            target, acc = frac * total, 0.0
            for a, b in spoken:
                if acc + (b - a) >= target - 1e-9:
                    return a + (target - acc)
                acc += b - a
            return spoken[-1][1]

        acc = 0.0
        for tok, wgt in zip(toks, weights):
            words.append({"text": tok, "start": round(at(acc / wsum), 3), "end": round(at((acc + wgt) / wsum), 3),
                          "sentence": rep["index"], "weak": rep["weak"]})
            acc += wgt
    return words


def sentence_times(words: list[dict]) -> dict[int, tuple[float, float]]:
    out: dict[int, tuple[float, float]] = {}
    for w in words:
        a, b = out.get(w["sentence"], (w["start"], w["end"]))
        out[w["sentence"]] = (min(a, w["start"]), max(b, w["end"]))
    return out
