from __future__ import annotations

import threading
import time
from dataclasses import dataclass

try:
    import msdisplay as msd
except ImportError:  # pragma: no cover
    msd = None  # type: ignore


@dataclass
class DeviceSession:
    handle: int
    width: int
    height: int
    jpeg_support: bool
    state_label: str
    sn: str = ""


@dataclass
class DeviceEntry:
    handle: int
    sn: str
    width: int
    height: int
    jpeg_support: bool
    state_label: str

    def label(self) -> str:
        reso = f"{self.width}×{self.height}" if self.width > 0 and self.height > 0 else "—"
        if self.sn:
            return f"{reso} · SN:{self.sn}"
        return f"{reso} · handle 0x{self.handle:X}"


def is_recoverable_send_error(exc: BaseException) -> bool:
    """USB unplug / low-level link errors that may recover after re-attach."""
    if msd is None:
        return False
    if not isinstance(exc, msd.MSDisplayError):
        return False
    return exc.code in (
        msd.RetCode.LOWLEVEL_ERROR,  # -9
        msd.RetCode.NO_DEVICE,  # -6
        msd.RetCode.STATE_UNREADY,  # -4
        msd.RetCode.PROCESSOR_UNREADY,  # -7
        msd.RetCode.WRONG_SDK_STATE,  # -2
        msd.RetCode.GENERAL_ERROR,  # -1 (sometimes on hotplug)
    )


