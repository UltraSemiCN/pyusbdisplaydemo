from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.core.orientation import normalize_orientation


APP_NAME = "UsbDisplayHud"
RUN_VALUE_NAME = "UsbDisplayHud"


def _settings_path() -> Path:
    root = Path.home() / "AppData" / "Roaming" / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root / "settings.json"


_SLIDESHOW_MODES = frozenset({"sequential", "shuffle", "single"})


def normalize_slideshow_mode(value: object) -> str:
    mode = str(value or "sequential").strip().lower()
    return mode if mode in _SLIDESHOW_MODES else "sequential"


def normalize_slideshow_interval(value: object) -> float:
    try:
        sec = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        sec = 10.0
    return max(1.0, min(3600.0, sec))


@dataclass
class AppSettings:
    theme_id: str = "classic_portrait"
    language: str = "zh_CN"
    favorite_theme_ids: list[str] = field(default_factory=list)
    autostart: bool = True
    auto_run: bool = True  # launch then start streaming
    live_preview: bool = False  # off: first frame only; on: refresh preview while running
    orientation: int = 0  # 0 | 90 | 180 | 270 — screen placement
    encode_jpeg: bool | None = None  # None = follow device.jpeg_support
    interval: float = 0.05  # ~20 Hz target; actual FPS also limited by render/USB
    start_minimized: bool = False
    slideshow_folder: str = ""  # empty = default photos/ next to app
    slideshow_interval_s: float = 10.0
    slideshow_mode: str = "sequential"  # sequential | shuffle | single
    themes_folder: str = ""  # empty = default themes/ next to app
    style_theme_id: str = "classic_portrait"  # last non-slideshow theme
    device_sn: str = ""  # preferred USB display serial; empty = first ready

    @classmethod
    def load(cls) -> AppSettings:
        path = _settings_path()
        if not path.is_file():
            cfg = cls()
            cfg.save()
            return cfg
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            known = set(cls.__dataclass_fields__)
            kwargs = {k: v for k, v in data.items() if k in known}
            fav = kwargs.get("favorite_theme_ids")
            if not isinstance(fav, list):
                kwargs["favorite_theme_ids"] = []
            else:
                kwargs["favorite_theme_ids"] = [str(x) for x in fav if x]
            kwargs["orientation"] = normalize_orientation(kwargs.get("orientation", 0))
            kwargs["slideshow_folder"] = str(kwargs.get("slideshow_folder") or "")
            kwargs["themes_folder"] = str(kwargs.get("themes_folder") or "")
            kwargs["slideshow_interval_s"] = normalize_slideshow_interval(
                kwargs.get("slideshow_interval_s", 10.0)
            )
            kwargs["slideshow_mode"] = normalize_slideshow_mode(
                kwargs.get("slideshow_mode", "sequential")
            )
            style_id = str(kwargs.get("style_theme_id") or "").strip()
            theme_id = str(kwargs.get("theme_id") or "classic_portrait")
            if not style_id or style_id == "photo_slideshow_portrait":
                style_id = (
                    theme_id
                    if theme_id != "photo_slideshow_portrait"
                    else "classic_portrait"
                )
            kwargs["style_theme_id"] = style_id
            kwargs["device_sn"] = str(kwargs.get("device_sn") or "").strip()
            return cls(**kwargs)
        except Exception:
            return cls()

    def save(self) -> None:
        path = _settings_path()
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
