from __future__ import annotations

from pathlib import Path

from PIL import ImageDraw, ImageFont

_FONT_CACHE: dict[tuple[int, bool, bool], ImageFont.ImageFont] = {}


def load_font(size: int, bold: bool = False, *, cjk: bool = False) -> ImageFont.ImageFont:
    """Load a TrueType font; prefer UI fonts, fall back to Microsoft YaHei for CJK coverage.

    Large sizes and Chinese glyphs previously fell through to Pillow's tiny default bitmap
    font — that looked like “missing fonts”. YaHei / SimHei are tried as reliable fallbacks.
    """
    key = (max(8, int(size)), bool(bold), bool(cjk))
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached

    windir = Path(r"C:\Windows\Fonts")
    # (filename, ttc_index)
    if cjk or bold:
        # Bold path still includes CJK-capable faces so mixed strings render.
        candidates: list[tuple[str, int]] = [
            ("msyhbd.ttc", 0),
            ("msyh.ttc", 0),
            ("seguibl.ttf", 0),
            ("arialbd.ttf", 0),
            ("bahnschrift.ttf", 0),
            ("simhei.ttf", 0),
            ("simsun.ttc", 0),
            ("consolab.ttf", 0),
        ]
    else:
        candidates = [
            ("msyh.ttc", 0),
            ("segoeui.ttf", 0),
            ("arial.ttf", 0),
            ("bahnschrift.ttf", 0),
            ("simhei.ttf", 0),
            ("simsun.ttc", 0),
            ("consola.ttf", 0),
        ]
    if cjk:
        # Prefer CJK faces first when explicitly requested.
        candidates = [
            ("msyhbd.ttc", 0) if bold else ("msyh.ttc", 0),
            ("msyh.ttc", 0),
            ("msyhbd.ttc", 0),
            ("simhei.ttf", 0),
            ("simsun.ttc", 0),
            ("seguibl.ttf", 0) if bold else ("segoeui.ttf", 0),
        ] + candidates

    size_n = key[0]
    font: ImageFont.ImageFont | None = None
    for name, index in candidates:
        path = windir / name
        if not path.is_file():
            continue
        try:
            font = ImageFont.truetype(str(path), size=size_n, index=index)
            break
        except OSError:
            # Some .ttc need another face index.
            for alt in (0, 1, 2):
                if alt == index:
                    continue
                try:
                    font = ImageFont.truetype(str(path), size=size_n, index=alt)
                    break
                except OSError:
                    continue
            if font is not None:
                break
            continue

    if font is None:
        font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def mix(a: tuple[int, ...], b: tuple[int, ...], t: float) -> tuple[int, ...]:
    t = clamp01(t)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(min(len(a), len(b))))


def text_right(draw: ImageDraw.ImageDraw, xy, text, font, fill) -> None:
    x, y = xy
    bb = draw.textbbox((0, 0), text, font=font)
    draw.text((x - (bb[2] - bb[0]), y), text, font=font, fill=fill)


def fmt_net(kb: float) -> str:
    if kb >= 1024:
        return f"{kb / 1024:.1f} MB/S"
    return f"{kb:.0f} KB/S"


def gauge(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    r: int,
    value: float,
    color,
    track=(50, 55, 60),
    width: int = 14,
) -> None:
    box = (cx - r, cy - r, cx + r, cy + r)
    draw.arc(box, -225, 45, fill=track, width=width)
    draw.arc(box, -225, -225 + int(270 * clamp01(value / 100)), fill=color, width=width)
