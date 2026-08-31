from __future__ import annotations

from datetime import datetime

from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app import autostart
from app import i18n
from app.core.device_service import DeviceEntry, DeviceService
from app.core.metrics import MetricsHub, SysSnapshot
from app.core.orientation import ORIENTATIONS, normalize_orientation
from app.core.slideshow import default_photos_dir, ensure_default_photos_dir, shared_album
from app.core.stream_worker import StreamWorker
from app.paths import default_themes_dir, set_themes_folder
from app.settings import (
    AppSettings,
    normalize_slideshow_interval,
    normalize_slideshow_mode,
)
from app.themes import all_themes, get_theme, themes_path
from app.themes.base import Theme
from app.themes.loader import discover_themes
from app.ui.about_dialog import AboutDialog
from app.ui.layout_metrics import layout_metrics

_SLIDESHOW_THEME_ID = "photo_slideshow_portrait"

# Win11 原生 QGroupBox 易出黑边；统一浅色描边，接近 Win10 观感
_PANEL_BOX_STYLE = """
QGroupBox {
    border: 1px solid #c8c8c8;
    border-radius: 3px;
    margin-top: 0.55em;
    padding-top: 4px;
    background-color: transparent;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 3px;
    background-color: palette(window);
}
"""


class _PreviewWorker(QThread):
    finished_ok = Signal(object, object, int)  # Image, SysSnapshot, orientation
    failed = Signal(str)

    def __init__(
        self,
        theme: Theme,
        metrics: MetricsHub,
        orientation: int = 0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._metrics = metrics
        self._orientation = normalize_orientation(orientation)

    def run(self) -> None:
        try:
            snap = self._metrics.sample()
            img = self._theme.render_frame(
                snap, datetime.now(), 1.0, orient=self._orientation
            )
            self.finished_ok.emit(img, snap, self._orientation)
        except Exception as exc:  # pragma: no cover
            self.failed.emit(str(exc))


class _PreviewPane(QWidget):
    """Preview surface that scales inside the splitter pane (does not drive window size)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setMinimumSize(120, 120)
        self.setStyleSheet("background:#0b1218; border:1px solid #244;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background:transparent; border:none;")
        lay.addWidget(self.label, 1)

        self._source: QPixmap | None = None
        self._aspect_w = 9
        self._aspect_h = 16

    def set_aspect(self, width: int, height: int) -> None:
        self._aspect_w = max(1, int(width))
        self._aspect_h = max(1, int(height))
        self._paint()

    def set_source(self, pixmap: QPixmap | None) -> None:
        self._source = pixmap
        self._paint()

    def clear_image(self, placeholder: str = "") -> None:
        self._source = None
        self.label.clear()
        self.label.setText(placeholder)
        self._paint()

    def has_image(self) -> bool:
        return self._source is not None and not self._source.isNull()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._paint()

    def _paint(self) -> None:
        if self._source is not None and not self._source.isNull():
            self.label.setPixmap(
                self._source.scaled(
                    max(1, self.width()),
                    max(1, self.height()),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.label.setText("")


class MainWindow(QMainWindow):
    """主窗口：上预览 + 下三栏控制区，垂直/水平 QSplitter 可拖拽（OBS 风格）。

    方法分区（自上而下）::
        初始化与托盘
        窗口几何与预览尺寸
        国际化
        主题列表（HUD 模板）
        显示模式（主题 / 照片轮播）
        照片轮播设置
        摆放方向
        USB 设备
        主题预览渲染
        应用设置（开机启动等）
        推流开停与 Worker 回调
        杂项动作（关于、退出）
        窗口生命周期
    """

    language_changed = Signal(str)
    _THEME_LIST_VISIBLE = 3
    # 默认窗宽按语言（layout_metrics）；横屏上预览下三栏；竖屏左三栏右预览
    _PREVIEW_MIN_H = 160
    _PREVIEW_MIN_W = 160
    _CONTROLS_MIN_H = 180
    _CONTROLS_MIN_W = 200
    _WIN_MIN_H = 480
    _WIN_DEFAULT_H = 700
    _STREAM_PREVIEW_ORIENT_DELAY_MS = 600

    # ------------------------------------------------------------------
    # 初始化与托盘
    # ------------------------------------------------------------------

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()

        self.settings = settings
        i18n.set_language(settings.language)
        set_themes_folder(settings.themes_folder)
        self.metrics = MetricsHub()
        self.device = DeviceService()
        self.worker: StreamWorker | None = None
        self._preview_worker: _PreviewWorker | None = None
        self._stream_preview_gate = False
        self._stream_preview_delay = QTimer(self)
        self._stream_preview_delay.setSingleShot(True)
        self._stream_preview_delay.timeout.connect(self._on_stream_preview_delay_done)
        self._tray = None  # set by AppTray

        try:
            self._current: Theme = get_theme(settings.theme_id)
            if self._current.id != settings.theme_id:
                self.settings.theme_id = self._current.id
                self.settings.save()
            if self._current.id != _SLIDESHOW_THEME_ID:
                self.settings.style_theme_id = self._current.id
                self.settings.save()
        except RuntimeError as exc:
            QMessageBox.critical(self, i18n.t("no_theme_title"), str(exc))
            self._current = None  # type: ignore

        root = QWidget()
        self.setCentralWidget(root)
        self._root_layout = QVBoxLayout(root)
        self._root_layout.setContentsMargins(10, 10, 10, 10)
        self._root_layout.setSpacing(6)

        # 顶栏：角度选项左（无「摆放方向」省宽）；模式/语言/按钮右
        self.orient_bar = QWidget()
        orient_row = QHBoxLayout(self.orient_bar)
        orient_row.setContentsMargins(0, 0, 0, 0)
        orient_row.setSpacing(4)
        self.orient_group = QButtonGroup(self)
        self.orient_radios: dict[int, QRadioButton] = {}
        for deg in ORIENTATIONS:
            rb = QRadioButton()
            self.orient_radios[deg] = rb
            self.orient_group.addButton(rb, deg)
            orient_row.addWidget(rb)
        orient_row.addStretch(1)

        self.mode_label = QLabel()
        orient_row.addWidget(self.mode_label)
        self.display_mode_combo = QComboBox()
        self.display_mode_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self.display_mode_combo.currentIndexChanged.connect(self._on_display_mode_changed)
        orient_row.addWidget(self.display_mode_combo)

        self.lang_combo = QComboBox()
        for code, label in i18n.LANG_CHOICES:
            self.lang_combo.addItem(label, code)
        idx = max(0, self.lang_combo.findData(settings.language))
        self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        orient_row.addWidget(self.lang_combo)

        self.quit_btn = QPushButton()
        self.quit_btn.clicked.connect(self.quit_app)
        orient_row.addWidget(self.quit_btn)

        self.about_btn = QPushButton()
        self.about_btn.clicked.connect(self.show_about)
        orient_row.addWidget(self.about_btn)
        self._root_layout.addWidget(self.orient_bar, 0)
        cur_orient = normalize_orientation(settings.orientation)
        self.orient_radios[cur_orient].setChecked(True)
        self.orient_group.idToggled.connect(self._on_orientation_toggled)

        self._splitter = QSplitter(Qt.Orientation.Vertical)

        self.preview_stage = QWidget()
        self.preview_stage.setMinimumHeight(self._PREVIEW_MIN_H)
        preview_stage_lay = QVBoxLayout(self.preview_stage)
        preview_stage_lay.setContentsMargins(0, 0, 0, 0)
        preview_stage_lay.setSpacing(0)

        self.preview = _PreviewPane()
        preview_stage_lay.addWidget(self.preview, 1)

        # 控制区：主题 | 照片轮播 | 推流，三栏同时显示，可左右拖
        self.controls_pane = QWidget()
        self.controls_pane.setMinimumHeight(self._CONTROLS_MIN_H)
        self._controls_hsplit = QSplitter(Qt.Orientation.Horizontal)
        self._controls_hsplit.setChildrenCollapsible(False)

        self.panel_themes = QGroupBox()
        self.panel_themes.setStyleSheet(_PANEL_BOX_STYLE)
        self.panel_themes.setMinimumWidth(layout_metrics().panel_min_w)
        themes_lay = QVBoxLayout(self.panel_themes)
        themes_lay.setContentsMargins(6, 6, 6, 6)
        themes_lay.setSpacing(6)

        self.themes_folder_label = QLabel()
        themes_lay.addWidget(self.themes_folder_label)
        self.themes_folder_edit = QLineEdit()
        self.themes_folder_edit.setReadOnly(True)
        themes_lay.addWidget(self.themes_folder_edit)

        themes_folder_btns = QHBoxLayout()
        themes_folder_btns.setSpacing(6)
        self.themes_browse_btn = QPushButton()
        self.themes_browse_btn.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self.themes_browse_btn.clicked.connect(self._on_themes_browse)
        self.themes_reset_btn = QPushButton()
        self.themes_reset_btn.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self.themes_reset_btn.clicked.connect(self._on_themes_reset)
        themes_folder_btns.addWidget(self.themes_browse_btn)
        themes_folder_btns.addWidget(self.themes_reset_btn)
        themes_lay.addLayout(themes_folder_btns)

        self.theme_panel = QWidget()
        theme_panel_lay = QVBoxLayout(self.theme_panel)
        theme_panel_lay.setContentsMargins(0, 0, 0, 0)
        theme_panel_lay.setSpacing(6)

        self.list = QListWidget()
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.list.currentItemChanged.connect(self._on_theme_changed)
        self.list.itemChanged.connect(self._on_theme_favorite_toggled)
        theme_panel_lay.addWidget(self.list, 1)

        self.reload_btn = QPushButton()
        self.reload_btn.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        self.reload_btn.clicked.connect(self.reload_themes)
        theme_panel_lay.addWidget(self.reload_btn)
        themes_lay.addWidget(self.theme_panel, 1)

        self.slideshow_group = QGroupBox()
        self.slideshow_group.setStyleSheet(_PANEL_BOX_STYLE)
        self.slideshow_group.setMinimumWidth(layout_metrics().panel_min_w)
        ss = QVBoxLayout(self.slideshow_group)
        ss.setContentsMargins(6, 6, 6, 6)
        ss.setSpacing(6)

        self.slideshow_folder_label = QLabel()
        ss.addWidget(self.slideshow_folder_label)
        self.slideshow_folder_edit = QLineEdit()
        self.slideshow_folder_edit.setReadOnly(True)
        ss.addWidget(self.slideshow_folder_edit)

        folder_btns = QHBoxLayout()
        folder_btns.setSpacing(6)
        self.slideshow_browse_btn = QPushButton()
        self.slideshow_browse_btn.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self.slideshow_browse_btn.clicked.connect(self._on_slideshow_browse)
        self.slideshow_reset_btn = QPushButton()
        self.slideshow_reset_btn.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self.slideshow_reset_btn.clicked.connect(self._on_slideshow_reset)
        folder_btns.addWidget(self.slideshow_browse_btn)
        folder_btns.addWidget(self.slideshow_reset_btn)
        ss.addLayout(folder_btns)

        interval_row = QHBoxLayout()
        self.slideshow_interval_label = QLabel()
        self.slideshow_interval_spin = QDoubleSpinBox()
        self.slideshow_interval_spin.setRange(1.0, 3600.0)
        self.slideshow_interval_spin.setSingleStep(1.0)
        self.slideshow_interval_spin.setDecimals(0)
        self.slideshow_interval_spin.setValue(
            normalize_slideshow_interval(settings.slideshow_interval_s)
        )
        self.slideshow_interval_spin.valueChanged.connect(self._on_slideshow_interval)
        interval_row.addWidget(self.slideshow_interval_label)
        interval_row.addWidget(self.slideshow_interval_spin, 1)
        ss.addLayout(interval_row)

        mode_row = QHBoxLayout()
        self.slideshow_mode_label = QLabel()
        self.slideshow_mode_combo = QComboBox()
        self.slideshow_mode_combo.currentIndexChanged.connect(self._on_slideshow_mode)
        mode_row.addWidget(self.slideshow_mode_label)
        mode_row.addWidget(self.slideshow_mode_combo, 1)
        ss.addLayout(mode_row)
        ss.addStretch(1)

        self._sync_themes_folder_edit()
        self._sync_slideshow_folder_edit()
        self._fill_slideshow_mode_combo()
        self._fill_display_mode_combo()
        self._apply_slideshow_to_theme()

        self.panel_stream = QGroupBox()
        self.panel_stream.setStyleSheet(_PANEL_BOX_STYLE)
        self.panel_stream.setMinimumWidth(layout_metrics().stream_min_w)
        stream_lay = QVBoxLayout(self.panel_stream)
        stream_lay.setContentsMargins(6, 6, 6, 6)
        stream_lay.setSpacing(6)

        self.play_panel = QWidget()
        play = QVBoxLayout(self.play_panel)
        play.setContentsMargins(0, 0, 0, 0)
        play.setSpacing(6)

        self.source_label = QLabel()
        self.source_label.setWordWrap(True)
        play.addWidget(self.source_label)

        opts_row = QHBoxLayout()
        opts_row.setSpacing(8)
        self.autostart_cb = QCheckBox()
        self.autostart_cb.setChecked(settings.autostart)
        self.autostart_cb.toggled.connect(self._on_autostart)
        self.autorun_cb = QCheckBox()
        self.autorun_cb.setChecked(settings.auto_run)
        self.autorun_cb.toggled.connect(self._on_autorun)
        self.live_preview_cb = QCheckBox()
        self.live_preview_cb.setChecked(settings.live_preview)
        self.live_preview_cb.toggled.connect(self._on_live_preview)
        for cb in (self.autostart_cb, self.autorun_cb, self.live_preview_cb):
            cb.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            opts_row.addWidget(cb)
        opts_row.addStretch(1)
        play.addLayout(opts_row)

        self.device_label = QLabel()
        play.addWidget(self.device_label)

        device_row = QHBoxLayout()
        device_row.setSpacing(6)
        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(32)
        self.device_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        self.device_refresh_btn = QPushButton()
        self.device_refresh_btn.setMinimumHeight(32)
        self.device_refresh_btn.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self.device_refresh_btn.clicked.connect(self.refresh_device_list)
        device_row.addWidget(self.device_combo, 1)
        device_row.addWidget(self.device_refresh_btn)
        play.addLayout(device_row)

        self.start_btn = QPushButton()
        self.stop_btn = QPushButton()
        self.start_btn.setMinimumHeight(32)
        self.stop_btn.setMinimumHeight(32)
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_stream)
        self.stop_btn.clicked.connect(self.stop_stream)
        self.stream_btns_host = QWidget()
        play.addWidget(self.stream_btns_host)
        stream_lay.addWidget(self.play_panel)
        stream_lay.addStretch(1)

        self._controls_hsplit.addWidget(self.panel_themes)
        self._controls_hsplit.addWidget(self.slideshow_group)
        self._controls_hsplit.addWidget(self.panel_stream)
        self._controls_hsplit.setStretchFactor(0, 2)
        self._controls_hsplit.setStretchFactor(1, 2)
        self._controls_hsplit.setStretchFactor(2, 2)

        controls_outer = QVBoxLayout(self.controls_pane)
        controls_outer.setContentsMargins(0, 0, 0, 0)
        controls_outer.setSpacing(0)
        controls_outer.addWidget(self._controls_hsplit)

        self._splitter.addWidget(self.preview_stage)
        self._splitter.addWidget(self.controls_pane)
        self._splitter.setStretchFactor(0, 5)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setChildrenCollapsible(False)
        self._root_layout.addWidget(self._splitter, 1)
        self._layout_portrait: bool | None = None  # 由 _apply_body_layout 设置
        self._apply_body_layout(normalize_orientation(settings.orientation))

        # 最底一行：分辨率 + 就绪/状态
        self.info_bar = QWidget()
        info_row = QHBoxLayout(self.info_bar)
        info_row.setContentsMargins(0, 2, 0, 0)
        info_row.setSpacing(12)
        self.res_label = QLabel()
        self.res_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.status_label = QLabel()
        self.status_label.setWordWrap(False)
        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        info_row.addWidget(self.res_label, 0)
        info_row.addWidget(self.status_label, 1)
        self._root_layout.addWidget(self.info_bar, 0)

        self.setMinimumSize(layout_metrics().win_min_w, self._WIN_MIN_H)
        self.resize(layout_metrics().win_default_w, self._WIN_DEFAULT_H)

        if self._current is not None:
            cw, ch = self._current.canvas_size(
                normalize_orientation(settings.orientation)
            )
            self.preview.set_aspect(cw, ch)

        self._update_mode_panels()
        # 仅同步比例/标签；分区尺寸等界面文案与列表就绪后由 _initial_layout 统一做
        self._apply_orientation_change(
            normalize_orientation(settings.orientation),
            refresh=False,
            relayout=False,
        )

        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(1200)
        self._preview_timer.timeout.connect(self.refresh_preview)
        self._sync_preview_timer()

        self.retranslate_ui()
        self._populate_theme_list()
        self._apply_theme_labels()
        QTimer.singleShot(0, self._initial_layout)
        QTimer.singleShot(0, self.refresh_preview)
        QTimer.singleShot(200, self.refresh_device_list)

        if settings.autostart:
            autostart.set_enabled(True)

    def set_tray(self, tray) -> None:
        """注入系统托盘，供退出等操作委托给托盘。"""
        self._tray = tray

    # ------------------------------------------------------------------
    # 窗口几何与预览尺寸
    # ------------------------------------------------------------------

    def _layout_m(self):
        return layout_metrics()

    def _apply_layout_metrics(self, *, relayout: bool = False) -> None:
        """按当前语言刷新宽度地板；切语言时可重套默认分区。"""
        m = self._layout_m()
        self.setMinimumSize(m.win_min_w, self._WIN_MIN_H)
        self._fit_control_panel_mins()
        if relayout:
            self._apply_default_splitter_sizes()

    def _aspect(self) -> tuple[int, int]:
        """Preview aspect from theme canvas_size at current placement orientation."""
        if self._current is not None:
            orient = normalize_orientation(self.settings.orientation)
            w, h = self._current.canvas_size(orient)
            return max(1, int(w)), max(1, int(h))
        return self.preview._aspect_w, self.preview._aspect_h

    def _is_portrait_ui(self, deg: int | None = None) -> bool:
        """0°/180°：竖屏 UI（左三栏 + 右预览）；90°/270°：横屏 UI。"""
        d = normalize_orientation(
            self.settings.orientation if deg is None else deg
        )
        return d in (0, 180)

    def _sync_stream_buttons_layout(self, *, portrait: bool) -> None:
        """横屏：开停各一行；竖屏：开停并排。"""
        host = self.stream_btns_host
        old = host.layout()
        if old is not None:
            while old.count():
                old.takeAt(0)
            # 卸掉旧 layout，避免 setLayout 失败
            QWidget().setLayout(old)
        if portrait:
            row = QHBoxLayout(host)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            row.addWidget(self.start_btn, 1)
            row.addWidget(self.stop_btn, 1)
        else:
            col = QVBoxLayout(host)
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(6)
            col.addWidget(self.start_btn)
            col.addWidget(self.stop_btn)

    def _apply_body_layout(self, deg: int | None = None) -> None:
        """按摆放角度切换：横屏 上预览/下三栏；竖屏 左三栏/右预览。"""
        portrait = self._is_portrait_ui(deg)
        if self._layout_portrait is portrait:
            return
        self._layout_portrait = portrait
        self._sync_stream_buttons_layout(portrait=portrait)

        if portrait:
            self._splitter.setOrientation(Qt.Orientation.Horizontal)
            self._controls_hsplit.setOrientation(Qt.Orientation.Vertical)
            self._splitter.insertWidget(0, self.controls_pane)
            self._splitter.insertWidget(1, self.preview_stage)
            self.controls_pane.setMinimumWidth(self._CONTROLS_MIN_W)
            self.controls_pane.setMinimumHeight(0)
            self.preview_stage.setMinimumWidth(self._PREVIEW_MIN_W)
            self.preview_stage.setMinimumHeight(self._PREVIEW_MIN_H)
        else:
            self._splitter.setOrientation(Qt.Orientation.Vertical)
            self._controls_hsplit.setOrientation(Qt.Orientation.Horizontal)
            self._splitter.insertWidget(0, self.preview_stage)
            self._splitter.insertWidget(1, self.controls_pane)
            self.controls_pane.setMinimumWidth(0)
            self.controls_pane.setMinimumHeight(self._CONTROLS_MIN_H)
            self.preview_stage.setMinimumWidth(0)
            self.preview_stage.setMinimumHeight(self._PREVIEW_MIN_H)

        self._splitter.setChildrenCollapsible(False)
        self._controls_hsplit.setChildrenCollapsible(False)

    def _chrome_height(self) -> int:
        om = self._root_layout.contentsMargins()
        return (
            om.top()
            + om.bottom()
            + self._root_layout.spacing() * 2
            + max(self.orient_bar.sizeHint().height(), 28)
            + max(self.info_bar.sizeHint().height(), 22)
        )

    def _landscape_default_metrics(self) -> tuple[int, int, int, int]:
        """横屏基准：窗宽、窗高、预览高、控制条高（三栏接近正方形）。"""
        om = self._root_layout.contentsMargins()
        content_w = self._layout_m().win_default_w - om.left() - om.right()
        handles = 2 * max(1, self._controls_hsplit.handleWidth())
        col_w = max(1, (content_w - handles) // 3)
        content_h = self._fit_controls_min_height()
        ctrl_h = max(content_h, col_w)
        preview_h = max(self._PREVIEW_MIN_H, int(content_w * 9 / 16))
        win_h = max(
            self._WIN_MIN_H,
            self._chrome_height() + preview_h + ctrl_h + 6,
        )
        return self._layout_m().win_default_w, win_h, preview_h, ctrl_h

    def _fit_controls_min_height(self) -> int:
        """三栏内容所需最小高度（列表等不可再压扁）。"""
        self._fit_theme_list_height()
        for w in (self.panel_themes, self.slideshow_group, self.panel_stream):
            w.adjustSize()
        return max(
            self._CONTROLS_MIN_H,
            self.panel_themes.minimumSizeHint().height(),
            self.slideshow_group.minimumSizeHint().height(),
            self.panel_stream.minimumSizeHint().height(),
        )

    def _fit_control_panel_mins(self) -> None:
        """三栏最小宽：右栏按勾选/开停不挤；总和压进可用宽时优先保右栏。"""
        def row_min(*widgets: QWidget) -> int:
            return sum(max(36, w.sizeHint().width()) for w in widgets) + 6 * max(
                0, len(widgets) - 1
            )

        m = self._layout_m()
        themes_w = max(
            m.panel_min_w,
            row_min(self.themes_browse_btn, self.themes_reset_btn) + 28,
        )
        ss_w = max(
            m.panel_min_w,
            row_min(self.slideshow_browse_btn, self.slideshow_reset_btn) + 28,
        )
        stream_w = max(
            m.stream_min_w,
            (
                row_min(self.start_btn, self.stop_btn) + 28
                if self._layout_portrait
                else max(
                    self.start_btn.sizeHint().width(),
                    self.stop_btn.sizeHint().width(),
                )
                + 28
            ),
            row_min(self.autostart_cb, self.autorun_cb, self.live_preview_cb) + 28,
        )

        om = self._root_layout.contentsMargins()
        if self._layout_portrait:
            # 竖屏：三栏纵向叠放，宽度=左栏宽，不按三宽相加
            col = max(
                self._CONTROLS_MIN_W,
                themes_w,
                ss_w,
                stream_w,
            )
            self.panel_themes.setMinimumWidth(col)
            self.slideshow_group.setMinimumWidth(col)
            self.panel_stream.setMinimumWidth(col)
            return

        avail = self._controls_hsplit.width()
        if avail < 60:
            avail = max(200, self.width() - om.left() - om.right())
        handles = 2 * max(1, self._controls_hsplit.handleWidth())
        budget = max(3 * 120, avail - handles)
        mins = [themes_w, ss_w, stream_w]
        total = sum(mins)
        if total > budget:
            overflow = total - budget
            for i in (0, 1):
                if overflow <= 0:
                    break
                can = mins[i] - 140
                if can <= 0:
                    continue
                cut = min(can, overflow)
                mins[i] -= cut
                overflow -= cut
            if overflow > 0:
                can = mins[2] - 160
                if can > 0:
                    mins[2] -= min(can, overflow)

        # 横屏：风格模板与轮播最小宽取齐，避免默认宽不一致
        pair = max(mins[0], mins[1])
        mins[0] = pair
        mins[1] = pair
        if sum(mins) > budget:
            overflow = sum(mins) - budget
            can = mins[2] - 160
            if can > 0:
                cut = min(can, overflow)
                mins[2] -= cut
                overflow -= cut
            if overflow > 0:
                each = overflow // 2
                mins[0] = max(140, mins[0] - each)
                mins[1] = max(140, mins[1] - (overflow - each))

        self.panel_themes.setMinimumWidth(mins[0])
        self.slideshow_group.setMinimumWidth(mins[1])
        self.panel_stream.setMinimumWidth(mins[2])

    def _apply_default_splitter_sizes(self) -> None:
        """默认窗；横屏上下分；竖屏预览宽按满高比例收紧，余量给左三栏。"""
        win_w, win_h, preview_h, ctrl_h = self._landscape_default_metrics()
        self.resize(win_w, win_h)
        self._fit_control_panel_mins()

        handles = 2 * max(1, self._controls_hsplit.handleWidth())
        if self._layout_portrait:
            # 右预览宽=竖图在满高下刚好铺满所需（不留左右黑边），多出的给左三栏
            om = self._root_layout.contentsMargins()
            content_w = win_w - om.left() - om.right()
            main_handle = max(1, self._splitter.handleWidth())
            prev_h = max(
                self._PREVIEW_MIN_H,
                win_h - self._chrome_height() - main_handle,
            )
            aw, ah = self._aspect()
            # 高度贴满时，宽度收紧到不改变图像高度
            prev_w = max(self._PREVIEW_MIN_W, int(prev_h * aw / max(ah, 1)))
            ctrl_w = max(self._CONTROLS_MIN_W, content_w - main_handle - prev_w)
            # 若左栏不够最小宽，再让预览让一点（仍尽量贴比例）
            if ctrl_w + prev_w + main_handle > content_w:
                ctrl_w = self._CONTROLS_MIN_W
                prev_w = max(self._PREVIEW_MIN_W, content_w - main_handle - ctrl_w)
            self.controls_pane.setMinimumWidth(self._CONTROLS_MIN_W)
            self.controls_pane.setMinimumHeight(0)
            self._splitter.setSizes([ctrl_w, prev_w])
            # 用算出的满窗高度，避免首次 show 时 splitter 高度未就绪
            inner = max(3, prev_h - handles)
            # 2、3 收紧到内容高度，余量留给 1（与切换角度后同一算法）
            self.slideshow_group.updateGeometry()
            self.panel_stream.updateGeometry()
            h2 = max(72, self.slideshow_group.sizeHint().height() + 6)
            h3 = max(72, self.panel_stream.sizeHint().height() + 6)
            max_23 = (inner * 55) // 100
            if h2 + h3 > max_23:
                scale = max_23 / max(1, h2 + h3)
                h2 = max(72, int(h2 * scale))
                h3 = max(72, max_23 - h2)
            h1 = max(80, inner - h2 - h3)
            self._controls_hsplit.setSizes([h1, h2, h3])
        else:
            self.controls_pane.setMinimumHeight(self._fit_controls_min_height())
            total = max(self._splitter.height(), preview_h + ctrl_h)
            self._splitter.setSizes(
                [max(self._PREVIEW_MIN_H, total - ctrl_h), ctrl_h]
            )
            avail = max(self._controls_hsplit.width(), 1)
            om = self._root_layout.contentsMargins()
            content_w = win_w - om.left() - om.right()
            if avail < content_w // 2:
                avail = content_w
            inner = max(3, avail - handles)
            # 风格模板与轮播同宽，剩余给设备栏；总宽不变
            c = inner // 3
            left = inner - c
            a = left // 2
            b = left - a
            self._controls_hsplit.setSizes([a, b, c])

    def _initial_layout(self) -> None:
        """首次显示：与切换角度同一路径（强制重挂布局再设默认分区）。"""
        self._layout_portrait = None
        self._apply_orientation_change(
            normalize_orientation(self.settings.orientation),
            refresh=False,
            relayout=True,
        )

    def _apply_orientation_change(
        self, deg: int, *, refresh: bool = True, relayout: bool = True
    ) -> None:
        """更新布局（竖/横）、预览比例；切换时恢复默认窗口与横屏同级分区。"""
        deg = normalize_orientation(deg)
        if relayout:
            # 与切换一致：强制走完整 body 重挂，避免首次 early-return 量错高度
            self._layout_portrait = None
            self._apply_body_layout(deg)
            self._apply_default_splitter_sizes()
            QTimer.singleShot(0, self._apply_default_splitter_sizes)

        if self._current is not None:
            cw, ch = self._current.canvas_size(deg)
        else:
            cw, ch = self._aspect()
        streaming = bool(self.worker is not None and self.worker.isRunning())
        if refresh:
            self._cancel_preview_worker()
            if not streaming:
                self.preview.clear_image(i18n.t("preview_loading"))
        self.preview.set_aspect(cw, ch)
        self.res_label.setText(f"{cw}×{ch} · {deg}°")
        if refresh:
            if streaming:
                self._schedule_stream_preview_after_orient_change()
            else:
                self.refresh_preview(force=True)

    # ------------------------------------------------------------------
    # 国际化
    # ------------------------------------------------------------------

    def retranslate_ui(self) -> None:
        self.setWindowTitle(i18n.t("app_title"))
        self.mode_label.setText(i18n.t("display_mode"))
        self.display_mode_combo.setToolTip(i18n.t("display_mode_tip"))
        self.quit_btn.setText(i18n.t("quit"))
        self.about_btn.setText(i18n.t("about"))
        self.lang_combo.setToolTip(i18n.t("language"))
        self.reload_btn.setText(i18n.t("rescan_themes"))
        self.reload_btn.setToolTip(i18n.t("rescan_tip", path=themes_path()))
        self.list.setToolTip(i18n.t("themes_list_tip"))
        self.themes_folder_label.setText(i18n.t("themes_folder"))
        self.themes_folder_edit.setToolTip(i18n.t("themes_folder_tip"))
        self.themes_browse_btn.setText(i18n.t("slideshow_browse"))
        self.themes_reset_btn.setText(i18n.t("slideshow_reset"))
        self._fill_display_mode_combo()
        self._refresh_theme_item_texts()
        self._fit_theme_list_height()
        self.panel_themes.setTitle(i18n.t("display_mode_themes"))
        self.slideshow_group.setTitle(i18n.t("slideshow_group"))
        self.panel_stream.setTitle(f"{i18n.t('device')} / {i18n.t('start')}")
        self.autostart_cb.setText(i18n.t("autostart"))
        self.autorun_cb.setText(i18n.t("auto_run"))
        self.live_preview_cb.setText(i18n.t("live_preview"))
        self.live_preview_cb.setToolTip(i18n.t("live_preview_tip"))
        tip = i18n.t("orientation_tip")
        for deg, rb in self.orient_radios.items():
            rb.setText(i18n.t(f"orient_{deg}"))
            rb.setToolTip(tip)
        self.device_label.setText(i18n.t("device"))
        self.device_label.setToolTip(i18n.t("device_tip"))
        self.device_combo.setToolTip(i18n.t("device_tip"))
        self.device_refresh_btn.setText(i18n.t("device_refresh"))
        self.device_refresh_btn.setToolTip(i18n.t("device_tip"))
        # Refresh labels for current entries without rescanning SDK.
        self._relabel_device_combo()
        self.start_btn.setText(i18n.t("start"))
        self.stop_btn.setText(i18n.t("stop"))
        self.slideshow_folder_label.setText(i18n.t("slideshow_folder"))
        self.slideshow_folder_edit.setToolTip(i18n.t("slideshow_folder_tip"))
        self.slideshow_browse_btn.setText(i18n.t("slideshow_browse"))
        self.slideshow_reset_btn.setText(i18n.t("slideshow_reset"))
        self.slideshow_interval_label.setText(i18n.t("slideshow_interval"))
        self.slideshow_mode_label.setText(i18n.t("slideshow_mode"))
        self._fill_slideshow_mode_combo()
        self._apply_layout_metrics()
        if self._layout_portrait:
            self.controls_pane.setMinimumWidth(self._CONTROLS_MIN_W)
            self.controls_pane.setMinimumHeight(0)
        else:
            self.controls_pane.setMinimumHeight(self._fit_controls_min_height())
        if not (self.worker and self.worker.isRunning()):
            self.status_label.setText(i18n.t("ready"))
        if self._stream_preview_gate:
            self.preview.clear_image(i18n.t("preview_fetching"))
        elif not self.preview.has_image():
            self.preview.clear_image(i18n.t("preview_loading"))
        self._apply_theme_labels()
        if self._tray is not None:
            self._tray.retranslate_ui()

    def _on_language_changed(self, _index: int) -> None:
        code = self.lang_combo.currentData()
        if not code or code == i18n.language():
            return
        i18n.set_language(code)
        self.settings.language = code
        self.settings.save()
        self.retranslate_ui()
        self._apply_layout_metrics(relayout=True)
        self.language_changed.emit(code)

    def _source_text(self, snap: SysSnapshot | None = None) -> str:
        """格式化数据源标签（AIDA64 / 本地 / 模拟等）。"""
        raw = (snap.source if snap else self.metrics.source_label()).lower()
        if raw in ("aida64",):
            label = i18n.t("source_aida64")
        elif raw in ("local", "本地"):
            label = i18n.t("source_local")
        elif raw in ("mock", "模拟"):
            label = i18n.t("source_mock")
        else:
            label = snap.source if snap else self.metrics.source_label()
        return i18n.t("data_source", value=label)

    # ------------------------------------------------------------------
    # 主题列表（HUD 模板）
    # ------------------------------------------------------------------

    def _fit_theme_list_height(self) -> None:
        """Minimum list height for ~N rows; splitter supplies extra space."""
        visible = self._THEME_LIST_VISIBLE
        row_h = self.list.sizeHintForRow(0) if self.list.count() else 0
        if row_h <= 0:
            row_h = max(24, self.list.fontMetrics().height() + 10)
        frame = 2 * self.list.frameWidth()
        spacing = max(0, self.list.spacing()) * max(0, visible - 1)
        self.list.setMinimumHeight(frame + visible * row_h + spacing)

    def _ordered_themes(self, themes: list[Theme]) -> list[Theme]:
        by_id = {t.id: t for t in themes}
        fav_ids = [tid for tid in self.settings.favorite_theme_ids if tid in by_id]
        # Drop stale favorite ids
        if fav_ids != self.settings.favorite_theme_ids:
            self.settings.favorite_theme_ids = fav_ids
            self.settings.save()
        fav_set = set(fav_ids)
        fav_themes = [by_id[tid] for tid in fav_ids]
        other = [t for t in themes if t.id not in fav_set]
        return fav_themes + other

    def _theme_item_text(self, theme: Theme, favored: bool) -> str:
        if favored:
            return i18n.t("theme_name_fav", name=theme.name)
        return theme.name

    def _theme_item_tooltip(self, theme: Theme, favored: bool) -> str:
        return i18n.t(
            "theme_tooltip",
            desc=theme.description or "",
            res=theme.resolution_label,
            id=theme.id,
            fav_hint=i18n.t("theme_fav_on" if favored else "theme_fav_off"),
        )

    def _refresh_theme_item_texts(self) -> None:
        by_id = {t.id: t for t in all_themes()}
        fav = set(self.settings.favorite_theme_ids)
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            item = self.list.item(i)
            theme_id = item.data(Qt.ItemDataRole.UserRole)
            theme = by_id.get(theme_id)
            if theme is None:
                continue
            favored = theme_id in fav
            item.setText(self._theme_item_text(theme, favored))
            item.setToolTip(self._theme_item_tooltip(theme, favored))
            item.setCheckState(
                Qt.CheckState.Checked if favored else Qt.CheckState.Unchecked
            )
        self.list.blockSignals(False)

    def _style_themes(self, *, force: bool = False) -> list[Theme]:
        return [t for t in all_themes(force=force) if t.id != _SLIDESHOW_THEME_ID]

    def _populate_theme_list(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        themes = self._ordered_themes(self._style_themes(force=True))
        # Prefer remembered style theme when active theme is slideshow.
        select_id = self.settings.style_theme_id or self.settings.theme_id
        if select_id == _SLIDESHOW_THEME_ID:
            select_id = self.settings.style_theme_id or "classic_portrait"
        current_row = 0
        fav = set(self.settings.favorite_theme_ids)
        for i, theme in enumerate(themes):
            favored = theme.id in fav
            item = QListWidgetItem(self._theme_item_text(theme, favored))
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            item.setData(Qt.ItemDataRole.UserRole, theme.id)
            item.setCheckState(
                Qt.CheckState.Checked if favored else Qt.CheckState.Unchecked
            )
            item.setToolTip(self._theme_item_tooltip(theme, favored))
            self.list.addItem(item)
            if theme.id == select_id:
                current_row = i
        if themes and not self._is_slideshow_mode():
            self.list.setCurrentRow(current_row)
            self._current = themes[current_row]
            self.settings.theme_id = self._current.id
            self.settings.style_theme_id = self._current.id
            self.settings.save()
        elif themes:
            # Keep list selection for when user switches back; don't override slideshow.
            self.list.setCurrentRow(current_row)
        self.list.blockSignals(False)
        self._fit_theme_list_height()
        errs = getattr(discover_themes, "last_errors", [])
        if errs:
            self.status_label.setText(i18n.t("theme_load_warn", detail="; ".join(errs[:3])))

    def _on_theme_favorite_toggled(self, item: QListWidgetItem) -> None:
        theme_id = item.data(Qt.ItemDataRole.UserRole)
        if not theme_id:
            return
        favored = item.checkState() == Qt.CheckState.Checked
        favs = list(self.settings.favorite_theme_ids)
        if favored and theme_id not in favs:
            favs.append(theme_id)
        elif not favored and theme_id in favs:
            favs.remove(theme_id)
        else:
            return
        # Slideshow theme is not listed; drop if somehow present.
        favs = [x for x in favs if x != _SLIDESHOW_THEME_ID]
        self.settings.favorite_theme_ids = favs
        self.settings.save()
        # Re-sort so favorites stay on top; keep current selection
        self._populate_theme_list()

    def reload_themes(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, i18n.t("tip"), i18n.t("stop_before_rescan"))
            return
        discover_themes(force=True)
        self._populate_theme_list()
        if self._is_slideshow_mode():
            try:
                self._current = get_theme(_SLIDESHOW_THEME_ID)
            except RuntimeError as exc:
                self.status_label.setText(str(exc))
        self._apply_theme_labels()
        self.refresh_preview()
        self.status_label.setText(i18n.t("rescanned", count=self.list.count()))

    def _on_theme_changed(self, current: QListWidgetItem | None, _prev) -> None:
        """列表选中项变化：切换当前 HUD 主题。"""
        if current is None or self._is_slideshow_mode():
            return
        theme_id = current.data(Qt.ItemDataRole.UserRole)
        try:
            self._current = get_theme(theme_id)
        except RuntimeError as exc:
            self.status_label.setText(str(exc))
            return
        self.settings.theme_id = self._current.id
        self.settings.style_theme_id = self._current.id
        preferred = getattr(self._current, "preferred_orientation", None)
        if preferred is not None:
            self._set_orientation_ui(normalize_orientation(preferred), save=True)
        self.settings.save()
        self._apply_theme_labels()
        self.refresh_preview()

    def _apply_theme_labels(self) -> None:
        """同步分辨率、数据源等标签，并触发模式面板。"""
        self._update_mode_panels()
        if self._current is None:
            self.res_label.setText(i18n.t("resolution_na"))
            return
        t = self._current
        orient = normalize_orientation(self.settings.orientation)
        cw, ch = t.canvas_size(orient)
        self.preview.set_aspect(cw, ch)
        self.res_label.setText(f"{cw}×{ch} · {orient}°")
        self.source_label.setText(self._source_text())

    # ------------------------------------------------------------------
    # 显示模式（主题 / 照片轮播）
    # ------------------------------------------------------------------

    def _is_slideshow_mode(self) -> bool:
        return self.settings.theme_id == _SLIDESHOW_THEME_ID

    def _is_slideshow_theme(self) -> bool:
        return self._is_slideshow_mode()

    def _fill_display_mode_combo(self) -> None:
        current = "slideshow" if self._is_slideshow_mode() else "themes"
        self.display_mode_combo.blockSignals(True)
        self.display_mode_combo.clear()
        self.display_mode_combo.addItem(i18n.t("display_mode_themes"), "themes")
        self.display_mode_combo.addItem(i18n.t("display_mode_slideshow"), "slideshow")
        idx = max(0, self.display_mode_combo.findData(current))
        self.display_mode_combo.setCurrentIndex(idx)
        self.display_mode_combo.blockSignals(False)
        # 英文项较长（Photo slideshow 等），按内容加箭头余量定最小宽
        fm = self.display_mode_combo.fontMetrics()
        text_w = max(
            (
                fm.horizontalAdvance(self.display_mode_combo.itemText(i))
                for i in range(self.display_mode_combo.count())
            ),
            default=0,
        )
        self.display_mode_combo.setMinimumWidth(text_w + 36)

    def _on_display_mode_changed(self, _index: int) -> None:
        mode = self.display_mode_combo.currentData()
        if not mode:
            return
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, i18n.t("tip"), i18n.t("stop_before_mode"))
            self._fill_display_mode_combo()
            return
        want_slideshow = mode == "slideshow"
        if want_slideshow == self._is_slideshow_mode():
            self._update_mode_panels()
            return
        if want_slideshow:
            if self._current is not None and self._current.id != _SLIDESHOW_THEME_ID:
                self.settings.style_theme_id = self._current.id
            try:
                self._current = get_theme(_SLIDESHOW_THEME_ID)
            except RuntimeError as exc:
                QMessageBox.warning(self, i18n.t("cannot_start"), str(exc))
                self._fill_display_mode_combo()
                return
            self.settings.theme_id = _SLIDESHOW_THEME_ID
            self.settings.save()
            self._apply_slideshow_to_theme()
        else:
            style_id = self.settings.style_theme_id or "classic_portrait"
            if style_id == _SLIDESHOW_THEME_ID:
                style_id = "classic_portrait"
            try:
                self._current = get_theme(style_id)
            except RuntimeError:
                themes = self._style_themes()
                if not themes:
                    self.status_label.setText(i18n.t("no_themes"))
                    self._fill_display_mode_combo()
                    return
                self._current = themes[0]
            self.settings.theme_id = self._current.id
            self.settings.style_theme_id = self._current.id
            preferred = getattr(self._current, "preferred_orientation", None)
            if preferred is not None:
                self._set_orientation_ui(normalize_orientation(preferred), save=False)
            self.settings.save()
        self._update_mode_panels()
        if not want_slideshow:
            self._populate_theme_list()
        self._apply_theme_labels()
        self.refresh_preview()

    def _update_mode_panels(self) -> None:
        """三栏始终并排显示；显示模式只影响预览内容，不隐藏控制块。"""
        return

    # ------------------------------------------------------------------
    # 照片轮播设置
    # ------------------------------------------------------------------

    def _sync_themes_folder_edit(self) -> None:
        folder = (self.settings.themes_folder or "").strip()
        display = folder if folder else str(default_themes_dir())
        self.themes_folder_edit.setText(display)

    def _on_themes_browse(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, i18n.t("tip"), i18n.t("stop_before_rescan"))
            return
        start = (self.settings.themes_folder or "").strip() or str(default_themes_dir())
        path = QFileDialog.getExistingDirectory(
            self, i18n.t("themes_pick_folder"), start
        )
        if not path:
            return
        self.settings.themes_folder = path
        self.settings.save()
        set_themes_folder(path)
        self._sync_themes_folder_edit()
        self.reload_themes()

    def _on_themes_reset(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, i18n.t("tip"), i18n.t("stop_before_rescan"))
            return
        self.settings.themes_folder = ""
        self.settings.save()
        set_themes_folder("")
        self._sync_themes_folder_edit()
        self.reload_themes()

    def _sync_slideshow_folder_edit(self) -> None:
        folder = (self.settings.slideshow_folder or "").strip()
        display = folder if folder else str(default_photos_dir())
        self.slideshow_folder_edit.setText(display)

    def _fill_slideshow_mode_combo(self) -> None:
        current = normalize_slideshow_mode(self.settings.slideshow_mode)
        self.slideshow_mode_combo.blockSignals(True)
        self.slideshow_mode_combo.clear()
        for mode, key in (
            ("sequential", "slideshow_mode_sequential"),
            ("shuffle", "slideshow_mode_shuffle"),
            ("single", "slideshow_mode_single"),
        ):
            self.slideshow_mode_combo.addItem(i18n.t(key), mode)
        idx = max(0, self.slideshow_mode_combo.findData(current))
        self.slideshow_mode_combo.setCurrentIndex(idx)
        self.slideshow_mode_combo.blockSignals(False)

    def _apply_slideshow_to_theme(self) -> None:
        ensure_default_photos_dir()
        shared_album().apply_settings(self.settings)
        theme = self._current
        if theme is not None and hasattr(theme, "apply_slideshow_settings"):
            theme.apply_slideshow_settings(self.settings)  # type: ignore[attr-defined]
        if self.worker is not None and self.worker.isRunning():
            wtheme = getattr(self.worker, "_theme", None)
            if wtheme is not None and hasattr(wtheme, "apply_slideshow_settings"):
                wtheme.apply_slideshow_settings(self.settings)

    def _on_slideshow_browse(self) -> None:
        start = (self.settings.slideshow_folder or "").strip() or str(default_photos_dir())
        path = QFileDialog.getExistingDirectory(
            self, i18n.t("slideshow_pick_folder"), start
        )
        if not path:
            return
        self.settings.slideshow_folder = path
        self.settings.save()
        self._sync_slideshow_folder_edit()
        self._apply_slideshow_to_theme()
        self.refresh_preview()

    def _on_slideshow_reset(self) -> None:
        self.settings.slideshow_folder = ""
        self.settings.save()
        self._sync_slideshow_folder_edit()
        self._apply_slideshow_to_theme()
        self.refresh_preview()

    def _on_slideshow_interval(self, value: float) -> None:
        self.settings.slideshow_interval_s = normalize_slideshow_interval(value)
        self.settings.save()
        self._apply_slideshow_to_theme()

    def _on_slideshow_mode(self, _index: int) -> None:
        mode = self.slideshow_mode_combo.currentData()
        if not mode:
            return
        self.settings.slideshow_mode = normalize_slideshow_mode(mode)
        self.settings.save()
        self._apply_slideshow_to_theme()
        self.refresh_preview()

    # ------------------------------------------------------------------
    # 摆放方向
    # ------------------------------------------------------------------

    def _set_orientation_ui(self, degrees: int, *, save: bool) -> None:
        deg = normalize_orientation(degrees)
        rb = self.orient_radios.get(deg)
        if rb is None:
            return
        prev = normalize_orientation(self.settings.orientation)
        # Avoid re-entrant toggles when syncing from theme preference.
        self.orient_group.blockSignals(True)
        rb.setChecked(True)
        self.orient_group.blockSignals(False)
        self.settings.orientation = deg
        if save:
            self.settings.save()
        if self.worker is not None:
            self.worker.orientation = deg
        if prev != deg:
            self._apply_orientation_change(deg)

    def _on_orientation_toggled(self, button_id: int, checked: bool) -> None:
        if not checked:
            return
        deg = normalize_orientation(button_id)
        prev = normalize_orientation(self.settings.orientation)
        self.settings.orientation = deg
        self.settings.save()
        if self.worker is not None:
            self.worker.orientation = deg
        if prev != deg:
            self._apply_orientation_change(deg)

    # ------------------------------------------------------------------
    # USB 设备
    # ------------------------------------------------------------------

    def refresh_device_list(self) -> None:
        """Start SDK if needed and refill the USB device combo."""
        if not self.device.available:
            self.device_combo.blockSignals(True)
            self.device_combo.clear()
            self.device_combo.addItem(i18n.t("msdisplay_missing"), None)
            self.device_combo.setEnabled(False)
            self.device_combo.blockSignals(False)
            return
        try:
            self.device.start_sdk()
        except Exception as exc:
            self.status_label.setText(i18n.t("device_sdk_fail", msg=exc))
            self.device_combo.blockSignals(True)
            self.device_combo.clear()
            self.device_combo.addItem(i18n.t("device_none"), None)
            self.device_combo.setEnabled(False)
            self.device_combo.blockSignals(False)
            return

        entries = self.device.list_devices()
        pref_sn = (self.settings.device_sn or "").strip()
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        if not entries:
            self.device_combo.addItem(i18n.t("device_none"), None)
            self.device_combo.setEnabled(True)
            self.device_combo.blockSignals(False)
            return

        select = 0
        for i, entry in enumerate(entries):
            self.device_combo.addItem(entry.label(), entry)
            if pref_sn and entry.sn == pref_sn:
                select = i
        self.device_combo.setCurrentIndex(select)
        self.device_combo.setEnabled(True)
        self.device_combo.blockSignals(False)
        # Persist SN from selection (may fill empty settings on first detect).
        self._persist_selected_device(save=True)

    def _relabel_device_combo(self) -> None:
        """Update empty-state text after language change without SDK rescan."""
        if self.device_combo.count() == 1 and self.device_combo.itemData(0) is None:
            self.device_combo.blockSignals(True)
            self.device_combo.setItemText(0, i18n.t("device_none"))
            self.device_combo.blockSignals(False)

    def _selected_device(self) -> DeviceEntry | None:
        data = self.device_combo.currentData()
        return data if isinstance(data, DeviceEntry) else None

    def _persist_selected_device(self, *, save: bool) -> None:
        entry = self._selected_device()
        sn = entry.sn if entry is not None else ""
        if sn == self.settings.device_sn:
            return
        self.settings.device_sn = sn
        if save:
            self.settings.save()

    def _on_device_changed(self, _index: int) -> None:
        entry = self._selected_device()
        sn = entry.sn if entry is not None else ""
        handle = entry.handle if entry is not None else None
        if sn != self.settings.device_sn:
            self.settings.device_sn = sn
            self.settings.save()
        if self.worker is not None and self.worker.isRunning() and entry is not None:
            self.worker.set_preferred_device(
                preferred_handle=handle,
                preferred_sn=sn or None,
            )

    # ------------------------------------------------------------------
    # 主题预览渲染
    # ------------------------------------------------------------------

    def refresh_preview(self, *, force: bool = False) -> None:
        if self._current is None:
            return
        if self.worker and self.worker.isRunning():
            return
        if self._preview_worker is not None:
            if not force:
                return
            self._cancel_preview_worker()
        worker = _PreviewWorker(
            self._current,
            self.metrics,
            orientation=self.settings.orientation,
            parent=self,
        )

        def _clear() -> None:
            if self._preview_worker is worker:
                self._preview_worker = None

        worker.finished_ok.connect(self._on_preview_ready)
        worker.failed.connect(lambda m: self.status_label.setText(i18n.t("preview_fail", msg=m)))
        worker.finished.connect(_clear)
        self._preview_worker = worker
        worker.start()

    def _cancel_preview_worker(self) -> None:
        old = self._preview_worker
        if old is None:
            return
        self._preview_worker = None
        for sig in (old.finished_ok, old.failed, old.finished):
            try:
                sig.disconnect()
            except (RuntimeError, TypeError):
                pass
        if old.isRunning():
            old.wait(500)

    def _schedule_stream_preview_after_orient_change(self) -> None:
        """推流中切角度：先显示「获取预览」，延迟后再取发送链路帧。"""
        self._stream_preview_gate = True
        self.preview.clear_image(i18n.t("preview_fetching"))
        if self.worker is not None:
            self.worker.invalidate_preview_cache()
        self._stream_preview_delay.start(self._STREAM_PREVIEW_ORIENT_DELAY_MS)

    def _on_stream_preview_delay_done(self) -> None:
        self._stream_preview_gate = False
        if self.worker is not None and self.worker.isRunning():
            self.worker.request_preview()

    def _accept_preview(self, _img, orient: int) -> bool:
        """Ignore stale frames from before an orientation switch."""
        return normalize_orientation(orient) == normalize_orientation(
            self.settings.orientation
        )

    def _on_preview_ready(self, img, snap: SysSnapshot, orient: int) -> None:
        if not self._accept_preview(img, orient):
            return
        self._show_pil(img)
        self.source_label.setText(self._source_text(snap))

    def _on_stream_preview_frame(self, img, orient: int) -> None:
        if self._stream_preview_gate:
            return
        if not self._accept_preview(img, orient):
            return
        self._show_pil(img)

    def _show_pil(self, img) -> None:
        try:
            rgba = img.convert("RGBA")
            qimg = ImageQt(rgba)
            if not isinstance(qimg, QImage):
                qimg = QImage(qimg)
            # Copy: ImageQt may keep a weak ref to PIL buffer.
            pix = QPixmap.fromImage(QImage(qimg))
            # 比例/窗口已在切角度或 _apply_theme_labels 里定好，这里只换图，避免二次跳动。
            self.preview.set_source(pix)
        except Exception as exc:
            self.status_label.setText(i18n.t("preview_show_fail", msg=exc))

    # ------------------------------------------------------------------
    # 应用设置（开机启动等）
    # ------------------------------------------------------------------

    def _on_autostart(self, checked: bool) -> None:
        self.settings.autostart = checked
        self.settings.save()
        autostart.set_enabled(checked)

    def _on_autorun(self, checked: bool) -> None:
        self.settings.auto_run = checked
        self.settings.save()

    def _on_live_preview(self, checked: bool) -> None:
        self.settings.live_preview = checked
        self.settings.save()
        if self.worker is not None:
            self.worker.live_preview = checked
        self._sync_preview_timer()

    def _sync_preview_timer(self) -> None:
        if self.settings.live_preview:
            if not self._preview_timer.isActive():
                self._preview_timer.start()
        else:
            self._preview_timer.stop()

    # ------------------------------------------------------------------
    # 推流开停与 Worker 回调
    # ------------------------------------------------------------------

    def start_stream(self) -> None:
        if self._current is None:
            QMessageBox.warning(
                self,
                i18n.t("cannot_start"),
                i18n.t("add_theme_first", path=themes_path()),
            )
            return
        if self.worker and self.worker.isRunning():
            return
        self._cancel_preview_worker()
        if not self.device.available:
            QMessageBox.warning(self, i18n.t("cannot_start"), i18n.t("msdisplay_missing"))
            return
        # Drop stale handle from a previous unplug before starting again.
        self.device.invalidate_session()
        self.refresh_device_list()
        entry = self._selected_device()
        self._current = get_theme(self.settings.theme_id)
        self._apply_slideshow_to_theme()
        self.worker = StreamWorker(
            theme=self._current,
            device=self.device,
            metrics=self.metrics,
            interval=self.settings.interval,
            encode_jpeg=self.settings.encode_jpeg,
            live_preview=self.settings.live_preview,
            orientation=self.settings.orientation,
            preferred_handle=entry.handle if entry else None,
            preferred_sn=(entry.sn if entry and entry.sn else None)
            or (self.settings.device_sn or None),
        )
        self.worker.status.connect(self.status_label.setText)
        self.worker.failed.connect(self._on_failed)
        self.worker.frame_sent.connect(self._on_frame)
        self.worker.preview_frame.connect(self._on_stream_preview_frame)
        self.worker.finished.connect(self._on_worker_finished)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.list.setEnabled(False)
        self.reload_btn.setEnabled(False)
        self.display_mode_combo.setEnabled(False)
        self.worker.start()

    def stop_stream(self) -> None:
        if self.worker:
            self.worker.stop()
            self.status_label.setText(i18n.t("stopping"))

    def _on_failed(self, msg: str) -> None:
        self.status_label.setText(i18n.t("error", msg=msg))
        QMessageBox.critical(self, i18n.t("stream_failed"), msg)

    def _on_frame(self, ok: int, fps: float) -> None:
        orient = (
            self.worker.orientation
            if self.worker is not None
            else self.settings.orientation
        )
        self.status_label.setText(
            i18n.t(
                "streaming",
                ok=ok,
                fps=fps,
                orient=normalize_orientation(orient),
            )
        )

    def _on_worker_finished(self) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.list.setEnabled(True)
        self.reload_btn.setEnabled(True)
        self.display_mode_combo.setEnabled(True)
        self.status_label.setText(i18n.t("ready"))

    # ------------------------------------------------------------------
    # 杂项动作（关于、退出）
    # ------------------------------------------------------------------

    def show_about(self) -> None:
        AboutDialog(self).exec()

    def quit_app(self) -> None:
        if self._tray is not None:
            self._tray.quit_app()
            return
        self.shutdown()
        from PySide6.QtWidgets import QApplication

        QApplication.instance().quit()

    # ------------------------------------------------------------------
    # 窗口生命周期
    # ------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        event.ignore()
        self.hide()

    def shutdown(self) -> None:
        self._preview_timer.stop()
        self._stream_preview_delay.stop()
        self._stream_preview_gate = False
        self._cancel_preview_worker()
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        self.device.stop_sdk()
        self.settings.save()
