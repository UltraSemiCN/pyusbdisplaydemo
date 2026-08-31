from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import clamp01, fmt_net, load_font, mix, text_right

_BG, _PANEL, _LINE = (4, 5, 6), (10, 12, 14), (47, 52, 56)
_WHITE, _GRAY = (235, 238, 239), (139, 147, 151)
_YELLOW, _CYAN, _GREEN, _AMBER, _RED = (
    (241, 212, 74),
    (52, 181, 218),
    (61, 195, 126),
    (245, 159, 54),
    (232, 73, 76),
)


class Aida64DensePortraitTheme(Theme):
    id = "aida64_dense_portrait"
    name = "AIDA64 Dense · 专家监控"
    width = 720
    height = 1280
    description = (
        "高密度专家视图：只展示真实采集指标，异常状态优先显色。"
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
    def _severity(value, warn=75, hot=90, normal=_GREEN):
        return _RED if value >= hot else _AMBER if value >= warn else normal

    @staticmethod
    def _panel_box(d, box, title, accent=_YELLOW, font=None):
        d.rounded_rectangle(box, 8, fill=_PANEL, outline=_LINE, width=2)
        d.rectangle((box[0], box[1], box[0] + 4, box[3]), fill=accent)
        d.text((box[0] + 16, box[1] + 11), title, font=font, fill=_GRAY)

    @staticmethod
    def _progress(d, x0, y, x1, value, color):
        d.rectangle((x0, y, x1, y + 8), fill=(29, 33, 36))
        x2 = x0 + int((x1 - x0) * clamp01(value / 100))
        if x2 > x0:
            d.rectangle((x0, y, x2, y + 8), fill=color)

    @staticmethod
    def _metric(d, x, y, label, value, color=_WHITE, right=None, f12=None, f18=None):
        d.text((x, y), label, font=f12, fill=_GRAY)
        if right is None:
            d.text((x, y + 18), value, font=f18, fill=color)
        else:
            text_right(d, (right, y + 18), value, f18, color)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f12, f14, f16, f18, f22, f30, f48 = (
            load_font(n, True) for n in (12, 14, 16, 18, 22, 30, 48)
        )
        severity = self._severity
        panel_box = lambda box, title, accent=_YELLOW: self._panel_box(
            d, box, title, accent, f14
        )
        progress = lambda x0, y, x1, value, color: self._progress(d, x0, y, x1, value, color)
        metric = lambda x, y, label, value, color=_WHITE, right=None: self._metric(
            d, x, y, label, value, color, right, f12, f18
        )

        d.text((24, 20), "SYSTEM TELEMETRY", font=f18, fill=_YELLOW)
        d.text((24, 49), snap.host[:24], font=f14, fill=_GRAY)
        text_right(d, (w - 24, 18), now.strftime("%H:%M:%S"), f22, _WHITE)
        fps_s = f"{snap.fps:.0f} FPS" if snap.fps > 0.05 else "FPS --"
        text_right(d, (w - 24, 51), f"{snap.source.upper()}  ·  {fps_s}", f12, _CYAN)
        d.line((24, 78, w - 24, 78), fill=_LINE, width=2)

        panel_box((20, 94, 700, 286), "PRIMARY HEALTH", _RED)
        primary = (
            ("CPU TEMP", snap.cpu_temp, "°C", _CYAN, 85),
            ("CPU LOAD", snap.cpu_usage, "%", _CYAN, 90),
            ("GPU TEMP", snap.gpu_temp, "°C", _GREEN, 85),
            ("GPU LOAD", snap.gpu_usage, "%", _GREEN, 90),
        )
        for i, (lab, val, unit, accent, hot) in enumerate(primary):
            x = 42 + (i % 2) * 334
            y = 132 + (i // 2) * 72
            col = severity(val, hot - 12, hot, accent)
            d.text((x, y), lab, font=f14, fill=_GRAY)
            d.text((x, y + 21), f"{val:.0f}{unit}", font=f30, fill=col)
            progress(x + 118, y + 35, x + 290, val, col)

        panel_box((20, 304, 350, 500), "CPU / PROCESSOR", _CYAN)
        metric(42, 344, "CLOCK", f"{snap.cpu_clock:.0f} MHz")
        metric(190, 344, "FAN", f"{snap.cpu_fan:.0f} RPM")
        d.text((42, 402), "MODEL", font=f12, fill=_GRAY)
        d.text((42, 423), snap.cpu_name[:26], font=f16, fill=_WHITE)
        d.text(
            (42, 464),
            f"LOAD {snap.cpu_usage:.0f}%",
            font=f16,
            fill=severity(snap.cpu_usage, normal=_CYAN),
        )
        text_right(
            d,
            (326, 464),
            f"TEMP {snap.cpu_temp:.0f}°C",
            f16,
            severity(snap.cpu_temp, 73, 85, _CYAN),
        )

        panel_box((370, 304, 700, 500), "GPU / GRAPHICS", _GREEN)
        metric(392, 344, "CLOCK", f"{snap.gpu_clock:.0f} MHz")
        metric(540, 344, "FAN", f"{snap.gpu_fan:.0f} RPM")
        d.text((392, 402), "MODEL", font=f12, fill=_GRAY)
        d.text((392, 423), snap.gpu_name[:26], font=f16, fill=_WHITE)
        d.text(
            (392, 464),
            f"LOAD {snap.gpu_usage:.0f}%",
            font=f16,
            fill=severity(snap.gpu_usage, normal=_GREEN),
        )
        text_right(
            d,
            (676, 464),
            f"TEMP {snap.gpu_temp:.0f}°C",
            f16,
            severity(snap.gpu_temp, 73, 85, _GREEN),
        )

        panel_box((20, 518, 700, 666), "MEMORY", _YELLOW)
        d.text(
            (42, 558),
            f"{snap.ram_percent:.0f}%",
            font=f48,
            fill=severity(snap.ram_percent, 80, 92, _YELLOW),
        )
        d.text((174, 572), "USED", font=f12, fill=_GRAY)
        d.text((174, 592), f"{snap.ram_used_mb / 1024:.1f} GB", font=f22, fill=_WHITE)
        d.text((360, 572), "TOTAL", font=f12, fill=_GRAY)
        d.text((360, 592), f"{snap.ram_total_gb:.1f} GB", font=f22, fill=_WHITE)
        progress(42, 640, 676, snap.ram_percent, severity(snap.ram_percent, 80, 92, _CYAN))

        panel_box((20, 684, 700, 858), "STORAGE", _GREEN)
        disks = snap.disks[:3]
        if not disks:
            d.text((42, 744), "NO STORAGE TELEMETRY", font=f18, fill=_GRAY)
        for i, (name, pct) in enumerate(disks):
            y = 724 + i * 42
            col = severity(pct, 80, 92, _GREEN)
            d.text((42, y), str(name)[:14], font=f16, fill=_WHITE)
            progress(166, y + 6, 590, pct, mix(_GREEN, _RED, clamp01(pct / 100)))
            text_right(d, (676, y), f"{pct:.0f}%", f16, col)

        panel_box((20, 876, 350, 1038), "COOLING", _CYAN)
        metric(42, 920, "CPU FAN", f"{snap.cpu_fan:.0f} RPM")
        metric(190, 920, "GPU FAN", f"{snap.gpu_fan:.0f} RPM")
        d.text((42, 986), "DIRECT SENSOR VALUES", font=f12, fill=_GRAY)

        panel_box((370, 876, 700, 1038), "THERMAL", _RED)
        metric(
            392,
            920,
            "CPU",
            f"{snap.cpu_temp:.0f} °C",
            severity(snap.cpu_temp, 73, 85, _CYAN),
        )
        metric(
            540,
            920,
            "GPU",
            f"{snap.gpu_temp:.0f} °C",
            severity(snap.gpu_temp, 73, 85, _GREEN),
        )
        d.text((392, 986), "MEASURED ONLY", font=f12, fill=_GRAY)

        panel_box((20, 1056, 700, 1248), "NETWORK / LIVE", _CYAN)
        metric(42, 1098, "DOWNLOAD", fmt_net(snap.net_down_kb), _CYAN)
        metric(276, 1098, "UPLOAD", fmt_net(snap.net_up_kb), _GREEN)
        metric(510, 1098, "RENDER", fps_s, _YELLOW)
        baseline = 1210
        d.line((42, baseline, 676, baseline), fill=_LINE, width=1)
        for j, col in enumerate((_CYAN, _GREEN)):
            pts = [
                (
                    x,
                    baseline
                    - 8
                    - j * 12
                    - int(10 * abs(math.sin(i * 0.37 + t * 3.2 + j))),
                )
                for i, x in enumerate(range(42, 677, 6))
            ]
            if len(pts) > 1:
                d.line(pts, fill=col, width=2)
        d.text((42, 1224), "DL", font=f12, fill=_CYAN)
        d.text((78, 1224), "UL", font=f12, fill=_GREEN)
        text_right(d, (676, 1224), now.strftime("%Y-%m-%d"), f12, _GRAY)
        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f12, f14, f16, f18, f22, f30, f40 = (
            load_font(n, True) for n in (12, 14, 16, 18, 22, 30, 40)
        )
        severity = self._severity
        panel_box = lambda box, title, accent=_YELLOW: self._panel_box(
            d, box, title, accent, f14
        )
        progress = lambda x0, y, x1, value, color: self._progress(d, x0, y, x1, value, color)
        metric = lambda x, y, label, value, color=_WHITE, right=None: self._metric(
            d, x, y, label, value, color, right, f12, f18
        )

        d.text((20, 14), "SYSTEM TELEMETRY", font=f18, fill=_YELLOW)
        d.text((20, 42), f"{snap.host[:28]} · {snap.source.upper()}", font=f14, fill=_GRAY)
        text_right(d, (w - 20, 12), now.strftime("%H:%M:%S"), f22, _WHITE)
        fps_s = f"{snap.fps:.0f} FPS" if snap.fps > 0.05 else "FPS --"
        text_right(d, (w - 20, 44), f"{fps_s}  ·  LANDSCAPE", f12, _CYAN)
        d.line((20, 68, w - 20, 68), fill=_LINE, width=2)

        panel_box((16, 80, 630, 250), "PRIMARY HEALTH", _RED)
        primary = (
            ("CPU TEMP", snap.cpu_temp, "°C", _CYAN, 85),
            ("CPU LOAD", snap.cpu_usage, "%", _CYAN, 90),
            ("GPU TEMP", snap.gpu_temp, "°C", _GREEN, 85),
            ("GPU LOAD", snap.gpu_usage, "%", _GREEN, 90),
        )
        for i, (lab, val, unit, accent, hot) in enumerate(primary):
            x = 36 + (i % 2) * 290
            y = 114 + (i // 2) * 58
            col = severity(val, hot - 12, hot, accent)
            d.text((x, y), lab, font=f12, fill=_GRAY)
            d.text((x, y + 16), f"{val:.0f}{unit}", font=f22, fill=col)
            progress(x + 100, y + 24, x + 250, val, col)

        panel_box((650, 80, w - 16, 250), "MEMORY", _YELLOW)
        d.text(
            (670, 118),
            f"{snap.ram_percent:.0f}%",
            font=f40,
            fill=severity(snap.ram_percent, 80, 92, _YELLOW),
        )
        d.text(
            (670, 175),
            f"{snap.ram_used_mb / 1024:.1f} / {snap.ram_total_gb:.1f} GB",
            font=f16,
            fill=_WHITE,
        )
        progress(670, 210, w - 36, snap.ram_percent, severity(snap.ram_percent, 80, 92, _CYAN))

        panel_box((16, 266, 630, 430), "CPU / PROCESSOR", _CYAN)
        metric(36, 300, "CLOCK", f"{snap.cpu_clock:.0f} MHz")
        metric(220, 300, "FAN", f"{snap.cpu_fan:.0f} RPM")
        d.text((36, 360), snap.cpu_name[:36], font=f14, fill=_WHITE)
        d.text(
            (36, 390),
            f"LOAD {snap.cpu_usage:.0f}%",
            font=f16,
            fill=severity(snap.cpu_usage, normal=_CYAN),
        )
        text_right(
            d,
            (610, 390),
            f"TEMP {snap.cpu_temp:.0f}°C",
            f16,
            severity(snap.cpu_temp, 73, 85, _CYAN),
        )

        panel_box((650, 266, w - 16, 430), "GPU / GRAPHICS", _GREEN)
        metric(670, 300, "CLOCK", f"{snap.gpu_clock:.0f} MHz")
        metric(880, 300, "FAN", f"{snap.gpu_fan:.0f} RPM")
        d.text((670, 360), snap.gpu_name[:32], font=f14, fill=_WHITE)
        d.text(
            (670, 390),
            f"LOAD {snap.gpu_usage:.0f}%",
            font=f16,
            fill=severity(snap.gpu_usage, normal=_GREEN),
        )
        text_right(
            d,
            (w - 36, 390),
            f"TEMP {snap.gpu_temp:.0f}°C",
            f16,
            severity(snap.gpu_temp, 73, 85, _GREEN),
        )

        col_w = (w - 48) // 3
        b0 = (16, 446, 16 + col_w, h - 16)
        b1 = (16 + col_w + 8, 446, 16 + 2 * col_w + 8, h - 16)
        b2 = (16 + 2 * col_w + 16, 446, w - 16, h - 16)

        panel_box(b0, "STORAGE", _GREEN)
        disks = snap.disks[:3]
        if not disks:
            d.text((b0[0] + 20, 510), "NO STORAGE TELEMETRY", font=f14, fill=_GRAY)
        for i, (name, pct) in enumerate(disks):
            y = 490 + i * 52
            col = severity(pct, 80, 92, _GREEN)
            d.text((b0[0] + 20, y), str(name)[:12], font=f14, fill=_WHITE)
            progress(b0[0] + 20, y + 24, b0[2] - 20, pct, mix(_GREEN, _RED, clamp01(pct / 100)))
            text_right(d, (b0[2] - 20, y), f"{pct:.0f}%", f14, col)

        panel_box(b1, "COOLING / THERMAL", _RED)
        metric(b1[0] + 20, 490, "CPU FAN", f"{snap.cpu_fan:.0f} RPM")
        metric(b1[0] + 180, 490, "GPU FAN", f"{snap.gpu_fan:.0f} RPM")
        metric(
            b1[0] + 20,
            560,
            "CPU",
            f"{snap.cpu_temp:.0f} °C",
            severity(snap.cpu_temp, 73, 85, _CYAN),
        )
        metric(
            b1[0] + 180,
            560,
            "GPU",
            f"{snap.gpu_temp:.0f} °C",
            severity(snap.gpu_temp, 73, 85, _GREEN),
        )
        d.text((b1[0] + 20, 640), "MEASURED ONLY", font=f12, fill=_GRAY)

        panel_box(b2, "NETWORK / LIVE", _CYAN)
        metric(b2[0] + 20, 490, "DOWNLOAD", fmt_net(snap.net_down_kb), _CYAN)
        metric(b2[0] + 20, 545, "UPLOAD", fmt_net(snap.net_up_kb), _GREEN)
        metric(b2[0] + 200, 490, "RENDER", fps_s, _YELLOW)
        baseline = 640
        d.line((b2[0] + 20, baseline, b2[2] - 20, baseline), fill=_LINE, width=1)
        for j, col in enumerate((_CYAN, _GREEN)):
            pts = [
                (
                    x,
                    baseline
                    - 6
                    - j * 10
                    - int(8 * abs(math.sin(i * 0.37 + t * 3.2 + j))),
                )
                for i, x in enumerate(range(b2[0] + 20, b2[2] - 20, 6))
            ]
            if len(pts) > 1:
                d.line(pts, fill=col, width=2)
        d.text((b2[0] + 20, 658), "DL", font=f12, fill=_CYAN)
        d.text((b2[0] + 52, 658), "UL", font=f12, fill=_GREEN)
        text_right(d, (b2[2] - 20, 658), now.strftime("%Y-%m-%d"), f12, _GRAY)
        return img
