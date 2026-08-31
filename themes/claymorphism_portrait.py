from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, load_font, text_right

_BG = (255, 228, 236)
_INK = (70, 50, 80)
_MUTE = (140, 120, 150)
_PINK = (255, 150, 180)
_LILAC = (190, 160, 255)
_MINT = (140, 230, 200)
_PEACH = (255, 200, 150)


class ClaymorphismPortraitTheme(Theme):
    id = "claymorphism_portrait"
    name = "粘土拟态"
    width = 720
    height = 1280
    description = (
        "StyleKit Claymorphism：大圆角、软阴影、可爱立体感。"
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
    def _clay(d: ImageDraw.ImageDraw, box, fill, r=36) -> None:
        x0, y0, x1, y1 = box
        d.rounded_rectangle((x0 + 6, y0 + 8, x1 + 6, y1 + 8), r, fill=(220, 180, 200))
        d.rounded_rectangle(box, r, fill=fill)
        d.rounded_rectangle((x0 + 10, y0 + 8, x1 - 10, y0 + 22), 8, fill=tuple(min(255, c + 25) for c in fill))

    @staticmethod
    def _pbar(d: ImageDraw.ImageDraw, x, y, ww, pct, fill) -> None:
        d.rounded_rectangle((x, y, x + ww, y + 16), 8, fill=(255, 245, 250))
        fw = int(ww * max(0, min(100, pct)) / 100)
        if fw > 4:
            d.rounded_rectangle((x, y, x + fw, y + 16), 8, fill=fill)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f18, f28, f44, f64 = (load_font(n, True) for n in (14, 18, 28, 44, 64))
        clay = lambda box, fill, r=36: self._clay(d, box, fill, r)
        pbar = lambda x, y, ww, pct, fill: self._pbar(d, x, y, ww, pct, fill)

        clay((28, 28, w - 28, 170), _PEACH)
        d.text((52, 55), now.strftime("%H:%M"), font=f64, fill=_INK)
        d.text((52, 125), f"{snap.host[:16]} · {snap.source.upper()}", font=f14, fill=_MUTE)
        text_right(d, (w - 52, 70), f"{snap.fps:.0f}", f28, _INK)

        clay((28, 194, w - 28, 450), _PINK)
        d.text((52, 220), "CPU", font=f18, fill=(120, 40, 70))
        d.text((52, 260), f"{snap.cpu_usage:.0f}%", font=f64, fill=_INK)
        d.text((280, 280), f"{snap.cpu_temp:.0f}°C", font=f44, fill=(120, 40, 70))
        d.text((52, 350), f"{snap.cpu_clock:.0f} MHz · {snap.cpu_fan:.0f} RPM", font=f18, fill=_INK)
        d.text((52, 385), snap.cpu_name[:24], font=f14, fill=_MUTE)
        pbar(52, 415, w - 120, snap.cpu_usage, (120, 40, 70))

        clay((28, 474, w - 28, 730), _LILAC)
        d.text((52, 500), "GPU", font=f18, fill=(70, 40, 120))
        d.text((52, 540), f"{snap.gpu_usage:.0f}%", font=f64, fill=_INK)
        d.text((280, 560), f"{snap.gpu_temp:.0f}°C", font=f44, fill=(70, 40, 120))
        d.text((52, 630), f"{snap.gpu_clock:.0f} MHz · {snap.gpu_fan:.0f} RPM", font=f18, fill=_INK)
        d.text((52, 665), snap.gpu_name[:24], font=f14, fill=_MUTE)
        pbar(52, 695, w - 120, snap.gpu_usage, (70, 40, 120))

        clay((28, 754, w - 28, 920), _MINT)
        d.text((52, 780), "MEMORY", font=f18, fill=(20, 90, 70))
        d.text((52, 820), f"{snap.ram_percent:.0f}%", font=f44, fill=_INK)
        d.text((220, 840), f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB", font=f18, fill=_INK)
        pbar(52, 880, w - 120, snap.ram_percent, (20, 90, 70))

        clay((28, 944, 348, 1140), _PEACH)
        d.text((52, 970), "STORAGE", font=f18, fill=_INK)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 1015 + i * 36
            d.text((52, y), f"{str(name)[:8]} {pct:.0f}%", font=f14, fill=_INK)

        clay((372, 944, w - 28, 1140), _PINK)
        d.text((396, 970), "NETWORK", font=f18, fill=_INK)
        d.text((396, 1020), f"↑ {fmt_net(snap.net_up_kb)}", font=f18, fill=_INK)
        d.text((396, 1060), f"↓ {fmt_net(snap.net_down_kb)}", font=f18, fill=_INK)
        pts = [(396 + i * 7, 1115 - int(12 * abs(math.sin(i * 0.4 + t)))) for i in range(36)]
        if len(pts) > 1:
            d.line(pts, fill=(120, 40, 70), width=3)

        clay((28, 1160, w - 28, 1256), _LILAC, r=28)
        d.text((52, 1190), now.strftime("%A, %d %b"), font=f18, fill=_INK)
        text_right(d, (w - 52, 1185), "CLAY", f28, (70, 40, 120))
        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f18, f28, f44, f56 = (load_font(n, True) for n in (14, 18, 28, 44, 56))
        clay = lambda box, fill, r=32: self._clay(d, box, fill, r)
        pbar = lambda x, y, ww, pct, fill: self._pbar(d, x, y, ww, pct, fill)

        clay((20, 16, 420, 110), _PEACH, r=28)
        d.text((44, 32), now.strftime("%H:%M"), font=f56, fill=_INK)
        d.text((44, 78), f"{snap.host[:18]} · {snap.source.upper()}", font=f14, fill=_MUTE)
        clay((440, 16, w - 20, 110), _LILAC, r=28)
        d.text((464, 38), f"{snap.fps:.0f}", font=f56, fill=_INK)
        d.text((464, 78), "FPS", font=f14, fill=(70, 40, 120))

        half = w // 2
        clay((20, 130, half - 10, 380), _PINK)
        d.text((44, 152), "CPU", font=f18, fill=(120, 40, 70))
        d.text((44, 188), f"{snap.cpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((240, 206), f"{snap.cpu_temp:.0f}°C", font=f44, fill=(120, 40, 70))
        d.text((44, 280), f"{snap.cpu_clock:.0f} MHz · {snap.cpu_fan:.0f} RPM", font=f18, fill=_INK)
        d.text((44, 312), snap.cpu_name[:28], font=f14, fill=_MUTE)
        pbar(44, 342, half - 64, snap.cpu_usage, (120, 40, 70))

        clay((half + 10, 130, w - 20, 380), _LILAC)
        d.text((half + 34, 152), "GPU", font=f18, fill=(70, 40, 120))
        d.text((half + 34, 188), f"{snap.gpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((half + 230, 206), f"{snap.gpu_temp:.0f}°C", font=f44, fill=(70, 40, 120))
        d.text((half + 34, 280), f"{snap.gpu_clock:.0f} MHz · {snap.gpu_fan:.0f} RPM", font=f18, fill=_INK)
        d.text((half + 34, 312), snap.gpu_name[:28], font=f14, fill=_MUTE)
        pbar(half + 34, 342, w - half - 54, snap.gpu_usage, (70, 40, 120))

        col = (w - 56) // 3
        b0 = (20, 400, 20 + col, h - 20)
        b1 = (20 + col + 8, 400, 20 + 2 * col + 8, h - 20)
        b2 = (20 + 2 * col + 16, 400, w - 20, h - 20)

        clay(b0, _MINT, r=28)
        d.text((b0[0] + 24, 420), "MEMORY", font=f18, fill=(20, 90, 70))
        d.text((b0[0] + 24, 460), f"{snap.ram_percent:.0f}%", font=f44, fill=_INK)
        d.text((b0[0] + 24, 520), f"{snap.ram_used_mb:.0f} MB", font=f18, fill=_INK)
        d.text((b0[0] + 24, 552), f"/ {snap.ram_total_gb:.0f} GB", font=f14, fill=_MUTE)
        pbar(b0[0] + 24, 600, b0[2] - b0[0] - 48, snap.ram_percent, (20, 90, 70))

        clay(b1, _PEACH, r=28)
        d.text((b1[0] + 24, 420), "STORAGE", font=f18, fill=_INK)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 468 + i * 52
            d.text((b1[0] + 24, y), f"{str(name)[:10]} {pct:.0f}%", font=f14, fill=_INK)

        clay(b2, _PINK, r=28)
        d.text((b2[0] + 24, 420), "NETWORK", font=f18, fill=_INK)
        d.text((b2[0] + 24, 468), f"↑ {fmt_net(snap.net_up_kb)}", font=f18, fill=_INK)
        d.text((b2[0] + 24, 508), f"↓ {fmt_net(snap.net_down_kb)}", font=f18, fill=_INK)
        pts = [(b2[0] + 24 + i * 7, 640 - int(12 * abs(math.sin(i * 0.4 + t)))) for i in range(48)]
        if len(pts) > 1:
            d.line(pts, fill=(120, 40, 70), width=3)

        d.text((44, h - 36), now.strftime("%A, %d %b"), font=f14, fill=_MUTE)
        text_right(d, (w - 44, h - 36), "CLAY · LANDSCAPE", f18, (70, 40, 120))
        return img
