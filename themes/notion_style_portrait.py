from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, load_font

_BG, _INK, _MUTE, _LINE = (255, 255, 255), (55, 53, 47), (120, 119, 116), (233, 233, 231)
_RED, _BLUE, _GREEN = (226, 68, 63), (46, 117, 212), (15, 123, 108)


class NotionStylePortraitTheme(Theme):
    id = "notion_style_portrait"
    name = "Notion 风格"
    width = 720
    height = 1280
    description = (
        "StyleKit Notion Style：文档感、清爽层级。"
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

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f16, f22, f36, f48 = (load_font(n, True) for n in (14, 16, 22, 36, 48))
        f14r = load_font(14, False)

        def h1(y, text):
            d.text((40, y), text, font=f36, fill=_INK)

        def prop(y, label, value, color=_INK):
            d.text((40, y), label, font=f14r, fill=_MUTE)
            d.text((200, y), value, font=f16, fill=color)

        def divider(y):
            d.line([(40, y), (w - 40, y)], fill=_LINE, width=1)

        def callout(box, fill, title, body_lines):
            d.rounded_rectangle(box, 8, fill=fill)
            d.text((box[0] + 20, box[1] + 16), title, font=f16, fill=_INK)
            for i, line_s in enumerate(body_lines):
                d.text((box[0] + 20, box[1] + 48 + i * 26), line_s, font=f14r, fill=_MUTE)

        d.text((40, 36), "System status", font=f22, fill=_INK)
        d.text((40, 72), now.strftime("%B %d, %Y · %H:%M:%S"), font=f14r, fill=_MUTE)
        divider(110)

        h1(130, "Overview")
        prop(190, "Host", snap.host[:28])
        prop(220, "Source", snap.source.upper(), _BLUE)
        prop(250, "Stream FPS", f"{snap.fps:.0f}", _GREEN)
        divider(290)

        h1(310, "CPU")
        callout(
            (40, 370, w - 40, 520),
            (251, 243, 219),
            f"{snap.cpu_usage:.0f}% · {snap.cpu_temp:.0f}°C",
            [
                f"Clock {snap.cpu_clock:.0f} MHz · Fan {snap.cpu_fan:.0f} RPM",
                snap.cpu_name[:40],
            ],
        )

        h1(550, "GPU")
        callout(
            (40, 610, w - 40, 760),
            (232, 242, 252),
            f"{snap.gpu_usage:.0f}% · {snap.gpu_temp:.0f}°C",
            [
                f"Clock {snap.gpu_clock:.0f} MHz · Fan {snap.gpu_fan:.0f} RPM",
                snap.gpu_name[:40],
            ],
        )

        h1(790, "Memory & storage")
        prop(
            850,
            "RAM",
            f"{snap.ram_percent:.0f}%  ({snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB)",
            _GREEN,
        )
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            prop(890 + i * 30, str(name)[:10], f"{pct:.0f}% used", _RED if pct > 85 else _INK)
        d.rounded_rectangle((40, 990, w - 40, 1000), 3, fill=_LINE)
        fw = int((w - 80) * max(0, min(100, snap.ram_percent)) / 100)
        d.rounded_rectangle((40, 990, 40 + fw, 1000), 3, fill=_GREEN)

        divider(1030)
        h1(1050, "Network")
        prop(1110, "Upload", fmt_net(snap.net_up_kb), _BLUE)
        prop(1140, "Download", fmt_net(snap.net_down_kb), _GREEN)
        pts = [
            (40 + i * 5, 1220 - int(14 * abs(math.sin(i * 0.3 + t * 2))))
            for i in range(128)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_LINE, width=2)
        d.text((40, 1245), "Notion-inspired layout", font=f14r, fill=_MUTE)

        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f16, f22, f28, f36 = (load_font(n, True) for n in (14, 16, 22, 28, 36))
        f14r = load_font(14, False)

        def prop(x, y, label, value, color=_INK):
            d.text((x, y), label, font=f14r, fill=_MUTE)
            d.text((x + 120, y), value, font=f16, fill=color)

        def divider(x0, y0, x1, y1):
            d.line([(x0, y0), (x1, y1)], fill=_LINE, width=1)

        def callout(box, fill, title, body_lines):
            d.rounded_rectangle(box, 8, fill=fill)
            d.text((box[0] + 16, box[1] + 12), title, font=f16, fill=_INK)
            for i, line_s in enumerate(body_lines):
                d.text((box[0] + 16, box[1] + 40 + i * 24), line_s, font=f14r, fill=_MUTE)

        d.text((32, 24), "System status", font=f22, fill=_INK)
        d.text((32, 54), now.strftime("%B %d, %Y · %H:%M:%S"), font=f14r, fill=_MUTE)
        prop(400, 28, "Host", snap.host[:28])
        prop(400, 54, "Source", snap.source.upper(), _BLUE)
        prop(720, 28, "Stream FPS", f"{snap.fps:.0f}", _GREEN)
        divider(32, 88, w - 32, 88)

        d.text((32, 104), "CPU", font=f28, fill=_INK)
        callout(
            (32, 140, 620, 340),
            (251, 243, 219),
            f"{snap.cpu_usage:.0f}% · {snap.cpu_temp:.0f}°C",
            [
                f"Clock {snap.cpu_clock:.0f} MHz · Fan {snap.cpu_fan:.0f} RPM",
                snap.cpu_name[:40],
            ],
        )

        d.text((660, 104), "GPU", font=f28, fill=_INK)
        callout(
            (660, 140, w - 32, 340),
            (232, 242, 252),
            f"{snap.gpu_usage:.0f}% · {snap.gpu_temp:.0f}°C",
            [
                f"Clock {snap.gpu_clock:.0f} MHz · Fan {snap.gpu_fan:.0f} RPM",
                snap.gpu_name[:40],
            ],
        )

        divider(32, 360, w - 32, 360)

        d.text((32, 376), "Memory & storage", font=f28, fill=_INK)
        prop(
            32,
            430,
            "RAM",
            f"{snap.ram_percent:.0f}%  ({snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB)",
            _GREEN,
        )
        d.rounded_rectangle((32, 470, 400, 480), 3, fill=_LINE)
        fw = int(368 * max(0, min(100, snap.ram_percent)) / 100)
        d.rounded_rectangle((32, 470, 32 + fw, 480), 3, fill=_GREEN)

        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            prop(32, 500 + i * 28, str(name)[:10], f"{pct:.0f}% used", _RED if pct > 85 else _INK)

        divider(440, 376, 440, h - 24)

        d.text((460, 376), "Network", font=f28, fill=_INK)
        prop(460, 430, "Upload", fmt_net(snap.net_up_kb), _BLUE)
        prop(460, 460, "Download", fmt_net(snap.net_down_kb), _GREEN)
        pts = [
            (460 + i * 6, 640 - int(14 * abs(math.sin(i * 0.3 + t * 2))))
            for i in range(120)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_LINE, width=2)
        d.text((460, 670), "Notion-inspired layout", font=f14r, fill=_MUTE)

        return img
