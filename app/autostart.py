from __future__ import annotations

import sys
from pathlib import Path

from app.settings import RUN_VALUE_NAME

try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None  # type: ignore


_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _launch_command() -> str:
    # Boot: start minimized + auto stream is handled by settings.auto_run
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    main = Path(__file__).resolve().parents[1] / "run_app.py"
    return f'"{sys.executable}" "{main}" --minimized'


def is_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return True
    except OSError:
        return False


def set_enabled(enabled: bool) -> None:
    if winreg is None:
        return
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, _launch_command())
        else:
            try:
                winreg.DeleteValue(key, RUN_VALUE_NAME)
            except FileNotFoundError:
                pass
