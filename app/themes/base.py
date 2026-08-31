from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from PIL import Image

from app.core.metrics import SysSnapshot


class Theme(ABC):
    """Style template: resolution and look are defined by the theme itself."""

    id: str
    name: str
    width: int
    height: int
    description: str = ""

    @property
    def resolution_label(self) -> str:
        return f"{self.width}×{self.height}"

    def canvas_size(self, orient: int = 0) -> tuple[int, int]:
        """Logical pic size before send-side rotation. Default: theme width×height."""
        return self.width, self.height

    def render_frame(
        self,
        snap: SysSnapshot,
        now: datetime,
        t: float = 0.0,
        *,
        orient: int = 0,
    ) -> Image.Image:
        """Render logical frame for placement orientation.

        Default ignores *orient* and calls :meth:`render`, so existing themes
        keep their previous behaviour. Orient-aware themes override this.
        """
        return self.render(snap, now, t)

    @abstractmethod
    def render(self, snap: SysSnapshot, now: datetime, t: float = 0.0) -> Image.Image:
        """Render at self.width x self.height."""
