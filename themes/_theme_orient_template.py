# =============================================================================
# 角度适配主题 · 代码模板（本文件以下划线开头，不会被应用加载）
# =============================================================================
#
# 【用法】
# 1. 复制本文件，改名为不含前导 _ 的名字，例如：aurora_hud.py
# 2. 把下面「生成主题提示词」整段发给 AI，并附上你的风格描述
# 3. 或人工把标记 <<<...>>> 的地方全部替换掉
# 4. 应用内点「刷新模板」即可出现新主题
#
# 【摆放角度约定 — 必须遵守】
# - 0° / 180° → 逻辑画布 720×1280（竖屏排布），画在 _render_portrait
# - 90° / 270° → 逻辑画布 1280×720（横屏排布），画在 _render_landscape
# - 不要「先画竖屏再旋转当横屏」；发送侧会再按角度旋转，主题只画逻辑图
# - 两套排布要用同一套配色 / 字体气质，只改布局
#
# 【可选用字段 SysSnapshot】
#   host, source, fps
#   cpu_name, cpu_usage, cpu_temp, cpu_clock, cpu_fan
#   gpu_name, gpu_usage, gpu_temp, gpu_clock, gpu_fan
#   ram_percent, ram_used_mb, ram_total_gb
#   disks: list[(name, percent)]
#   net_up_kb, net_down_kb
#   工具: load_font, text_right, fmt_net, mix, clamp01
#
# 【生成主题提示词 — 复制从下一行到 END PROMPT】
# -----------------------------------------------------------------------------
# 请基于仓库文件 themes/_theme_orient_template.py 生成一个新的 USB Display HUD 主题。
#
# 硬性要求：
# 1. 新建 themes/<snake_id>.py（不要以下划线开头），不要改模板文件本身。
# 2. 继承 app.themes.base.Theme；实现 canvas_size / render_frame / render /
#    _render_portrait / _render_landscape（结构与模板一致）。
# 3. id、name、description、类名与文件名一致且唯一；width=720, height=1280。
# 4. 0°/180° 画 720×1280 竖屏布局；90°/270° 画 1280×720 横屏布局。
#    两套布局视觉语言一致，禁止只旋转竖屏图冒充横屏。
# 5. 展示至少：时间、主机/数据源、CPU、GPU、内存、磁盘、网络；可用 snap.* 字段。
# 6. 只用 PIL Image/ImageDraw 与 app.themes.draw_utils；不要新增依赖。
# 7. 不要设置 preferred_orientation（让用户自由选角度），除非我明确要求。
#
# 风格需求（由用户填写）：
# - 风格名 / 参考：<<<例如 StyleKit Soft UI / 赛博霓虹 / 杂志排版>>>
# - 主色与氛围：<<<例如深色背景 + 青色描边，克制不要紫渐变默认腔>>>
# - 版式偏好：<<<例如竖屏上下卡片；横屏左右 CPU|GPU，底栏三列>>>
# - 其它约束：<<<可选>>>
# END PROMPT
# -----------------------------------------------------------------------------
# =============================================================================

from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.themes.base import Theme
from app.themes.draw_utils import fmt_net, load_font, mix, text_right

# <<<REPLACE: 配色 — 用主题气质替换下面占位色>>>
_BG = (18, 22, 28)
_PANEL = (28, 34, 42)
_LINE = (48, 58, 70)
_TEXT = (236, 240, 244)
_MUTED = (140, 152, 164)
_ACCENT = (80, 200, 180)
_ACCENT2 = (240, 180, 80)


