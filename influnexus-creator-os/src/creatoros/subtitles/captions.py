"""Caption grouping and ASS/SRT writers."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from .. import config


@lru_cache(maxsize=8)
def _font(file: str, size: int):
    return ImageFont.truetype(str(config.path(config.style()["font_dir"], file)), size)


def text_width(text: str, file: str, size: int) -> float:
    return _font(file, size).getlength(text)


def _best_split(words: list[str], file: str, size: int) -> tuple[list[str], float]:
    """Lay words on one or two lines; returns the lines and the widest line's width."""
    one = " ".join(words)
    best, best_w = [one], text_width(one, file, size)
    if best_w <= config.style()["captions"]["max_line_width"]:
        return best, best_w            # one line whenever it fits
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        w = max(text_width(a, file, size), text_width(b, file, size))
        if w < best_w:
            best, best_w = [a, b], w
    return best, best_w


def group(words: list[dict], style: dict | None = None) -> list[dict]:
    """2-5 words per caption, at most two lines, never crossing a sentence or a long pause."""
    st = (style or config.style())
    cap, file = st["captions"], st["fonts"]["caption_file"]
    groups, cur = [], []

    def fits(ws):
        lines, width = _best_split([w["text"] for w in ws], file, cap["font_size"])
        if width > cap["max_line_width"]:
            for i in range(1, len(ws)):
                a, b = " ".join(w["text"] for w in ws[:i]), " ".join(w["text"] for w in ws[i:])
                if max(text_width(a, file, cap["font_size"]), text_width(b, file, cap["font_size"])) <= cap["max_line_width"]:
                    return True
            return False
        return True

    def flush():
        nonlocal cur
        if cur:
            groups.append(cur)
            cur = []

    for w in words:
        if cur and (w["sentence"] != cur[-1]["sentence"] or w["start"] - cur[-1]["end"] > 0.35
                    or len(cur) >= cap["max_words"] or not fits(cur + [w])):
            flush()
        cur.append(w)
        if re.search(r"[.?!:,]$", w["text"]) and len(cur) >= cap["min_words"]:
            flush()
    flush()
    merged = []
    for g in groups:                      # avoid one-word orphans where a neighbour in the same sentence has room
        if (merged and len(g) < cap["min_words"] and merged[-1][-1]["sentence"] == g[0]["sentence"]
                and len(merged[-1]) + len(g) <= cap["max_words"] and fits(merged[-1] + g)
                and g[0]["start"] - merged[-1][-1]["end"] <= 0.35):
            merged[-1] = merged[-1] + g
        else:
            merged.append(g)
    out = []
    for i, g in enumerate(merged):
        texts = [w["text"] for w in g]
        lines, width = _best_split(texts, file, cap["font_size"])
        if width > cap["max_line_width"]:
            cands = [([" ".join(texts[:k]), " ".join(texts[k:])]) for k in range(1, len(texts))]
            if cands:
                lines = min(cands, key=lambda ls: max(text_width(x, file, cap["font_size"]) for x in ls))
                width = max(text_width(x, file, cap["font_size"]) for x in lines)
        end = g[-1]["end"]
        if i + 1 < len(merged):
            end = min(max(end, g[-1]["end"] + 0.12), merged[i + 1][0]["start"])
        out.append({"start": g[0]["start"], "end": round(end, 3), "lines": lines, "width": round(width, 1),
                    "words": texts, "weak": any(w.get("weak") for w in g), "sentence": g[0]["sentence"]})
    return out


def _ass_color(hex_rgb: str) -> str:
    h = hex_rgb.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def _ts(t: float) -> str:
    cs = int(round(max(t, 0) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def is_emphasis(word: str, emphasis: set[str]) -> bool:
    bare = re.sub(r"[^\w$₹%]", "", word).lower()
    return bare in emphasis or bool(re.search(r"\d", bare))


def write_ass(groups: list[dict], dst: Path, emphasis: list[str] | None = None, canvas=(1080, 1920)) -> Path:
    st = config.style()
    cap, col = st["captions"], st["colors"]
    emph = {e.lower() for e in (emphasis or [])}
    white, accent = _ass_color(col["text"]), _ass_color(col["accent"])
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {canvas[0]}
PlayResY: {canvas[1]}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{st['fonts']['caption']},{cap['font_size']},{white},{white},{_ass_color(col['outline'])},&H80000000,0,0,0,0,100,100,0,0,1,{cap['outline']},{cap['shadow']},5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for g in groups:
        rendered = []
        for line in g["lines"]:
            parts = [(f"{{\\c{accent}}}{w}{{\\c{white}}}" if is_emphasis(w, emph) else w) for w in line.split(" ")]
            rendered.append(" ".join(parts))
        pop = f"{{\\pos({canvas[0] // 2},{cap['center_y']})\\fscx92\\fscy92\\t(0,{cap['pop_ms']},\\fscx100\\fscy100)}}"
        lines.append(f"Dialogue: 0,{_ts(g['start'])},{_ts(g['end'])},Cap,,0,0,0,,{pop}{'\\N'.join(rendered)}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")
    return dst


def write_srt(groups: list[dict], dst: Path) -> Path:
    def ts(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    body = [f"{i}\n{ts(g['start'])} --> {ts(g['end'])}\n" + "\n".join(g["lines"]) + "\n" for i, g in enumerate(groups, 1)]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(body), encoding="utf-8")
    return dst


def check_layout(groups: list[dict], canvas=(1080, 1920)) -> list[str]:
    """Problems that would make captions overflow or sit under platform UI."""
    st = config.style()
    cap, safe = st["captions"], st["safe_area"]
    line_h = cap["font_size"] * 1.25
    problems = []
    for g in groups:
        if len(g["lines"]) > cap["max_lines"]:
            problems.append(f"{g['start']:.2f}s: {len(g['lines'])} lines")
        half = g["width"] / 2 + cap["outline"]
        if canvas[0] / 2 - half < safe["left"] or canvas[0] / 2 + half > canvas[0] - safe["right"]:
            problems.append(f"{g['start']:.2f}s: caption {g['width']:.0f}px wide leaves the safe area: {' '.join(g['words'])}")
        top = cap["center_y"] - line_h * len(g["lines"]) / 2
        bottom = cap["center_y"] + line_h * len(g["lines"]) / 2
        if top < safe["top"] or bottom > canvas[1] - safe["bottom"]:
            problems.append(f"{g['start']:.2f}s: caption outside vertical safe area")
    return problems
