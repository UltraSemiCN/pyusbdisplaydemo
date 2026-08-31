from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, load_font, mix, text_right

_BG = (245, 236, 220)
_SOIL, _MOSS, _CLAY, _SAND, _INK = (
    (92, 64, 51),
    (95, 130, 80),
    (180, 110, 70),
    (220, 200, 160),
    (55, 42, 35),
)
_CREAM = (255, 250, 240)
_LEAF = (220, 235, 200)


class NaturalOrganicPortraitTheme(Theme):
    id = "natural_organic_portrait"
    name = "自然有机风"
    width = 720
    height = 1280
    description = "StyleKit Natural Organic：大地色、温暖纹理感。0°/180° 竖屏；90°/270° 横屏。"

    def canvas_size(self, orient: int = 0) -> tuple[int, int]:
        if normalize_orientation(orient) in (90, 270):
            return 1280, 720
        return 720, 1280

    def render_frame(
        self,
        snap: SysSnapshot,
        now: datetime,
        t: float = 0.0,
        *,
        orient: int = 0,
    ) -> Image.Image:
        if normalize_orientation(orient) in (90, 270):
            return self._render_landscape(snap, now, t)
        return self._render_portrait(snap, now, t)

    def render(self, snap: SysSnapshot, now: datetime, t: float = 0.0) -> Image.Image:
        return self._render_portrait(snap, now, t)

    def _paper(self, w: int, h: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        for y in range(0, h, 3):
            shade = 4 if (y // 3) % 2 == 0 else 0
            d.line(
                [(0, y), (w, y)],
                fill=(_BG[0] - shade, _BG[1] - shade, _BG[2] - shade),
            )
        return img, d

    @staticmethod
    def _leaf_card(d: ImageDraw.ImageDraw, box, fill) -> None:
        d.rounded_rectangle(box, 28, fill=fill)

    @staticmethod
    def _bar(d: ImageDraw.ImageDraw, x, y, ww, pct, fill) -> None:
        d.rounded_rectangle((x, y, x + ww, y + 12), 6, fill=_SAND)
        fw = int(ww * max(0, min(100, pct)) / 100)
        if fw > 3:
            d.rounded_rectangle((x, y, x + fw, y + 12), 6, fill=fill)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img, d = self._paper(w, h)
        f14, f18, f28, f44, f64 = (load_font(n, True) for n in (14, 18, 28, 44, 64))
        leaf = self._leaf_card
        bar = self._bar

        leaf(d, (24, 24, w - 24, 160), _SOIL)
        d.text((48, 48), now.strftime("%H:%M"), font=f64, fill=_BG)
        d.text((48, 120), f"{snap.host[:18]} · {snap.source.upper()}", font=f14, fill=_SAND)
        text_right(d, (w - 48, 60), f"{snap.fps:.0f}", f28, _SAND)

        leaf(d, (24, 184, w - 24, 430), _CREAM)
        d.text((48, 210), "CPU  ·  core warmth", font=f14, fill=_CLAY)
        d.text((48, 250), f"{snap.cpu_usage:.0f}%", font=f64, fill=_INK)
        d.text((280, 270), f"{snap.cpu_temp:.0f}°C", font=f44, fill=_MOSS)
        d.text((48, 340), f"{snap.cpu_clock:.0f} MHz · {snap.cpu_fan:.0f} RPM", font=f18, fill=_SOIL)
        d.text((48, 375), snap.cpu_name[:26], font=f14, fill=_CLAY)
        bar(d, 48, 405, w - 120, snap.cpu_usage, _MOSS)

        leaf(d, (24, 454, w - 24, 700), _MOSS)
        d.text((48, 480), "GPU  ·  green power", font=f14, fill=_LEAF)
        d.text((48, 520), f"{snap.gpu_usage:.0f}%", font=f64, fill=_BG)
        d.text((280, 540), f"{snap.gpu_temp:.0f}°C", font=f44, fill=_SAND)
        d.text((48, 610), f"{snap.gpu_clock:.0f} MHz · {snap.gpu_fan:.0f} RPM", font=f18, fill=_LEAF)
        d.text((48, 645), snap.gpu_name[:24], font=f14, fill=_SAND)
        bar(d, 48, 675, w - 120, snap.gpu_usage, _SAND)

        leaf(d, (24, 724, w - 24, 900), _SAND)
        d.text((48, 750), "MEMORY", font=f14, fill=_SOIL)
        d.text((48, 790), f"{snap.ram_percent:.0f}%", font=f44, fill=_INK)
        d.text(
            (220, 810),
            f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB",
            font=f18,
            fill=_SOIL,
        )
        bar(d, 48, 860, w - 120, snap.ram_percent, _CLAY)

        leaf(d, (24, 924, 348, 1120), _CREAM)
        d.text((48, 950), "STORAGE", font=f14, fill=_CLAY)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 995 + i * 36
            d.text((48, y), str(name)[:8], font=f14, fill=_INK)
            text_right(d, (320, y), f"{pct:.0f}%", f14, mix(_MOSS, _CLAY, pct / 100))

        leaf(d, (372, 924, w - 24, 1120), _CLAY)
        d.text((396, 950), "NETWORK", font=f14, fill=_SAND)
        d.text((396, 1000), f"↑ {fmt_net(snap.net_up_kb)}", font=f18, fill=_CREAM)
        d.text((396, 1045), f"↓ {fmt_net(snap.net_down_kb)}", font=f18, fill=_SAND)
        pts = [(396 + i * 7, 1095 - int(12 * abs(math.sin(i * 0.35 + t)))) for i in range(36)]
        if len(pts) > 1:
            d.line(pts, fill=_SAND, width=2)

        leaf(d, (24, 1144, w - 24, 1256), _SOIL)
        d.text((48, 1180), now.strftime("%A · %d %B"), font=f18, fill=_SAND)
        text_right(d, (w - 48, 1175), "ORGANIC", f28, _MOSS)
        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img, d = self._paper(w, h)
        f14, f18, f28, f44, f56 = (load_font(n, True) for n in (14, 18, 28, 44, 56))
        leaf = self._leaf_card
        bar = self._bar

        leaf(d, (20, 16, w - 20, 110), _SOIL)
        d.text((44, 32), now.strftime("%H:%M"), font=f56, fill=_BG)
        d.text((240, 48), f"{snap.host[:22]} · {snap.source.upper()}", font=f18, fill=_SAND)
        d.text((240, 78), now.strftime("%A · %d %B"), font=f14, fill=_LEAF)
        text_right(d, (w - 44, 40), f"{snap.fps:.0f} FPS", f28, _SAND)
        text_right(d, (w - 44, 78), "ORGANIC", f14, _MOSS)

        leaf(d, (20, 130, 620, 420), _CREAM)
        d.text((44, 150), "CPU  ·  core warmth", font=f14, fill=_CLAY)
        d.text((44, 190), f"{snap.cpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((240, 210), f"{snap.cpu_temp:.0f}°C", font=f44, fill=_MOSS)
        d.text((44, 280), f"{snap.cpu_clock:.0f} MHz · {snap.cpu_fan:.0f} RPM", font=f18, fill=_SOIL)
        d.text((44, 320), snap.cpu_name[:32], font=f14, fill=_CLAY)
        bar(d, 44, 370, 540, snap.cpu_usage, _MOSS)

        leaf(d, (660, 130, w - 20, 420), _MOSS)
        d.text((684, 150), "GPU  ·  green power", font=f14, fill=_LEAF)
        d.text((684, 190), f"{snap.gpu_usage:.0f}%", font=f56, fill=_BG)
        d.text((880, 210), f"{snap.gpu_temp:.0f}°C", font=f44, fill=_SAND)
        d.text((684, 280), f"{snap.gpu_clock:.0f} MHz · {snap.gpu_fan:.0f} RPM", font=f18, fill=_LEAF)
        d.text((684, 320), snap.gpu_name[:28], font=f14, fill=_SAND)
        bar(d, 684, 370, 540, snap.gpu_usage, _SAND)

        leaf(d, (20, 440, 420, 700), _SAND)
        d.text((44, 460), "MEMORY", font=f14, fill=_SOIL)
        d.text((44, 500), f"{snap.ram_percent:.0f}%", font=f44, fill=_INK)
        d.text(
            (44, 570),
            f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB",
            font=f18,
            fill=_SOIL,
        )
        bar(d, 44, 640, 340, snap.ram_percent, _CLAY)

        leaf(d, (440, 440, 840, 700), _CREAM)
        d.text((464, 460), "STORAGE", font=f14, fill=_CLAY)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 520 + i * 48
            d.text((464, y), str(name)[:10], font=f18, fill=_INK)
            text_right(d, (800, y), f"{pct:.0f}%", f18, mix(_MOSS, _CLAY, pct / 100))
            bar(d, 464, y + 26, 300, pct, _MOSS)

        leaf(d, (860, 440, w - 20, 700), _CLAY)
        d.text((884, 460), "NETWORK", font=f14, fill=_SAND)
        d.text((884, 520), f"↑ {fmt_net(snap.net_up_kb)}", font=f28, fill=_CREAM)
        d.text((884, 575), f"↓ {fmt_net(snap.net_down_kb)}", font=f28, fill=_SAND)
        pts = [(884 + i * 8, 660 - int(18 * abs(math.sin(i * 0.35 + t)))) for i in range(40)]
        if len(pts) > 1:
            d.line(pts, fill=_SAND, width=2)

        return img
