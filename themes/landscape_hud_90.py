from __future__ import annotations

"""90° 摆放主题示例：画布按 picW×picH = screenH×screenW 设计（默认屏 720×1280 → 本主题 1280×720）。

推流链路（由应用层完成，主题只负责画逻辑图）：
  1. 主题 render → 1280×720
  2. 缩放到 picW×picH（= screenH×screenW）
  3. 旋转 90° 后得到 screenW×screenH，再发送
"""

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import clamp01, fmt_net, load_font, text_right

_BG = (6, 10, 14)
_PANEL = (12, 18, 24)
_LINE = (38, 52, 62)
_WHITE = (236, 242, 245)
_MUTED = (120, 140, 150)
_CYAN = (56, 196, 220)
_LIME = (120, 220, 120)
_AMBER = (240, 180, 60)
_RED = (230, 80, 80)


class LandscapeHud90Theme(Theme):
    id = "landscape_hud_90"
    name = "Landscape HUD · 90°"
    width = 1280
    height = 720
    description = (
        "横屏 1280×720 示例主题，配合「摆放方向 90°」："
        "生成图先按 pic=screenH×screenW，再旋转 90° 后发给屏幕。"
        "0°/180° 亦提供竖屏 720×1280 布局。"
    )
    preferred_orientation = 90

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
        return self._render_landscape(snap, now, t)

    @staticmethod
    def _tone(v: float, warn: float = 75, hot: float = 90, ok=_LIME):
        return _RED if v >= hot else _AMBER if v >= warn else ok

    @staticmethod
    def _card(d: ImageDraw.ImageDraw, box, title, f14) -> None:
        d.rounded_rectangle(box, 12, fill=_PANEL, outline=_LINE, width=2)
        d.text((box[0] + 16, box[1] + 12), title, font=f14, fill=_MUTED)

    @staticmethod
    def _bar(d: ImageDraw.ImageDraw, x0, y, x1, value, color) -> None:
        d.rounded_rectangle((x0, y, x1, y + 10), 5, fill=(28, 36, 42))
        x2 = x0 + int((x1 - x0) * clamp01(value / 100))
        if x2 > x0:
            d.rounded_rectangle((x0, y, x2, y + 10), 5, fill=color)

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f12, f14, f18, f22, f36, f56 = (load_font(n, True) for n in (12, 14, 18, 22, 36, 56))
        tone = self._tone
        card = lambda box, title: self._card(d, box, title, f14)
        bar = lambda x0, y, x1, value, color: self._bar(d, x0, y, x1, value, color)

        d.text((24, 18), "LANDSCAPE 90°", font=f18, fill=_CYAN)
        d.text((24, 44), snap.host[:28], font=f14, fill=_MUTED)
        text_right(d, (w - 24, 16), now.strftime("%H:%M:%S"), f36, _WHITE)
        fps_s = f"{snap.fps:.0f} FPS" if snap.fps > 0.05 else "FPS --"
        text_right(d, (w - 24, 56), f"{snap.source.upper()} · {fps_s} · canvas {w}×{h}", f12, _MUTED)
        d.line((24, 82, w - 24, 82), fill=_LINE, width=2)

        card((20, 98, 620, 340), "CPU")
        d.text((40, 140), f"{snap.cpu_usage:.0f}%", font=f56, fill=tone(snap.cpu_usage))
        d.text((200, 170), f"{snap.cpu_temp:.0f}°C", font=f36, fill=tone(snap.cpu_temp, 80, 95, _CYAN))
        d.text((40, 230), f"Clock  {snap.cpu_clock:.0f} MHz", font=f18, fill=_WHITE)
        d.text((40, 262), f"Fan    {snap.cpu_fan:.0f} RPM", font=f18, fill=_WHITE)
        d.text((40, 294), snap.cpu_name[:32], font=f14, fill=_MUTED)
        bar(40, 318, 600, snap.cpu_usage, _CYAN)

        card((660, 98, 1260, 340), "GPU")
        d.text((680, 140), f"{snap.gpu_usage:.0f}%", font=f56, fill=tone(snap.gpu_usage))
        d.text((840, 170), f"{snap.gpu_temp:.0f}°C", font=f36, fill=tone(snap.gpu_temp, 80, 95, _LIME))
        d.text((680, 230), f"Clock  {snap.gpu_clock:.0f} MHz", font=f18, fill=_WHITE)
        d.text((680, 262), f"Fan    {snap.gpu_fan:.0f} RPM", font=f18, fill=_WHITE)
        d.text((680, 294), snap.gpu_name[:32], font=f14, fill=_MUTED)
        bar(680, 318, 1240, snap.gpu_usage, _LIME)

        card((20, 360, 420, 690), "MEMORY")
        d.text((40, 410), f"{snap.ram_percent:.0f}%", font=f56, fill=tone(snap.ram_percent))
        d.text((40, 490), f"{snap.ram_used_mb / 1024:.1f} / {snap.ram_total_gb:.0f} GB", font=f18, fill=_WHITE)
        bar(40, 540, 400, snap.ram_percent, _AMBER)

        card((440, 360, 840, 690), "STORAGE")
        disks = snap.disks[:4] or [("—", 0.0)]
        for i, (name, pct) in enumerate(disks):
            y = 410 + i * 58
            d.text((460, y), str(name)[:14], font=f14, fill=_MUTED)
            text_right(d, (820, y), f"{pct:.0f}%", f18, tone(pct))
            bar(460, y + 28, 820, pct, _CYAN)

        card((860, 360, 1260, 690), "NETWORK")
        d.text((880, 420), "↓ DN", font=f14, fill=_MUTED)
        d.text((880, 448), fmt_net(snap.net_down_kb), font=f22, fill=_CYAN)
        d.text((880, 510), "↑ UP", font=f14, fill=_MUTED)
        d.text((880, 538), fmt_net(snap.net_up_kb), font=f22, fill=_LIME)
        pts = [
            (x, 640 - int(28 * abs(math.sin(i * 0.35 + t * 2.4))))
            for i, x in enumerate(range(880, 1240, 6))
        ]
        if len(pts) > 1:
            d.line(pts, fill=_CYAN, width=2)

        d.text((24, h - 22), "Design canvas 1280×720 → rotate 90° → screen 720×1280", font=f12, fill=_MUTED)
        return img

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        """720×1280 portrait layout using the same cyan HUD chrome."""
        w, h = 720, 1280
        img = Image.new("RGB", (w, h), _BG)
        d = ImageDraw.Draw(img)
        f12, f14, f18, f22, f36, f56 = (load_font(n, True) for n in (12, 14, 18, 22, 36, 56))
        tone = self._tone
        card = lambda box, title: self._card(d, box, title, f14)
        bar = lambda x0, y, x1, value, color: self._bar(d, x0, y, x1, value, color)

        d.text((24, 24), "HUD MONITOR", font=f22, fill=_CYAN)
        d.text((24, 56), snap.host[:22], font=f14, fill=_MUTED)
        text_right(d, (w - 24, 24), now.strftime("%H:%M:%S"), f36, _WHITE)
        fps_s = f"{snap.fps:.0f} FPS" if snap.fps > 0.05 else "FPS --"
        text_right(d, (w - 24, 68), f"{snap.source.upper()} · {fps_s}", f12, _MUTED)
        d.line((24, 96, w - 24, 96), fill=_LINE, width=2)

        card((20, 112, w - 20, 360), "CPU")
        d.text((40, 156), f"{snap.cpu_usage:.0f}%", font=f56, fill=tone(snap.cpu_usage))
        d.text((220, 186), f"{snap.cpu_temp:.0f}°C", font=f36, fill=tone(snap.cpu_temp, 80, 95, _CYAN))
        d.text((40, 250), f"Clock  {snap.cpu_clock:.0f} MHz", font=f18, fill=_WHITE)
        d.text((40, 282), f"Fan    {snap.cpu_fan:.0f} RPM", font=f18, fill=_WHITE)
        d.text((40, 314), snap.cpu_name[:28], font=f14, fill=_MUTED)
        bar(40, 338, w - 40, snap.cpu_usage, _CYAN)

        card((20, 380, w - 20, 628), "GPU")
        d.text((40, 424), f"{snap.gpu_usage:.0f}%", font=f56, fill=tone(snap.gpu_usage))
        d.text((220, 454), f"{snap.gpu_temp:.0f}°C", font=f36, fill=tone(snap.gpu_temp, 80, 95, _LIME))
        d.text((40, 518), f"Clock  {snap.gpu_clock:.0f} MHz", font=f18, fill=_WHITE)
        d.text((40, 550), f"Fan    {snap.gpu_fan:.0f} RPM", font=f18, fill=_WHITE)
        d.text((40, 582), snap.gpu_name[:28], font=f14, fill=_MUTED)
        bar(40, 606, w - 40, snap.gpu_usage, _LIME)

        card((20, 648, w - 20, 820), "MEMORY")
        d.text((40, 688), f"{snap.ram_percent:.0f}%", font=f56, fill=tone(snap.ram_percent))
        d.text((40, 768), f"{snap.ram_used_mb / 1024:.1f} / {snap.ram_total_gb:.0f} GB", font=f18, fill=_WHITE)
        bar(40, 790, w - 40, snap.ram_percent, _AMBER)

        card((20, 840, w - 20, 1040), "STORAGE")
        disks = snap.disks[:4] or [("—", 0.0)]
        for i, (name, pct) in enumerate(disks):
            y = 880 + i * 38
            d.text((40, y), str(name)[:12], font=f14, fill=_MUTED)
            text_right(d, (w - 40, y), f"{pct:.0f}%", f14, tone(pct))
            bar(40, y + 22, w - 40, pct, _CYAN)

        card((20, 1060, w - 20, 1240), "NETWORK")
        d.text((40, 1100), "↓ DN", font=f14, fill=_MUTED)
        d.text((40, 1128), fmt_net(snap.net_down_kb), font=f22, fill=_CYAN)
        d.text((40, 1170), "↑ UP", font=f14, fill=_MUTED)
        d.text((40, 1198), fmt_net(snap.net_up_kb), font=f22, fill=_LIME)
        pts = [
            (x, 1230 - int(20 * abs(math.sin(i * 0.35 + t * 2.4))))
            for i, x in enumerate(range(40, w - 40, 6))
        ]
        if len(pts) > 1:
            d.line(pts, fill=_CYAN, width=2)

        d.text((24, h - 28), "Portrait 720×1280 · HUD chrome", font=f12, fill=_MUTED)
        return img
