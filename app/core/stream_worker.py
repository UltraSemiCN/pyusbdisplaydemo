from __future__ import annotations

import time
from datetime import datetime

from PIL import Image
from PySide6.QtCore import QThread, Signal

from app import i18n
from app.core.device_service import DeviceService, is_recoverable_send_error
from app.core.metrics import MetricsHub
from app.core.orientation import normalize_orientation, pic_size, prepare_frame
from app.themes.base import Theme


class StreamWorker(QThread):
    status = Signal(str)
    frame_sent = Signal(int, float)  # ok_count, fps
    failed = Signal(str)
    preview_frame = Signal(object, int)  # PIL logical frame, orientation

    def __init__(
        self,
        theme: Theme,
        device: DeviceService,
        metrics: MetricsHub,
        interval: float = 0.05,
        encode_jpeg: bool | None = None,
        live_preview: bool = False,
        orientation: int = 0,
        preferred_handle: int | None = None,
        preferred_sn: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._device = device
        self._metrics = metrics
        self._interval = max(0.0, interval)
        self._encode_jpeg = encode_jpeg
        self.live_preview = bool(live_preview)
        self.orientation = normalize_orientation(orientation)
        self._preferred_handle = int(preferred_handle) if preferred_handle else None
        if self._preferred_handle == 0:
            self._preferred_handle = None
        self._preferred_sn = (preferred_sn or "").strip() or None
        self._rebind = False
        self._force_preview = False
        self._stop = False
        self._last_preview: Image.Image | None = None
        self._last_preview_orient = 0

    def stop(self) -> None:
        self._stop = True

    def invalidate_preview_cache(self) -> None:
        self._last_preview = None

    def request_preview(self) -> None:
        """Push the latest send-pipeline frame to the UI preview."""
        self._force_preview = True
        if (
            self._last_preview is not None
            and self._last_preview_orient == self.orientation
        ):
            self.preview_frame.emit(self._last_preview, self._last_preview_orient)
            self._force_preview = False

    def set_preferred_device(
        self,
        *,
        preferred_handle: int | None = None,
        preferred_sn: str | None = None,
    ) -> None:
        """Request mid-stream rebind to another USB display."""
        handle = int(preferred_handle) if preferred_handle else None
        if handle == 0:
            handle = None
        self._preferred_handle = handle
        self._preferred_sn = (preferred_sn or "").strip() or None
        self._rebind = True

    def _emit_streaming(self, screen_w: int, screen_h: int, use_jpeg: bool) -> None:
        pic_w, pic_h = pic_size(screen_w, screen_h, self.orientation)
        self.status.emit(
            i18n.t(
                "streaming_status",
                theme=self._theme.resolution_label,
                dev_w=screen_w,
                dev_h=screen_h,
                jpeg=use_jpeg,
                orient=self.orientation,
                pic_w=pic_w,
                pic_h=pic_h,
            )
        )

    def _acquire_session(self, timeout: float = 20.0):
        self._device.invalidate_session()
        self.status.emit(i18n.t("waiting_device"))
        session = self._device.wait_for_device(
            timeout=timeout,
            preferred_handle=self._preferred_handle,
            preferred_sn=self._preferred_sn,
        )
        use_jpeg = (
            session.jpeg_support if self._encode_jpeg is None else bool(self._encode_jpeg)
        )
        return session, use_jpeg

    def run(self) -> None:
        try:
            self.status.emit(i18n.t("sdk_starting"))
            self._device.start_sdk()
            session, use_jpeg = self._acquire_session(timeout=15.0)
            screen_w, screen_h = session.width, session.height
            self._emit_streaming(screen_w, screen_h, use_jpeg)

            ok = 0
            t0 = time.perf_counter()
            last_t = t0
            fps = 0.0
            reconnects = 0

            while not self._stop:
                if self._rebind:
                    self._rebind = False
                    try:
                        session, use_jpeg = self._acquire_session(timeout=15.0)
                    except TimeoutError:
                        self.status.emit(i18n.t("device_switch_failed"))
                        continue
                    screen_w, screen_h = session.width, session.height
                    self._emit_streaming(screen_w, screen_h, use_jpeg)
                    t0 = time.perf_counter()
                    last_t = t0
                    ok = 0
                    fps = 0.0
                    reconnects = 0
                    continue

                try:
                    snap = self._metrics.sample()
                    snap.fps = fps
                    now_t = time.perf_counter() - t0
                    logical = self._theme.render_frame(
                        snap, datetime.now(), now_t, orient=self.orientation
                    )
                    frame = prepare_frame(logical, screen_w, screen_h, self.orientation)
                    self._device.send_image(frame, encode_jpeg=use_jpeg)
                    self._last_preview = logical
                    self._last_preview_orient = self.orientation
                except Exception as exc:
                    if self._stop:
                        break
                    link_down = is_recoverable_send_error(exc) or (
                        isinstance(exc, RuntimeError) and "设备未就绪" in str(exc)
                    )
                    if not link_down:
                        raise

                    self.status.emit(i18n.t("device_lost", msg=str(exc)))
                    self._device.invalidate_session()
                    try:
                        session, use_jpeg = self._acquire_session(timeout=25.0)
                    except TimeoutError:
                        reconnects += 1
                        if reconnects >= 5 or self._stop:
                            self.failed.emit(i18n.t("reconnect_failed"))
                            return
                        continue
                    screen_w, screen_h = session.width, session.height
                    reconnects = 0
                    self._emit_streaming(screen_w, screen_h, use_jpeg)
                    # Reset timing so FPS isn't skewed by the outage.
                    t0 = time.perf_counter()
                    last_t = t0
                    ok = 0
                    fps = 0.0
                    continue

                ok += 1
                reconnects = 0
                now = time.perf_counter()
                inst = 1.0 / max(now - last_t, 1e-6)
                fps = inst if fps <= 0 else (fps * 0.8 + inst * 0.2)
                last_t = now
                if ok == 1 or ok % 15 == 0:
                    avg = ok / max(now - t0, 1e-6)
                    self.frame_sent.emit(ok, avg)
                if ok == 1 or self._force_preview or (self.live_preview and ok % 15 == 0):
                    self.preview_frame.emit(logical, self.orientation)
                    self._force_preview = False
                if self._interval > 0:
                    time.sleep(self._interval)
            self.status.emit(i18n.t("stopped"))
        except Exception as exc:
            self.failed.emit(str(exc))
