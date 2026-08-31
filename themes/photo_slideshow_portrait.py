from __future__ import annotations

"""照片轮播：竖屏 720×1280 cover；横屏把照片挤扁成 1280×720 再放置。"""

from datetime import datetime

from PIL import Image, ImageDraw

from app.core.metrics import SysSnapshot
from app.core.orientation import normalize_orientation
from app.core.slideshow import shared_album
from app.settings import AppSettings
from app.themes.base import Theme
from app.themes.draw_utils import load_font


class PhotoSlideshowPortraitTheme(Theme):
    id = "photo_slideshow_portrait"
    name = "照片轮播"
    width = 720
    height = 1280
    description = "纯照片全屏轮播：支持默认/自定义文件夹，顺序、乱序或单图"

    def apply_slideshow_settings(self, settings: AppSettings) -> None:
        shared_album().apply_settings(settings)

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
        land = normalize_orientation(orient) in (90, 270)
        return self._render_at(self.canvas_size(orient), stretch=land)

    def render(self, snap: SysSnapshot, now: datetime, t: float = 0.0) -> Image.Image:
        return self._render_at((self.width, self.height), stretch=False)

    def _placeholder(self, message: str, size: tuple[int, int]) -> Image.Image:
        w, h = size
        img = Image.new("RGB", (w, h), (20, 22, 26))
        d = ImageDraw.Draw(img)
        f18 = load_font(18, True, cjk=True)
        f22 = load_font(22, True, cjk=True)
        title = "照片轮播"
        bb = d.textbbox((0, 0), title, font=f22)
        d.text(((w - (bb[2] - bb[0])) / 2, h / 2 - 40), title, font=f22, fill=(220, 220, 220))
        bb2 = d.textbbox((0, 0), message, font=f18)
        d.text(
            ((w - (bb2[2] - bb2[0])) / 2, h / 2 + 4),
            message,
            font=f18,
            fill=(140, 145, 150),
        )
        album = shared_album()
        folder = str(album.folder)
        if len(folder) > 42:
            folder = "…" + folder[-41:]
        bb3 = d.textbbox((0, 0), folder, font=f18)
        d.text(
            ((w - (bb3[2] - bb3[0])) / 2, h / 2 + 40),
            folder,
            font=f18,
            fill=(90, 100, 110),
        )
        return img

    def _render_at(self, size: tuple[int, int], *, stretch: bool) -> Image.Image:
        album = shared_album()
        empty = self._placeholder("未找到图片，请放入 jpg/png 等", size)
        frame = album.frame(size, empty, stretch=stretch)
        return frame.image
