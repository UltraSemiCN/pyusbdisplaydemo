from __future__ import annotations

import math
import platform
import re
import subprocess
import time
from copy import deepcopy
from dataclasses import dataclass, field, replace
from xml.etree import ElementTree as ET

try:
    import mmap
except ImportError:  # pragma: no cover
    mmap = None  # type: ignore

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore


AIDA64_SHMEM = "AIDA64_SensorValues"


@dataclass
class SysSnapshot:
    host: str = "HOST"
    source: str = "mock"  # aida64 | local | mock
    cpu_name: str = "CPU"
    cpu_usage: float = 0.0
    cpu_temp: float = 0.0
    cpu_clock: float = 0.0
    cpu_fan: float = 0.0
    gpu_name: str = "GPU"
    gpu_usage: float = 0.0
    gpu_temp: float = 0.0
    gpu_clock: float = 0.0
    gpu_fan: float = 0.0
    ram_total_gb: float = 16.0
    ram_used_mb: float = 0.0
    ram_percent: float = 0.0
    disks: list[tuple[str, float]] = field(default_factory=list)
    net_up_kb: float = 0.0
    net_down_kb: float = 0.0
    fps: float = 0.0  # stream push rate; themes may display it


def _f(v: str | None, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(str(v).replace("%", "").replace(",", "").strip())
    except ValueError:
        return default


class Aida64Collector:
    """Read AIDA64 shared memory (Preferences → External Applications → Shared Memory)."""

    def __init__(self) -> None:
        self._host = platform.node() or "HOST"
        self._avail_cache: bool | None = None
        self._avail_t = 0.0

    def available(self) -> bool:
        now = time.perf_counter()
        if self._avail_cache is not None and now - self._avail_t < 2.0:
            return self._avail_cache
        self._avail_cache = self._raw() is not None
        self._avail_t = now
        return self._avail_cache

    def _raw(self) -> str | None:
        if mmap is None:
            return None
        try:
            with mmap.mmap(-1, 65535, tagname=AIDA64_SHMEM, access=mmap.ACCESS_READ) as mm:
                data = mm.read(65535)
            text = data.split(b"\x00", 1)[0].decode("utf-8", errors="ignore").strip()
            return text or None
        except Exception:
            return None

    def sample(self) -> SysSnapshot | None:
        raw = self._raw()
        if not raw:
            return None
        # AIDA64 dumps concatenated tags; wrap for XML parse.
        xml = f"<root>{raw}</root>"
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            # Fallback loose regex if malformed
            return self._parse_loose(raw)

        by_id: dict[str, tuple[str, str]] = {}
        by_label: dict[str, str] = {}
        for node in root:
            sid = (node.attrib.get("id") or "").upper()
            label = node.attrib.get("label") or ""
            value = node.attrib.get("value") or (node.text or "")
            if sid:
                by_id[sid] = (label, value)
            if label:
                by_label[label.lower()] = value

        def pick(*ids: str, label_contains: str | None = None) -> float:
            for i in ids:
                if i in by_id:
                    return _f(by_id[i][1])
            if label_contains:
                key = label_contains.lower()
                for lab, val in by_label.items():
                    if key in lab:
                        return _f(val)
            return 0.0

        snap = SysSnapshot(host=self._host, source="aida64")
        snap.cpu_usage = pick("SCPUUTI", label_contains="cpu utilization")
        snap.cpu_temp = pick("TCPU", "TMOBO", label_contains="cpu")
        snap.cpu_clock = pick("SCPUCLK", label_contains="cpu clock")
        snap.cpu_fan = pick("FCPU", label_contains="cpu")
        snap.gpu_usage = pick("SGPU1UTI", "SGPUUTI", label_contains="gpu utilization")
        snap.gpu_temp = pick("TGPU1", "TGPU", label_contains="gpu")
        snap.gpu_clock = pick("SGPU1CLK", "SGPUCLK", label_contains="gpu clock")
        snap.gpu_fan = pick("FGPU1", "FGPU", label_contains="gpu")
        snap.ram_percent = pick("SMEMUTI", label_contains="memory utilization")
        used = pick("SMEMUSED", label_contains="used memory")
        if used > 0:
            # AIDA64 often reports MB
            snap.ram_used_mb = used if used > 64 else used * 1024
        total = pick("SMEMFRE", "SMEMCOMM")  # weak; keep default if missing
        if snap.ram_percent > 0 and snap.ram_used_mb > 0:
            snap.ram_total_gb = max(1.0, snap.ram_used_mb / max(snap.ram_percent, 1.0) * 100 / 1024)
        elif total > 0:
            snap.ram_total_gb = total / 1024 if total > 64 else total

        # Disks: SDSK*UTI style if present
        disks: list[tuple[str, float]] = []
        for sid, (label, value) in by_id.items():
            if "DSK" in sid and "UTI" in sid:
                name = label or sid
                disks.append((name[:8], _f(value)))
            if len(disks) >= 3:
                break
        snap.disks = disks or [("C:/", 0.0)]

        snap.net_up_kb = pick("SNIC1ULRATE", "SNICULRATE", label_contains="upload")
        snap.net_down_kb = pick("SNIC1DLRATE", "SNICDLRATE", label_contains="download")
        # Some AIDA64 builds report KB/s already; if values look like B/s, scale down
        if snap.net_down_kb > 100_000:
            snap.net_down_kb /= 1024
            snap.net_up_kb /= 1024
        return snap

    def _parse_loose(self, raw: str) -> SysSnapshot | None:
        snap = SysSnapshot(host=self._host, source="aida64")
        for sid, val in re.findall(r'id="([^"]+)"[^>]*value="([^"]+)"', raw, flags=re.I):
            sid_u = sid.upper()
            v = _f(val)
            if sid_u == "SCPUUTI":
                snap.cpu_usage = v
            elif sid_u == "TCPU":
                snap.cpu_temp = v
            elif sid_u == "SCPUCLK":
                snap.cpu_clock = v
            elif sid_u in ("SGPU1UTI", "SGPUUTI"):
                snap.gpu_usage = v
            elif sid_u in ("TGPU1", "TGPU"):
                snap.gpu_temp = v
            elif sid_u == "SMEMUTI":
                snap.ram_percent = v
        return snap


class LocalCollector:
    def __init__(self) -> None:
        self._last_net = None
        self._last_t = time.perf_counter()
        self._has_nvidia = self._probe_nvidia()
        self._t0 = time.perf_counter()
        self._host = platform.node() or "HOST"
        self._gpu_cache: dict[str, float] | None = None
        self._gpu_cache_t = 0.0

    def _probe_nvidia(self) -> bool:
        try:
            subprocess.check_output(
                ["nvidia-smi", "-L"],
                stderr=subprocess.DEVNULL,
                timeout=1.5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return True
        except Exception:
            return False

    def _nvidia(self) -> dict[str, float] | None:
        if not self._has_nvidia:
            return None
        now = time.perf_counter()
        if self._gpu_cache is not None and now - self._gpu_cache_t < 1.5:
            return self._gpu_cache
        try:
            out = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,temperature.gpu,clocks.gr,fan.speed",
                    "--format=csv,noheader,nounits",
                ],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=1.0,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            parts = [p.strip() for p in out.strip().splitlines()[0].split(",")]
            self._gpu_cache = {
                "name": parts[0],
                "usage": float(parts[1]),
                "temp": float(parts[2]),
                "clock": float(parts[3]),
                "fan": float(parts[4]) if parts[4] not in ("", "[N/A]") else 0.0,
            }
            self._gpu_cache_t = now
            return self._gpu_cache
        except Exception:
            return self._gpu_cache

    def sample(self) -> SysSnapshot:
        t = time.perf_counter() - self._t0
        snap = SysSnapshot(host=self._host, source="local" if psutil else "mock")

        if psutil:
            snap.cpu_usage = float(psutil.cpu_percent(interval=None))
            freq = psutil.cpu_freq()
            if freq:
                snap.cpu_clock = float(freq.current)
            vm = psutil.virtual_memory()
            snap.ram_percent = float(vm.percent)
            snap.ram_used_mb = vm.used / (1024**2)
            snap.ram_total_gb = vm.total / (1024**3)
            disks: list[tuple[str, float]] = []
            seen: set[str] = set()
            for part in psutil.disk_partitions(all=False):
                if len(disks) >= 3:
                    break
                mount = part.mountpoint
                if mount in seen or "cdrom" in (part.opts or "").lower():
                    continue
                try:
                    u = psutil.disk_usage(mount)
                    label = mount.rstrip("\\/") + "/"
                    if len(label) > 4:
                        label = label[:2] + "/"
                    disks.append((label.upper() if label[0].isalpha() else label, float(u.percent)))
                    seen.add(mount)
                except Exception:
                    continue
            snap.disks = disks or [("C:/", 0.0)]
            now = time.perf_counter()
            net = psutil.net_io_counters()
            if self._last_net is not None:
                dt = max(now - self._last_t, 1e-3)
                snap.net_up_kb = max(0.0, (net.bytes_sent - self._last_net.bytes_sent) / 1024.0 / dt)
                snap.net_down_kb = max(0.0, (net.bytes_recv - self._last_net.bytes_recv) / 1024.0 / dt)
            self._last_net = net
            self._last_t = now
        else:
            snap.cpu_usage = 55 + 30 * math.sin(t * 0.8)
            snap.cpu_clock = 4200 + 600 * math.sin(t * 0.5)
            snap.ram_percent = 60 + 15 * math.sin(t * 0.3)
            snap.ram_used_mb = snap.ram_percent / 100 * 16 * 1024
            snap.disks = [("C:/", 65), ("D:/", 42)]
            snap.net_up_kb = abs(40 * math.sin(t))
            snap.net_down_kb = abs(120 * math.cos(t * 0.7))

        if not snap.cpu_temp:
            snap.cpu_temp = 38 + snap.cpu_usage * 0.25
        snap.cpu_fan = 900 + snap.cpu_usage * 8

        gpu = self._nvidia()
        if gpu:
            snap.gpu_name = gpu["name"][:24]
            snap.gpu_usage = gpu["usage"]
            snap.gpu_temp = gpu["temp"]
            snap.gpu_clock = gpu["clock"]
            snap.gpu_fan = gpu["fan"] or (800 + gpu["usage"] * 10)
        else:
            snap.gpu_usage = max(0.0, 40 + 35 * math.sin(t * 0.65 + 1.2))
            snap.gpu_temp = 40 + snap.gpu_usage * 0.3
            snap.gpu_clock = 1500 + snap.gpu_usage * 8
            snap.gpu_fan = 700 + snap.gpu_usage * 9
        return snap


METRIC_UPDATE_S = 0.5
METRIC_EMA_ALPHA = 0.45

_EMA_FLOAT_FIELDS = (
    "cpu_usage",
    "cpu_temp",
    "cpu_clock",
    "cpu_fan",
    "gpu_usage",
    "gpu_temp",
    "gpu_clock",
    "gpu_fan",
    "ram_total_gb",
    "ram_used_mb",
    "ram_percent",
    "net_up_kb",
    "net_down_kb",
)


class MetricsHub:
    """Prefer AIDA64 shared memory; fall back to local collectors.

    Displayed sensor values refresh at ~2 Hz with EMA smoothing so HUD digits
    do not jitter at the stream push rate. Callers may mutate the returned
    snapshot (e.g. ``fps``); the internal cache is not shared.
    """

    def __init__(self) -> None:
        self._aida = Aida64Collector()
        self._local = LocalCollector()
        self._display: SysSnapshot | None = None
        self._last_update = 0.0
        if psutil is not None:
            psutil.cpu_percent(interval=None)

    def _raw_sample(self) -> SysSnapshot:
        snap = self._aida.sample()
        if snap is not None:
            return snap
        return self._local.sample()

    @staticmethod
    def _ema_disks(
        old: list[tuple[str, float]], new: list[tuple[str, float]], alpha: float
    ) -> list[tuple[str, float]]:
        old_map = {label: pct for label, pct in old}
        out: list[tuple[str, float]] = []
        for label, pct in new:
            if label in old_map:
                out.append((label, alpha * pct + (1.0 - alpha) * old_map[label]))
            else:
                out.append((label, pct))
        return out

    def _blend(self, prev: SysSnapshot, raw: SysSnapshot) -> SysSnapshot:
        a = METRIC_EMA_ALPHA
        kwargs: dict = {
            "host": raw.host,
            "source": raw.source,
            "cpu_name": raw.cpu_name,
            "gpu_name": raw.gpu_name,
            "fps": 0.0,
            "disks": self._ema_disks(prev.disks, raw.disks, a),
        }
        for name in _EMA_FLOAT_FIELDS:
            new_v = getattr(raw, name)
            old_v = getattr(prev, name)
            kwargs[name] = a * new_v + (1.0 - a) * old_v
        return replace(prev, **kwargs)

    def sample(self) -> SysSnapshot:
        now = time.perf_counter()
        if self._display is not None and (now - self._last_update) < METRIC_UPDATE_S:
            return deepcopy(self._display)

        raw = self._raw_sample()
        if self._display is None:
            self._display = replace(raw, fps=0.0)
        else:
            self._display = self._blend(self._display, raw)
        # Stamp after collect so slow probes (e.g. nvidia-smi) do not shrink the hold.
        self._last_update = time.perf_counter()
        return deepcopy(self._display)

    def source_label(self) -> str:
        if self._aida.available():
            return "AIDA64"
        return "local" if psutil else "mock"
