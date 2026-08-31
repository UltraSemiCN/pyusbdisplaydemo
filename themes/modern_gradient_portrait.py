from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import clamp01, fmt_net, load_font, mix, text_right

_TOP, _BOT = (90, 40, 180), (20, 180, 220)
_INK, _MUTE = (255, 255, 255), (220, 230, 255)


class ModernGradientPortraitTheme(Theme):
    id = "modern_gradient_portrait"
    name = "现代渐变风"
    width = 720
    height = 1280
    description = "StyleKit Modern Gradient：多彩渐变与玻璃卡片。0°/180° 竖屏；90°/270° 横屏。"

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
    def _gradient_bg(w: int, h: int, t: float) -> Image.Image:
        img = Image.new("RGB", (w, h))
        d = ImageDraw.Draw(img)
        for y in range(h):
            c = mix(_TOP, _BOT, y / max(1, h - 1))
            k = int(12 * math.sin(y * 0.01 + t))
            d.line([(0, y), (w, y)], fill=tuple(max(0, min(255, v + k)) for v in c))
        return img

    @staticmethod
    def _frost(img: Image.Image, box, alpha: float = 0.24) -> None:
        x0, y0, x1, y1 = (int(v) for v in box)
        crop = img.crop((x0, y0, x1, y1))
        overlay = Image.new("RGB", crop.size, (255, 255, 255))
        img.paste(Image.blend(crop, overlay, alpha), (x0, y0))
        ImageDraw.Draw(img).rounded_rectangle(box, 22, outline=(255, 255, 255), width=2)

    @staticmethod
    def _bar(img: Image.Image, x, y, ww, pct) -> None:
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((x, y, x + ww, y + 12), 6, fill=(160, 190, 230))
        fw = int(ww * clamp01(pct / 100))
        if fw > 4:
            d.rounded_rectangle((x, y, x + fw, y + 12), 6, fill=(255, 255, 255))

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = self._gradient_bg(w, h, t)
        frost = self._frost
        bar = lambda x, y, ww, pct: self._bar(img, x, y, ww, pct)
        f14, f18, f28, f44, f64 = (load_font(n, True) for n in (14, 18, 28, 44, 64))

        frost(img, (28, 28, w - 28, 170))
        d = ImageDraw.Draw(img)
        d.text((52, 52), now.strftime("%H:%M"), font=f64, fill=_INK)
        d.text((52, 125), f"{snap.host[:18]}  ·  {snap.source.upper()}", font=f14, fill=_MUTE)
        text_right(d, (w - 52, 70), f"{snap.fps:.0f}", f28, _INK)
        text_right(d, (w - 52, 104), "FPS", f14, _MUTE)

        frost(img, (28, 194, w - 28, 440))
        d = ImageDraw.Draw(img)
        d.text((52, 220), "CPU", font=f18, fill=_MUTE)
        d.text((52, 260), f"{snap.cpu_usage:.0f}%", font=f64, fill=_INK)
        d.text((280, 280), f"{snap.cpu_temp:.0f}°C", font=f44, fill=_INK)
        d.text((52, 350), f"{snap.cpu_clock:.0f} MHz · {snap.cpu_fan:.0f} RPM", font=f18, fill=_MUTE)
        d.text((52, 382), snap.cpu_name[:26], font=f14, fill=_MUTE)
        bar(52, 410, w - 120, snap.cpu_usage)

        frost(img, (28, 464, w - 28, 710))
        d = ImageDraw.Draw(img)
        d.text((52, 490), "GPU", font=f18, fill=_MUTE)
        d.text((52, 530), f"{snap.gpu_usage:.0f}%", font=f64, fill=_INK)
        d.text((280, 550), f"{snap.gpu_temp:.0f}°C", font=f44, fill=_INK)
        d.text((52, 620), f"{snap.gpu_clock:.0f} MHz · {snap.gpu_fan:.0f} RPM", font=f18, fill=_MUTE)
        d.text((52, 652), snap.gpu_name[:26], font=f14, fill=_MUTE)
        bar(52, 680, w - 120, snap.gpu_usage)

        frost(img, (28, 734, w - 28, 900))
        d = ImageDraw.Draw(img)
        d.text((52, 760), "MEMORY", font=f18, fill=_MUTE)
        d.text((52, 800), f"{snap.ram_percent:.0f}%", font=f44, fill=_INK)
        d.text((220, 820), f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB", font=f18, fill=_MUTE)
        bar(52, 860, w - 120, snap.ram_percent)

        frost(img, (28, 924, 348, 1120))
        d = ImageDraw.Draw(img)
        d.text((52, 950), "STORAGE", font=f18, fill=_MUTE)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 995 + i * 36
            d.text((52, y), f"{str(name)[:8]}  {pct:.0f}%", font=f14, fill=_INK)
            bar(52, y + 20, 260, pct)

        frost(img, (372, 924, w - 28, 1120))
        d = ImageDraw.Draw(img)
        d.text((396, 950), "NETWORK", font=f18, fill=_MUTE)
        d.text((396, 1000), f"↑ {fmt_net(snap.net_up_kb)}", font=f18, fill=_INK)
        d.text((396, 1040), f"↓ {fmt_net(snap.net_down_kb)}", font=f18, fill=_INK)
        pts = [(396 + i * 7, 1095 - int(14 * abs(math.sin(i * 0.4 + t * 2.2)))) for i in range(36)]
        if len(pts) > 1:
            d.line(pts, fill=_INK, width=2)

        frost(img, (28, 1144, w - 28, 1252))
        d = ImageDraw.Draw(img)
        d.text((52, 1180), now.strftime("%A, %d %B %Y"), font=f18, fill=_MUTE)
        text_right(d, (w - 52, 1175), "GRADIENT", f28, _INK)

        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = self._gradient_bg(w, h, t)
        frost = self._frost
        bar = lambda x, y, ww, pct: self._bar(img, x, y, ww, pct)
        f14, f18, f28, f44, f56 = (load_font(n, True) for n in (14, 18, 28, 44, 56))

        frost(img, (24, 16, w - 24, 108))
        d = ImageDraw.Draw(img)
        d.text((48, 28), now.strftime("%H:%M"), font=f56, fill=_INK)
        d.text((260, 38), f"{snap.host[:24]}  ·  {snap.source.upper()}", font=f18, fill=_MUTE)
        d.text((260, 68), now.strftime("%A, %d %B %Y"), font=f14, fill=_MUTE)
        text_right(d, (w - 48, 32), f"{snap.fps:.0f}", f44, _INK)
        text_right(d, (w - 48, 72), "FPS", f14, _MUTE)

        frost(img, (24, 124, 620, 400))
        d = ImageDraw.Draw(img)
        d.text((48, 144), "CPU", font=f18, fill=_MUTE)
        d.text((48, 180), f"{snap.cpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((220, 200), f"{snap.cpu_temp:.0f}°C", font=f44, fill=_INK)
        d.text((48, 270), f"{snap.cpu_clock:.0f} MHz · {snap.cpu_fan:.0f} RPM", font=f18, fill=_MUTE)
        d.text((48, 305), snap.cpu_name[:32], font=f14, fill=_MUTE)
        bar(48, 350, 540, snap.cpu_usage)

        frost(img, (660, 124, w - 24, 400))
        d = ImageDraw.Draw(img)
        d.text((684, 144), "GPU", font=f18, fill=_MUTE)
        d.text((684, 180), f"{snap.gpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((860, 200), f"{snap.gpu_temp:.0f}°C", font=f44, fill=_INK)
        d.text((684, 270), f"{snap.gpu_clock:.0f} MHz · {snap.gpu_fan:.0f} RPM", font=f18, fill=_MUTE)
        d.text((684, 305), snap.gpu_name[:28], font=f14, fill=_MUTE)
        bar(684, 350, 540, snap.gpu_usage)

        frost(img, (24, 416, 400, h - 24))
        d = ImageDraw.Draw(img)
        d.text((48, 436), "MEMORY", font=f18, fill=_MUTE)
        d.text((48, 476), f"{snap.ram_percent:.0f}%", font=f44, fill=_INK)
        d.text(
            (48, 540),
            f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB",
            font=f18,
            fill=_MUTE,
        )
        bar(48, 620, 300, snap.ram_percent)

        frost(img, (420, 416, 860, h - 24))
        d = ImageDraw.Draw(img)
        d.text((444, 436), "STORAGE", font=f18, fill=_MUTE)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 490 + i * 56
            d.text((444, y), str(name)[:10], font=f18, fill=_INK)
            text_right(d, (820, y), f"{pct:.0f}%", f18, _INK)
            bar(444, y + 28, 340, pct)

        frost(img, (880, 416, w - 24, h - 24))
        d = ImageDraw.Draw(img)
        d.text((904, 436), "NETWORK", font=f18, fill=_MUTE)
        d.text((904, 500), f"↑ {fmt_net(snap.net_up_kb)}", font=f28, fill=_INK)
        d.text((904, 560), f"↓ {fmt_net(snap.net_down_kb)}", font=f28, fill=_INK)
        pts = [(904 + i * 7, 660 - int(16 * abs(math.sin(i * 0.4 + t * 2.2)))) for i in range(44)]
        if len(pts) > 1:
            d.line(pts, fill=_INK, width=2)
        text_right(d, (w - 48, 680), "GRADIENT", f28, _INK)

        return img