class DeviceService:
    def __init__(self) -> None:
        self._started = False
        self._lock = threading.Lock()
        self._devices: dict[int, list] = {}
        self.session: DeviceSession | None = None

    @property
    def available(self) -> bool:
        return msd is not None

    def _on_attach(self, handle: int, resolutions: list) -> None:
        with self._lock:
            self._devices[int(handle)] = resolutions

    def _on_detach(self, handle: int) -> None:
        handle = int(handle)
        with self._lock:
            self._devices.pop(handle, None)
        if self.session and self.session.handle == handle:
            self.session = None

    def invalidate_session(self) -> None:
        self.session = None

    def start_sdk(self, dll: str | None = None, loglevel: int = 1) -> None:
        if msd is None:
            raise RuntimeError("msdisplay 未安装，请 pip install pyusbdisplay")
        if self._started:
            return
        msd.load_sdk(dll)
        msd.register_callbacks(self._on_attach, self._on_detach)
        msd.start(loglevel=loglevel)
        try:
            msd.enable_sdk_screen_processor(True)
        except msd.MSDisplayError:
            pass
        self._started = True

    def stop_sdk(self) -> None:
        if msd is None or not self._started:
            return
        try:
            msd.stop()
        except msd.MSDisplayError:
            pass
        self._started = False
        with self._lock:
            self._devices.clear()
        self.session = None

    def _collect_handles(self) -> list[tuple[int, list]]:
        with self._lock:
            items = list(self._devices.items())
        if not items and msd is not None:
            try:
                for item in msd.get_device_list():
                    items.append((int(item.handle), []))
            except msd.MSDisplayError:
                pass
        return items

    def list_devices(self) -> list[DeviceEntry]:
        """Enumerate connected USB displays (SDK must already be started)."""
        if msd is None or not self._started:
            return []
        entries: list[DeviceEntry] = []
        seen: set[int] = set()
        for handle, resos in self._collect_handles():
            if handle == 0 or handle in seen:
                continue
            seen.add(handle)
            try:
                info = msd.get_device_info(handle)
            except msd.MSDisplayError:
                with self._lock:
                    self._devices.pop(handle, None)
                continue
            width = int(info.cur_reso.width or 0)
            height = int(info.cur_reso.height or 0)
            if (width <= 0 or height <= 0) and resos:
                width = int(getattr(resos[0], "width", 0) or 0)
                height = int(getattr(resos[0], "height", 0) or 0)
            if width <= 0 or height <= 0:
                cands = list(info.resolutions or [])
                if cands:
                    width = int(cands[0].width or 0)
                    height = int(cands[0].height or 0)
            entries.append(
                DeviceEntry(
                    handle=handle,
                    sn=str(info.sn or "").strip(),
                    width=width if width > 0 else 720,
                    height=height if height > 0 else 1280,
                    jpeg_support=bool(info.jpeg_support),
                    state_label=info.state_label,
                )
            )
        entries.sort(key=lambda e: (e.sn or "", e.handle))
        return entries

    @staticmethod
    def _is_ready(info, resos: list) -> bool:
        assert msd is not None
        return info.state in (msd.DeviceState.CREATED, msd.DeviceState.RUNNING) or bool(
            resos or info.resolutions
        )

    def wait_for_device(
        self,
        timeout: float = 12.0,
        *,
        preferred_handle: int | None = None,
        preferred_sn: str | None = None,
    ) -> DeviceSession:
        if msd is None:
            raise RuntimeError("msdisplay 不可用")
        # Drop any stale session before (re)binding.
        self.session = None
        pref_sn = (preferred_sn or "").strip() or None
        pref_h = int(preferred_handle) if preferred_handle else None
        if pref_h == 0:
            pref_h = None

        deadline = time.time() + timeout
        last_info = None
        last_handle = 0
        last_resos: list = []

        def try_bind_ready(candidates: list[tuple[int, list, object]]) -> DeviceSession | None:
            nonlocal last_info, last_handle, last_resos
            for handle, resos, info in candidates:
                last_info, last_handle, last_resos = info, handle, resos
                if self._is_ready(info, resos):
                    session = self._bind(handle, info, resos)
                    time.sleep(0.45)
                    return session
            return None

        while time.time() < deadline:
            probed: list[tuple[int, list, object]] = []
            for handle, resos in self._collect_handles():
                if handle == 0:
                    continue
                try:
                    info = msd.get_device_info(handle)
                except msd.MSDisplayError:
                    with self._lock:
                        self._devices.pop(handle, None)
                    continue
                probed.append((handle, resos, info))

            if pref_sn or pref_h is not None:
                ordered: list[tuple[int, list, object]] = []
                seen_h: set[int] = set()
                if pref_sn:
                    for h, r, info in probed:
                        if str(getattr(info, "sn", "") or "").strip() == pref_sn and h not in seen_h:
                            ordered.append((h, r, info))
                            seen_h.add(h)
                if pref_h is not None:
                    for h, r, info in probed:
                        if h == pref_h and h not in seen_h:
                            ordered.append((h, r, info))
                            seen_h.add(h)
                session = try_bind_ready(ordered)
                if session is not None:
                    return session
            else:
                session = try_bind_ready(probed)
                if session is not None:
                    return session

            time.sleep(0.4)

        if last_info is not None:
            session = self._bind(last_handle, last_info, last_resos)
            time.sleep(0.45)
            return session
        raise TimeoutError("未找到 USB 显示设备")

    def _bind(self, handle: int, info, resos) -> DeviceSession:
        assert msd is not None
        support_ext = False
        try:
            support_ext = msd.check_device_screen_capability(handle)
        except msd.MSDisplayError:
            pass
        if not support_ext:
            candidates = info.resolutions or resos
            if candidates:
                try:
                    msd.set_video_param(handle, candidates[0])
                    info = msd.get_device_info(handle)
                except msd.MSDisplayError:
                    pass
        width = info.cur_reso.width or (resos[0].width if resos else 720)
        height = info.cur_reso.height or (resos[0].height if resos else 1280)
        if width <= 0 or height <= 0:
            width, height = 720, 1280
        self.session = DeviceSession(
            handle=handle,
            width=width,
            height=height,
            jpeg_support=bool(info.jpeg_support),
            state_label=info.state_label,
            sn=str(getattr(info, "sn", "") or "").strip(),
        )
        return self.session

    def send_image(self, image, encode_jpeg: bool) -> None:
        if msd is None or self.session is None:
            raise RuntimeError("设备未就绪")
        frame = msd.from_pil(image)
        try:
            msd.send_picture(
                self.session.handle,
                frame.width,
                frame.height,
                frame.data,
                encode_jpeg=encode_jpeg,
            )
        except msd.MSDisplayError:
            # Stale handle after unplug — force re-bind on next wait_for_device.
            self.session = None
            raise
