from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Match:
    x: int
    y: int
    w: int
    h: int
    score: float

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)


def _require_cv2():
    try:
        import cv2  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("opencv-python is required for image anchors") from e
    return cv2


def match_template(screen_path: Path, template_path: Path, threshold: float) -> Optional[Match]:
    cv2 = _require_cv2()
    import numpy as np  # type: ignore

    screen = cv2.imdecode(np.fromfile(str(screen_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    templ = cv2.imdecode(np.fromfile(str(template_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if screen is None or templ is None:
        raise RuntimeError("failed to read images for template match")

    res = cv2.matchTemplate(screen, templ, cv2.TM_CCOEFF_NORMED)
    _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(res)
    if float(max_val) < threshold:
        return None

    h, w = templ.shape[:2]
    x, y = max_loc
    return Match(x=int(x), y=int(y), w=int(w), h=int(h), score=float(max_val))

