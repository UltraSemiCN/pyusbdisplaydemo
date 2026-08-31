from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, load_font, mix, text_right

_BG = (16, 18, 24)
_C1, _C2, _C3, _C4 = (36, 42, 58), (48, 120, 220), (40, 180, 140), (220, 120, 60)
_TEXT, _MUTE = (240, 244, 250), (140, 150, 170)


class BentoGridPortraitTheme(Theme):
    id = "bento_grid_portrait"
    name = "便当盒布局"
    width = 720
    height = 1280
    description = (
        "StyleKit Bento Grid：大小不一的卡片网格。"
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
    def _tile(d, box, fill, title="", font=None):
        d.rounded_rectangle(box, 22, fill=fill)
        if title and font is not None:
            d.text((box[0] + 20, box[1] + 16), title, font=font, fill=_MUTE)

    @staticmethod
    def _pbar(d, x, y, ww, pct, fill):
        d.rounded_rectangle((x, y, x + ww, y + 10), 5, fill=(28, 32, 44))
        fw = int(ww * max(0, min(100, pct)) / 100)
        if fw > 4:
            d.rounded_rectangle((x, y, x + fw, y + 10), 5, fill=fill)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f18, f24, f36, f56 = (load_font(n, True) for n in (14, 18, 24, 36, 56))
        tile = lambda box, fill, title="": self._tile(d, box, fill, title, f14)
        pbar = lambda x, y, ww, pct, fill: self._pbar(d, x, y, ww, pct, fill)

        tile((20, 20, 440, 200), _C1, "CLOCK")
        d.text((40, 60), now.strftime("%H:%M"), font=f56, fill=_TEXT)
        d.text((40, 140), now.strftime("%a %d %b"), font=f18, fill=_MUTE)

        tile((460, 20, 700, 200), _C2)
        d.text((480, 50), "FPS", font=f14, fill=(200, 220, 255))
        d.text((480, 90), f"{snap.fps:.0f}", font=f56, fill=_TEXT)

        tile((20, 220, 700, 470), _C1, "CPU")
        d.text((40, 270), f"{snap.cpu_usage:.0f}%", font=f56, fill=_TEXT)
        d.text((240, 290), f"{snap.cpu_temp:.0f}°C", font=f36, fill=_C2)
        d.text((40, 360), f"{snap.cpu_clock:.0f} MHz · {snap.cpu_fan:.0f} RPM", font=f18, fill=_MUTE)
        d.text((40, 395), snap.cpu_name[:28], font=f14, fill=_MUTE)
        pbar(40, 430, 640, snap.cpu_usage, _C2)

        tile((20, 490, 350, 760), (32, 48, 42), "GPU")
        d.text((40, 540), f"{snap.gpu_usage:.0f}%", font=f56, fill=_TEXT)
        d.text((40, 620), f"{snap.gpu_temp:.0f}°C", font=f36, fill=_C3)
        d.text((40, 680), f"{snap.gpu_clock:.0f} MHz", font=f14, fill=_MUTE)
        d.text((40, 710), snap.gpu_name[:16], font=f14, fill=_MUTE)

        tile((370, 490, 700, 760), (48, 40, 32), "MEMORY")
        d.text((390, 540), f"{snap.ram_percent:.0f}%", font=f56, fill=_TEXT)
        d.text((390, 620), f"{snap.ram_total_gb:.0f} GB", font=f24, fill=_C4)
        d.text((390, 670), f"{snap.ram_used_mb:.0f} MB used", font=f14, fill=_MUTE)
        pbar(390, 710, 280, snap.ram_percent, _C4)

        tile((20, 780, 700, 1000), _C1, "STORAGE")
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 830 + i * 50
            d.text((40, y), str(name)[:10], font=f18, fill=_TEXT)
            text_right(d, (680, y), f"{pct:.0f}%", f18, mix(_C3, _C4, pct / 100))
            pbar(40, y + 28, 640, pct, mix(_C3, _C4, pct / 100))

        tile((20, 1020, 350, 1260), _C2, "NETWORK")
        d.text((40, 1080), "↑ UP", font=f14, fill=(200, 220, 255))
        d.text((40, 1110), fmt_net(snap.net_up_kb), font=f24, fill=_TEXT)
        d.text((40, 1170), "↓ DOWN", font=f14, fill=(200, 220, 255))
        d.text((40, 1200), fmt_net(snap.net_down_kb), font=f24, fill=_TEXT)

        tile((370, 1020, 700, 1260), _C1, "HOST")
        d.text((390, 1080), snap.host[:14], font=f24, fill=_TEXT)
        d.text((390, 1140), snap.source.upper(), font=f18, fill=_C3)
        pts = [
            (390 + i * 6, 1230 - int(18 * abs(math.sin(i * 0.35 + t * 2.5))))
            for i in range(48)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_C2, width=2)

        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f18, f24, f36, f48 = (load_font(n, True) for n in (14, 18, 24, 36, 48))
        tile = lambda box, fill, title="": self._tile(d, box, fill, title, f14)
        pbar = lambda x, y, ww, pct, fill: self._pbar(d, x, y, ww, pct, fill)

        # Top: clock | host | fps
        tile((16, 16, 320, 130), _C1, "CLOCK")
        d.text((36, 50), now.strftime("%H:%M"), font=f48, fill=_TEXT)
        d.text((36, 100), now.strftime("%a %d %b"), font=f14, fill=_MUTE)

        tile((340, 16, 980, 130), _C1, "HOST")
        d.text((360, 55), snap.host[:28], font=f24, fill=_TEXT)
        d.text((360, 95), f"{snap.source.upper()} · LANDSCAPE", font=f18, fill=_C3)

        tile((1000, 16, w - 16, 130), _C2)
        d.text((1020, 40), "FPS", font=f14, fill=(200, 220, 255))
        d.text((1020, 70), f"{snap.fps:.0f}", font=f48, fill=_TEXT)

        # Mid: CPU | GPU
        tile((16, 150, 630, 400), _C1, "CPU")
        d.text((36, 200), f"{snap.cpu_usage:.0f}%", font=f48, fill=_TEXT)
        d.text((200, 220), f"{snap.cpu_temp:.0f}°C", font=f36, fill=_C2)
        d.text((36, 290), f"{snap.cpu_clock:.0f} MHz · {snap.cpu_fan:.0f} RPM", font=f18, fill=_MUTE)
        d.text((36, 325), snap.cpu_name[:34], font=f14, fill=_MUTE)
        pbar(36, 360, 560, snap.cpu_usage, _C2)

        tile((650, 150, w - 16, 400), (32, 48, 42), "GPU")
        d.text((670, 200), f"{snap.gpu_usage:.0f}%", font=f48, fill=_TEXT)
        d.text((840, 220), f"{snap.gpu_temp:.0f}°C", font=f36, fill=_C3)
        d.text((670, 290), f"{snap.gpu_clock:.0f} MHz · {snap.gpu_fan:.0f} RPM", font=f18, fill=_MUTE)
        d.text((670, 325), snap.gpu_name[:30], font=f14, fill=_MUTE)
        pbar(670, 360, 560, snap.gpu_usage, _C3)

        # Bottom: Memory | Storage | Network
        tile((16, 420, 400, h - 16), (48, 40, 32), "MEMORY")
        d.text((36, 470), f"{snap.ram_percent:.0f}%", font=f48, fill=_TEXT)
        d.text((36, 545), f"{snap.ram_total_gb:.0f} GB", font=f24, fill=_C4)
        d.text((36, 590), f"{snap.ram_used_mb:.0f} MB used", font=f14, fill=_MUTE)
        pbar(36, 640, 340, snap.ram_percent, _C4)

        tile((420, 420, 860, h - 16), _C1, "STORAGE")
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 470 + i * 60
            d.text((440, y), str(name)[:10], font=f18, fill=_TEXT)
            text_right(d, (840, y), f"{pct:.0f}%", f18, mix(_C3, _C4, pct / 100))
            pbar(440, y + 28, 380, pct, mix(_C3, _C4, pct / 100))

        tile((880, 420, w - 16, h - 16), _C2, "NETWORK")
        d.text((900, 480), "↑ UP", font=f14, fill=(200, 220, 255))
        d.text((900, 510), fmt_net(snap.net_up_kb), font=f24, fill=_TEXT)
        d.text((900, 570), "↓ DOWN", font=f14, fill=(200, 220, 255))
        d.text((900, 600), fmt_net(snap.net_down_kb), font=f24, fill=_TEXT)
        pts = [
            (900 + i * 7, 680 - int(16 * abs(math.sin(i * 0.35 + t * 2.5))))
            for i in range(40)
        ]
        if len(pts) > 1:
            d.line(pts, fill=(200, 220, 255), width=2)

        return img
