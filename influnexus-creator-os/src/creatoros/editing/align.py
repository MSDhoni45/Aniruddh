"""Match what was said against the approved script and choose the best take of each sentence."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from ..transcription.asr import Transcript
from ..transcription.phonetic import key, tokenize

FILLERS = {"um", "uh", "umm", "hmm", "er", "अम", "उम", "हम्म", "अं", "आं"}


@dataclass
class Take:
    sentence: int
    w0: int
    w1: int            # inclusive transcript word indexes
    score: float
    start: float
    end: float


def script_sentences(text: str) -> list[str]:
    """Split a script into spoken sentences; one-word fragments join the sentence that follows."""
    parts = [p.strip() for p in re.split(r"(?<=[.?!।])\s+|\n+", text.strip()) if p.strip()]
    out: list[str] = []
    carry = ""
    for p in parts:
        p = (carry + " " + p).strip()
        if len(tokenize(p)) < 2:
            carry = p
            continue
        carry = ""
        out.append(p)
    if carry:
        out.append(carry) if not out else out.__setitem__(-1, out[-1] + " " + carry)
    return out


def _flat(words: list[str]) -> tuple[str, list[int]]:
    s, owner = [], []
    for i, w in enumerate(words):
        k = key(w)
        if k == "_":
            continue
        s.append(k)
        owner += [i] * len(k)
    return "".join(s), owner


def _fit(pattern: str, text: str) -> tuple[list[int], list[int]]:
    """Sellers approximate matching: edit distance of `pattern` ending at each text position, with start positions."""
    n = len(text)
    prev_d, prev_s = [0] * (n + 1), list(range(n + 1))
    for i, pc in enumerate(pattern, 1):
        d, s = [i] + [0] * n, [0] + [0] * n
        for j in range(1, n + 1):
            best, start = prev_d[j - 1] + (pc != text[j - 1]), prev_s[j - 1]
            if prev_d[j] + 1 < best:
                best, start = prev_d[j] + 1, prev_s[j]
            if d[j - 1] + 1 < best:
                best, start = d[j - 1] + 1, s[j - 1]
            d[j], s[j] = best, start
        prev_d, prev_s = d, s
    return prev_d, prev_s


def similarity(a: str, b: str) -> float:
    """Best match of a's phonetic key anywhere inside b's (0..1)."""
    pa, _ = _flat(tokenize(a))
    pb, _ = _flat(tokenize(b))
    if not pa or not pb:
        return 0.0
    d, _ = _fit(pa, pb)
    return max(0.0, 1 - min(d) / len(pa))


def candidates(sentence: str, idx: int, t: Transcript, flat: str, owner: list[int], threshold: float) -> list[Take]:
    pat, _ = _flat(tokenize(sentence))
    if not pat or not flat:
        return []
    d, s = _fit(pat, flat)
    order = sorted(range(1, len(flat) + 1), key=lambda j: (d[j], j))
    found: list[Take] = []
    for j in order:
        score = 1 - d[j] / len(pat)
        if score < threshold:
            break
        a, b = s[j], j
        if b <= a:
            continue
        w0, w1 = _trim_partial_segments(owner[a], owner[b - 1], a, b, owner, t)
        if any(not (w1 < f.w0 or w0 > f.w1) for f in found):
            continue
        found.append(Take(idx, w0, w1, round(score, 3), t.words[w0].start, t.words[w1].end))
    return sorted(found, key=lambda c: c.w0)


def _trim_partial_segments(w0: int, w1: int, a: int, b: int, owner: list[int], t: Transcript) -> tuple[int, int]:
    """A match that only nibbles the edge of a neighbouring voice segment almost always belongs to the
    neighbouring sentence, so drop edge segments of which less than 40% was matched."""
    def seg_chars(seg):
        return sum(1 for o in owner if t.words[o].seg == seg)

    def covered(seg):
        return sum(1 for o in owner[a:b] if t.words[o].seg == seg)

    while t.words[w0].seg != t.words[w1].seg:
        last, first = t.words[w1].seg, t.words[w0].seg
        if covered(last) < 0.4 * seg_chars(last):
            while t.words[w1].seg == last:
                w1 -= 1
        elif covered(first) < 0.4 * seg_chars(first):
            while t.words[w0].seg == first:
                w0 += 1
        else:
            break
    return w0, w1


def _fill_gaps(chosen, sentences: list[str], t: Transcript) -> list[int]:
    """If the recogniser garbled a sentence, it can still be located: unclaimed speech sitting exactly
    between the takes of its neighbours, of about the expected length, is that sentence. Such takes get
    score 0 and are flagged for a human check."""
    def klen(s):
        return max(len(_flat(tokenize(s))[0]), 1)
    done = [c for c in chosen if c and c.end > c.start]
    if not done:
        return []
    rate = sum(klen(sentences[c.sentence]) for c in done) / sum(c.end - c.start for c in done)   # key chars per second
    inferred, i = [], 0
    while i < len(chosen):
        if chosen[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(chosen) and not chosen[j + 1]:
            j += 1
        lo = chosen[i - 1].w1 + 1 if i > 0 else None
        hi = chosen[j + 1].w0 - 1 if j + 1 < len(chosen) else None
        if lo is not None and hi is not None and hi >= lo:
            words = list(range(lo, hi + 1))
            segs = sorted({t.words[w].seg for w in words})
            spoken = sum(t.segments[s]["end"] - t.segments[s]["start"] for s in segs)
            expected = sum(klen(sentences[k]) for k in range(i, j + 1)) / rate
            if 0.6 * expected <= spoken <= 1.6 * expected:
                total = sum(klen(sentences[k]) for k in range(i, j + 1))
                pos, acc = 0, 0
                for k in range(i, j + 1):
                    acc += klen(sentences[k])
                    end = len(words) if k == j else max(pos + 1, round(len(words) * acc / total))
                    end = min(end, len(words) - (j - k))
                    chunk = words[pos:end]
                    if chunk:
                        chosen[k] = Take(k, chunk[0], chunk[-1], 0.0, t.words[chunk[0]].start, t.words[chunk[-1]].end)
                        inferred.append(k)
                    pos = end
        i = j + 1
    return inferred


def choose(all_cands: list[list[Take]]) -> list[Take | None]:
    """Pick one take per sentence so that takes stay in spoken order. Later takes win near-ties."""
    nodes = []
    for cands in all_cands:
        for r, c in enumerate(cands):
            nodes.append((c, c.score + 0.04 * (r / max(len(cands) - 1, 1) if len(cands) > 1 else 0)))
    nodes.sort(key=lambda n: (n[0].sentence, n[0].w0))
    best = [0.0] * len(nodes)
    back = [-1] * len(nodes)
    for i, (c, val) in enumerate(nodes):
        best[i] = val - 0.5 * c.sentence
        for k in range(i):
            p = nodes[k][0]
            if p.sentence < c.sentence and p.w1 < c.w0:
                v = best[k] + val - 0.5 * (c.sentence - p.sentence - 1)
                if v > best[i]:
                    best[i], back[i] = v, k
    chosen: list[Take | None] = [None] * len(all_cands)
    if nodes:
        n_sent = len(all_cands)
        i = max(range(len(nodes)), key=lambda i: best[i] - 0.5 * (n_sent - 1 - nodes[i][0].sentence))
        while i >= 0:
            chosen[nodes[i][0].sentence] = nodes[i][0]
            i = back[i]
    return chosen


def align(script_text: str, t: Transcript, threshold: float = 0.55, weak: float = 0.72) -> dict:
    sentences = script_sentences(script_text)
    flat, owner = _flat([w.text for w in t.words])
    cands = [candidates(s, i, t, flat, owner, threshold) for i, s in enumerate(sentences)]
    chosen = choose(cands)
    _snap_to_segments(chosen, t)
    inferred = _fill_gaps(chosen, sentences, t)
    kept = set()
    for c in chosen:
        if c:
            kept.update(range(c.w0, c.w1 + 1))
    removed, run = [], []
    for i in range(len(t.words) + 1):
        if i < len(t.words) and i not in kept:
            run.append(i)
            continue
        if run:
            removed.append(_classify(run, t, sentences, chosen))
            run = []
    pauses = []
    for a, b in zip(t.segments, t.segments[1:]):
        if b["start"] - a["end"] >= 1.0:
            pauses.append({"start": a["end"], "end": b["start"], "seconds": round(b["start"] - a["end"], 2)})
    report = []
    for i, s in enumerate(sentences):
        c = chosen[i]
        report.append({"index": i, "script": s, "found": bool(c), "score": c.score if c else 0.0,
                       "weak": bool(c) and c.score < weak, "inferred": i in inferred, "takes_heard": len(cands[i]),
                       "heard": " ".join(w.text for w in t.words[c.w0:c.w1 + 1]) if c else "",
                       "start": c.start if c else None, "end": c.end if c else None})
    first = cands[0] if cands else []
    starts = len(first) + sum(1 for r in removed if r["kind"] == "false_start" and r.get("sentence") == 0
                              and not any(c.start < r["end"] and c.end > r["start"] for c in first))
    return {"sentences": report, "takes": [asdict(c) if c else None for c in chosen], "removed": removed,
            "long_pauses": pauses, "missing": [r["index"] for r in report if not r["found"]],
            "weak": [r["index"] for r in report if r["weak"]], "inferred": inferred, "attempts_at_opening": starts,
            "word_timing": "approximate" if any(w.approx for w in t.words) else "word-level"}


def _snap_to_segments(chosen, t: Transcript) -> None:
    """With interpolated word times a cut inside a phrase is a guess, so a take grows to the
    edge of its voice segment whenever no other chosen take owns the words in between."""
    if not any(w.approx for w in t.words):
        return
    taken = {i for c in chosen if c for i in range(c.w0, c.w1 + 1)}
    for c in chosen:
        if not c:
            continue
        while c.w0 > 0 and t.words[c.w0 - 1].seg == t.words[c.w0].seg and (c.w0 - 1) not in taken:
            c.w0 -= 1
            taken.add(c.w0)
        while c.w1 + 1 < len(t.words) and t.words[c.w1 + 1].seg == t.words[c.w1].seg and (c.w1 + 1) not in taken:
            c.w1 += 1
            taken.add(c.w1)
        c.start, c.end = t.words[c.w0].start, t.words[c.w1].end


def _classify(run: list[int], t: Transcript, sentences: list[str], chosen) -> dict:
    words = [t.words[i] for i in run]
    text = " ".join(w.text for w in words)
    item = {"start": words[0].start, "end": words[-1].end, "heard": text}
    if all(w.text.lower() in FILLERS for w in words):
        return {**item, "kind": "filler"}
    scores = [(similarity(text, s), i) for i, s in enumerate(sentences)]
    score, idx = max(scores) if scores else (0, -1)
    if score >= 0.6:
        n_run, n_sent = len(_flat([w.text for w in words])[0]), len(_flat(tokenize(sentences[idx]))[0])
        kind = "false_start" if n_run < 0.75 * n_sent else "repeated_take"
        return {**item, "kind": kind, "sentence": idx, "score": round(score, 2)}
    return {**item, "kind": "off_script"}
