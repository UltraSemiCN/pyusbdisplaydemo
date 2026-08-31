from __future__ import annotations

"""Mecha / 机甲风竖屏主题（StyleKit mecha hard prompt）。

规则落地（PIL）：
- 直角装甲面板（禁止柔和圆角）
- 军绿边框 #4a5c3a + 深蓝面板 #1a2744
- 警告黄 #fbbf24 / 危险红，硬边偏移阴影
- 等宽技术标注、大写标题
"""

import math
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import clamp01, fmt_net, text_right


def _mono(size: int, bold: bool = True) -> ImageFont.ImageFont:
    windir = Path(r"C:\Windows\Fonts")
    names = (
        ["consolab.ttf", "CascadiaMono.ttf", "lucon.ttf", "courbd.ttf"]
        if bold
        else ["consola.ttf", "CascadiaMono.ttf", "lucon.ttf", "cour.ttf"]
    )
    for name in names:
        path = windir / name
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


_NAVY = (14, 22, 40)
_PANEL = (26, 39, 68)
_OLIVE = (74, 92, 58)
_WARN = (251, 191, 36)
_DANGER = (220, 38, 38)
_OK = (132, 168, 90)
_INK = (236, 240, 230)
_DIM = (148, 162, 130)
_TRACK = (32, 44, 56)


