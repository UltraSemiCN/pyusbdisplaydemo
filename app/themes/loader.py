from __future__ import annotations

import importlib.util
import inspect
import sys
import traceback
from pathlib import Path

from app.paths import themes_dir
from app.themes.base import Theme

_cache: list[Theme] | None = None


def _is_theme_class(obj: object) -> bool:
    return (
        inspect.isclass(obj)
        and issubclass(obj, Theme)  # type: ignore[arg-type]
        and obj is not Theme
        and not inspect.isabstract(obj)
    )


def _load_module(path: Path):
    mod_name = f"usbdisplay_user_theme_{path.stem}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load theme: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def discover_themes(force: bool = False) -> list[Theme]:
    """Load Theme subclasses from loose *.py files under themes/."""
    global _cache
    if _cache is not None and not force:
        return list(_cache)

    folder = themes_dir()
    folder.mkdir(parents=True, exist_ok=True)
    themes: list[Theme] = []
    errors: list[str] = []

    for path in sorted(folder.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            module = _load_module(path)
            found = False
            for _, obj in inspect.getmembers(module, _is_theme_class):
                themes.append(obj())  # type: ignore[operator]
                found = True
            if not found:
                errors.append(f"{path.name}: 未找到 Theme 子类")
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
            traceback.print_exc()

    _cache = themes
    # Stash last errors for UI if needed
    discover_themes.last_errors = errors  # type: ignore[attr-defined]
    return list(themes)


discover_themes.last_errors = []  # type: ignore[attr-defined]


def all_themes(force: bool = False) -> list[Theme]:
    return discover_themes(force=force)


def get_theme(theme_id: str) -> Theme:
    themes = all_themes()
    if not themes:
        folder = themes_dir()
        files = sorted(p.name for p in folder.glob("*.py") if not p.name.startswith("_"))
        errs = getattr(discover_themes, "last_errors", []) or []
        detail = ""
        if files:
            detail += f"\n已找到文件: {', '.join(files)}"
        else:
            detail += "\n目录下没有 .py 文件"
        if errs:
            detail += "\n加载失败:\n- " + "\n- ".join(errs[:8])
        raise RuntimeError(f"未在 {folder} 加载到可用风格模板。{detail}")
    for t in themes:
        if t.id == theme_id:
            return t
    return themes[0]


def themes_path() -> Path:
    return themes_dir()
