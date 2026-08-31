from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import clamp01, fmt_net, load_font, text_right

_BG, _PANEL = (3, 15, 23), (5, 25, 35)
_CYAN, _CYAN2, _LIME, _ORANGE = (49, 211, 238), (23, 116, 139), (148, 236, 93), (255, 148, 66)
_WHITE, _DIM, _TRACK = (231, 244, 246), (94, 142, 153), (11, 48, 61)


class CyanHudPortraitTheme(Theme):
    id = "cyan_hud_portrait"
    name = "Cyan HUD · 沉浸科技"
    width = 720
    height = 1280
    description = (
        "低噪点青色 HUD：以动态负载、温度和实时状态为视觉焦点。"
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
    def _label(d, xy, value, font, color=_DIM):
        d.text(xy, value, font=font, fill=color)

    @staticmethod
    def _segbar(d, x, y, value, width, active):
        count, gap = 16, 4
        sw = (width - gap * (count - 1)) // count
        on = int(round(clamp01(value / 100) * count))
        for i in range(count):
            col = active if i < on else _TRACK
            d.rounded_rectangle(
                (x + i * (sw + gap), y, x + i * (sw + gap) + sw, y + 12), 2, fill=col
            )

    @staticmethod
    def _corners(d, box, color=_CYAN2):
        x0, y0, x1, y1 = box
        n = 22
        paths = (
            ((x0, y0 + n), (x0, y0), (x0 + n, y0)),
            ((x1 - n, y0), (x1, y0), (x1, y0 + n)),
            ((x0, y1 - n), (x0, y1), (x0 + n, y1)),
            ((x1 - n, y1), (x1, y1), (x1, y1 - n)),
        )
        for path in paths:
            d.line(path, fill=color, width=2)

    def _core(self, d, box, title, usage, temp, clock, fan, name, accent, fonts):
        f12, f14, f20, f28, f42, f80 = fonts
        x0, y0, x1, y1 = box
        d.rounded_rectangle(box, 10, fill=_PANEL, outline=_TRACK, width=2)
        self._corners(d, box)
        d.text((x0 + 24, y0 + 22), title, font=f20, fill=accent)
        self._label(d, (x0 + 24, y0 + 58), "LOAD", f14)
        d.text((x0 + 22, y0 + 72), f"{usage:02.0f}", font=f80, fill=_WHITE)
        d.text((x0 + 139, y0 + 118), "%", font=f20, fill=_DIM)
        self._label(d, (x0 + 232, y0 + 66), "THERMAL", f14)
        d.text(
            (x0 + 230, y0 + 84),
            f"{temp:.0f}°",
            font=f42,
            fill=_ORANGE if temp >= 80 else accent,
        )
        self._label(d, (x0 + 430, y0 + 66), "CLOCK", f14)
        d.text((x0 + 430, y0 + 89), f"{clock:.0f}", font=f28, fill=_WHITE)
        self._label(d, (x0 + 430, y0 + 126), "MHz", f14)
        self._segbar(d, x0 + 24, y0 + 174, usage, x1 - x0 - 48, accent)
        self._label(d, (x0 + 24, y0 + 204), name[:26], f14)
        text_right(d, (x1 - 24, y0 + 204), f"FAN {fan:.0f} RPM", f14, _DIM)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f12, f14, f16, f20, f28, f42, f80 = (
            load_font(n, True) for n in (12, 14, 16, 20, 28, 42, 80)
        )
        fonts = (f12, f14, f20, f28, f42, f80)

        d.line((30, 34, 206, 34, 236, 58, w - 30, 58), fill=_CYAN2, width=2)
        d.text((38, 78), "SYSTEM / HUD", font=f16, fill=_CYAN)
        d.text((38, 106), now.strftime("%H:%M:%S"), font=f42, fill=_WHITE)
        self._label(d, (40, 160), now.strftime("%Y.%m.%d  %a").upper(), f14)
        text_right(d, (w - 38, 90), snap.host[:20], f16, _DIM)
        text_right(d, (w - 38, 122), snap.source.upper(), f14, _CYAN)
        d.ellipse((w - 56, 158, w - 46, 168), fill=_LIME)
        text_right(d, (w - 64, 154), "LINK ONLINE", f12, _DIM)

        self._core(
            d,
            (28, 206, w - 28, 458),
            "CPU / CORE",
            snap.cpu_usage,
            snap.cpu_temp,
            snap.cpu_clock,
            snap.cpu_fan,
            snap.cpu_name,
            _CYAN,
            fonts,
        )
        self._core(
            d,
            (28, 478, w - 28, 730),
            "GPU / GRAPHICS",
            snap.gpu_usage,
            snap.gpu_temp,
            snap.gpu_clock,
            snap.gpu_fan,
            snap.gpu_name,
            _LIME,
            fonts,
        )

        d.rounded_rectangle((28, 750, w - 28, 912), 10, fill=_PANEL, outline=_TRACK, width=2)
        self._corners(d, (28, 750, w - 28, 912))
        d.text((52, 774), "MEMORY", font=f16, fill=_CYAN)
        d.text((52, 805), f"{snap.ram_percent:.0f}%", font=f42, fill=_WHITE)
        self._label(
            d,
            (184, 826),
            f"{snap.ram_used_mb / 1024:.1f} / {snap.ram_total_gb:.0f} GB",
            f14,
        )
        self._segbar(d, 52, 872, snap.ram_percent, w - 104, _LIME)

        d.text((40, 944), "STORAGE / VOLUMES", font=f16, fill=_CYAN)
        disks = snap.disks[:3]
        if not disks:
            self._label(d, (40, 984), "NO DISK TELEMETRY", f14)
        for i, (name, pct) in enumerate(disks):
            y = 982 + i * 48
            d.text((40, y), str(name)[:12], font=f16, fill=_WHITE)
            self._segbar(d, 170, y + 4, pct, 390, _CYAN)
            text_right(d, (w - 40, y), f"{pct:.0f}%", f16, _DIM)

        d.line((30, 1136, w - 30, 1136), fill=_CYAN2, width=2)
        d.text((40, 1160), "NETWORK", font=f16, fill=_CYAN)
        d.text((40, 1192), f"DN  {fmt_net(snap.net_down_kb)}", font=f20, fill=_WHITE)
        d.text((360, 1192), f"UP  {fmt_net(snap.net_up_kb)}", font=f20, fill=_WHITE)
        pts = [
            (x, 1252 - int(11 * abs(math.sin(i * 0.38 + t * 2.8))))
            for i, x in enumerate(range(40, w - 40, 5))
        ]
        if len(pts) > 1:
            d.line(pts, fill=_CYAN2, width=2)
        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f12, f14, f16, f20, f28, f42, f56 = (
            load_font(n, True) for n in (12, 14, 16, 20, 28, 42, 56)
        )
        fonts = (f12, f14, f20, f28, f42, f56)

        d.line((24, 28, 180, 28, 210, 52, w - 24, 52), fill=_CYAN2, width=2)
        d.text((32, 64), "SYSTEM / HUD", font=f16, fill=_CYAN)
        d.text((32, 88), now.strftime("%H:%M:%S"), font=f42, fill=_WHITE)
        self._label(d, (240, 72), now.strftime("%Y.%m.%d  %a").upper(), f14)
        text_right(d, (w - 32, 68), snap.host[:24], f16, _DIM)
        text_right(d, (w - 32, 96), snap.source.upper(), f14, _CYAN)
        d.ellipse((w - 48, 118, w - 38, 128), fill=_LIME)
        text_right(d, (w - 56, 114), "LINK ONLINE", f12, _DIM)

        self._core(
            d,
            (20, 140, 620, 380),
            "CPU / CORE",
            snap.cpu_usage,
            snap.cpu_temp,
            snap.cpu_clock,
            snap.cpu_fan,
            snap.cpu_name,
            _CYAN,
            fonts,
        )
        self._core(
            d,
            (660, 140, w - 20, 380),
            "GPU / GRAPHICS",
            snap.gpu_usage,
            snap.gpu_temp,
            snap.gpu_clock,
            snap.gpu_fan,
            snap.gpu_name,
            _LIME,
            fonts,
        )

        d.rounded_rectangle((20, 400, 400, 700), 10, fill=_PANEL, outline=_TRACK, width=2)
        self._corners(d, (20, 400, 400, 700))
        d.text((44, 424), "MEMORY", font=f16, fill=_CYAN)
        d.text((44, 460), f"{snap.ram_percent:.0f}%", font=f42, fill=_WHITE)
        self._label(
            d,
            (44, 520),
            f"{snap.ram_used_mb / 1024:.1f} / {snap.ram_total_gb:.0f} GB",
            f14,
        )
        self._segbar(d, 44, 580, snap.ram_percent, 320, _LIME)

        d.rounded_rectangle((420, 400, 840, 700), 10, fill=_PANEL, outline=_TRACK, width=2)
        self._corners(d, (420, 400, 840, 700))
        d.text((444, 424), "STORAGE / VOLUMES", font=f16, fill=_CYAN)
        disks = snap.disks[:3]
        if not disks:
            self._label(d, (444, 470), "NO DISK TELEMETRY", f14)
        for i, (name, pct) in enumerate(disks):
            y = 470 + i * 58
            d.text((444, y), str(name)[:12], font=f16, fill=_WHITE)
            self._segbar(d, 560, y + 4, pct, 220, _CYAN)
            text_right(d, (820, y), f"{pct:.0f}%", f16, _DIM)

        d.rounded_rectangle((860, 400, w - 20, 700), 10, fill=_PANEL, outline=_TRACK, width=2)
        self._corners(d, (860, 400, w - 20, 700))
        d.text((884, 424), "NETWORK", font=f16, fill=_CYAN)
        d.text((884, 470), f"DN  {fmt_net(snap.net_down_kb)}", font=f20, fill=_WHITE)
        d.text((884, 520), f"UP  {fmt_net(snap.net_up_kb)}", font=f20, fill=_WHITE)
        pts = [
            (884 + i * 7, 660 - int(14 * abs(math.sin(i * 0.38 + t * 2.8))))
            for i in range(48)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_CYAN2, width=2)

        return img
