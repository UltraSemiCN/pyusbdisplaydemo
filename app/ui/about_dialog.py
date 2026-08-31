from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app import i18n, meta


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(i18n.t("about_title"))
        self.setModal(True)
        self.resize(420, 280)

        root = QVBoxLayout(self)
        title = QLabel(f"<b>{meta.APP_TITLE}</b>  v{meta.APP_VERSION}")
        title.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(title)

        summary = QLabel(i18n.t("about_summary"))
        summary.setWordWrap(True)
        root.addWidget(summary)

        root.addSpacing(8)
        root.addWidget(QLabel(i18n.t("about_home")))
        root.addLayout(self._link_row(meta.PROJECT_URL))

        root.addWidget(QLabel(i18n.t("about_source")))
        root.addLayout(self._link_row(meta.GITHUB_URL))

        root.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)

    def _link_row(self, url: str) -> QHBoxLayout:
        row = QHBoxLayout()
        label = QLabel(f'<a href="{url}">{url}</a>')
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        label.setWordWrap(True)
        open_btn = QPushButton(i18n.t("about_open"))
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        row.addWidget(label, 1)
        row.addWidget(open_btn)
        return row
