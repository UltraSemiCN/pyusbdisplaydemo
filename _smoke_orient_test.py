"""Quick smoke test for orientation-aware themes."""
from __future__ import annotations

import inspect
from datetime import datetime
from pathlib import Path

from app.core.metrics import SysSnapshot
from app.themes.loader import _is_theme_class, _load_module

THEMES = [
    "cyan_hud_portrait",
    "soft_ui_portrait",
    "retro_vintage_portrait",
    "notion_style_portrait",
    "neo_brutalist_portrait",
    "photo_slideshow_portrait",
]


def main() -> None:
    snap = SysSnapshot(
        host="TEST-HOST",
        source="mock",
        cpu_name="Test CPU",
        cpu_usage=45.0,
        cpu_temp=62.0,
        cpu_clock=3600.0,
        cpu_fan=1200.0,
        gpu_name="Test GPU",
        gpu_usage=30.0,
        gpu_temp=55.0,
        gpu_clock=1800.0,
        gpu_fan=900.0,
        ram_total_gb=16.0,
        ram_used_mb=8192.0,
        ram_percent=50.0,
        disks=[("C:/", 60.0), ("D:/", 40.0)],
        net_up_kb=512.0,
        net_down_kb=1024.0,
        fps=30.0,
    )
    now = datetime.now()
    folder = Path("themes")

    for name in THEMES:
        mod = _load_module(folder / f"{name}.py")
        theme = None
        for _, obj in inspect.getmembers(mod, _is_theme_class):
            theme = obj()
            break
        assert theme is not None, f"{name}: no Theme subclass"

        cs0 = theme.canvas_size(0)
        cs90 = theme.canvas_size(90)
        assert cs0 == (720, 1280), f"{name} canvas_size(0) = {cs0}"
        assert cs90 == (1280, 720), f"{name} canvas_size(90) = {cs90}"

        img0 = theme.render_frame(snap, now, 0.0, orient=0)
        img90 = theme.render_frame(snap, now, 0.0, orient=90)
        assert img0.size == (720, 1280), f"{name} render_frame(0) = {img0.size}"
        assert img90.size == (1280, 720), f"{name} render_frame(90) = {img90.size}"
        print(f"OK  {name}")

    print("ALL PASSED")


if __name__ == "__main__":
    main()
