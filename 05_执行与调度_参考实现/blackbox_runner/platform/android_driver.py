from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional

from blackbox_runner.core.io import ensure_dir
from blackbox_runner.core.types import Anchor, AndroidUiaAnchor


class AndroidDriver:
    platform = "android"

    def __init__(self, device_serial: Optional[str], package_name: Optional[str]) -> None:
        self.serial = device_serial or ""
        self.package = package_name or ""
        self._d = None
        self._logcat_proc: subprocess.Popen[str] | None = None
        self._logcat_path: Path | None = None

    def _adb_base(self) -> list[str]:
        base = ["adb"]
        if self.serial:
            base += ["-s", self.serial]
        return base

    def start(self) -> None:
        try:
            import uiautomator2 as u2  # type: ignore
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("uiautomator2 is required for android runner") from e

        self._d = u2.connect(self.serial) if self.serial else u2.connect()

        # keep screen on during tests
        try:
            self._d.screen_on()
        except Exception:
            pass

        # clear old logcat to keep postmortem smaller
        try:
            base = self._adb_base()
            subprocess.check_call(base + ["logcat", "-c"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def stop(self) -> None:
        if self._logcat_proc and self._logcat_proc.poll() is None:
            try:
                self._logcat_proc.terminate()
            except Exception:
                pass

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def screenshot(self, out_path: Path) -> None:
        ensure_dir(out_path.parent)
        if not self._d:
            raise RuntimeError("driver not started")
        self._d.screenshot(str(out_path))

    def click_anchor(self, anchor: Anchor, assets_root: Path) -> None:
        if not self._d:
            raise RuntimeError("driver not started")

        if isinstance(anchor, AndroidUiaAnchor):
            sel = self._build_selector(anchor)
            obj = self._d(**sel)
            if not obj.exists:
                raise TimeoutError(f"uia anchor not found: {anchor}")
            obj.click()
            return

        # Image anchor on Android is optional; keep a clear error
        raise RuntimeError("image anchors on Android are not enabled by default; use android_uia anchors")

    def click_xy(self, x: int, y: int) -> None:
        if not self._d:
            raise RuntimeError("driver not started")
        self._d.click(int(x), int(y))

    def drag_xy(self, x1: int, y1: int, x2: int, y2: int, duration_sec: float) -> None:
        if not self._d:
            raise RuntimeError("driver not started")
        self._d.swipe(int(x1), int(y1), int(x2), int(y2), duration=float(duration_sec))

    def press(self, key: str) -> None:
        if not self._d:
            raise RuntimeError("driver not started")
        # common android keys: home, back, menu, enter
        self._d.press(key)

    def wait_anchor(self, anchor: Anchor, assets_root: Path, timeout_sec: float) -> bool:
        if not self._d:
            raise RuntimeError("driver not started")

        if isinstance(anchor, AndroidUiaAnchor):
            sel = self._build_selector(anchor)
            return bool(self._d(**sel).wait(timeout=timeout_sec))

        # image anchor not supported by default
        return False

    def _build_selector(self, anchor: AndroidUiaAnchor) -> dict:
        sel: dict = {}
        if anchor.resource_id:
            sel["resourceId"] = anchor.resource_id
        if anchor.text:
            sel["text"] = anchor.text
        if not sel:
            raise ValueError("android_uia anchor requires resource_id and/or text")
        return sel

    def _start_logcat(self, out_path: Path) -> None:
        ensure_dir(out_path.parent)
        base = self._adb_base()
        cmd = base + ["logcat", "-v", "threadtime"]
        f = out_path.open("w", encoding="utf-8", errors="ignore")
        self._logcat_proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
        self._logcat_path = out_path

    def collect_postmortem(self, out_dir: Path) -> dict[str, str]:
        artifacts: dict[str, str] = {}
        # Ensure we have at least a bounded logcat slice
        logcat_path = out_dir / "android" / "logcat.txt"
        try:
            # dump current logcat snapshot (bounded) instead of continuous streaming
            base = self._adb_base()
            out = subprocess.check_output(
                base + ["logcat", "-d", "-v", "threadtime"],
                text=True,
                errors="ignore",
            )
            ensure_dir(logcat_path.parent)
            logcat_path.write_text(out, encoding="utf-8", errors="ignore")
            artifacts["logcat"] = str(logcat_path.relative_to(out_dir))
        except Exception:
            pass
        return artifacts

