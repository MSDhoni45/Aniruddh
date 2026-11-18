"""Original motion-graphics plates drawn with Pillow. Each overlay becomes a full-canvas RGBA PNG."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .. import config

W, H = 1080, 1920


def _rgba(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in range(0, len(h), 2)) + ((255,) if len(h) == 6 else ())


def _font(kind: str, size: int):
    st = config.style()
    return ImageFont.truetype(str(config.path(st["font_dir"], st["fonts"][f"{kind}_file"])), size)


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split():
            trial = (cur + " " + word).strip()
            if draw.textlength(trial, font=font) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def _fit(draw, text: str, kind: str, size: int, max_w: int, max_lines: int):
    while size > 28:
        font = _font(kind, size)
        lines = _wrap(draw, text, font, max_w)
        if len(lines) <= max_lines and all(draw.textlength(l, font=font) <= max_w for l in lines):
            return font, lines
        size -= 4
    font = _font(kind, size)
    return font, _wrap(draw, text, font, max_w)


def _block(draw, lines, font, x, y, fill, spacing=1.18, anchor="la", stroke=0, stroke_fill=None):
    lh = int(font.size * spacing)
    for i, line in enumerate(lines):
        draw.text((x, y + i * lh), line, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)
    return y + len(lines) * lh


def render(ov: dict, dst: Path) -> dict:
    """Draw one overlay. Returns its bounding box so QC can check safe areas."""
    st = config.style()
    col, safe = st["colors"], st["safe_area"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    left, right = safe["left"], W - safe["right"]
    max_w = right - left
    kind = ov["type"]
    box = None
    if kind == "hook_title":
        font, lines = _fit(d, ov["text"].upper() if ov.get("upper", True) else ov["text"], "heading", ov.get("size", 132), max_w, 3)
        y0 = ov.get("y", safe["top"] + 60)
        y1 = _block(d, lines, font, (left + right) // 2,
                    y0, _rgba(col["text"]), anchor="ma", stroke=8, stroke_fill=_rgba(col["outline"]))
        box = (left, y0, right, y1)
    elif kind == "label":
        font = _font("body", ov.get("size", 40))
        text = ov["text"].upper()
        tw = int(d.textlength(text, font=font))
        x0, y0 = left, ov.get("y", safe["top"])
        box = (x0, y0, x0 + tw + 44, y0 + font.size + 28)
        d.rounded_rectangle(box, radius=14, fill=_rgba(col["label_bg"]))
        d.text((x0 + 22, y0 + 14), text, font=font, fill=_rgba(col["label_text"]))
    elif kind in ("stat_card", "split"):
        rows = ov["rows"] if kind == "split" else [{"title": ov["title"], "text": ov.get("text", "")}]
        pad, gap = 36, 22
        y = ov.get("y", safe["top"] + 40)
        top = y
        for row in rows:
            tfont, tlines = _fit(d, row["title"], "heading", ov.get("size", 62), max_w - 2 * pad, 2)
            bfont, blines = (_fit(d, row["text"], "body", 40, max_w - 2 * pad, 3) if row.get("text") else (None, []))
            h = pad * 2 + int(tfont.size * 1.18) * len(tlines) + (int(bfont.size * 1.18) * len(blines) + 10 if blines else 0)
            d.rounded_rectangle((left, y, right, y + h), radius=28, fill=_rgba(col["card_bg"]))
            d.rounded_rectangle((left, y, left + 12, y + h), radius=6, fill=_rgba(row.get("color", col["accent"])))
            yy = _block(d, tlines, tfont, left + pad, y + pad, _rgba(col["card_text"]))
            if blines:
                _block(d, blines, bfont, left + pad, yy + 10, _rgba("#C9CCD3"))
            y += h + gap
        box = (left, top, right, y - gap)
    elif kind == "credit":
        font = _font("body", 30)
        y0 = ov.get("y", H - safe["bottom"] - 50)
        d.text((left, y0), ov["text"], font=font, fill=(255, 255, 255, 215), stroke_width=3, stroke_fill=_rgba(col["outline"]))
        box = (left, y0, left + int(d.textlength(ov["text"], font=font)), y0 + 40)
    elif kind == "image":
        src = Image.open(config.path(ov["file"])).convert("RGBA")
        bw = max_w
        bh = min(int(bw * src.height / src.width), 760)
        src = src.resize((int(bh * src.width / src.height), bh)) if bh < int(bw * src.height / src.width) else src.resize((bw, bh))
        x0, y0 = left + (bw - src.width) // 2, ov.get("y", safe["top"] + 40)
        mask = Image.new("L", src.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, *src.size), radius=28, fill=255)
        d.rounded_rectangle((x0 - 6, y0 - 6, x0 + src.width + 6, y0 + src.height + 6), radius=32, fill=_rgba(col["outline"]))
        img.paste(src, (x0, y0), mask)
        box = (x0, y0, x0 + src.width, y0 + src.height)
        if ov.get("caption"):
            font = _font("body", 30)
            d.text((x0 + 8, y0 + src.height + 14), ov["caption"], font=font, fill=(255, 255, 255, 230), stroke_width=3, stroke_fill=_rgba(col["outline"]))
            box = (x0, y0, x0 + src.width, y0 + src.height + 56)
    else:
        raise ValueError(f"unknown overlay type: {kind}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst)
    return {"box": [int(v) for v in box], "file": str(dst)}


def resolve_time(spec, sentence_times: dict[int, tuple[float, float]], total: float) -> float:
    """A time is either seconds, or {"sentence": n, "edge": "start"|"end", "offset": s}."""
    if isinstance(spec, (int, float)):
        return float(min(max(spec, 0), total))
    idx = spec["sentence"]
    if idx not in sentence_times:
        raise KeyError(f"overlay anchored to sentence {idx}, which is not in the edit")
    a, b = sentence_times[idx]
    return float(min(max((a if spec.get("edge", "start") == "start" else b) + spec.get("offset", 0.0), 0), total))


def check_boxes(rendered: list[dict]) -> list[str]:
    safe = config.style()["safe_area"]
    problems = []
    for r in rendered:
        x0, y0, x1, y1 = r["box"]
        if x0 < safe["left"] - 8 or x1 > W - safe["right"] + 8 or y0 < safe["top"] - 8 or y1 > H - safe["bottom"] + 8:
            problems.append(f"overlay {r['id']} box {r['box']} leaves the Instagram safe area")
    return problems
