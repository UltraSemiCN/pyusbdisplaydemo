from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, load_font, text_right

_BG, _INK = (245, 240, 230), (18, 18, 18)
_YELLOW, _PINK, _MINT = (255, 230, 0), (255, 90, 150), (100, 240, 180)


class NeoBrutalistPortraitTheme(Theme):
    id = "neo_brutalist_portrait"
    name = "新野兽派"
    width = 720
    height = 1280
    description = (
        "StyleKit Neo-Brutalist：粗黑边、硬阴影、高对比。"
        "0°/180° 竖屏；90°/270° 横屏。"
    )

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

    @staticmethod
    def _card(d, box, fill, shift=8):
        x0, y0, x1, y1 = box
        d.rectangle((x0 + shift, y0 + shift, x1 + shift, y1 + shift), fill=_INK)
        d.rectangle(box, fill=fill, outline=_INK, width=4)

    @staticmethod
    def _bar(d, x, y, ww, pct, fill):
        d.rectangle((x, y, x + ww, y + 22), fill=(255, 255, 255), outline=_INK, width=3)
        fw = int((ww - 6) * max(0, min(100, pct)) / 100)
        if fw > 0:
            d.rectangle((x + 3, y + 3, x + 3 + fw, y + 19), fill=fill)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f16, f20, f28, f48, f72 = (load_font(n, True) for n in (16, 20, 28, 48, 72))
        card = lambda box, fill, shift=8: self._card(d, box, fill, shift)
        bar = lambda x, y, ww, pct, fill: self._bar(d, x, y, ww, pct, fill)

        card((28, 28, w - 36, 150), _YELLOW)
        d.text((48, 48), now.strftime("%H:%M"), font=f72, fill=_INK)
        d.text((48, 118), f"{snap.host[:18]}  ·  {snap.source.upper()}", font=f16, fill=_INK)
        text_right(d, (w - 52, 60), f"{snap.fps:.0f}", f28, _INK)
        text_right(d, (w - 52, 96), "FPS", f16, _INK)

        card((28, 180, w - 36, 430), (255, 255, 255))
        d.rectangle((28, 180, 160, 220), fill=_PINK, outline=_INK, width=4)
        d.text((48, 188), "CPU", font=f28, fill=_INK)
        d.text((48, 250), f"{snap.cpu_usage:.0f}%", font=f72, fill=_INK)
        d.text((280, 250), f"{snap.cpu_temp:.0f}°C", font=f48, fill=_INK)
        d.text((48, 340), f"Clock {snap.cpu_clock:.0f} MHz", font=f20, fill=_INK)
        d.text((48, 372), f"Fan   {snap.cpu_fan:.0f} RPM", font=f20, fill=_INK)
        d.text((48, 404), snap.cpu_name[:22], font=f16, fill=_INK)
        bar(280, 340, 360, snap.cpu_usage, _PINK)

        card((28, 460, w - 36, 710), _MINT)
        d.rectangle((28, 460, 160, 500), fill=_YELLOW, outline=_INK, width=4)
        d.text((48, 468), "GPU", font=f28, fill=_INK)
        d.text((48, 530), f"{snap.gpu_usage:.0f}%", font=f72, fill=_INK)
        d.text((280, 530), f"{snap.gpu_temp:.0f}°C", font=f48, fill=_INK)
        d.text((48, 620), f"Clock {snap.gpu_clock:.0f} MHz", font=f20, fill=_INK)
        d.text((48, 652), f"Fan   {snap.gpu_fan:.0f} RPM", font=f20, fill=_INK)
        d.text((48, 684), snap.gpu_name[:22], font=f16, fill=_INK)
        bar(280, 620, 360, snap.gpu_usage, _INK)

        card((28, 740, w - 36, 900), (255, 255, 255))
        d.text((48, 760), "MEMORY", font=f28, fill=_INK)
        d.text((48, 810), f"{snap.ram_percent:.0f}%", font=f48, fill=_INK)
        d.text(
            (220, 828),
            f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB",
            font=f20,
            fill=_INK,
        )
        bar(48, 880, w - 120, snap.ram_percent, _YELLOW)

        card((28, 930, 350, 1120), _PINK)
        d.text((48, 950), "STORAGE", font=f20, fill=_INK)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 1000 + i * 36
            d.text((48, y), str(name)[:8], font=f16, fill=_INK)
            bar(130, y + 2, 180, pct, _INK)

        card((380, 930, w - 36, 1120), _YELLOW)
        d.text((400, 950), "NETWORK", font=f20, fill=_INK)
        d.text((400, 1000), f"↑ {fmt_net(snap.net_up_kb)}", font=f20, fill=_INK)
        d.text((400, 1040), f"↓ {fmt_net(snap.net_down_kb)}", font=f20, fill=_INK)
        pts = [
            (400 + i * 8, 1100 - int(16 * abs(math.sin(i * 0.4 + t * 3))))
            for i in range(30)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_INK, width=4)

        card((28, 1150, w - 36, 1250), _INK, shift=0)
        d.text((48, 1180), now.strftime("%A  %d %B %Y"), font=f20, fill=_YELLOW)
        text_right(d, (w - 52, 1180), "NEO", f28, _PINK)

        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f16, f20, f28, f48, f56 = (load_font(n, True) for n in (16, 20, 28, 48, 56))
        card = lambda box, fill, shift=8: self._card(d, box, fill, shift)
        bar = lambda x, y, ww, pct, fill: self._bar(d, x, y, ww, pct, fill)

        card((20, 16, w - 28, 110), _YELLOW)
        d.text((40, 32), now.strftime("%H:%M"), font=f56, fill=_INK)
        d.text(
            (240, 48),
            f"{snap.host[:22]}  ·  {snap.source.upper()}",
            font=f16,
            fill=_INK,
        )
        d.text((240, 76), now.strftime("%A  %d %B %Y"), font=f16, fill=_INK)
        text_right(d, (w - 44, 36), f"{snap.fps:.0f}", f28, _INK)
        text_right(d, (w - 44, 72), "FPS", f16, _INK)

        card((20, 130, 620, 380), (255, 255, 255))
        d.rectangle((20, 130, 140, 168), fill=_PINK, outline=_INK, width=4)
        d.text((36, 136), "CPU", font=f28, fill=_INK)
        d.text((36, 190), f"{snap.cpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((240, 200), f"{snap.cpu_temp:.0f}°C", font=f48, fill=_INK)
        d.text((36, 280), f"Clock {snap.cpu_clock:.0f} MHz", font=f20, fill=_INK)
        d.text((36, 310), f"Fan   {snap.cpu_fan:.0f} RPM", font=f20, fill=_INK)
        d.text((36, 340), snap.cpu_name[:28], font=f16, fill=_INK)
        bar(240, 280, 340, snap.cpu_usage, _PINK)

        card((660, 130, w - 20, 380), _MINT)
        d.rectangle((660, 130, 780, 168), fill=_YELLOW, outline=_INK, width=4)
        d.text((676, 136), "GPU", font=f28, fill=_INK)
        d.text((676, 190), f"{snap.gpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((880, 200), f"{snap.gpu_temp:.0f}°C", font=f48, fill=_INK)
        d.text((676, 280), f"Clock {snap.gpu_clock:.0f} MHz", font=f20, fill=_INK)
        d.text((676, 310), f"Fan   {snap.gpu_fan:.0f} RPM", font=f20, fill=_INK)
        d.text((676, 340), snap.gpu_name[:28], font=f16, fill=_INK)
        bar(880, 280, 340, snap.gpu_usage, _INK)

        card((20, 400, 400, h - 16), (255, 255, 255))
        d.text((40, 420), "MEMORY", font=f28, fill=_INK)
        d.text((40, 470), f"{snap.ram_percent:.0f}%", font=f48, fill=_INK)
        d.text(
            (40, 530),
            f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB",
            font=f20,
            fill=_INK,
        )
        bar(40, 590, 320, snap.ram_percent, _YELLOW)

        card((420, 400, 860, h - 16), _PINK)
        d.text((440, 420), "STORAGE", font=f20, fill=_INK)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 470 + i * 58
            d.text((440, y), str(name)[:10], font=f16, fill=_INK)
            bar(540, y + 2, 260, pct, _INK)
            text_right(d, (840, y), f"{pct:.0f}%", f16, _INK)

        card((880, 400, w - 20, h - 16), _YELLOW)
        d.text((900, 420), "NETWORK", font=f20, fill=_INK)
        d.text((900, 470), f"↑ {fmt_net(snap.net_up_kb)}", font=f20, fill=_INK)
        d.text((900, 510), f"↓ {fmt_net(snap.net_down_kb)}", font=f20, fill=_INK)
        pts = [
            (900 + i * 8, 660 - int(16 * abs(math.sin(i * 0.4 + t * 3))))
            for i in range(36)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_INK, width=4)
        text_right(d, (w - 44, 640), "NEO", f28, _PINK)

        return img
