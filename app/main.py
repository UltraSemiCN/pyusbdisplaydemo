from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Before PySide6: prefer System DPI Aware; hide qt.qpa.window noise if denied.
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false")
os.environ.setdefault("QT_QPA_PLATFORM", "windows:dpiawareness=1")

from PySide6.QtCore import QSharedMemory, QTimer
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from app import i18n
from app.settings import AppSettings
from app.ui.main_window import MainWindow
from app.ui.tray import AppTray


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--minimized", action="store_true", help="Start hidden in tray")
    p.add_argument("--no-auto-run", action="store_true", help="Do not auto-start streaming")
    args, _unknown = p.parse_known_args(argv[1:])
    return args


def _default_icon() -> QIcon:
    assets = Path(__file__).resolve().parents[1] / "assets" / "icon.png"
    if assets.is_file():
        return QIcon(str(assets))
    pix = QPixmap(64, 64)
    pix.fill(QColor(10, 24, 36))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(42, 205, 239))
    p.setPen(QColor(118, 255, 0))
    p.drawRoundedRect(10, 8, 44, 48, 8, 8)
    p.end()
    return QIcon(pix)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    cli = _parse_args(sys.argv)

    argv = list(sys.argv)
    if sys.platform == "win32" and not any(a.startswith("windows:dpiawareness") for a in argv):
        argv[1:1] = ["-platform", "windows:dpiawareness=1"]

    app = QApplication(argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("USB Display HUD")

    settings = AppSettings.load()
    i18n.set_language(settings.language)

    guard = QSharedMemory("UsbDisplayHud.SingleInstance")
    if not guard.create(1):
        QMessageBox.information(
            None,
            i18n.t("already_running_title"),
            i18n.t("already_running_body"),
        )
        return 0

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            i18n.t("tray_unavailable_title"),
            i18n.t("tray_unavailable_body"),
        )
        return 1

    if cli.minimized:
        settings.start_minimized = True
    icon = _default_icon()
    app.setWindowIcon(icon)

    window = MainWindow(settings)
    tray = AppTray(window, icon)
    tray.show()

    if settings.start_minimized or cli.minimized:
        window.hide()
        tray.showMessage(
            i18n.t("app_title"),
            i18n.t("tray_running"),
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )
    else:
        window.show()

    if settings.auto_run and not cli.no_auto_run:
        QTimer.singleShot(600, window.start_stream)

    code = app.exec()
    window.shutdown()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