class MechaPortraitTheme(Theme):
    id = "mecha_portrait"
    name = "机甲风 Mecha"
    width = 720
    height = 1280
    description = "StyleKit Mecha：军绿装甲、警告黄、直角工业面板。0°/180° 竖屏；90°/270° 横屏。"

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
    def _severity(v: float, warn_at: float = 75, hot: float = 90) -> tuple[int, int, int]:
        return _DANGER if v >= hot else _WARN if v >= warn_at else _OK

    @staticmethod
    def _grid(d: ImageDraw.ImageDraw, w: int, h: int) -> None:
        for x in range(0, w, 40):
            d.line((x, 0, x, h), fill=(20, 30, 48), width=1)
        for y in range(0, h, 40):
            d.line((0, y, w, y), fill=(20, 30, 48), width=1)

    @staticmethod
    def _hard_shadow(d: ImageDraw.ImageDraw, box, shift: int = 4) -> None:
        x0, y0, x1, y1 = box
        d.rectangle((x0 + shift, y0 + shift, x1 + shift, y1 + shift), fill=(60, 48, 16))

    def _armor(
        self,
        d: ImageDraw.ImageDraw,
        box,
        fill=_PANEL,
        border=_OLIVE,
        shadow: int = 4,
    ) -> None:
        if shadow:
            self._hard_shadow(d, box, shadow)
        d.rectangle(box, fill=fill, outline=border, width=2)

    @staticmethod
    def _hazard_stripe(d: ImageDraw.ImageDraw, x0, y0, x1, y1, band: int = 10) -> None:
        d.rectangle((x0, y0, x1, y1), fill=(40, 32, 12))
        step = band * 2
        for i, x in enumerate(range(x0 - y1, x1 + y1, step)):
            pts = [
                (x, y1),
                (x + band, y1),
                (x + band + (y1 - y0), y0),
                (x + (y1 - y0), y0),
            ]
            d.polygon(pts, fill=_WARN if i % 2 == 0 else (20, 16, 8))

    @staticmethod
    def _bar(d: ImageDraw.ImageDraw, x0, y, x1, value, color) -> None:
        d.rectangle((x0, y, x1, y + 12), fill=_TRACK, outline=_OLIVE, width=2)
        fill_w = int((x1 - x0 - 4) * clamp01(value / 100))
        if fill_w > 0:
            d.rectangle((x0 + 2, y + 2, x0 + 2 + fill_w, y + 10), fill=color)

    @staticmethod
    def _label(d: ImageDraw.ImageDraw, xy, text, font, fill=_DIM) -> None:
        d.text(xy, text.upper(), font=font, fill=fill)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _NAVY)
        d = ImageDraw.Draw(img)
        f12, f14, f16, f20, f28, f40, f64 = (_mono(n) for n in (12, 14, 16, 20, 28, 40, 64))
        severity = self._severity
        armor = lambda box, **kw: self._armor(d, box, **kw)
        bar = self._bar
        label = lambda xy, text, font=f14, fill=_DIM: self._label(d, xy, text, font, fill)

        self._grid(d, w, h)

        self._hazard_stripe(d, 0, 0, w, 18)
        armor((20, 36, w - 20, 150), fill=_PANEL, shadow=4)
        d.rectangle((20, 36, 28, 150), fill=_WARN)
        label((40, 48), "UNIT / TELEMETRY", f14, _WARN)
        d.text((40, 72), now.strftime("%H:%M:%S"), font=f40, fill=_WARN)
        label((40, 120), f"{snap.host[:20]}  ·  SRC {snap.source.upper()}", f12, _DIM)
        fps_s = f"{snap.fps:.0f}" if snap.fps > 0.05 else "--"
        text_right(d, (w - 40, 72), fps_s, f40, _INK)
        text_right(d, (w - 40, 120), "FPS", f14, _WARN)

        hot = snap.cpu_temp >= 85 or snap.gpu_temp >= 85
        armor((20, 168, 350, 220), fill=(48, 20, 20) if hot else (24, 36, 28), shadow=3)
        d.text(
            (36, 182),
            "ALERT  HOT" if hot else "STATUS  NOMINAL",
            font=f16,
            fill=_DANGER if hot else _OK,
        )
        armor((370, 168, w - 20, 220), fill=_PANEL, shadow=3)
        label((386, 186), f"FRAME  MECHA-{now.strftime('%y%m%d')}", f14, _DIM)

        armor((20, 240, w - 20, 480))
        d.rectangle((20, 240, 160, 280), fill=_WARN)
        d.text((36, 248), "CPU", font=f20, fill=_NAVY)
        d.text((40, 300), f"{snap.cpu_usage:02.0f}", font=f64, fill=_INK)
        d.text((200, 340), "%", font=f20, fill=_DIM)
        d.text((280, 300), f"{snap.cpu_temp:.0f}", font=f40, fill=severity(snap.cpu_temp))
        d.text((400, 320), "°C", font=f16, fill=_DIM)
        label((40, 390), f"CLK  {snap.cpu_clock:.0f} MHZ", f14, _DIM)
        label((40, 416), f"FAN  {snap.cpu_fan:.0f} RPM", f14, _DIM)
        label((40, 442), snap.cpu_name[:28], f12, _DIM)
        bar(d, 280, 400, w - 48, snap.cpu_usage, severity(snap.cpu_usage))

        armor((20, 500, w - 20, 740))
        d.rectangle((20, 500, 160, 540), fill=_OLIVE)
        d.text((36, 508), "GPU", font=f20, fill=_WARN)
        d.text((40, 560), f"{snap.gpu_usage:02.0f}", font=f64, fill=_INK)
        d.text((200, 600), "%", font=f20, fill=_DIM)
        d.text((280, 560), f"{snap.gpu_temp:.0f}", font=f40, fill=severity(snap.gpu_temp))
        d.text((400, 580), "°C", font=f16, fill=_DIM)
        label((40, 650), f"CLK  {snap.gpu_clock:.0f} MHZ", f14, _DIM)
        label((40, 676), f"FAN  {snap.gpu_fan:.0f} RPM", f14, _DIM)
        label((40, 702), snap.gpu_name[:28], f12, _DIM)
        bar(d, 280, 660, w - 48, snap.gpu_usage, severity(snap.gpu_usage))

        armor((20, 760, w - 20, 920))
        label((40, 780), "MEMORY BANK", f16, _WARN)
        d.text((40, 820), f"{snap.ram_percent:.0f}%", font=f40, fill=severity(snap.ram_percent))
        label(
            (200, 838),
            f"{snap.ram_used_mb / 1024:.1f} / {snap.ram_total_gb:.0f} GB",
            f14,
            _DIM,
        )
        bar(d, 40, 880, w - 48, snap.ram_percent, _WARN)

        armor((20, 940, 350, 1140))
        label((36, 958), "STORAGE", f14, _WARN)
        disks = (snap.disks + [("D:/", 0), ("E:/", 0)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 1000 + i * 40
            d.text((36, y), str(name)[:8].upper(), font=f12, fill=_DIM)
            bar(d, 110, y + 2, 330, pct, severity(pct, 80, 95))

        armor((370, 940, w - 20, 1140))
        label((386, 958), "NETWORK", f14, _WARN)
        d.text((386, 1000), f"UP  {fmt_net(snap.net_up_kb)}", font=f16, fill=_OK)
        d.text((386, 1036), f"DN  {fmt_net(snap.net_down_kb)}", font=f16, fill=_WARN)
        pts = [
            (386 + i * 6, 1108 - int(18 * abs(math.sin(i * 0.35 + t * 2.8))))
            for i in range(48)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_WARN, width=2)

        self._hazard_stripe(d, 0, 1160, w, 1178)
        armor((20, 1190, w - 20, 1260), shadow=3)
        label((40, 1210), now.strftime("%a %Y-%m-%d").upper(), f14, _DIM)
        text_right(d, (w - 40, 1210), "MECHA / MS-DISPLAY", f14, _WARN)
        label((40, 1236), "SHARP PANEL  ·  NO GLASS  ·  HARD SHADOW", f12, _DIM)

        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _NAVY)
        d = ImageDraw.Draw(img)
        f12, f14, f16, f20, f28, f40, f56 = (_mono(n) for n in (12, 14, 16, 20, 28, 40, 56))
        severity = self._severity
        armor = lambda box, **kw: self._armor(d, box, **kw)
        bar = self._bar
        label = lambda xy, text, font=f14, fill=_DIM: self._label(d, xy, text, font, fill)

        self._grid(d, w, h)
        self._hazard_stripe(d, 0, 0, w, 16)

        armor((16, 24, w - 16, 108), fill=_PANEL, shadow=4)
        d.rectangle((16, 24, 24, 108), fill=_WARN)
        label((36, 36), "UNIT / TELEMETRY", f14, _WARN)
        d.text((36, 56), now.strftime("%H:%M:%S"), font=f40, fill=_WARN)
        label((280, 40), f"{snap.host[:24]}  ·  SRC {snap.source.upper()}", f12, _DIM)
        label((280, 68), now.strftime("%a %Y-%m-%d").upper(), f12, _DIM)
        fps_s = f"{snap.fps:.0f}" if snap.fps > 0.05 else "--"
        text_right(d, (w - 36, 52), fps_s, f40, _INK)
        text_right(d, (w - 36, 84), "FPS", f14, _WARN)

        hot = snap.cpu_temp >= 85 or snap.gpu_temp >= 85
        armor((16, 120, 280, 168), fill=(48, 20, 20) if hot else (24, 36, 28), shadow=3)
        d.text(
            (32, 134),
            "ALERT  HOT" if hot else "STATUS  NOMINAL",
            font=f14,
            fill=_DANGER if hot else _OK,
        )
        armor((300, 120, w - 16, 168), fill=_PANEL, shadow=3)
        label((316, 138), f"FRAME  MECHA-{now.strftime('%y%m%d')}", f14, _DIM)

        armor((16, 184, 620, 420))
        d.rectangle((16, 184, 140, 220), fill=_WARN)
        d.text((32, 190), "CPU", font=f20, fill=_NAVY)
        d.text((36, 240), f"{snap.cpu_usage:02.0f}", font=f56, fill=_INK)
        d.text((180, 270), "%", font=f20, fill=_DIM)
        d.text((260, 240), f"{snap.cpu_temp:.0f}", font=f40, fill=severity(snap.cpu_temp))
        d.text((380, 260), "°C", font=f16, fill=_DIM)
        label((36, 310), f"CLK  {snap.cpu_clock:.0f} MHZ", f14, _DIM)
        label((36, 336), f"FAN  {snap.cpu_fan:.0f} RPM", f14, _DIM)
        label((36, 362), snap.cpu_name[:32], f12, _DIM)
        bar(d, 260, 380, 580, snap.cpu_usage, severity(snap.cpu_usage))

        armor((660, 184, w - 16, 420))
        d.rectangle((660, 184, 784, 220), fill=_OLIVE)
        d.text((676, 190), "GPU", font=f20, fill=_WARN)
        d.text((680, 240), f"{snap.gpu_usage:02.0f}", font=f56, fill=_INK)
        d.text((824, 270), "%", font=f20, fill=_DIM)
        d.text((904, 240), f"{snap.gpu_temp:.0f}", font=f40, fill=severity(snap.gpu_temp))
        d.text((1024, 260), "°C", font=f16, fill=_DIM)
        label((680, 310), f"CLK  {snap.gpu_clock:.0f} MHZ", f14, _DIM)
        label((680, 336), f"FAN  {snap.gpu_fan:.0f} RPM", f14, _DIM)
        label((680, 362), snap.gpu_name[:28], f12, _DIM)
        bar(d, 904, 380, w - 36, snap.gpu_usage, severity(snap.gpu_usage))

        armor((16, 440, 360, h - 24))
        label((32, 458), "MEMORY BANK", f16, _WARN)
        d.text((32, 500), f"{snap.ram_percent:.0f}%", font=f40, fill=severity(snap.ram_percent))
        label(
            (32, 560),
            f"{snap.ram_used_mb / 1024:.1f} / {snap.ram_total_gb:.0f} GB",
            f14,
            _DIM,
        )
        bar(d, 32, 620, 340, snap.ram_percent, _WARN)

        armor((380, 440, 820, h - 24))
        label((396, 458), "STORAGE", f14, _WARN)
        disks = (snap.disks + [("D:/", 0), ("E:/", 0)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 510 + i * 56
            d.text((396, y), str(name)[:8].upper(), font=f12, fill=_DIM)
            bar(d, 470, y + 2, 780, pct, severity(pct, 80, 95))

        armor((840, 440, w - 16, h - 24))
        label((856, 458), "NETWORK", f14, _WARN)
        d.text((856, 510), f"UP  {fmt_net(snap.net_up_kb)}", font=f20, fill=_OK)
        d.text((856, 560), f"DN  {fmt_net(snap.net_down_kb)}", font=f20, fill=_WARN)
        pts = [
            (856 + i * 7, 660 - int(16 * abs(math.sin(i * 0.35 + t * 2.8))))
            for i in range(52)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_WARN, width=2)
        text_right(d, (w - 36, 660), "MECHA / MS-DISPLAY", f14, _WARN)

        self._hazard_stripe(d, 0, h - 16, w, h)
        return img
