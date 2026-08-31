from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, load_font, text_right

_BG = (12, 12, 14)
_YLW, _MAG, _CYN, _WH = (255, 220, 0), (255, 40, 120), (0, 230, 220), (245, 245, 245)


class GeometricBoldPortraitTheme(Theme):
    id = "geometric_bold_portrait"
    name = "几何大胆风"
    width = 720
    height = 1280
    description = (
        "StyleKit Geometric Bold：强色块与几何构图。"
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
    def _backdrop(d: ImageDraw.ImageDraw, w: int, h: int) -> None:
        d.polygon([(0, 0), (int(w * 0.58), 0), (0, int(h * 0.25))], fill=(28, 28, 34))
        d.polygon([(w, int(h * 0.16)), (w, int(h * 0.44)), (int(w * 0.5), int(h * 0.44))], fill=(40, 10, 30))
        d.ellipse((int(w * 0.67), -int(h * 0.06), int(w * 1.14), int(h * 0.2)), fill=(20, 50, 55))
        d.rectangle((0, h - int(h * 0.078), w, h), fill=_YLW)

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f20, f36, f56, f72 = (load_font(n, True) for n in (14, 20, 36, 56, 72))
        self._backdrop(d, w, h)

        d.text((32, 36), now.strftime("%H:%M"), font=f72, fill=_WH)
        d.text((32, 120), snap.host[:18], font=f20, fill=_CYN)
        text_right(d, (w - 32, 48), "GEO", f36, _MAG)

        d.polygon([(32, 180), (680, 180), (640, 420), (32, 420)], fill=_MAG)
        d.text((56, 200), "CPU", font=f20, fill=_WH)
        d.text((56, 240), f"{snap.cpu_usage:.0f}%", font=f72, fill=_WH)
        d.text((320, 270), f"{snap.cpu_temp:.0f}°C", font=f56, fill=_YLW)
        d.text((56, 340), f"{snap.cpu_clock:.0f} MHz  ·  {snap.cpu_fan:.0f} RPM", font=f20, fill=_WH)
        d.text((56, 380), snap.cpu_name[:24], font=f14, fill=(255, 180, 200))

        d.polygon([(80, 450), (w - 32, 450), (w - 32, 690), (120, 690)], fill=_CYN)
        d.text((140, 470), "GPU", font=f20, fill=_BG)
        d.text((140, 510), f"{snap.gpu_usage:.0f}%", font=f72, fill=_BG)
        d.text((400, 540), f"{snap.gpu_temp:.0f}°C", font=f56, fill=_MAG)
        d.text((140, 610), f"{snap.gpu_clock:.0f} MHz  ·  {snap.gpu_fan:.0f} RPM", font=f20, fill=_BG)
        d.text((140, 650), snap.gpu_name[:22], font=f14, fill=(10, 80, 80))

        d.ellipse((48, 720, 280, 952), fill=_YLW)
        d.text((164, 800), f"{snap.ram_percent:.0f}", font=f56, fill=_BG, anchor="mm")
        d.text((164, 860), "RAM %", font=f14, fill=_BG, anchor="mm")
        d.rectangle((300, 740, w - 32, 930), fill=(30, 30, 38))
        d.text((320, 760), "MEMORY", font=f14, fill=_CYN)
        d.text((320, 800), f"{snap.ram_used_mb:.0f} MB", font=f36, fill=_WH)
        d.text((320, 860), f"TOTAL {snap.ram_total_gb:.0f} GB", font=f20, fill=(160, 160, 170))

        d.rectangle((32, 970, 350, 1160), outline=_YLW, width=4)
        d.text((52, 990), "STORAGE", font=f14, fill=_YLW)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 1030 + i * 36
            d.text((52, y), f"{str(name)[:8]}", font=f14, fill=_WH)
            text_right(d, (330, y), f"{pct:.0f}%", f14, _MAG)

        d.rectangle((370, 970, w - 32, 1160), fill=_WH)
        d.text((390, 990), "NET", font=f14, fill=_BG)
        d.text((390, 1030), f"↑ {fmt_net(snap.net_up_kb)}", font=f20, fill=_MAG)
        d.text((390, 1080), f"↓ {fmt_net(snap.net_down_kb)}", font=f20, fill=_CYN)
        pts = [(390 + i * 6, 1140 - int(12 * abs(math.sin(i * 0.4 + t * 3)))) for i in range(44)]
        if len(pts) > 1:
            d.line(pts, fill=_BG, width=3)

        d.text((32, 1205), f"{snap.fps:.0f} FPS", font=f36, fill=_BG)
        text_right(d, (w - 32, 1210), now.strftime("%Y.%m.%d"), f20, _BG)
        return img

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f14, f18, f20, f36, f56, f72 = (load_font(n, True) for n in (14, 18, 20, 36, 56, 72))
        self._backdrop(d, w, h)

        d.text((28, 20), now.strftime("%H:%M"), font=f72, fill=_WH)
        d.text((240, 36), snap.host[:22], font=f20, fill=_CYN)
        text_right(d, (w - 28, 28), "GEO · LANDSCAPE", f36, _MAG)

        d.polygon([(20, 100), (620, 100), (580, 340), (20, 340)], fill=_MAG)
        d.text((44, 118), "CPU", font=f20, fill=_WH)
        d.text((44, 152), f"{snap.cpu_usage:.0f}%", font=f56, fill=_WH)
        d.text((260, 168), f"{snap.cpu_temp:.0f}°C", font=f36, fill=_YLW)
        d.text((44, 240), f"{snap.cpu_clock:.0f} MHz  ·  {snap.cpu_fan:.0f} RPM", font=f18, fill=_WH)
        d.text((44, 280), snap.cpu_name[:28], font=f14, fill=(255, 180, 200))

        d.polygon([(660, 100), (w - 20, 100), (w - 20, 340), (700, 340)], fill=_CYN)
        d.text((684, 118), "GPU", font=f20, fill=_BG)
        d.text((684, 152), f"{snap.gpu_usage:.0f}%", font=f56, fill=_BG)
        d.text((900, 168), f"{snap.gpu_temp:.0f}°C", font=f36, fill=_MAG)
        d.text((684, 240), f"{snap.gpu_clock:.0f} MHz  ·  {snap.gpu_fan:.0f} RPM", font=f18, fill=_BG)
        d.text((684, 280), snap.gpu_name[:26], font=f14, fill=(10, 80, 80))

        d.ellipse((24, 370, 200, 546), fill=_YLW)
        d.text((112, 440), f"{snap.ram_percent:.0f}", font=f56, fill=_BG, anchor="mm")
        d.text((112, 490), "RAM", font=f14, fill=_BG, anchor="mm")
        d.rectangle((220, 370, 500, 546), fill=(30, 30, 38))
        d.text((240, 390), "MEMORY", font=f14, fill=_CYN)
        d.text((240, 430), f"{snap.ram_used_mb:.0f} MB", font=f36, fill=_WH)
        d.text((240, 490), f"/ {snap.ram_total_gb:.0f} GB", font=f18, fill=(160, 160, 170))

        d.rectangle((520, 370, 840, 546), outline=_YLW, width=4)
        d.text((540, 390), "STORAGE", font=f14, fill=_YLW)
        disks = (snap.disks + [("D:/", 40), ("E:/", 20)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 430 + i * 36
            d.text((540, y), f"{str(name)[:10]}", font=f14, fill=_WH)
            text_right(d, (820, y), f"{pct:.0f}%", f14, _MAG)

        d.rectangle((860, 370, w - 20, 546), fill=_WH)
        d.text((880, 390), "NET", font=f14, fill=_BG)
        d.text((880, 430), f"↑ {fmt_net(snap.net_up_kb)}", font=f20, fill=_MAG)
        d.text((880, 470), f"↓ {fmt_net(snap.net_down_kb)}", font=f20, fill=_CYN)
        pts = [(880 + i * 6, 530 - int(12 * abs(math.sin(i * 0.4 + t * 3)))) for i in range(58)]
        if len(pts) > 1:
            d.line(pts, fill=_BG, width=3)

        d.text((28, h - 52), f"{snap.fps:.0f} FPS", font=f36, fill=_BG)
        text_right(d, (w - 28, h - 48), now.strftime("%Y.%m.%d"), f20, _BG)
        return img
