"""Screen placement orientation → pic size + send-side rotation."""

from __future__ import annotations

from PIL import Image

# UI / settings values
ORIENTATIONS: tuple[int, ...] = (0, 90, 180, 270)

# PIL transpose angles are counter-clockwise.
_ROTATE = {
    90: Image.Transpose.ROTATE_90,
    180: Image.Transpose.ROTATE_180,
    270: Image.Transpose.ROTATE_270,
}


def normalize_orientation(value: object) -> int:
    try:
        deg = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    return deg if deg in ORIENTATIONS else 0


def pic_size(screen_w: int, screen_h: int, orientation: int) -> tuple[int, int]:
    """Logical generate size (picW, picH) before rotation."""
    sw, sh = max(1, int(screen_w)), max(1, int(screen_h))
    orient = normalize_orientation(orientation)
    if orient in (90, 270):
        return sh, sw  # picW=screenH, picH=screenW
    return sw, sh


def prepare_frame(image: Image.Image, screen_w: int, screen_h: int, orientation: int) -> Image.Image:
    """Resize to pic size, then rotate so the result matches screenW×screenH."""
    orient = normalize_orientation(orientation)
    pic_w, pic_h = pic_size(screen_w, screen_h, orient)
    img = image
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    if img.size != (pic_w, pic_h):
        img = img.resize((pic_w, pic_h), Image.Resampling.LANCZOS)
    op = _ROTATE.get(orient)
    if op is not None:
        img = img.transpose(op)
    # Guard: device expects exact screen size
    if img.size != (screen_w, screen_h):
        img = img.resize((screen_w, screen_h), Image.Resampling.LANCZOS)
    return img
