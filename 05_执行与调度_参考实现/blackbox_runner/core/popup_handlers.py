from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from blackbox_runner.core.types import Anchor


class PopupDriver(Protocol):
    def click_anchor(self, anchor: Anchor, assets_root: Path) -> None: ...
    def wait_anchor(self, anchor: Anchor, assets_root: Path, timeout_sec: float) -> bool: ...


@dataclass(frozen=True)
class PopupRule:
    name: str
    detect: Anchor
    dismiss: Anchor
    cooldown_sec: float = 2.0


def try_handle_popups(driver: PopupDriver, assets_root: Path, rules: list[PopupRule]) -> list[str]:
    """
    Best-effort popup auto-dismiss. Returns handled popup names.
    """
    handled: list[str] = []
    for rule in rules:
        try:
            if driver.wait_anchor(rule.detect, assets_root=assets_root, timeout_sec=0.05):
                driver.click_anchor(rule.dismiss, assets_root=assets_root)
                handled.append(rule.name)
        except Exception:
            continue
    return handled

