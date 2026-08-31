from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """Directory that contains themes/ next to the app (dev or frozen exe)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def default_themes_dir() -> Path:
    return app_root() / "themes"


# Empty / None → default themes/ next to the app.
_custom_themes_dir: str | None = None


def set_themes_folder(folder: str | None) -> None:
    """Override themes directory; empty restores default_themes_dir()."""
    global _custom_themes_dir
    raw = (folder or "").strip()
    _custom_themes_dir = raw or None


def themes_dir() -> Path:
    if _custom_themes_dir:
        return Path(_custom_themes_dir)
    return default_themes_dir()
