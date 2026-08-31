from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, load_font, text_right

_BG, _PAPER, _INK = (52, 36, 28), (232, 210, 170), (48, 28, 18)
_RUST, _CREAM, _TEAL = (180, 70, 40), (245, 230, 190), (40, 110, 100)


class RetroVintagePortraitTheme(Theme):
    id = "retro_vintage_portrait"
    name = "复古怀旧风"
    width = 720
    height = 1280
    description = (
        "StyleKit Retro Vintage：暖色纸感、老式仪表盘。"
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
    def _plate(d, box, fill=_PAPER):
        d.rounded_rectangle(
            (box[0] + 3, box[1] + 3, box[2] + 3, box[3] + 3), 6, fill=(30, 20, 14)
        )
        d.rounded_rectangle(box, 6, fill=fill, outline=_INK, width=3)
        for x, y in (
            (box[0] + 12, box[1] + 12),
            (box[2] - 12, box[1] + 12),
            (box[0] + 12, box[3] - 12),
            (box[2] - 12, box[3] - 12),
        ):
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=_INK)

    @staticmethod
    def _needle_gauge(d, cx, cy, r, val, label, f14):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=_INK, width=4, fill=_CREAM)
        d.arc((cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8), 200, 340, fill=_RUST, width=3)
        ang = math.radians(200 + 140 * max(0, min(100, val)) / 100)
        d.line(
            [
                (cx, cy),
                (
                    cx + int((r - 18) * math.cos(ang)),
                    cy + int((r - 18) * math.sin(ang)),
                ),
            ],
            fill=_RUST,
            width=4,
        )
        d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=_INK)
        d.text((cx, cy + r + 8), label, font=f14, fill=_CREAM, anchor="ma")

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f18, f28, f44, f64 = (load_font(n, True) for n in (14, 18, 28, 44, 64))
        plate = lambda box, fill=_PAPER: self._plate(d, box, fill)
        needle = lambda cx, cy, r, val, label: self._needle_gauge(d, cx, cy, r, val, label, f14)

        plate((28, 28, w - 28, 150), _CREAM)
        d.text((56, 50), "TERMINAL MONITOR", font=f18, fill=_RUST)
        d.text((56, 85), now.strftime("%H:%M:%S"), font=f44, fill=_INK)
        text_right(d, (w - 56, 95), snap.host[:12], f14, _TEAL)

        plate((28, 170, w - 28, 480))
        d.text((56, 190), "ENGINE ROOM", font=f14, fill=_RUST)
        needle(180, 330, 90, snap.cpu_usage, f"CPU {snap.cpu_temp:.0f}C")
        needle(500, 330, 90, snap.gpu_usage, f"GPU {snap.gpu_temp:.0f}C")

        plate((28, 500, w - 28, 700), _CREAM)
        d.text((56, 525), "CPU", font=f14, fill=_RUST)
        d.text(
            (56, 555),
            f"{snap.cpu_usage:.0f}%   {snap.cpu_clock:.0f} MHz",
            font=f28,
            fill=_INK,
        )
        d.text((56, 600), f"FAN {snap.cpu_fan:.0f} RPM", font=f18, fill=_TEAL)
        d.text((56, 640), snap.cpu_name[:28], font=f14, fill=_INK)
        d.text((380, 525), "GPU", font=f14, fill=_RUST)
        d.text(
            (380, 555),
            f"{snap.gpu_usage:.0f}%   {snap.gpu_clock:.0f} MHz",
            font=f28,
            fill=_INK,
        )
        d.text((380, 600), f"FAN {snap.gpu_fan:.0f} RPM", font=f18, fill=_TEAL)
        d.text((380, 640), snap.gpu_name[:16], font=f14, fill=_INK)

        plate((28, 720, w - 28, 900))
        d.text((56, 745), "MEMORY TANKS", font=f14, fill=_CREAM)
        d.text((56, 785), f"{snap.ram_percent:.0f}%", font=f64, fill=_CREAM)
        d.text(
            (260, 820),
            f"{snap.ram_used_mb:.0f} / {snap.ram_total_gb * 1024:.0f} MB",
            font=f18,
            fill=_PAPER,
        )
        d.rectangle((56, 860, w - 56, 882), outline=_CREAM, width=2)
        fw = int((w - 116) * max(0, min(100, snap.ram_percent)) / 100)
        d.rectangle((58, 862, 58 + fw, 880), fill=_RUST)

        plate((28, 920, 350, 1120), _CREAM)
        d.text((50, 945), "DRIVES", font=f14, fill=_RUST)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 985 + i * 38
            d.text((50, y), f"{str(name)[:8]} {pct:.0f}%", font=f14, fill=_INK)

        plate((380, 920, w - 28, 1120), _CREAM)
        d.text((400, 945), "WIRELESS", font=f14, fill=_RUST)
        d.text((400, 990), f"UP {fmt_net(snap.net_up_kb)}", font=f18, fill=_INK)
        d.text((400, 1030), f"DN {fmt_net(snap.net_down_kb)}", font=f18, fill=_TEAL)
        pts = [
            (400 + i * 6, 1095 - int(12 * abs(math.sin(i * 0.4 + t))))
            for i in range(40)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_RUST, width=2)

        plate((28, 1140, w - 28, 1256), _INK)
        d.text((56, 1175), now.strftime("%a %d %b %Y").upper(), font=f18, fill=_CREAM)
        text_right(d, (w - 56, 1170), f"{snap.fps:.0f} FPS", f28, _RUST)

        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f18, f28, f44, f56 = (load_font(n, True) for n in (14, 18, 28, 44, 56))
        plate = lambda box, fill=_PAPER: self._plate(d, box, fill)
        needle = lambda cx, cy, r, val, label: self._needle_gauge(d, cx, cy, r, val, label, f14)

        plate((20, 16, w - 20, 110), _CREAM)
        d.text((44, 32), "TERMINAL MONITOR", font=f18, fill=_RUST)
        d.text((44, 62), now.strftime("%H:%M:%S"), font=f44, fill=_INK)
        d.text((280, 48), snap.host[:18], font=f14, fill=_TEAL)
        d.text((280, 72), now.strftime("%a %d %b %Y").upper(), font=f14, fill=_RUST)
        text_right(d, (w - 44, 48), f"{snap.fps:.0f} FPS", f28, _RUST)

        plate((20, 130, 620, 420))
        d.text((44, 148), "ENGINE ROOM", font=f14, fill=_RUST)
        needle(200, 290, 80, snap.cpu_usage, f"CPU {snap.cpu_temp:.0f}C")
        needle(480, 290, 80, snap.gpu_usage, f"GPU {snap.gpu_temp:.0f}C")

        plate((660, 130, w - 20, 420), _CREAM)
        d.text((684, 148), "CPU", font=f14, fill=_RUST)
        d.text(
            (684, 178),
            f"{snap.cpu_usage:.0f}%   {snap.cpu_clock:.0f} MHz",
            font=f28,
            fill=_INK,
        )
        d.text((684, 220), f"FAN {snap.cpu_fan:.0f} RPM", font=f18, fill=_TEAL)
        d.text((684, 252), snap.cpu_name[:28], font=f14, fill=_INK)
        d.text((684, 300), "GPU", font=f14, fill=_RUST)
        d.text(
            (684, 330),
            f"{snap.gpu_usage:.0f}%   {snap.gpu_clock:.0f} MHz",
            font=f28,
            fill=_INK,
        )
        d.text((684, 372), f"FAN {snap.gpu_fan:.0f} RPM", font=f18, fill=_TEAL)
        d.text((684, 404), snap.gpu_name[:28], font=f14, fill=_INK)

        plate((20, 440, 400, h - 16))
        d.text((44, 460), "MEMORY TANKS", font=f14, fill=_CREAM)
        d.text((44, 500), f"{snap.ram_percent:.0f}%", font=f56, fill=_CREAM)
        d.text(
            (44, 570),
            f"{snap.ram_used_mb:.0f} / {snap.ram_total_gb * 1024:.0f} MB",
            font=f18,
            fill=_PAPER,
        )
        d.rectangle((44, 620, 376, 642), outline=_CREAM, width=2)
        fw = int(330 * max(0, min(100, snap.ram_percent)) / 100)
        d.rectangle((46, 622, 46 + fw, 640), fill=_RUST)

        plate((420, 440, 860, h - 16), _CREAM)
        d.text((444, 460), "DRIVES", font=f14, fill=_RUST)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 510 + i * 58
            d.text((444, y), f"{str(name)[:10]} {pct:.0f}%", font=f18, fill=_INK)
            d.rectangle((444, y + 28, 820, y + 44), outline=_INK, width=2)
            fw_d = int(374 * max(0, min(100, pct)) / 100)
            d.rectangle((446, y + 30, 446 + fw_d, y + 42), fill=_RUST)

        plate((880, 440, w - 20, h - 16), _CREAM)
        d.text((904, 460), "WIRELESS", font=f14, fill=_RUST)
        d.text((904, 510), f"UP {fmt_net(snap.net_up_kb)}", font=f18, fill=_INK)
        d.text((904, 550), f"DN {fmt_net(snap.net_down_kb)}", font=f18, fill=_TEAL)
        pts = [
            (904 + i * 7, 660 - int(12 * abs(math.sin(i * 0.4 + t))))
            for i in range(40)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_RUST, width=2)

        return img