class OrientThemeTemplate(Theme):  # <<<REPLACE: 类名，如 AuroraHudTheme>>>
    id = "orient_theme_template"  # <<<REPLACE: 唯一 snake_case id>>>
    name = "角度主题模板"  # <<<REPLACE: 列表显示名>>>
    width = 720
    height = 1280
    description = (
        "可复制的角度适配主题骨架：0°/180° 竖屏，90°/270° 横屏。"
        # <<<REPLACE: 一句话描述风格>>>
    )
    # preferred_orientation = 90  # 可选：选中主题时自动勾选该角度

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

    # --- 共用绘制 -----------------------------------------------------------

    def _canvas(self, w: int, h: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (w, h), _BG)
        return img, ImageDraw.Draw(img)

    @staticmethod
    def _card(d: ImageDraw.ImageDraw, box, fill=_PANEL) -> None:
        d.rounded_rectangle(box, 14, fill=fill, outline=_LINE, width=2)

    @staticmethod
    def _bar(d: ImageDraw.ImageDraw, x0: int, y: int, x1: int, pct: float, fill) -> None:
        d.rounded_rectangle((x0, y, x1, y + 10), 5, fill=_LINE)
        x2 = x0 + int((x1 - x0) * max(0.0, min(100.0, pct)) / 100.0)
        if x2 > x0 + 2:
            d.rounded_rectangle((x0, y, x2, y + 10), 5, fill=fill)

    # --- 竖屏 720×1280（0° / 180°）------------------------------------------

    def _render_portrait(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 720, 1280
        img, d = self._canvas(w, h)
        f14, f18, f28, f40, f56 = (load_font(n, True) for n in (14, 18, 28, 40, 56))

        # <<<REPLACE: 按风格重排；保留指标完整性>>>
        self._card(d, (20, 20, w - 20, 140))
        d.text((40, 36), now.strftime("%H:%M"), font=f56, fill=_TEXT)
        d.text((40, 105), f"{snap.host[:18]} · {snap.source.upper()}", font=f14, fill=_MUTED)
        text_right(d, (w - 40, 44), f"{snap.fps:.0f}", f28, _ACCENT)

        self._card(d, (20, 160, w - 20, 400))
        d.text((40, 180), "CPU", font=f14, fill=_MUTED)
        d.text((40, 220), f"{snap.cpu_usage:.0f}%", font=f56, fill=_TEXT)
        d.text((260, 240), f"{snap.cpu_temp:.0f}°C", font=f40, fill=_ACCENT)
        d.text((40, 310), f"{snap.cpu_clock:.0f} MHz · {snap.cpu_fan:.0f} RPM", font=f18, fill=_MUTED)
        d.text((40, 345), snap.cpu_name[:28], font=f14, fill=_MUTED)
        self._bar(d, 40, 370, w - 40, snap.cpu_usage, _ACCENT)

        self._card(d, (20, 420, w - 20, 660))
        d.text((40, 440), "GPU", font=f14, fill=_MUTED)
        d.text((40, 480), f"{snap.gpu_usage:.0f}%", font=f56, fill=_TEXT)
        d.text((260, 500), f"{snap.gpu_temp:.0f}°C", font=f40, fill=_ACCENT2)
        d.text((40, 570), f"{snap.gpu_clock:.0f} MHz · {snap.gpu_fan:.0f} RPM", font=f18, fill=_MUTED)
        d.text((40, 605), snap.gpu_name[:26], font=f14, fill=_MUTED)
        self._bar(d, 40, 630, w - 40, snap.gpu_usage, _ACCENT2)

        self._card(d, (20, 680, w - 20, 860))
        d.text((40, 700), "MEMORY", font=f14, fill=_MUTED)
        d.text((40, 740), f"{snap.ram_percent:.0f}%", font=f40, fill=_TEXT)
        d.text(
            (40, 800),
            f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB",
            font=f18,
            fill=_MUTED,
        )
        self._bar(d, 40, 830, w - 40, snap.ram_percent, _ACCENT)

        mid = w // 2
        self._card(d, (20, 880, mid - 8, 1120))
        d.text((40, 900), "STORAGE", font=f14, fill=_MUTED)
        disks = (snap.disks + [("D:/", 40.0), ("E:/", 20.0)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 950 + i * 48
            d.text((40, y), str(name)[:8], font=f14, fill=_TEXT)
            text_right(d, (mid - 24, y), f"{pct:.0f}%", f14, mix(_ACCENT, _ACCENT2, pct / 100))

        self._card(d, (mid + 8, 880, w - 20, 1120))
        d.text((mid + 28, 900), "NETWORK", font=f14, fill=_MUTED)
        d.text((mid + 28, 960), f"↑ {fmt_net(snap.net_up_kb)}", font=f18, fill=_ACCENT)
        d.text((mid + 28, 1010), f"↓ {fmt_net(snap.net_down_kb)}", font=f18, fill=_ACCENT2)
        pts = [
            (mid + 28 + i * 6, 1085 - int(12 * abs(math.sin(i * 0.35 + t))))
            for i in range(40)
        ]
        if len(pts) > 1:
            d.line(pts, fill=_ACCENT, width=2)

        self._card(d, (20, 1140, w - 20, h - 20))
        d.text((40, 1185), now.strftime("%A · %d %B"), font=f18, fill=_MUTED)
        text_right(d, (w - 40, 1180), "TEMPLATE", f28, _ACCENT)
        return img

    # --- 横屏 1280×720（90° / 270°）------------------------------------------

    def _render_landscape(
        self, snap: SysSnapshot, now: datetime, t: float
    ) -> Image.Image:
        w, h = 1280, 720
        img, d = self._canvas(w, h)
        f14, f18, f22, f28, f40, f56 = (load_font(n, True) for n in (14, 18, 22, 28, 40, 56))

        # <<<REPLACE: 横屏版式 — 建议顶栏 + CPU|GPU + 底三列>>>
        self._card(d, (16, 14, w - 16, 100))
        d.text((36, 28), now.strftime("%H:%M"), font=f56, fill=_TEXT)
        d.text((220, 36), f"{snap.host[:22]} · {snap.source.upper()}", font=f18, fill=_MUTED)
        d.text((220, 66), now.strftime("%A · %d %B"), font=f14, fill=_MUTED)
        text_right(d, (w - 36, 32), f"{snap.fps:.0f} FPS", f22, _ACCENT)
        text_right(d, (w - 36, 66), "LANDSCAPE", f14, _MUTED)

        self._card(d, (16, 116, w // 2 - 10, 400))
        d.text((36, 134), "CPU", font=f14, fill=_MUTED)
        d.text((36, 168), f"{snap.cpu_usage:.0f}%", font=f56, fill=_TEXT)
        d.text((220, 188), f"{snap.cpu_temp:.0f}°C", font=f40, fill=_ACCENT)
        d.text((36, 260), f"{snap.cpu_clock:.0f} MHz · {snap.cpu_fan:.0f} RPM", font=f18, fill=_MUTED)
        d.text((36, 300), snap.cpu_name[:34], font=f14, fill=_MUTED)
        self._bar(d, 36, 350, w // 2 - 36, snap.cpu_usage, _ACCENT)

        self._card(d, (w // 2 + 10, 116, w - 16, 400))
        d.text((w // 2 + 30, 134), "GPU", font=f14, fill=_MUTED)
        d.text((w // 2 + 30, 168), f"{snap.gpu_usage:.0f}%", font=f56, fill=_TEXT)
        d.text((w // 2 + 214, 188), f"{snap.gpu_temp:.0f}°C", font=f40, fill=_ACCENT2)
        d.text(
            (w // 2 + 30, 260),
            f"{snap.gpu_clock:.0f} MHz · {snap.gpu_fan:.0f} RPM",
            font=f18,
            fill=_MUTED,
        )
        d.text((w // 2 + 30, 300), snap.gpu_name[:30], font=f14, fill=_MUTED)
        self._bar(d, w // 2 + 30, 350, w - 36, snap.gpu_usage, _ACCENT2)

        col = (w - 48) // 3
        b0 = (16, 420, 16 + col, h - 16)
        b1 = (16 + col + 8, 420, 16 + 2 * col + 8, h - 16)
        b2 = (16 + 2 * col + 16, 420, w - 16, h - 16)

        self._card(d, b0)
        d.text((b0[0] + 20, 440), "MEMORY", font=f14, fill=_MUTED)
        d.text((b0[0] + 20, 480), f"{snap.ram_percent:.0f}%", font=f40, fill=_TEXT)
        d.text(
            (b0[0] + 20, 545),
            f"{snap.ram_used_mb:.0f} MB / {snap.ram_total_gb:.0f} GB",
            font=f14,
            fill=_MUTED,
        )
        self._bar(d, b0[0] + 20, 600, b0[2] - 20, snap.ram_percent, _ACCENT)

        self._card(d, b1)
        d.text((b1[0] + 20, 440), "STORAGE", font=f14, fill=_MUTED)
        disks = (snap.disks + [("D:/", 40.0), ("E:/", 20.0)])[:3]
        for i, (name, pct) in enumerate(disks):
            y = 490 + i * 48
            d.text((b1[0] + 20, y), str(name)[:10], font=f18, fill=_TEXT)
            text_right(d, (b1[2] - 20, y), f"{pct:.0f}%", f18, mix(_ACCENT, _ACCENT2, pct / 100))
            self._bar(d, b1[0] + 20, y + 26, b1[2] - 20, pct, _ACCENT2)

        self._card(d, b2)
        d.text((b2[0] + 20, 440), "NETWORK", font=f14, fill=_MUTED)
        d.text((b2[0] + 20, 500), f"↑ {fmt_net(snap.net_up_kb)}", font=f28, fill=_ACCENT)
        d.text((b2[0] + 20, 555), f"↓ {fmt_net(snap.net_down_kb)}", font=f28, fill=_ACCENT2)
        pts = [
            (b2[0] + 20 + i * 7, 660 - int(16 * abs(math.sin(i * 0.35 + t))))
            for i in range(max(8, (b2[2] - b2[0] - 40) // 7))
        ]
        if len(pts) > 1:
            d.line(pts, fill=_ACCENT, width=2)
        return img
