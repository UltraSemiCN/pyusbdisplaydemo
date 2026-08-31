from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, load_font, text_right


def _serif(size: int) -> ImageFont.ImageFont:
    for name in ("georgia.ttf", "times.ttf", "timesbd.ttf", "GARA.TTF"):
        path = Path(r"C:\Windows\Fonts") / name
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return load_font(size, True)


_BG = (250, 248, 242)
_INK = (22, 22, 22)
_RULE = (30, 30, 30)
_ACCENT = (170, 40, 40)
_MUTE = (110, 110, 110)


class EditorialPortraitTheme(Theme):
    id = "editorial_portrait"
    name = "编辑杂志风"
    width = 720
    height = 1280
    description = (
        "StyleKit Editorial：衬线标题、精致留白与网格。"
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
    def _rule_h(d: ImageDraw.ImageDraw, y: int, w: int, margin: int = 36) -> None:
        d.rectangle((margin, y, w - margin, y + 1), fill=_RULE)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        ser48, ser36, ser24 = _serif(48), _serif(36), _serif(24)
        f14, f18, f28 = (load_font(n, True) for n in (14, 18, 28))

        d.text((36, 36), "SYSTEM", font=ser24, fill=_ACCENT)
        d.text((36, 70), "MONITOR", font=ser48, fill=_INK)
        self._rule_h(d, 140, w)
        d.text((36, 156), now.strftime("%A · %d %B %Y").upper(), font=f14, fill=_MUTE)
        text_right(d, (w - 36, 156), now.strftime("%H:%M:%S"), f18, _INK)
        self._rule_h(d, 186, w)

        d.text((36, 210), "01  PROCESSOR", font=f14, fill=_ACCENT)
        d.text((36, 240), f"{snap.cpu_usage:.0f}", font=ser48, fill=_INK)
        d.text((180, 270), "% LOAD", font=f18, fill=_MUTE)
        d.text((360, 240), f"{snap.cpu_temp:.0f}°", font=ser48, fill=_INK)
        d.text((520, 270), "TEMP", font=f18, fill=_MUTE)
        d.text((36, 320), f"{snap.cpu_name[:32]}", font=f14, fill=_MUTE)
        d.text((36, 348), f"{snap.cpu_clock:.0f} MHz   ·   {snap.cpu_fan:.0f} RPM", font=f14, fill=_INK)
        self._rule_h(d, 380, w)

        d.text((36, 404), "02  GRAPHICS", font=f14, fill=_ACCENT)
        d.text((36, 434), f"{snap.gpu_usage:.0f}", font=ser48, fill=_INK)
        d.text((180, 464), "% LOAD", font=f18, fill=_MUTE)
        d.text((360, 434), f"{snap.gpu_temp:.0f}°", font=ser48, fill=_INK)
        d.text((520, 464), "TEMP", font=f18, fill=_MUTE)
        d.text((36, 514), f"{snap.gpu_name[:32]}", font=f14, fill=_MUTE)
        d.text((36, 542), f"{snap.gpu_clock:.0f} MHz   ·   {snap.gpu_fan:.0f} RPM", font=f14, fill=_INK)
        self._rule_h(d, 574, w)

        mid = w // 2
        d.line([(mid, 600), (mid, 780)], fill=_RULE, width=1)
        d.text((36, 600), "MEMORY", font=f14, fill=_ACCENT)
        d.text((36, 640), f"{snap.ram_percent:.0f}%", font=ser36, fill=_INK)
        d.text((36, 700), f"{snap.ram_used_mb:.0f} MB", font=f18, fill=_INK)
        d.text((36, 732), f"of {snap.ram_total_gb:.0f} GB", font=f14, fill=_MUTE)

        d.text((mid + 24, 600), "HOST", font=f14, fill=_ACCENT)
        d.text((mid + 24, 640), snap.host[:12], font=ser24, fill=_INK)
        d.text((mid + 24, 700), snap.source.upper(), font=f18, fill=_INK)
        d.text((mid + 24, 732), f"{snap.fps:.0f} FPS STREAM", font=f14, fill=_MUTE)
        self._rule_h(d, 800, w)

        d.text((36, 824), "03  STORAGE", font=f14, fill=_ACCENT)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 860 + i * 44
            d.text((36, y), str(name)[:12], font=f18, fill=_INK)
            d.rectangle((200, y + 12, w - 100, y + 14), fill=(210, 205, 195))
            fw = int((w - 300) * max(0, min(100, pct)) / 100)
            d.rectangle((200, y + 12, 200 + fw, y + 14), fill=_ACCENT)
            text_right(d, (w - 36, y), f"{pct:.0f}%", f18, _INK)

        self._rule_h(d, 1000, w)

        d.text((36, 1028), "04  NETWORK", font=f14, fill=_ACCENT)
        d.text((36, 1070), "UPLOAD", font=f14, fill=_MUTE)
        d.text((36, 1100), fmt_net(snap.net_up_kb), font=ser24, fill=_INK)
        d.text((360, 1070), "DOWNLOAD", font=f14, fill=_MUTE)
        d.text((360, 1100), fmt_net(snap.net_down_kb), font=ser24, fill=_INK)
        pts = [(36 + i * 6, 1200 - int(16 * abs(math.sin(i * 0.35 + t * 2)))) for i in range(108)]
        if len(pts) > 1:
            d.line(pts, fill=_ACCENT, width=1)
        self._rule_h(d, 1236, w)
        d.text((36, 1248), "EDITORIAL  ·  STYLEKIT", font=f14, fill=_MUTE)
        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        ser48, ser36, ser24 = _serif(48), _serif(36), _serif(24)
        f14, f18, f22 = (load_font(n, True) for n in (14, 18, 22))

        d.text((28, 20), "SYSTEM", font=ser24, fill=_ACCENT)
        d.text((28, 48), "MONITOR", font=ser48, fill=_INK)
        d.text((420, 32), now.strftime("%A · %d %B %Y").upper(), font=f14, fill=_MUTE)
        text_right(d, (w - 28, 28), now.strftime("%H:%M:%S"), f22, _INK)
        text_right(d, (w - 28, 58), f"{snap.host[:16]} · {snap.fps:.0f} FPS", f14, _MUTE)
        self._rule_h(d, 108, w, margin=28)

        half = w // 2
        d.line([(half, 120), (half, 380)], fill=_RULE, width=1)

        d.text((28, 130), "01  PROCESSOR", font=f14, fill=_ACCENT)
        d.text((28, 162), f"{snap.cpu_usage:.0f}", font=ser48, fill=_INK)
        d.text((160, 192), "% LOAD", font=f18, fill=_MUTE)
        d.text((300, 162), f"{snap.cpu_temp:.0f}°", font=ser36, fill=_INK)
        d.text((28, 250), snap.cpu_name[:34], font=f14, fill=_MUTE)
        d.text((28, 278), f"{snap.cpu_clock:.0f} MHz   ·   {snap.cpu_fan:.0f} RPM", font=f14, fill=_INK)

        d.text((half + 28, 130), "02  GRAPHICS", font=f14, fill=_ACCENT)
        d.text((half + 28, 162), f"{snap.gpu_usage:.0f}", font=ser48, fill=_INK)
        d.text((half + 160, 192), "% LOAD", font=f18, fill=_MUTE)
        d.text((half + 300, 162), f"{snap.gpu_temp:.0f}°", font=ser36, fill=_INK)
        d.text((half + 28, 250), snap.gpu_name[:34], font=f14, fill=_MUTE)
        d.text((half + 28, 278), f"{snap.gpu_clock:.0f} MHz   ·   {snap.gpu_fan:.0f} RPM", font=f14, fill=_INK)
        self._rule_h(d, 390, w, margin=28)

        col = (w - 56) // 3
        x0, x1, x2 = 28, 28 + col + 8, 28 + 2 * col + 16
        d.line([(x1 - 4, 400), (x1 - 4, 660)], fill=_RULE, width=1)
        d.line([(x2 - 4, 400), (x2 - 4, 660)], fill=_RULE, width=1)

        d.text((x0, 412), "MEMORY", font=f14, fill=_ACCENT)
        d.text((x0, 448), f"{snap.ram_percent:.0f}%", font=ser36, fill=_INK)
        d.text((x0, 510), f"{snap.ram_used_mb:.0f} MB", font=f18, fill=_INK)
        d.text((x0, 542), f"of {snap.ram_total_gb:.0f} GB", font=f14, fill=_MUTE)

        d.text((x1, 412), "03  STORAGE", font=f14, fill=_ACCENT)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 452 + i * 52
            d.text((x1, y), str(name)[:10], font=f18, fill=_INK)
            d.rectangle((x1 + 120, y + 10, x2 - 36, y + 12), fill=(210, 205, 195))
            fw = int((x2 - x1 - 156) * max(0, min(100, pct)) / 100)
            d.rectangle((x1 + 120, y + 10, x1 + 120 + fw, y + 12), fill=_ACCENT)
            text_right(d, (x2 - 36, y), f"{pct:.0f}%", f14, _INK)

        d.text((x2, 412), "04  NETWORK", font=f14, fill=_ACCENT)
        d.text((x2, 452), "UPLOAD", font=f14, fill=_MUTE)
        d.text((x2, 478), fmt_net(snap.net_up_kb), font=ser24, fill=_INK)
        d.text((x2, 530), "DOWNLOAD", font=f14, fill=_MUTE)
        d.text((x2, 556), fmt_net(snap.net_down_kb), font=ser24, fill=_INK)
        pts = [(x2 + i * 6, 640 - int(14 * abs(math.sin(i * 0.35 + t * 2)))) for i in range(48)]
        if len(pts) > 1:
            d.line(pts, fill=_ACCENT, width=1)

        self._rule_h(d, 680, w, margin=28)
        d.text((28, 692), "EDITORIAL  ·  LANDSCAPE  ·  STYLEKIT", font=f14, fill=_MUTE)
        return img
