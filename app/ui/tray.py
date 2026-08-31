from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app import i18n
from app.ui.main_window import MainWindow


class AppTray(QSystemTrayIcon):
    def __init__(self, window: MainWindow, icon: QIcon, parent=None) -> None:
        super().__init__(icon, parent)
        self.window = window
        window.set_tray(self)

        self._menu = QMenu()
        self.act_show = QAction(self._menu)
        self.act_start = QAction(self._menu)
        self.act_stop = QAction(self._menu)
        self.act_about = QAction(self._menu)
        self.act_quit = QAction(self._menu)
        self.act_show.triggered.connect(self.show_window)
        self.act_start.triggered.connect(window.start_stream)
        self.act_stop.triggered.connect(window.stop_stream)
        self.act_about.triggered.connect(window.show_about)
        self.act_quit.triggered.connect(self.quit_app)
        self._menu.addAction(self.act_show)
        self._menu.addSeparator()
        self._menu.addAction(self.act_start)
        self._menu.addAction(self.act_stop)
        self._menu.addSeparator()
        self._menu.addAction(self.act_about)
        self._menu.addSeparator()
        self._menu.addAction(self.act_quit)
        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setToolTip(i18n.t("app_title"))
        self.act_show.setText(i18n.t("tray_show"))
        self.act_start.setText(i18n.t("tray_start"))
        self.act_stop.setText(i18n.t("tray_stop"))
        self.act_about.setText(i18n.t("tray_about"))
        self.act_quit.setText(i18n.t("tray_quit"))

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()

    def show_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def quit_app(self) -> None:
        self.window.shutdown()
        self.hide()
        from PySide6.QtWidgets import QApplication

        QApplication.instance().quit()
