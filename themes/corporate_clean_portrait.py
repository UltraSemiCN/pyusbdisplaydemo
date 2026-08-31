from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, load_font, mix, text_right

_BG = (245, 247, 250)
_CARD = (255, 255, 255)
_LINE = (220, 226, 235)
_INK = (30, 41, 59)
_MUTE = (100, 116, 139)
_BRAND = (37, 99, 235)
_OK = (16, 185, 129)
_WARN = (245, 158, 11)


class CorporateCleanPortraitTheme(Theme):
    id = "corporate_clean_portrait"
    name = "企业简洁风"
    width = 720
    height = 1280
    description = (
        "StyleKit Corporate Clean：专业、清晰、信任感。"
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
    def _panel(d: ImageDraw.ImageDraw, box) -> None:
        d.rounded_rectangle(box, 12, fill=_CARD, outline=_LINE, width=1)

    @staticmethod
    def _bar(d: ImageDraw.ImageDraw, x, y, ww, pct, fill=_BRAND) -> None:
        d.rounded_rectangle((x, y, x + ww, y + 8), 4, fill=_LINE)
        fw = int(ww * max(0, min(100, pct)) / 100)
        if fw > 2:
            d.rounded_rectangle((x, y, x + fw, y + 8), 4, fill=fill)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f13, f16, f22, f36, f56 = (load_font(n, True) for n in (13, 16, 22, 36, 56))
        panel = lambda box: self._panel(d, box)
        bar = lambda x, y, ww, pct, fill=_BRAND: self._bar(d, x, y, ww, pct, fill)

        d.rectangle((0, 0, w, 96), fill=_CARD)
        d.rectangle((0, 96, w, 97), fill=_LINE)
        d.text((28, 28), "USB Display HUD", font=f22, fill=_INK)
        d.text((28, 60), f"{snap.host[:20]}  ·  {snap.source.upper()}", font=f13, fill=_MUTE)
        text_right(d, (w - 28, 32), now.strftime("%H:%M:%S"), f22, _BRAND)

        panel((24, 120, w - 24, 340))
        d.text((44, 140), "CPU", font=f13, fill=_MUTE)
        d.text((44, 170), f"{snap.cpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((260, 190), f"{snap.cpu_temp:.0f}°C", font=f36, fill=_BRAND)
        d.text((44, 250), f"{snap.cpu_clock:.0f} MHz   {snap.cpu_fan:.0f} RPM", font=f16, fill=_MUTE)
        d.text((44, 280), snap.cpu_name[:30], font=f13, fill=_MUTE)
        bar(44, 310, w - 96, snap.cpu_usage)

        panel((24, 360, w - 24, 580))
        d.text((44, 380), "GPU", font=f13, fill=_MUTE)
        d.text((44, 410), f"{snap.gpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((260, 430), f"{snap.gpu_temp:.0f}°C", font=f36, fill=_WARN)
        d.text((44, 490), f"{snap.gpu_clock:.0f} MHz   {snap.gpu_fan:.0f} RPM", font=f16, fill=_MUTE)
        d.text((44, 520), snap.gpu_name[:30], font=f13, fill=_MUTE)
        bar(44, 550, w - 96, snap.gpu_usage, _WARN)

        panel((24, 600, 348, 820))
        d.text((44, 620), "MEMORY", font=f13, fill=_MUTE)
        d.text((44, 660), f"{snap.ram_percent:.0f}%", font=f36, fill=_INK)
        d.text((44, 720), f"{snap.ram_used_mb:.0f} MB", font=f16, fill=_MUTE)
        d.text((44, 748), f"/ {snap.ram_total_gb:.0f} GB", font=f13, fill=_MUTE)
        bar(44, 780, 280, snap.ram_percent, _OK)

        panel((372, 600, w - 24, 820))
        d.text((392, 620), "NETWORK", font=f13, fill=_MUTE)
        d.text((392, 670), f"↑ {fmt_net(snap.net_up_kb)}", font=f22, fill=_INK)
        d.text((392, 720), f"↓ {fmt_net(snap.net_down_kb)}", font=f22, fill=_BRAND)
        pts = [(392 + i * 6, 790 - int(14 * abs(math.sin(i * 0.35 + t * 2)))) for i in range(44)]
        if len(pts) > 1:
            d.line(pts, fill=_BRAND, width=2)

        panel((24, 840, w - 24, 1080))
        d.text((44, 860), "STORAGE", font=f13, fill=_MUTE)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 900 + i * 52
            d.text((44, y), str(name)[:12], font=f16, fill=_INK)
            text_right(d, (w - 44, y), f"{pct:.0f}%", f16, _MUTE)
            bar(44, y + 28, w - 96, pct, mix(_OK, _WARN, pct / 100))

        panel((24, 1100, w - 24, 1256))
        d.text((44, 1135), now.strftime("%A, %d %B %Y"), font=f16, fill=_MUTE)
        text_right(d, (w - 44, 1125), f"{snap.fps:.0f}", f36, _BRAND)
        text_right(d, (w - 44, 1175), "FPS", f13, _MUTE)
        d.text((44, 1195), "Corporate Clean", font=f13, fill=_LINE)
        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f13, f16, f22, f36, f56 = (load_font(n, True) for n in (13, 16, 22, 36, 56))
        panel = lambda box: self._panel(d, box)
        bar = lambda x, y, ww, pct, fill=_BRAND: self._bar(d, x, y, ww, pct, fill)

        d.rectangle((0, 0, w, 72), fill=_CARD)
        d.rectangle((0, 72, w, 73), fill=_LINE)
        d.text((24, 16), "USB Display HUD", font=f22, fill=_INK)
        d.text((24, 46), f"{snap.host[:28]}  ·  {snap.source.upper()}", font=f13, fill=_MUTE)
        text_right(d, (w - 24, 20), now.strftime("%H:%M:%S"), f22, _BRAND)
        text_right(d, (w - 24, 48), f"{snap.fps:.0f} FPS", f13, fill=_MUTE)

        half = w // 2
        panel((20, 88, half - 10, 340))
        d.text((40, 108), "CPU", font=f13, fill=_MUTE)
        d.text((40, 138), f"{snap.cpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((240, 158), f"{snap.cpu_temp:.0f}°C", font=f36, fill=_BRAND)
        d.text((40, 220), f"{snap.cpu_clock:.0f} MHz   {snap.cpu_fan:.0f} RPM", font=f16, fill=_MUTE)
        d.text((40, 252), snap.cpu_name[:34], font=f13, fill=_MUTE)
        bar(40, 300, half - 60, snap.cpu_usage)

        panel((half + 10, 88, w - 20, 340))
        d.text((half + 30, 108), "GPU", font=f13, fill=_MUTE)
        d.text((half + 30, 138), f"{snap.gpu_usage:.0f}%", font=f56, fill=_INK)
        d.text((half + 230, 158), f"{snap.gpu_temp:.0f}°C", font=f36, fill=_WARN)
        d.text((half + 30, 220), f"{snap.gpu_clock:.0f} MHz   {snap.gpu_fan:.0f} RPM", font=f16, fill=_MUTE)
        d.text((half + 30, 252), snap.gpu_name[:34], font=f13, fill=_MUTE)
        bar(half + 30, 300, w - half - 50, snap.gpu_usage, _WARN)

        col = (w - 56) // 3
        b0 = (20, 360, 20 + col, h - 20)
        b1 = (20 + col + 8, 360, 20 + 2 * col + 8, h - 20)
        b2 = (20 + 2 * col + 16, 360, w - 20, h - 20)

        panel(b0)
        d.text((b0[0] + 20, 380), "MEMORY", font=f13, fill=_MUTE)
        d.text((b0[0] + 20, 420), f"{snap.ram_percent:.0f}%", font=f36, fill=_INK)
        d.text((b0[0] + 20, 480), f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB", font=f16, fill=_MUTE)
        bar(b0[0] + 20, 540, b0[2] - b0[0] - 40, snap.ram_percent, _OK)

        panel(b1)
        d.text((b1[0] + 20, 380), "NETWORK", font=f13, fill=_MUTE)
        d.text((b1[0] + 20, 420), f"↑ {fmt_net(snap.net_up_kb)}", font=f22, fill=_INK)
        d.text((b1[0] + 20, 470), f"↓ {fmt_net(snap.net_down_kb)}", font=f22, fill=_BRAND)
        pts = [(b1[0] + 20 + i * 6, 620 - int(14 * abs(math.sin(i * 0.35 + t * 2)))) for i in range(48)]
        if len(pts) > 1:
            d.line(pts, fill=_BRAND, width=2)

        panel(b2)
        d.text((b2[0] + 20, 380), "STORAGE", font=f13, fill=_MUTE)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 420 + i * 58
            d.text((b2[0] + 20, y), str(name)[:12], font=f16, fill=_INK)
            text_right(d, (b2[2] - 20, y), f"{pct:.0f}%", f16, _MUTE)
            bar(b2[0] + 20, y + 28, b2[2] - b2[0] - 40, pct, mix(_OK, _WARN, pct / 100))

        d.text((24, h - 36), now.strftime("%A, %d %B %Y"), font=f13, fill=_MUTE)
        text_right(d, (w - 24, h - 36), "Corporate Clean · Landscape", f13, _LINE)
        return img
