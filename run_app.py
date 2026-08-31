#!/usr/bin/env python3
"""Launch USB Display HUD desktop app."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Silence harmless DPI warning when the host process already locked DPI awareness
# (common under RDP / IDE-integrated terminals).
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false")
os.environ.setdefault("QT_QPA_PLATFORM", "windows:dpiawareness=1")

# Best-effort: set DPI awareness before Qt loads (ignore if already set).
if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
