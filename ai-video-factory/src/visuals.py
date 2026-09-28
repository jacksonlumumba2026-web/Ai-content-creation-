"""On-screen graphics ("visual beats") drawn with Pillow, overlaid by the renderer.

Scripts list visuals in front matter; each one appears when its `at` phrase is spoken:

    visuals:
      - at: "Forty-six percent"          # words from the narration (first match after the previous visual)
        type: stat                       # stat | list | compare | icon | text
        value: "46%"
        label: "of small businesses use AI"
        percent: 46                      # optional: draws a ring filled to this percent
      - at: "Number one"
        type: list
        number: 1
        icon: "✍️"
        label: "Writing & marketing"
      - at: "labor costs"
        type: compare
        bars: [{label: "Labor costs", value: 10, note: "no change"},
               {label: "Productivity", value: 85, note: "up"}]
      - at: "competitors"
        type: icon
        icon: "🏁"
        label: "Same team. More output."
      - at: "real question"
        type: text
        label: "Replace your team? Or outwork your competitors?"

A visual stays on screen until the next one starts (max `MAX_SECONDS`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.captions import Word

CARD_W, CARD_H = 940, 640
MAX_SECONDS = 7.0
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
VALID_TYPES = {"stat", "list", "compare", "icon", "text"}


@dataclass
class Beat:
    image: Path
    start: float
    end: float


def _rgb(hex_rgb: str) -> tuple[int, int, int]:
    return tuple(int(hex_rgb[i:i + 2], 16) for i in (0, 2, 4))


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def _emoji(char: str, size: int) -> Image.Image:
    font = ImageFont.truetype(FONT_EMOJI, 109)  # the only size the bitmap font supports
    canvas = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).text((10, 10), char, font=font, embedded_color=True)
    box = canvas.getbbox()
    if not box:
        raise ValueError(f"emoji {char!r} could not be drawn")
    return canvas.crop(box).resize((size, size), Image.LANCZOS)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines: list[str] = []
    for word in text.split():
        if lines and draw.textlength(lines[-1] + " " + word, font=font) <= max_w:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def _centered_lines(draw, lines, font, y, fill, spacing=12) -> int:
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((CARD_W - w) / 2, y), line, font=font, fill=fill)
        y += font.size + spacing
    return y


def _panel(accent: tuple[int, int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, CARD_W - 1, CARD_H - 1), radius=48,
                        fill=(255, 255, 255, 26), outline=(255, 255, 255, 60), width=3)
    d.rounded_rectangle((60, 0, CARD_W - 60, 8), radius=4, fill=accent + (255,))
    return img, d


def draw_stat(spec: dict, accent) -> Image.Image:
    img, d = _panel(accent)
    value = str(spec["value"])
    percent = spec.get("percent")
    if percent is not None:
        cx, cy, r, width = CARD_W // 2, 250, 175, 34
        box = (cx - r, cy - r, cx + r, cy + r)
        d.ellipse(box, outline=(255, 255, 255, 45), width=width)
        d.arc(box, start=-90, end=-90 + 360 * float(percent) / 100, fill=accent + (255,), width=width)
        vf = _font(120)
        w = d.textlength(value, font=vf)
        d.text((cx - w / 2, cy - 72), value, font=vf, fill=(255, 255, 255))
        y = 460
    else:
        vf = _font(190)
        w = d.textlength(value, font=vf)
        d.text(((CARD_W - w) / 2, 90), value, font=vf, fill=accent)
        y = 340
    lf = _font(52)
    _centered_lines(d, _wrap(d, spec.get("label", ""), lf, CARD_W - 120)[:3], lf, y, (255, 255, 255))
    return img


def draw_list(spec: dict, accent) -> Image.Image:
    img, d = _panel(accent)
    cx, cy, r = 200, CARD_H // 2 - 40, 110
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=accent + (255,))
    nf = _font(130)
    num = str(spec.get("number", ""))
    w = d.textlength(num, font=nf)
    d.text((cx - w / 2, cy - 80), num, font=nf, fill=(20, 20, 30))
    if spec.get("icon"):
        img.alpha_composite(_emoji(spec["icon"], 200), (CARD_W - 330, cy - 100))
    lf = _font(64)
    _centered_lines(d, _wrap(d, spec.get("label", ""), lf, CARD_W - 100)[:2], lf, CARD_H - 190, (255, 255, 255))
    return img


def draw_compare(spec: dict, accent) -> Image.Image:
    img, d = _panel(accent)
    bars = spec.get("bars", [])[:3]
    lf, nf = _font(48), _font(40, bold=False)
    max_w, row = CARD_W - 140, 180
    top = (CARD_H - (len(bars) * row - 60)) // 2
    for i, bar in enumerate(bars):
        y = top + i * row
        d.text((70, y), str(bar.get("label", "")), font=lf, fill=(255, 255, 255))
        d.rounded_rectangle((70, y + 70, 70 + max_w, y + 120), radius=25, fill=(255, 255, 255, 40))
        fill_w = max(50, int(max_w * float(bar.get("value", 0)) / 100))
        color = accent if i == len(bars) - 1 else (170, 170, 190)
        d.rounded_rectangle((70, y + 70, 70 + fill_w, y + 120), radius=25, fill=color + (255,))
        if bar.get("note"):
            note = str(bar["note"])
            w = d.textlength(note, font=nf)
            d.text((CARD_W - 70 - w, y + 4), note, font=nf, fill=(230, 230, 240))
    return img


def draw_icon(spec: dict, accent) -> Image.Image:
    img, d = _panel(accent)
    img.alpha_composite(_emoji(spec["icon"], 260), ((CARD_W - 260) // 2, 70))
    lf = _font(60)
    _centered_lines(d, _wrap(d, spec.get("label", ""), lf, CARD_W - 120)[:3], lf, 380, (255, 255, 255))
    return img


def draw_text(spec: dict, accent) -> Image.Image:
    img, d = _panel(accent)
    lf = _font(76)
    lines = _wrap(d, spec.get("label", ""), lf, CARD_W - 140)[:5]
    height = len(lines) * (lf.size + 18)
    _centered_lines(d, lines, lf, (CARD_H - height) // 2, (255, 255, 255), spacing=18)
    return img


DRAWERS = {"stat": draw_stat, "list": draw_list, "compare": draw_compare,
           "icon": draw_icon, "text": draw_text}


def _norm(token: str) -> str:
    return re.sub(r"[^a-z0-9]", "", token.lower())


def find_phrase(words: list[Word], phrase: str, from_index: int) -> int | None:
    target = [t for t in (_norm(x) for x in phrase.split()) if t]
    tokens = [_norm(w.text) for w in words]
    for i in range(from_index, len(words) - len(target) + 1):
        if tokens[i:i + len(target)] == target:
            return i
    return None


def validate(specs: list) -> list[str]:
    problems = []
    for n, spec in enumerate(specs or [], start=1):
        if not isinstance(spec, dict) or spec.get("type") not in VALID_TYPES:
            problems.append(f"visual {n}: type must be one of {sorted(VALID_TYPES)}")
            continue
        if not spec.get("at"):
            problems.append(f"visual {n}: missing 'at' phrase")
        need = {"stat": ["value"], "list": ["number", "label"], "compare": ["bars"],
                "icon": ["icon", "label"], "text": ["label"]}[spec["type"]]
        problems += [f"visual {n}: missing '{k}'" for k in need if not spec.get(k)]
    return problems


def build_beats(specs: list, words: list[Word], accent_hex: str, out_dir: Path,
                duration: float) -> tuple[list[Beat], list[str]]:
    """Render each visual to PNG and time it against the aligned words."""
    problems = validate(specs)
    if problems:
        return [], problems
    accent = _rgb(accent_hex)
    out_dir.mkdir(parents=True, exist_ok=True)
    timed: list[tuple[float, Path]] = []
    cursor = 0
    for n, spec in enumerate(specs or [], start=1):
        idx = find_phrase(words, str(spec["at"]), cursor)
        if idx is None:
            problems.append(f"visual {n}: phrase {spec['at']!r} not found in narration (in order)")
            continue
        cursor = idx + 1
        path = out_dir / f"visual_{n:02d}.png"
        DRAWERS[spec["type"]](spec, accent).save(path)
        timed.append((words[idx].start, path))

    beats = []
    for i, (start, path) in enumerate(timed):
        nxt = timed[i + 1][0] if i + 1 < len(timed) else duration
        beats.append(Beat(path, round(start, 2), round(min(nxt, start + MAX_SECONDS), 2)))
    return beats, problems
