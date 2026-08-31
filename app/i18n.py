"""Simple UI i18n (zh_CN / en_US)."""

from __future__ import annotations

from typing import Any

LANG_CHOICES: list[tuple[str, str]] = [
    ("zh_CN", "中文"),
    ("en_US", "English"),
]

_DEFAULT = "zh_CN"
_lang = _DEFAULT

_STRINGS: dict[str, dict[str, str]] = {
    "zh_CN": {
        "app_title": "USB Display HUD",
        "themes": "风格模板",
        "about": "关于",
        "language": "语言",
        "rescan_themes": "重新扫描主题",
        "rescan_tip": "重新扫描目录中的 *.py 模板：\n{path}",
        "themes_dir": "模板目录：{path}",
        "themes_folder": "模板文件夹",
        "themes_folder_tip": "留空或恢复默认则使用程序旁 themes 目录。",
        "themes_pick_folder": "选择模板文件夹",
        "themes_list_tip": "勾选左侧方框可将主题标为喜欢，喜欢的主题排在最前。",
        "resolution": "分辨率：{value}",
        "no_themes": "无可用模板",
        "data_source": "数据源：{value}",
        "autostart": "开机启动",
        "auto_run": "自动运行",
        "live_preview": "实时预览",
        "live_preview_tip": "关闭时仅用第一帧作预览；开启后推流过程中持续刷新预览。",
        "orientation": "摆放方向",
        "orientation_tip": (
            "按屏幕物理摆放旋转后再发送。"
            "0°/180°：pic=屏宽×屏高；90°/270°：pic=屏高×屏宽，再旋转。"
        ),
        "orient_0": "0°",
        "orient_90": "90°",
        "orient_180": "180°",
        "orient_270": "270°",
        "quit": "退出",
        "start": "开始运行",
        "stop": "停止运行",
        "ready": "就绪",
        "preview_loading": "预览加载中…",
        "preview_fetching": "获取预览…",
        "tip": "提示",
        "stop_before_rescan": "请先停止运行再重新扫描主题。",
        "rescanned": "已重新扫描主题（{count} 个）",
        "theme_load_warn": "模板加载警告：{detail}",
        "cannot_start": "无法开始",
        "add_theme_first": "请先在 {path} 添加模板 .py",
        "msdisplay_missing": "未安装 msdisplay（pip install pyusbdisplay）",
        "stopping": "正在停止…",
        "error": "错误：{msg}",
        "stream_failed": "推流失败",
        "streaming": "推流中 · frames={ok} · {fps:.1f} fps · {orient}°",
        "preview_fail": "预览失败：{msg}",
        "preview_show_fail": "预览显示失败：{msg}",
        "no_theme_title": "无模板",
        "resolution_na": "—",
        "source_local": "本地",
        "source_mock": "模拟",
        "source_aida64": "AIDA64",
        "tray_show": "显示主界面",
        "tray_start": "开始运行",
        "tray_stop": "停止运行",
        "tray_about": "关于…",
        "tray_quit": "退出",
        "tray_running": "已在托盘运行",
        "about_title": "关于",
        "about_home": "项目主页",
        "about_source": "开源地址",
        "about_open": "打开",
        "about_summary": (
            "将系统监控画面推送到 USB 副屏的桌面工具。"
            "支持可选风格模板、托盘运行与开机自启。"
            "风格模板以 themes/*.py 源码分发，便于自定义。"
        ),
        "theme_name_fav": "★ {name}",
        "theme_tooltip": "{desc}\n分辨率 {res}\nid={id}\n{fav_hint}",
        "theme_fav_on": "已标为喜欢",
        "theme_fav_off": "勾选可标为喜欢",
        "sdk_starting": "启动 SDK…",
        "waiting_device": "等待设备…",
        "device_lost": "设备断开（{msg}），正在重连…",
        "reconnect_failed": "设备重连失败，请重新插入 USB 后点击开始运行。",
        "streaming_status": (
            "推流中 · 模板 {theme} · 设备 {dev_w}x{dev_h} · pic {pic_w}x{pic_h}"
            " · {orient}° · jpeg={jpeg}"
        ),
        "stopped": "已停止",
        "already_running_title": "已在运行",
        "already_running_body": "USB Display HUD 已在运行，请从托盘打开。",
        "tray_unavailable_title": "错误",
        "tray_unavailable_body": "系统托盘不可用，无法运行。",
        "slideshow_group": "轮播设置",
        "slideshow_folder": "图片文件夹",
        "slideshow_browse": "浏览…",
        "slideshow_reset": "恢复默认",
        "slideshow_interval": "切图间隔（秒）",
        "slideshow_mode": "播放模式",
        "slideshow_mode_sequential": "顺序轮播",
        "slideshow_mode_shuffle": "乱序轮播",
        "slideshow_mode_single": "单图片",
        "slideshow_folder_tip": "留空或恢复默认则使用程序旁 photos 目录。",
        "slideshow_pick_folder": "选择图片文件夹",
        "display_mode": "显示模式",
        "display_mode_themes": "风格模板",
        "display_mode_slideshow": "照片轮播",
        "display_mode_tip": "风格模板与照片轮播互斥，选择其一。",
        "stop_before_mode": "请先停止运行再切换显示模式。",
        "device": "USB 设备",
        "device_refresh": "刷新",
        "device_none": "未检测到设备",
        "device_tip": "选择推流目标副屏。推流中切换会立即改绑到新屏。",
        "device_sdk_fail": "无法启动显示 SDK：{msg}",
        "device_switch_failed": "切换设备失败，仍在等待所选副屏…",
    },
    "en_US": {
        "app_title": "USB Display HUD",
        "themes": "Themes",
        "about": "About",
        "language": "Language",
        "rescan_themes": "Rescan themes",
        "rescan_tip": "Rescan *.py themes in:\n{path}",
        "themes_dir": "Themes folder: {path}",
        "themes_folder": "Themes folder",
        "themes_folder_tip": "Empty or reset uses the themes folder next to the app.",
        "themes_pick_folder": "Choose themes folder",
        "themes_list_tip": "Check a theme to mark it as favorite. Favorites stay at the top.",
        "resolution": "Resolution: {value}",
        "no_themes": "No themes available",
        "data_source": "Data source: {value}",
        "autostart": "Start on boot",
        "auto_run": "Auto run",
        "live_preview": "Live preview",
        "live_preview_tip": "Off: keep the first frame as preview. On: refresh the preview while streaming.",
        "orientation": "Orientation",
        "orientation_tip": (
            "Rotate the frame for physical screen placement. "
            "0°/180°: pic=screenW×screenH; 90°/270°: pic=screenH×screenW, then rotate."
        ),
        "orient_0": "0°",
        "orient_90": "90°",
        "orient_180": "180°",
        "orient_270": "270°",
        "quit": "Quit",
        "start": "Start",
        "stop": "Stop",
        "ready": "Ready",
        "preview_loading": "Loading preview…",
        "preview_fetching": "Fetching preview…",
        "tip": "Notice",
        "stop_before_rescan": "Stop streaming before rescanning themes.",
        "rescanned": "Themes rescanned ({count})",
        "theme_load_warn": "Theme load warning: {detail}",
        "cannot_start": "Cannot start",
        "add_theme_first": "Add a theme .py under {path} first",
        "msdisplay_missing": "msdisplay not installed (pip install pyusbdisplay)",
        "stopping": "Stopping…",
        "error": "Error: {msg}",
        "stream_failed": "Streaming failed",
        "streaming": "Streaming · frames={ok} · {fps:.1f} fps · {orient}°",
        "preview_fail": "Preview failed: {msg}",
        "preview_show_fail": "Preview display failed: {msg}",
        "no_theme_title": "No themes",
        "resolution_na": "—",
        "source_local": "Local",
        "source_mock": "Mock",
        "source_aida64": "AIDA64",
        "tray_show": "Show window",
        "tray_start": "Start",
        "tray_stop": "Stop",
        "tray_about": "About…",
        "tray_quit": "Quit",
        "tray_running": "Running in tray",
        "about_title": "About",
        "about_home": "Project website",
        "about_source": "Source code",
        "about_open": "Open",
        "about_summary": (
            "Desktop tool that streams system-monitor visuals to a USB secondary display. "
            "Supports selectable themes, tray mode, and autostart. "
            "Themes ship as editable themes/*.py files."
        ),
        "theme_name_fav": "★ {name}",
        "theme_tooltip": "{desc}\nResolution {res}\nid={id}\n{fav_hint}",
        "theme_fav_on": "Marked as favorite",
        "theme_fav_off": "Check to mark as favorite",
        "sdk_starting": "Starting SDK…",
        "waiting_device": "Waiting for device…",
        "device_lost": "Device lost ({msg}), reconnecting…",
        "reconnect_failed": "Reconnect failed. Re-plug USB, then click Start.",
        "streaming_status": (
            "Streaming · theme {theme} · device {dev_w}x{dev_h} · pic {pic_w}x{pic_h}"
            " · {orient}° · jpeg={jpeg}"
        ),
        "stopped": "Stopped",
        "already_running_title": "Already running",
        "already_running_body": "USB Display HUD is already running. Open it from the tray.",
        "tray_unavailable_title": "Error",
        "tray_unavailable_body": "System tray is unavailable.",
        "slideshow_group": "Slideshow",
        "slideshow_folder": "Photo folder",
        "slideshow_browse": "Browse…",
        "slideshow_reset": "Use default",
        "slideshow_interval": "Interval (sec)",
        "slideshow_mode": "Play mode",
        "slideshow_mode_sequential": "Sequential",
        "slideshow_mode_shuffle": "Shuffle",
        "slideshow_mode_single": "Single image",
        "slideshow_folder_tip": "Empty or reset uses the photos folder next to the app.",
        "slideshow_pick_folder": "Choose photo folder",
        "display_mode": "Display mode",
        "display_mode_themes": "Style themes",
        "display_mode_slideshow": "Photo slideshow",
        "display_mode_tip": "Style themes and photo slideshow are mutually exclusive.",
        "stop_before_mode": "Stop streaming before changing display mode.",
        "device": "USB device",
        "device_refresh": "Refresh",
        "device_none": "No device detected",
        "device_tip": "Choose which USB panel to stream to. Changing while streaming rebinds immediately.",
        "device_sdk_fail": "Cannot start display SDK: {msg}",
        "device_switch_failed": "Device switch failed; still waiting for the selected panel…",
    },
}


def set_language(code: str) -> None:
    global _lang
    _lang = code if code in _STRINGS else _DEFAULT


def language() -> str:
    return _lang


def t(key: str, **kwargs: Any) -> str:
    table = _STRINGS.get(_lang) or _STRINGS[_DEFAULT]
    text = table.get(key) or _STRINGS[_DEFAULT].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
