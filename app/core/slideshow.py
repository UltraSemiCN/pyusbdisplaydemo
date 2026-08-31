from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from app.paths import app_root
from app.settings import (
    AppSettings,
    normalize_slideshow_interval,
    normalize_slideshow_mode,
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
FADE_SECONDS = 0.6


def default_photos_dir() -> Path:
    return app_root() / "photos"


def ensure_default_photos_dir() -> Path:
    """Create default photos folder and a short README if missing."""
    root = default_photos_dir()
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.txt"
    if not readme.is_file():
        readme.write_text(
            "将图片放进此目录即可用于「照片轮播」主题。\n"
            "支持 jpg / jpeg / png / bmp / webp。\n"
            "Put image files here for the Photo Slideshow theme.\n",
            encoding="utf-8",
        )
    return root


def resolve_folder(folder: str | None) -> Path:
    raw = (folder or "").strip()
    if not raw:
        return ensure_default_photos_dir()
    return Path(raw)


def scan_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    files: list[Path] = []
    try:
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                files.append(p)
    except OSError:
        return []
    files.sort(key=lambda p: p.name.lower())
    return files


def cover_fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale and center-crop so the image fills size exactly."""
    tw, th = size
    src = img.convert("RGB")
    sw, sh = src.size
    if sw <= 0 or sh <= 0:
        return Image.new("RGB", size, (20, 22, 26))
    scale = max(tw / sw, th / sh)
    nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, (nw - tw) // 2)
    top = max(0, (nh - th) // 2)
    return resized.crop((left, top, left + tw, top + th))


def stretch_fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Resize to size exactly, allowing the image to be squashed."""
    tw, th = size
    src = img.convert("RGB")
    sw, sh = src.size
    if sw <= 0 or sh <= 0:
        return Image.new("RGB", size, (20, 22, 26))
    if src.size == (tw, th):
        return src
    return src.resize((tw, th), Image.Resampling.LANCZOS)


@dataclass
class SlideFrame:
    image: Image.Image
    path: Path | None
    fading: bool = False


class SlideshowAlbum:
    """Wall-clock slideshow: sequential / shuffle / single with optional fade."""

    def __init__(self) -> None:
        self._folder = ensure_default_photos_dir()
        self._interval_s = 10.0
        self._mode = "sequential"
        self._files: list[Path] = []
        self._order: list[Path] = []
        self._index = 0
        self._slide_started = time.monotonic()
        self._cache: dict[str, Image.Image] = {}
        self._prev_path: Path | None = None
        self._curr_path: Path | None = None
        self.reload()

    def apply_settings(self, settings: AppSettings) -> None:
        folder = resolve_folder(settings.slideshow_folder)
        interval = normalize_slideshow_interval(settings.slideshow_interval_s)
        mode = normalize_slideshow_mode(settings.slideshow_mode)
        changed = (
            folder != self._folder
            or abs(interval - self._interval_s) > 1e-6
            or mode != self._mode
        )
        self._folder = folder
        self._interval_s = interval
        self._mode = mode
        if changed:
            self.reload()

    def reload(self) -> None:
        self._files = scan_images(self._folder)
        self._rebuild_order(reshuffle=True)
        self._index = 0
        self._slide_started = time.monotonic()
        self._prev_path = None
        self._curr_path = self._order[0] if self._order else None
        self._cache.clear()

    @property
    def folder(self) -> Path:
        return self._folder

    @property
    def file_count(self) -> int:
        return len(self._files)

    def _rebuild_order(self, *, reshuffle: bool) -> None:
        if not self._files:
            self._order = []
            return
        if self._mode == "shuffle":
            self._order = list(self._files)
            if reshuffle and len(self._order) > 1:
                random.shuffle(self._order)
                # Avoid starting with the same file as last current when possible.
                if self._curr_path in self._order and self._order[0] == self._curr_path:
                    self._order[0], self._order[1] = self._order[1], self._order[0]
        else:
            self._order = list(self._files)

    def _advance(self) -> None:
        if self._mode == "single" or len(self._order) <= 1:
            return
        self._prev_path = self._curr_path
        self._index += 1
        if self._index >= len(self._order):
            self._index = 0
            if self._mode == "shuffle":
                last = self._curr_path
                self._rebuild_order(reshuffle=True)
                if last is not None and len(self._order) > 1 and self._order[0] == last:
                    self._order[0], self._order[1] = self._order[1], self._order[0]
        self._curr_path = self._order[self._index]
        self._slide_started = time.monotonic()

    def _tick(self, now_mono: float | None = None) -> None:
        if self._mode == "single" or not self._order:
            return
        now = time.monotonic() if now_mono is None else now_mono
        if now - self._slide_started >= self._interval_s:
            self._advance()

    def _load(self, path: Path, size: tuple[int, int], *, stretch: bool = False) -> Image.Image | None:
        try:
            mtime = path.stat().st_mtime_ns
            mode = "stretch" if stretch else "cover"
            key = f"{path.resolve()}|{size[0]}x{size[1]}|{mode}|{mtime}"
        except OSError:
            return None
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            with Image.open(path) as im:
                fitted = stretch_fit(im, size) if stretch else cover_fit(im, size)
        except Exception:
            return None
        # Keep cache small
        if len(self._cache) > 8:
            self._cache.clear()
        self._cache[key] = fitted
        return fitted

    def frame(
        self,
        size: tuple[int, int],
        placeholder: Image.Image,
        *,
        stretch: bool = False,
    ) -> SlideFrame:
        self._tick()
        if not self._curr_path:
            return SlideFrame(image=placeholder, path=None, fading=False)

        curr = self._load(self._curr_path, size, stretch=stretch)
        if curr is None:
            # Skip broken file once
            if self._mode != "single" and len(self._order) > 1:
                self._advance()
                if self._curr_path:
                    curr = self._load(self._curr_path, size, stretch=stretch)
            if curr is None:
                return SlideFrame(image=placeholder, path=None, fading=False)

        elapsed = time.monotonic() - self._slide_started
        if (
            self._prev_path is not None
            and self._mode != "single"
            and elapsed < FADE_SECONDS
        ):
            prev = self._load(self._prev_path, size, stretch=stretch)
            if prev is not None:
                alpha = max(0.0, min(1.0, elapsed / FADE_SECONDS))
                blended = Image.blend(prev, curr, alpha)
                return SlideFrame(image=blended, path=self._curr_path, fading=True)

        return SlideFrame(image=curr, path=self._curr_path, fading=False)


# Shared album used by the photo slideshow theme (injected from UI).
_SHARED: SlideshowAlbum | None = None


def shared_album() -> SlideshowAlbum:
    global _SHARED
    if _SHARED is None:
        _SHARED = SlideshowAlbum()
    return _SHARED
