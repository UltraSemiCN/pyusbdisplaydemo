from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, load_font, text_right

_BG, _INK, _MUTE = (255, 255, 255), (17, 17, 17), (120, 120, 120)
_A1, _A2, _A3 = (255, 90, 70), (40, 40, 40), (70, 200, 160)


class MinimalFlatPortraitTheme(Theme):
    id = "minimal_flat_portrait"
    name = "极简扁平风"
    width = 720
    height = 1280
    description = "StyleKit Minimalist Flat：无阴影无渐变，色块与留白。0°/180° 竖屏；90°/270° 横屏。"

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
    def _flat_bar(d: ImageDraw.ImageDraw, x0, y, x1, pct, track, fill) -> None:
        d.rectangle((x0, y, x1, y + 16), fill=track)
        fw = int((x1 - x0) * max(0, min(100, pct)) / 100)
        if fw > 0:
            d.rectangle((x0, y, x0 + fw, y + 16), fill=fill)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f18, f32, f56, f80 = (load_font(n, True) for n in (14, 18, 32, 56, 80))

        d.rectangle((0, 0, w, 8), fill=_INK)
        d.text((32, 40), now.strftime("%H:%M"), font=f80, fill=_INK)
        d.text((32, 130), snap.host[:24], font=f18, fill=_MUTE)
        text_right(d, (w - 32, 50), snap.source.upper(), f14, _A1)

        d.rectangle((32, 180, 348, 420), fill=_A1)
        d.text((52, 200), "CPU", font=f14, fill=(255, 255, 255))
        d.text((52, 240), f"{snap.cpu_usage:.0f}%", font=f56, fill=(255, 255, 255))
        d.text((52, 320), f"{snap.cpu_temp:.0f}°C", font=f32, fill=(255, 255, 255))
        d.text((52, 370), f"{snap.cpu_clock:.0f} MHz", font=f14, fill=(255, 230, 220))

        d.rectangle((372, 180, w - 32, 420), fill=_A2)
        d.text((392, 200), "GPU", font=f14, fill=(200, 200, 200))
        d.text((392, 240), f"{snap.gpu_usage:.0f}%", font=f56, fill=(255, 255, 255))
        d.text((392, 320), f"{snap.gpu_temp:.0f}°C", font=f32, fill=(255, 255, 255))
        d.text((392, 370), f"{snap.gpu_clock:.0f} MHz", font=f14, fill=(180, 180, 180))

        d.rectangle((32, 444, w - 32, 620), fill=_A3)
        d.text((52, 470), "MEMORY", font=f14, fill=(20, 60, 50))
        d.text((52, 510), f"{snap.ram_percent:.0f}%", font=f56, fill=(10, 40, 35))
        d.text((260, 540), f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB", font=f18, fill=(20, 60, 50))
        d.rectangle((52, 580, w - 52, 596), fill=(20, 90, 70))
        fw = int((w - 104) * max(0, min(100, snap.ram_percent)) / 100)
        d.rectangle((52, 580, 52 + fw, 596), fill=(10, 40, 35))

        d.text((32, 660), "STORAGE", font=f14, fill=_MUTE)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 700 + i * 70
            d.rectangle((32, y, w - 32, y + 56), fill=(245, 245, 245))
            d.text((48, y + 16), str(name)[:10], font=f18, fill=_INK)
            text_right(d, (w - 48, y + 16), f"{pct:.0f}%", f18, _A1)
            d.rectangle((200, y + 24, w - 160, y + 32), fill=(220, 220, 220))
            fw = int((w - 360) * max(0, min(100, pct)) / 100)
            d.rectangle((200, y + 24, 200 + fw, y + 32), fill=_INK)

        d.text((32, 940), "NETWORK", font=f14, fill=_MUTE)
        d.rectangle((32, 970, 348, 1120), fill=(245, 245, 245))
        d.text((52, 1000), "UPLOAD", font=f14, fill=_MUTE)
        d.text((52, 1040), fmt_net(snap.net_up_kb), font=f32, fill=_INK)
        d.rectangle((372, 970, w - 32, 1120), fill=(245, 245, 245))
        d.text((392, 1000), "DOWNLOAD", font=f14, fill=_MUTE)
        d.text((392, 1040), fmt_net(snap.net_down_kb), font=f32, fill=_INK)

        pts = [(32 + i * 5, 1180 - int(18 * abs(math.sin(i * 0.3 + t * 2)))) for i in range(130)]
        if len(pts) > 1:
            d.line(pts, fill=_A1, width=3)
        d.text((32, 1220), f"{snap.fps:.0f} FPS  ·  MINIMAL FLAT", font=f14, fill=_MUTE)
        d.rectangle((0, h - 8, w, h), fill=_INK)

        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f18, f32, f48, f64 = (load_font(n, True) for n in (14, 18, 32, 48, 64))

        d.rectangle((0, 0, w, 8), fill=_INK)
        d.text((32, 24), now.strftime("%H:%M"), font=f64, fill=_INK)
        d.text((280, 36), snap.host[:28], font=f18, fill=_MUTE)
        text_right(d, (w - 32, 28), snap.source.upper(), f14, _A1)
        d.text((280, 64), f"{snap.fps:.0f} FPS  ·  MINIMAL FLAT", font=f14, fill=_MUTE)

        d.rectangle((24, 96, 400, 340), fill=_A1)
        d.text((44, 116), "CPU", font=f14, fill=(255, 255, 255))
        d.text((44, 150), f"{snap.cpu_usage:.0f}%", font=f48, fill=(255, 255, 255))
        d.text((44, 220), f"{snap.cpu_temp:.0f}°C", font=f32, fill=(255, 255, 255))
        d.text((44, 270), f"{snap.cpu_clock:.0f} MHz · {snap.cpu_fan:.0f} RPM", font=f14, fill=(255, 230, 220))
        d.text((44, 300), snap.cpu_name[:24], font=f14, fill=(255, 230, 220))

        d.rectangle((420, 96, w - 24, 340), fill=_A2)
        d.text((440, 116), "GPU", font=f14, fill=(200, 200, 200))
        d.text((440, 150), f"{snap.gpu_usage:.0f}%", font=f48, fill=(255, 255, 255))
        d.text((440, 220), f"{snap.gpu_temp:.0f}°C", font=f32, fill=(255, 255, 255))
        d.text((440, 270), f"{snap.gpu_clock:.0f} MHz · {snap.gpu_fan:.0f} RPM", font=f14, fill=(180, 180, 180))
        d.text((440, 300), snap.gpu_name[:24], font=f14, fill=(180, 180, 180))

        d.rectangle((24, 360, 320, h - 24), fill=_A3)
        d.text((44, 380), "MEMORY", font=f14, fill=(20, 60, 50))
        d.text((44, 420), f"{snap.ram_percent:.0f}%", font=f48, fill=(10, 40, 35))
        d.text(
            (44, 490),
            f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB",
            font=f14,
            fill=(20, 60, 50),
        )
        self._flat_bar(d, 44, 560, 280, snap.ram_percent, (20, 90, 70), (10, 40, 35))

        d.text((344, 368), "STORAGE", font=f14, fill=_MUTE)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 400 + i * 88
            d.rectangle((344, y, 820, y + 68), fill=(245, 245, 245))
            d.text((360, y + 12), str(name)[:10], font=f18, fill=_INK)
            text_right(d, (800, y + 12), f"{pct:.0f}%", f18, _A1)
            d.rectangle((480, y + 44, 760, y + 56), fill=(220, 220, 220))
            fw = int(280 * max(0, min(100, pct)) / 100)
            d.rectangle((480, y + 44, 480 + fw, y + 56), fill=_INK)

        d.rectangle((844, 360, w - 24, 520), fill=(245, 245, 245))
        d.text((864, 380), "UPLOAD", font=f14, fill=_MUTE)
        d.text((864, 420), fmt_net(snap.net_up_kb), font=f32, fill=_INK)
        d.rectangle((844, 540, w - 24, h - 24), fill=(245, 245, 245))
        d.text((864, 560), "DOWNLOAD", font=f14, fill=_MUTE)
        d.text((864, 600), fmt_net(snap.net_down_kb), font=f32, fill=_INK)

        pts = [(844 + i * 5, 680 - int(14 * abs(math.sin(i * 0.3 + t * 2)))) for i in range(70)]
        if len(pts) > 1:
            d.line(pts, fill=_A1, width=3)

        d.rectangle((0, h - 8, w, h), fill=_INK)
        return img
