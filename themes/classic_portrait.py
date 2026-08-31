from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import clamp01, fmt_net, load_font, mix, text_right

_BG, _SURFACE, _LINE = (8, 11, 14), (14, 18, 22), (42, 49, 56)
_WHITE, _MUTED = (242, 245, 247), (137, 148, 158)
_CYAN, _GREEN, _AMBER, _RED = (65, 190, 230), (73, 205, 137), (244, 190, 61), (238, 86, 86)


class ClassicPortraitTheme(Theme):
    id = "classic_portrait"
    name = "Classic · 日常监控"
    width = 720
    height = 1280
    description = (
        "高可读日常仪表盘：温度、负载、内存与网络一眼可见。"
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
    def _color_for(value, warn=75, hot=90, normal=_GREEN):
        return _RED if value >= hot else _AMBER if value >= warn else normal

    @staticmethod
    def _card(d, box, title, accent=_LINE, font=None):
        d.rounded_rectangle(box, 14, fill=_SURFACE, outline=_LINE, width=2)
        d.rounded_rectangle((box[0], box[1], box[0] + 5, box[3]), 3, fill=accent)
        d.text((box[0] + 22, box[1] + 16), title, font=font, fill=_MUTED)

    @staticmethod
    def _bar(d, x0, y, x1, value, color):
        d.rounded_rectangle((x0, y, x1, y + 10), 5, fill=(31, 37, 43))
        x2 = x0 + int((x1 - x0) * clamp01(value / 100))
        if x2 > x0:
            d.rounded_rectangle((x0, y, x2, y + 10), 5, fill=color)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f16, f18, f22, f28, f40, f64 = (
            load_font(n, True) for n in (14, 16, 18, 22, 28, 40, 64)
        )
        color_for = self._color_for

        def card(box, title, accent=_LINE):
            self._card(d, box, title, accent, f16)

        def bar(x0, y, x1, value, color):
            self._bar(d, x0, y, x1, value, color)

        def compute_card(box, label, usage, temp, clock, fan, name, accent):
            x0, y0, x1, y1 = box
            card(box, label, accent)
            temp_c = color_for(temp, 70, 85, accent)
            d.text((x0 + 22, y0 + 52), f"{temp:.0f}", font=f64, fill=temp_c)
            d.text((x0 + 118, y0 + 84), "°C", font=f18, fill=_MUTED)
            d.text((x0 + 188, y0 + 58), f"{usage:.0f}%", font=f40, fill=_WHITE)
            d.text((x0 + 190, y0 + 104), "LOAD", font=f14, fill=_MUTED)
            bar(x0 + 22, y0 + 144, x1 - 22, usage, color_for(usage, normal=accent))
            d.text((x0 + 22, y0 + 176), f"{clock:.0f} MHz", font=f18, fill=_WHITE)
            text_right(d, (x1 - 22, y0 + 176), f"{fan:.0f} RPM", f18, _WHITE)
            d.text((x0 + 22, y0 + 210), name[:30], font=f14, fill=_MUTED)

        d.text((36, 32), now.strftime("%H:%M"), font=f40, fill=_WHITE)
        d.text((38, 82), now.strftime("%a · %d %b"), font=f14, fill=_MUTED)
        text_right(d, (w - 36, 38), snap.host[:24], f18, _WHITE)
        text_right(d, (w - 36, 70), snap.source.upper(), f14, _CYAN)
        d.line((36, 116, w - 36, 116), fill=_LINE, width=2)

        compute_card(
            (28, 142, w - 28, 394),
            "CPU",
            snap.cpu_usage,
            snap.cpu_temp,
            snap.cpu_clock,
            snap.cpu_fan,
            snap.cpu_name,
            _CYAN,
        )
        compute_card(
            (28, 414, w - 28, 666),
            "GPU",
            snap.gpu_usage,
            snap.gpu_temp,
            snap.gpu_clock,
            snap.gpu_fan,
            snap.gpu_name,
            _GREEN,
        )

        card((28, 686, w - 28, 824), "MEMORY", _CYAN)
        d.text((50, 728), f"{snap.ram_percent:.0f}%", font=f40, fill=_WHITE)
        d.text(
            (174, 744),
            f"{snap.ram_used_mb / 1024:.1f} / {snap.ram_total_gb:.0f} GB",
            font=f18,
            fill=_MUTED,
        )
        bar(50, 790, w - 50, snap.ram_percent, color_for(snap.ram_percent, 80, 92, _CYAN))

        card((28, 844, w - 28, 1010), "STORAGE", _GREEN)
        disks = snap.disks[:3]
        if not disks:
            d.text((50, 900), "No disk data", font=f18, fill=_MUTED)
        for i, (name, pct) in enumerate(disks):
            y = 886 + i * 38
            d.text((50, y), str(name)[:12], font=f16, fill=_WHITE)
            bar(174, y + 5, 570, pct, mix(_GREEN, _RED, clamp01(pct / 100)))
            text_right(d, (w - 50, y), f"{pct:.0f}%", f16, _MUTED)

        card((28, 1030, w - 28, 1244), "NETWORK", _CYAN)
        d.text((50, 1075), "DOWNLOAD", font=f14, fill=_MUTED)
        d.text((50, 1100), fmt_net(snap.net_down_kb), font=f28, fill=_WHITE)
        d.text((370, 1075), "UPLOAD", font=f14, fill=_MUTED)
        d.text((370, 1100), fmt_net(snap.net_up_kb), font=f28, fill=_WHITE)
        pts = [
            (
                x,
                1204 - int(14 * (0.25 + 0.75 * abs(math.sin(i * 0.31 + t * 2.2)))),
            )
            for i, x in enumerate(range(50, w - 50, 6))
        ]
        if len(pts) > 1:
            d.line(pts, fill=(36, 88, 105), width=2)
        d.text((50, 1216), "LIVE SYSTEM OVERVIEW", font=f14, fill=_MUTED)
        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f16, f18, f22, f28, f40, f56 = (
            load_font(n, True) for n in (14, 16, 18, 22, 28, 40, 56)
        )
        color_for = self._color_for

        def card(box, title, accent=_LINE):
            self._card(d, box, title, accent, f16)

        def bar(x0, y, x1, value, color):
            self._bar(d, x0, y, x1, value, color)

        def compute_card(box, label, usage, temp, clock, fan, name, accent):
            x0, y0, x1, y1 = box
            card(box, label, accent)
            temp_c = color_for(temp, 70, 85, accent)
            d.text((x0 + 22, y0 + 48), f"{temp:.0f}", font=f56, fill=temp_c)
            d.text((x0 + 110, y0 + 76), "°C", font=f18, fill=_MUTED)
            d.text((x0 + 180, y0 + 52), f"{usage:.0f}%", font=f40, fill=_WHITE)
            d.text((x0 + 182, y0 + 98), "LOAD", font=f14, fill=_MUTED)
            bar(x0 + 22, y0 + 130, x1 - 22, usage, color_for(usage, normal=accent))
            d.text((x0 + 22, y0 + 160), f"{clock:.0f} MHz", font=f18, fill=_WHITE)
            text_right(d, (x1 - 22, y0 + 160), f"{fan:.0f} RPM", f18, _WHITE)
            d.text((x0 + 22, y0 + 192), name[:34], font=f14, fill=_MUTED)

        d.text((28, 18), now.strftime("%H:%M"), font=f40, fill=_WHITE)
        d.text((200, 28), now.strftime("%a · %d %b"), font=f14, fill=_MUTED)
        d.text((200, 52), f"{snap.host[:28]} · {snap.source.upper()}", font=f16, fill=_MUTED)
        text_right(d, (w - 28, 24), "CLASSIC · LANDSCAPE", f14, _CYAN)
        d.line((28, 82, w - 28, 82), fill=_LINE, width=2)

        compute_card(
            (20, 98, w // 2 - 10, 350),
            "CPU",
            snap.cpu_usage,
            snap.cpu_temp,
            snap.cpu_clock,
            snap.cpu_fan,
            snap.cpu_name,
            _CYAN,
        )
        compute_card(
            (w // 2 + 10, 98, w - 20, 350),
            "GPU",
            snap.gpu_usage,
            snap.gpu_temp,
            snap.gpu_clock,
            snap.gpu_fan,
            snap.gpu_name,
            _GREEN,
        )

        col = (w - 56) // 3
        b0 = (20, 370, 20 + col, h - 20)
        b1 = (20 + col + 8, 370, 20 + 2 * col + 8, h - 20)
        b2 = (20 + 2 * col + 16, 370, w - 20, h - 20)

        card(b0, "MEMORY", _CYAN)
        d.text((b0[0] + 22, 420), f"{snap.ram_percent:.0f}%", font=f40, fill=_WHITE)
        d.text(
            (b0[0] + 22, 480),
            f"{snap.ram_used_mb / 1024:.1f} / {snap.ram_total_gb:.0f} GB",
            font=f16,
            fill=_MUTED,
        )
        bar(
            b0[0] + 22,
            540,
            b0[2] - 22,
            snap.ram_percent,
            color_for(snap.ram_percent, 80, 92, _CYAN),
        )

        card(b1, "STORAGE", _GREEN)
        disks = snap.disks[:3]
        if not disks:
            d.text((b1[0] + 22, 440), "No disk data", font=f18, fill=_MUTED)
        for i, (name, pct) in enumerate(disks):
            y = 420 + i * 58
            d.text((b1[0] + 22, y), str(name)[:12], font=f16, fill=_WHITE)
            bar(b1[0] + 22, y + 26, b1[2] - 22, pct, mix(_GREEN, _RED, clamp01(pct / 100)))
            text_right(d, (b1[2] - 22, y), f"{pct:.0f}%", f16, _MUTED)

        card(b2, "NETWORK", _CYAN)
        d.text((b2[0] + 22, 420), "DOWNLOAD", font=f14, fill=_MUTED)
        d.text((b2[0] + 22, 448), fmt_net(snap.net_down_kb), font=f28, fill=_WHITE)
        d.text((b2[0] + 22, 500), "UPLOAD", font=f14, fill=_MUTED)
        d.text((b2[0] + 22, 528), fmt_net(snap.net_up_kb), font=f28, fill=_WHITE)
        pts = [
            (
                x,
                640 - int(14 * (0.25 + 0.75 * abs(math.sin(i * 0.31 + t * 2.2)))),
            )
            for i, x in enumerate(range(b2[0] + 22, b2[2] - 22, 6))
        ]
        if len(pts) > 1:
            d.line(pts, fill=(36, 88, 105), width=2)
        d.text((b2[0] + 22, 660), "LIVE OVERVIEW", font=f14, fill=_MUTED)
        return img
