from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, gauge, load_font, mix, text_right

_GLASS = (22, 28, 44)
_EDGE = (120, 150, 200)
_TEXT, _MUTE = (235, 240, 255), (150, 160, 185)
_ACCENT, _WARM = (110, 200, 255), (255, 170, 120)


class GlassDarkPortraitTheme(Theme):
    id = "glass_dark_portrait"
    name = "玻璃暗色"
    width = 720
    height = 1280
    description = "StyleKit Glassmorphism / Dark：深色毛玻璃质感面板。0°/180° 竖屏；90°/270° 横屏。"

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
    def _bg(w: int, h: int, landscape: bool = False) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (w, h), (8, 10, 18))
        d = ImageDraw.Draw(img)
        for y in range(h):
            c = int(8 + 18 * (y / h))
            d.line([(0, y), (w, y)], fill=(c, 12, 28 + c // 2))
        if landscape:
            d.ellipse((-120, -80, 360, 280), fill=(40, 60, 120))
            d.ellipse((880, 420, 1380, 820), fill=(60, 30, 90))
        else:
            d.ellipse((-80, -40, 280, 320), fill=(40, 60, 120))
            d.ellipse((420, 700, 820, 1180), fill=(60, 30, 90))
        return img, d

    @staticmethod
    def _panel(d: ImageDraw.ImageDraw, box, title="", f14=None) -> None:
        d.rounded_rectangle(box, 20, fill=_GLASS, outline=_EDGE, width=1)
        d.rounded_rectangle((box[0] + 1, box[1] + 1, box[2] - 1, box[1] + 3), 2, fill=(80, 100, 140))
        if title and f14 is not None:
            d.text((box[0] + 22, box[1] + 14), title, font=f14, fill=_MUTE)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img, d = self._bg(w, h)
        f14, f18, f24, f40, f64 = (load_font(n, True) for n in (14, 18, 24, 40, 64))
        panel = lambda box, title="": self._panel(d, box, title, f14)

        panel((24, 24, w - 24, 150))
        d.text((48, 48), now.strftime("%H:%M:%S"), font=f40, fill=_TEXT)
        d.text((48, 100), f"{snap.host[:20]}  ·  {snap.source.upper()}", font=f14, fill=_MUTE)
        text_right(d, (w - 48, 56), f"{snap.fps:.0f} FPS", f18, _ACCENT)

        panel((24, 170, 348, 470), "CPU")
        gauge(d, 186, 340, 78, snap.cpu_temp, _ACCENT, track=(40, 50, 70), width=12)
        d.text((186, 320), f"{snap.cpu_temp:.0f}", font=f40, fill=_TEXT, anchor="mm")
        d.text((48, 420), f"{snap.cpu_usage:.0f}%  ·  {snap.cpu_clock:.0f} MHz", font=f14, fill=_MUTE)

        panel((372, 170, w - 24, 470), "GPU")
        gauge(d, 546, 340, 78, snap.gpu_temp, _WARM, track=(40, 50, 70), width=12)
        d.text((546, 320), f"{snap.gpu_temp:.0f}", font=f40, fill=_TEXT, anchor="mm")
        d.text((396, 420), f"{snap.gpu_usage:.0f}%  ·  {snap.gpu_clock:.0f} MHz", font=f14, fill=_MUTE)

        panel((24, 490, w - 24, 680), "DETAILS")
        rows = [
            ("CPU Fan", f"{snap.cpu_fan:.0f} RPM"),
            ("GPU Fan", f"{snap.gpu_fan:.0f} RPM"),
            ("CPU", snap.cpu_name[:28]),
            ("GPU", snap.gpu_name[:28]),
        ]
        for i, (a, b) in enumerate(rows):
            y = 530 + i * 36
            d.text((48, y), a, font=f14, fill=_MUTE)
            text_right(d, (w - 48, y), b, f18, _TEXT)

        panel((24, 700, w - 24, 860), "MEMORY")
        d.text((48, 745), f"{snap.ram_percent:.0f}%", font=f64, fill=_TEXT)
        d.text((250, 780), f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB", font=f18, fill=_MUTE)
        d.rounded_rectangle((48, 820, w - 48, 838), 9, fill=(40, 50, 70))
        fw = int((w - 96) * max(0, min(100, snap.ram_percent)) / 100)
        if fw > 0:
            d.rounded_rectangle((48, 820, 48 + fw, 838), 9, fill=_ACCENT)

        panel((24, 880, w - 24, 1050), "STORAGE")
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 920 + i * 40
            d.text((48, y), str(name)[:10], font=f14, fill=_MUTE)
            d.rounded_rectangle((160, y + 6, 560, y + 16), 5, fill=(40, 50, 70))
            fw = int(400 * max(0, min(100, pct)) / 100)
            if fw > 0:
                d.rounded_rectangle((160, y + 6, 160 + fw, y + 16), 5, fill=mix(_ACCENT, _WARM, pct / 100))
            text_right(d, (w - 48, y), f"{pct:.0f}%", f14, _TEXT)

        panel((24, 1070, w - 24, 1256), "NETWORK")
        d.text((48, 1120), f"↑ {fmt_net(snap.net_up_kb)}", font=f24, fill=_WARM)
        d.text((360, 1120), f"↓ {fmt_net(snap.net_down_kb)}", font=f24, fill=_ACCENT)
        pts = [(48 + i * 5, 1220 - int(20 * abs(math.sin(i * 0.3 + t * 2)))) for i in range(125)]
        if len(pts) > 1:
            d.line(pts, fill=_ACCENT, width=2)

        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img, d = self._bg(w, h, landscape=True)
        f14, f18, f24, f40, f56 = (load_font(n, True) for n in (14, 18, 24, 40, 56))
        panel = lambda box, title="": self._panel(d, box, title, f14)

        panel((20, 16, w - 20, 100))
        d.text((44, 32), now.strftime("%H:%M:%S"), font=f40, fill=_TEXT)
        d.text((44, 72), f"{snap.host[:26]}  ·  {snap.source.upper()}", font=f14, fill=_MUTE)
        text_right(d, (w - 44, 36), f"{snap.fps:.0f} FPS", f18, _ACCENT)

        panel((20, 116, 400, 380), "CPU")
        gauge(d, 210, 250, 68, snap.cpu_temp, _ACCENT, track=(40, 50, 70), width=12)
        d.text((210, 232), f"{snap.cpu_temp:.0f}", font=f40, fill=_TEXT, anchor="mm")
        d.text((44, 320), f"{snap.cpu_usage:.0f}%  ·  {snap.cpu_clock:.0f} MHz", font=f14, fill=_MUTE)
        d.text((44, 348), snap.cpu_name[:22], font=f14, fill=_MUTE)

        panel((420, 116, w - 20, 380), "GPU")
        gauge(d, 850, 250, 68, snap.gpu_temp, _WARM, track=(40, 50, 70), width=12)
        d.text((850, 232), f"{snap.gpu_temp:.0f}", font=f40, fill=_TEXT, anchor="mm")
        d.text((444, 320), f"{snap.gpu_usage:.0f}%  ·  {snap.gpu_clock:.0f} MHz", font=f14, fill=_MUTE)
        d.text((444, 348), snap.gpu_name[:22], font=f14, fill=_MUTE)

        panel((20, 400, 520, 520), "DETAILS")
        rows = [
            ("CPU Fan", f"{snap.cpu_fan:.0f} RPM"),
            ("GPU Fan", f"{snap.gpu_fan:.0f} RPM"),
        ]
        for i, (a, b) in enumerate(rows):
            y = 438 + i * 36
            d.text((44, y), a, font=f14, fill=_MUTE)
            text_right(d, (500, y), b, f18, _TEXT)

        panel((540, 400, 820, 520), "MEMORY")
        d.text((564, 430), f"{snap.ram_percent:.0f}%", font=f56, fill=_TEXT)
        d.text(
            (564, 480),
            f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB",
            font=f14,
            fill=_MUTE,
        )
        d.rounded_rectangle((564, 492, 796, 506), 7, fill=(40, 50, 70))
        fw = int(232 * max(0, min(100, snap.ram_percent)) / 100)
        if fw > 0:
            d.rounded_rectangle((564, 492, 564 + fw, 506), 7, fill=_ACCENT)

        panel((840, 400, w - 20, 520), "STORAGE")
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:2]
        for i, (name, pct) in enumerate(disks):
            y = 430 + i * 40
            d.text((864, y), str(name)[:8], font=f14, fill=_MUTE)
            text_right(d, (w - 44, y), f"{pct:.0f}%", f14, _TEXT)

        panel((20, 540, 620, h - 20), "NETWORK")
        d.text((44, 580), f"↑ {fmt_net(snap.net_up_kb)}", font=f24, fill=_WARM)
        d.text((44, 630), f"↓ {fmt_net(snap.net_down_kb)}", font=f24, fill=_ACCENT)
        pts = [(44 + i * 5, 680 - int(16 * abs(math.sin(i * 0.3 + t * 2)))) for i in range(110)]
        if len(pts) > 1:
            d.line(pts, fill=_ACCENT, width=2)

        panel((640, 540, w - 20, h - 20), "DISKS")
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 580 + i * 36
            d.text((664, y), str(name)[:10], font=f14, fill=_MUTE)
            d.rounded_rectangle((760, y + 6, 1180, y + 16), 5, fill=(40, 50, 70))
            fw = int(420 * max(0, min(100, pct)) / 100)
            if fw > 0:
                d.rounded_rectangle((760, y + 6, 760 + fw, y + 16), 5, fill=mix(_ACCENT, _WARM, pct / 100))
            text_right(d, (w - 44, y), f"{pct:.0f}%", f14, _TEXT)

        return img
