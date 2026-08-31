from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, load_font, text_right

_BG = (230, 234, 242)
_CARD = (230, 234, 242)
_DARK, _LIGHT = (190, 198, 212), (250, 252, 255)
_INK, _MUTE = (55, 65, 85), (120, 130, 150)
_BLUE, _CORAL, _GREEN = (100, 140, 220), (230, 120, 110), (90, 180, 150)


class SoftUiPortraitTheme(Theme):
    id = "soft_ui_portrait"
    name = "柔和界面"
    width = 720
    height = 1280
    description = (
        "StyleKit Soft UI：圆角、低饱和、柔和阴影。"
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
    def _soft_card(d, box, r=24):
        x0, y0, x1, y1 = box
        d.rounded_rectangle((x0 + 4, y0 + 4, x1 + 4, y1 + 4), r, fill=_DARK)
        d.rounded_rectangle((x0 - 2, y0 - 2, x1 - 2, y1 - 2), r, fill=_LIGHT)
        d.rounded_rectangle(box, r, fill=_CARD)

    @staticmethod
    def _soft_bar(d, x, y, ww, pct, fill):
        d.rounded_rectangle((x, y, x + ww, y + 14), 7, fill=_DARK)
        fw = int(ww * max(0, min(100, pct)) / 100)
        if fw > 4:
            d.rounded_rectangle((x, y, x + fw, y + 14), 7, fill=fill)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f18, f28, f44, f64 = (load_font(n, True) for n in (14, 18, 28, 44, 64))
        soft_card = lambda box, r=24: self._soft_card(d, box, r)
        soft_bar = lambda x, y, ww, pct, fill: self._soft_bar(d, x, y, ww, pct, fill)

        soft_card((28, 28, w - 28, 160))
        d.text((52, 52), now.strftime("%H:%M"), font=f64, fill=_INK)
        d.text((52, 120), f"{snap.host[:18]}  ·  {snap.source.upper()}", font=f14, fill=_MUTE)
        text_right(d, (w - 52, 70), f"{snap.fps:.0f}", f28, _BLUE)
        text_right(d, (w - 52, 104), "fps", f14, _MUTE)

        soft_card((28, 184, w - 28, 430))
        d.text((52, 208), "CPU", font=f18, fill=_MUTE)
        d.text((52, 250), f"{snap.cpu_usage:.0f}%", font=f64, fill=_INK)
        d.text((280, 270), f"{snap.cpu_temp:.0f}°C", font=f44, fill=_BLUE)
        d.text((52, 340), f"Clock {snap.cpu_clock:.0f} MHz", font=f18, fill=_MUTE)
        d.text(
            (52, 370),
            f"Fan {snap.cpu_fan:.0f} RPM · {snap.cpu_name[:16]}",
            font=f14,
            fill=_MUTE,
        )
        soft_bar(52, 400, w - 120, snap.cpu_usage, _BLUE)

        soft_card((28, 454, w - 28, 700))
        d.text((52, 478), "GPU", font=f18, fill=_MUTE)
        d.text((52, 520), f"{snap.gpu_usage:.0f}%", font=f64, fill=_INK)
        d.text((280, 540), f"{snap.gpu_temp:.0f}°C", font=f44, fill=_CORAL)
        d.text((52, 610), f"Clock {snap.gpu_clock:.0f} MHz", font=f18, fill=_MUTE)
        d.text(
            (52, 640),
            f"Fan {snap.gpu_fan:.0f} RPM · {snap.gpu_name[:16]}",
            font=f14,
            fill=_MUTE,
        )
        soft_bar(52, 670, w - 120, snap.gpu_usage, _CORAL)

        soft_card((28, 724, w - 28, 900))
        d.text((52, 748), "MEMORY", font=f18, fill=_MUTE)
        d.text((52, 790), f"{snap.ram_percent:.0f}%", font=f44, fill=_INK)
        d.text(
            (220, 810),
            f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB",
            font=f18,
            fill=_MUTE,
        )
        soft_bar(52, 860, w - 120, snap.ram_percent, _GREEN)

        soft_card((28, 924, 348, 1120))
        d.text((52, 948), "STORAGE", font=f18, fill=_MUTE)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 990 + i * 36
            d.text((52, y), str(name)[:8], font=f14, fill=_INK)
            soft_bar(130, y + 4, 180, pct, _GREEN)

        soft_card((372, 924, w - 28, 1120))
        d.text((396, 948), "NETWORK", font=f18, fill=_MUTE)
        d.text((396, 1000), f"↑ {fmt_net(snap.net_up_kb)}", font=f18, fill=_CORAL)
        d.text((396, 1040), f"↓ {fmt_net(snap.net_down_kb)}", font=f18, fill=_BLUE)
        pts = [
            (396 + i * 7, 1095 - int(14 * abs(math.sin(i * 0.4 + t * 2))))
            for i in range(36)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_BLUE, width=3)

        soft_card((28, 1144, w - 28, 1252))
        d.text((52, 1180), now.strftime("%A, %d %B %Y"), font=f18, fill=_MUTE)
        text_right(d, (w - 52, 1175), "SOFT", f28, _BLUE)

        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f18, f28, f44, f56 = (load_font(n, True) for n in (14, 18, 28, 44, 56))
        soft_card = lambda box, r=24: self._soft_card(d, box, r)
        soft_bar = lambda x, y, ww, pct, fill: self._soft_bar(d, x, y, ww, pct, fill)

        soft_card((20, 16, w - 20, 120))
        d.text((44, 36), now.strftime("%H:%M"), font=f56, fill=_INK)
        d.text(
            (240, 48),
            f"{snap.host[:22]}  ·  {snap.source.upper()}",
            font=f14,
            fill=_MUTE,
        )
        d.text((240, 78), now.strftime("%A, %d %B %Y"), font=f14, fill=_MUTE)
        text_right(d, (w - 44, 40), f"{snap.fps:.0f}", f28, _BLUE)
        text_right(d, (w - 44, 76), "fps", f14, _MUTE)

        soft_card((20, 140, 620, 400))
        d.text((44, 164), "CPU", font=f18, fill=_MUTE)
        d.text((44, 200), f"{snap.cpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((240, 220), f"{snap.cpu_temp:.0f}°C", font=f44, fill=_BLUE)
        d.text((44, 290), f"Clock {snap.cpu_clock:.0f} MHz", font=f18, fill=_MUTE)
        d.text(
            (44, 320),
            f"Fan {snap.cpu_fan:.0f} RPM · {snap.cpu_name[:22]}",
            font=f14,
            fill=_MUTE,
        )
        soft_bar(44, 360, 540, snap.cpu_usage, _BLUE)

        soft_card((660, 140, w - 20, 400))
        d.text((684, 164), "GPU", font=f18, fill=_MUTE)
        d.text((684, 200), f"{snap.gpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((880, 220), f"{snap.gpu_temp:.0f}°C", font=f44, fill=_CORAL)
        d.text((684, 290), f"Clock {snap.gpu_clock:.0f} MHz", font=f18, fill=_MUTE)
        d.text(
            (684, 320),
            f"Fan {snap.gpu_fan:.0f} RPM · {snap.gpu_name[:22]}",
            font=f14,
            fill=_MUTE,
        )
        soft_bar(684, 360, 540, snap.gpu_usage, _CORAL)

        soft_card((20, 420, 400, h - 16))
        d.text((44, 444), "MEMORY", font=f18, fill=_MUTE)
        d.text((44, 480), f"{snap.ram_percent:.0f}%", font=f44, fill=_INK)
        d.text(
            (44, 540),
            f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB",
            font=f18,
            fill=_MUTE,
        )
        soft_bar(44, 600, 320, snap.ram_percent, _GREEN)

        soft_card((420, 420, 860, h - 16))
        d.text((444, 444), "STORAGE", font=f18, fill=_MUTE)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 490 + i * 58
            d.text((444, y), str(name)[:10], font=f14, fill=_INK)
            soft_bar(540, y + 4, 260, pct, _GREEN)
            text_right(d, (840, y), f"{pct:.0f}%", f14, _MUTE)

        soft_card((880, 420, w - 20, h - 16))
        d.text((904, 444), "NETWORK", font=f18, fill=_MUTE)
        d.text((904, 490), f"↑ {fmt_net(snap.net_up_kb)}", font=f18, fill=_CORAL)
        d.text((904, 530), f"↓ {fmt_net(snap.net_down_kb)}", font=f18, fill=_BLUE)
        pts = [
            (904 + i * 7, 660 - int(14 * abs(math.sin(i * 0.4 + t * 2))))
            for i in range(40)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_BLUE, width=3)

        return img
