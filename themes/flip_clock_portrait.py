from __future__ import annotations

"""竖屏翻页时钟：上半翻页时分秒，下半 AIDA 风格系统信息。"""

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.themes.base import Theme
from app.themes.draw_utils import clamp01, fmt_net, load_font, mix, text_right

_WEEKDAYS_ZH = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
_MONTHS_ZH = (
    "",
    "1月",
    "2月",
    "3月",
    "4月",
    "5月",
    "6月",
    "7月",
    "8月",
    "9月",
    "10月",
    "11月",
    "12月",
)


class FlipClockPortraitTheme(Theme):
    id = "flip_clock_portrait"
    name = "翻页时钟"
    width = 720
    height = 1280
    description = "上半翻页时钟，下半 AIDA 系统信息，各占一半"

    def render(self, snap: SysSnapshot, now: datetime, t: float = 0.0) -> Image.Image:
        w, h = self.width, self.height
        mid = h // 2  # 640

        # Clock palette
        bg = (28, 30, 34)
        case = (18, 19, 22)
        card_hi = (48, 50, 58)
        card_lo = (28, 30, 36)
        crease = (12, 12, 14)
        digit = (245, 240, 230)
        mute = (140, 145, 150)

        # AIDA palette
        panel = (10, 12, 14)
        line = (47, 52, 56)
        white, gray = (235, 238, 239), (139, 147, 151)
        yellow, cyan, green, amber, red = (
            (241, 212, 74),
            (52, 181, 218),
            (61, 195, 126),
            (245, 159, 54),
            (232, 73, 76),
        )

        img = Image.new("RGB", (w, h), bg)
        d = ImageDraw.Draw(img)

        f12 = load_font(12, True, cjk=True)
        f14 = load_font(14, True, cjk=True)
        f16 = load_font(16, True, cjk=True)
        f18 = load_font(18, True, cjk=True)
        f22 = load_font(22, True, cjk=True)
        f28 = load_font(28, True, cjk=True)
        f80 = load_font(80, True)

        def severity(value, warn=75, hot=90, normal=green):
            return red if value >= hot else amber if value >= warn else normal

        # ── Top half: flip clock ──────────────────────────────────────────
        d.rounded_rectangle((24, 20, w - 24, mid - 16), 24, fill=case)
        d.rounded_rectangle((36, 32, w - 36, mid - 28), 18, fill=(24, 25, 28))

        def flip_card(box: tuple[int, int, int, int], ch: str, pulse: float = 0.0) -> None:
            x0, y0, x1, y1 = box
            d.rounded_rectangle((x0 + 4, y0 + 5, x1 + 4, y1 + 5), 12, fill=(10, 10, 12))
            m = (y0 + y1) // 2
            d.rounded_rectangle((x0, y0, x1, m + 2), 12, fill=card_hi)
            d.rounded_rectangle((x0, m - 2, x1, y1), 12, fill=card_lo)
            d.rectangle((x0, m - 2, x1, m + 2), fill=crease)
            d.rectangle((x0 + 10, y0 + 8, x1 - 10, y0 + 12), fill=(70, 72, 80))
            if pulse > 0.55:
                d.rectangle((x0, m - 8, x1, m + 8), fill=(55, 58, 66))
            bb = d.textbbox((0, 0), ch, font=f80)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            d.text(((x0 + x1 - tw) / 2, (y0 + y1 - th) / 2 - bb[1]), ch, font=f80, fill=digit)
            d.rectangle((x0, m - 1, x1, m + 1), fill=crease)
            d.line((x0 + 6, m, x1 - 6, m), fill=(60, 62, 70), width=1)

        hh, mm, ss = now.strftime("%H"), now.strftime("%M"), now.strftime("%S")
        sec_pulse = 0.5 + 0.5 * math.sin(t * math.pi * 2)

        card_w, card_h, gap = 200, 145, 20
        rows = (
            (hh, "时", 48, 0.0),
            (mm, "分", 48 + card_h + 42, 0.0),
            (ss, "秒", 48 + 2 * (card_h + 42), sec_pulse),
        )
        for digits, label, top, pulse in rows:
            total = card_w * 2 + gap
            left = (w - total) // 2
            flip_card((left, top, left + card_w, top + card_h), digits[0], pulse)
            flip_card(
                (left + card_w + gap, top, left + total, top + card_h),
                digits[1],
                pulse,
            )
            bb = d.textbbox((0, 0), label, font=f14)
            d.text(((w - (bb[2] - bb[0])) / 2, top + card_h + 6), label, font=f14, fill=mute)

        date_s = f"{now.year}年{_MONTHS_ZH[now.month]}{now.day}日  {_WEEKDAYS_ZH[now.weekday()]}"
        bb = d.textbbox((0, 0), date_s, font=f18)
        d.text(((w - (bb[2] - bb[0])) / 2, mid - 58), date_s, font=f18, fill=digit)

        # ── Bottom half: AIDA info ────────────────────────────────────────
        y0 = mid + 8

        def panel_box(box, title, accent=yellow):
            d.rounded_rectangle(box, 8, fill=panel, outline=line, width=2)
            d.rectangle((box[0], box[1], box[0] + 4, box[3]), fill=accent)
            d.text((box[0] + 14, box[1] + 8), title, font=f12, fill=gray)

        def progress(x_a, y, x_b, value, color):
            d.rectangle((x_a, y, x_b, y + 7), fill=(29, 33, 36))
            x2 = x_a + int((x_b - x_a) * clamp01(value / 100))
            if x2 > x_a:
                d.rectangle((x_a, y, x2, y + 7), fill=color)

        def metric(x, y, label, value, color=white):
            d.text((x, y), label, font=f12, fill=gray)
            d.text((x, y + 16), value, font=f16, fill=color)

        # Header strip
        d.text((28, y0), "AIDA64 / SYSTEM", font=f16, fill=yellow)
        d.text((28, y0 + 24), snap.host[:22], font=f14, fill=gray)
        fps_s = f"{snap.fps:.0f} FPS" if snap.fps > 0.05 else "FPS --"
        text_right(d, (w - 28, y0), snap.source.upper(), f16, cyan)
        text_right(d, (w - 28, y0 + 24), fps_s, f12, mute)
        d.line((28, y0 + 50, w - 28, y0 + 50), fill=line, width=2)

        # Primary health — 4 metrics
        panel_box((20, y0 + 60, 700, y0 + 200), "PRIMARY HEALTH", red)
        primary = (
            ("CPU TEMP", snap.cpu_temp, "°C", cyan, 85),
            ("CPU LOAD", snap.cpu_usage, "%", cyan, 90),
            ("GPU TEMP", snap.gpu_temp, "°C", green, 85),
            ("GPU LOAD", snap.gpu_usage, "%", green, 90),
        )
        for i, (lab, val, unit, accent, hot) in enumerate(primary):
            x = 40 + (i % 2) * 340
            y = y0 + 92 + (i // 2) * 48
            col = severity(val, hot - 12, hot, accent)
            d.text((x, y), lab, font=f12, fill=gray)
            d.text((x, y + 16), f"{val:.0f}{unit}", font=f22, fill=col)
            progress(x + 100, y + 24, x + 300, val, col)

        # CPU / GPU side panels
        panel_box((20, y0 + 212, 350, y0 + 360), "CPU", cyan)
        metric(40, y0 + 244, "CLOCK", f"{snap.cpu_clock:.0f} MHz")
        metric(190, y0 + 244, "FAN", f"{snap.cpu_fan:.0f} RPM")
        d.text((40, y0 + 296), snap.cpu_name[:22], font=f14, fill=white)
        d.text(
            (40, y0 + 324),
            f"{snap.cpu_usage:.0f}%  ·  {snap.cpu_temp:.0f}°C",
            font=f16,
            fill=severity(max(snap.cpu_usage, snap.cpu_temp), normal=cyan),
        )

        panel_box((370, y0 + 212, 700, y0 + 360), "GPU", green)
        metric(390, y0 + 244, "CLOCK", f"{snap.gpu_clock:.0f} MHz")
        metric(540, y0 + 244, "FAN", f"{snap.gpu_fan:.0f} RPM")
        d.text((390, y0 + 296), snap.gpu_name[:22], font=f14, fill=white)
        d.text(
            (390, y0 + 324),
            f"{snap.gpu_usage:.0f}%  ·  {snap.gpu_temp:.0f}°C",
            font=f16,
            fill=severity(max(snap.gpu_usage, snap.gpu_temp), normal=green),
        )

        # Memory
        panel_box((20, y0 + 372, 700, y0 + 478), "MEMORY", yellow)
        ram_col = severity(snap.ram_percent, 80, 92, yellow)
        d.text((40, y0 + 404), f"{snap.ram_percent:.0f}%", font=f28, fill=ram_col)
        d.text((140, y0 + 408), "USED", font=f12, fill=gray)
        d.text((140, y0 + 426), f"{snap.ram_used_mb / 1024:.1f} GB", font=f18, fill=white)
        d.text((320, y0 + 408), "TOTAL", font=f12, fill=gray)
        d.text((320, y0 + 426), f"{snap.ram_total_gb:.1f} GB", font=f18, fill=white)
        progress(40, y0 + 458, 680, snap.ram_percent, severity(snap.ram_percent, 80, 92, cyan))

        # Storage + network row
        panel_box((20, y0 + 490, 350, y0 + 612), "STORAGE", green)
        disks = snap.disks[:2]
        if not disks:
            d.text((40, y0 + 540), "NO DISK DATA", font=f14, fill=gray)
        for i, (name, pct) in enumerate(disks):
            y = y0 + 528 + i * 36
            col = severity(pct, 80, 92, green)
            d.text((40, y), str(name)[:10], font=f14, fill=white)
            progress(120, y + 5, 280, pct, mix(green, red, clamp01(pct / 100)))
            text_right(d, (330, y), f"{pct:.0f}%", f14, col)

        panel_box((370, y0 + 490, 700, y0 + 612), "NETWORK", cyan)
        metric(390, y0 + 528, "↓ DOWN", fmt_net(snap.net_down_kb), cyan)
        metric(540, y0 + 528, "↑ UP", fmt_net(snap.net_up_kb), green)
        d.text((390, y0 + 580), f"SRC {snap.source.upper()}", font=f12, fill=gray)

        return img
