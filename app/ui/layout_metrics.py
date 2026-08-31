"""Language-keyed UI size floors. Add a row when adding a language.

Unknown languages fall back to en_US (typically longer strings).
Metrics are floors only — layout still takes max(floor, sizeHint).
"""

from __future__ import annotations

from dataclasses import dataclass

from app import i18n


@dataclass(frozen=True)
class LayoutMetrics:
    panel_min_w: int
    stream_min_w: int
    win_min_w: int
    win_default_w: int


LAYOUT_BY_LANG: dict[str, LayoutMetrics] = {
    "zh_CN": LayoutMetrics(180, 180, 560, 680),
    "en_US": LayoutMetrics(200, 260, 640, 760),
}


def layout_metrics(lang: str | None = None) -> LayoutMetrics:
    code = lang or i18n.language()
    return LAYOUT_BY_LANG.get(code, LAYOUT_BY_LANG["en_US"])
