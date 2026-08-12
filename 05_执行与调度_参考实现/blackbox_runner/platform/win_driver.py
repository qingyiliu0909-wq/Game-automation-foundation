from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from blackbox_runner.core.artifacts import copy_tree_if_exists
from blackbox_runner.core.io import ensure_dir
from blackbox_runner.core.types import Anchor, AndroidUiaAnchor
from blackbox_runner.platform.cv import match_template


class WindowsDriver:
    platform = "win"

    def __init__(
        self,
        exe_path: Optional[str],
        title_hint: Optional[str],
        artifact_sources: list[Path] | None = None,
    ) -> None:
        self.exe_path = exe_path
        self.title_hint = title_hint or ""
        self._proc: subprocess.Popen[str] | None = None
        self._tmp_dir: Path | None = None
        self._app = None
        self._win = None
        self.artifact_sources = artifact_sources or []

    def start(self) -> None:
        self._tmp_dir = ensure_dir(Path(os.getenv("TEMP", ".")) / "game_blackbox_runner")
        if self.exe_path:
            self._proc = subprocess.Popen([self.exe_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)

        # Blackbox mode can work without attaching to the window (screenshot + input).
        # Window attach is best-effort: if it fails/hangs in some environments, we still proceed.
        if not self.title_hint:
            return

        try:
            from pywinauto import Application  # type: ignore
        except Exception:
            return

        try:
            self._app = Application(backend="uia")
            # Use short timeout to avoid hanging forever on some game windows
            self._app.connect(title_re=self.title_hint, timeout=5, retry_interval=0.2)
            self._win = self._app.window(title_re=self.title_hint)
            try:
                self._win.set_focus()
            except Exception:
                pass
        except Exception:
            # Ignore attach failures; user can keep the game focused manually.
            self._app = None
            self._win = None
            return

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:
                pass

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def screenshot(self, out_path: Path) -> None:
        ensure_dir(out_path.parent)
        try:
            import pyautogui  # type: ignore
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("pyautogui is required for screenshot") from e

        img = pyautogui.screenshot()
        img.save(str(out_path))

    def _resolve_asset(self, assets_root: Path, asset: str) -> Path:
        p = Path(asset)
        return p if p.is_absolute() else (assets_root / asset)

    def click_anchor(self, anchor: Anchor, assets_root: Path) -> None:
        if isinstance(anchor, AndroidUiaAnchor):
            raise RuntimeError("android_uia anchor not supported on Windows")

        if not self._tmp_dir:
            self._tmp_dir = ensure_dir(Path(os.getenv("TEMP", ".")) / "game_blackbox_runner")
        screen = self._tmp_dir / "screen.png"
        self.screenshot(screen)
        templ = self._resolve_asset(assets_root, anchor.asset)
        if not templ.exists():
            raise FileNotFoundError(f"template not found on disk: {templ}")
        m = match_template(screen, templ, threshold=anchor.threshold)
        if not m:
            raise TimeoutError(f"template not found: {anchor.asset}")

        x, y = m.center
        self.click_xy(x, y)

    def click_xy(self, x: int, y: int) -> None:
        try:
            import pydirectinput  # type: ignore

            pydirectinput.moveTo(int(x), int(y))
            pydirectinput.click()
        except Exception:
            import pyautogui  # type: ignore

            pyautogui.click(int(x), int(y))

    def mouse_down(self, x: int | None = None, y: int | None = None) -> None:
        # Move first if provided
        if x is not None and y is not None:
            try:
                import pyautogui  # type: ignore

                pyautogui.moveTo(int(x), int(y))
            except Exception:
                pass

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            INPUT_MOUSE = 0
            MOUSEEVENTF_LEFTDOWN = 0x0002

            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ("dx", wintypes.LONG),
                    ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", wintypes.ULONG_PTR),
                ]

            class INPUT(ctypes.Structure):
                class _I(ctypes.Union):
                    _fields_ = [("mi", MOUSEINPUT)]

                _anonymous_ = ("i",)
                _fields_ = [("type", wintypes.DWORD), ("i", _I)]

            inp = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=MOUSEEVENTF_LEFTDOWN, time=0, dwExtraInfo=0))
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
            return
        except Exception:
            pass

        import pyautogui  # type: ignore

        pyautogui.mouseDown()

    def move_xy(self, x: int, y: int, duration_sec: float) -> None:
        duration_sec = float(duration_sec)
        try:
            import ctypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            steps = max(80, int(duration_sec * 120))
            # Read current cursor pos
            pt = ctypes.wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            x0, y0 = int(pt.x), int(pt.y)
            dx = (int(x) - x0) / steps
            dy = (int(y) - y0) / steps
            fx = float(x0)
            fy = float(y0)
            for _ in range(steps):
                fx += dx
                fy += dy
                user32.SetCursorPos(int(round(fx)), int(round(fy)))
                time.sleep(duration_sec / steps)
            return
        except Exception:
            pass

        import pyautogui  # type: ignore

        pyautogui.moveTo(int(x), int(y), duration=duration_sec)

    def mouse_up(self) -> None:
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            INPUT_MOUSE = 0
            MOUSEEVENTF_LEFTUP = 0x0004

            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ("dx", wintypes.LONG),
                    ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", wintypes.ULONG_PTR),
                ]

            class INPUT(ctypes.Structure):
                class _I(ctypes.Union):
                    _fields_ = [("mi", MOUSEINPUT)]

                _anonymous_ = ("i",)
                _fields_ = [("type", wintypes.DWORD), ("i", _I)]

            inp = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=MOUSEEVENTF_LEFTUP, time=0, dwExtraInfo=0))
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
            return
        except Exception:
            pass

        import pyautogui  # type: ignore

        pyautogui.mouseUp()

    def scroll(self, clicks: int) -> None:
        """
        Mouse wheel scroll. Positive -> up, Negative -> down.
        Uses Win32 SendInput WHEEL for better reliability in games.
        """
        clicks = int(clicks)
        if clicks == 0:
            return
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            INPUT_MOUSE = 0
            MOUSEEVENTF_WHEEL = 0x0800
            WHEEL_DELTA = 120

            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ("dx", wintypes.LONG),
                    ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", wintypes.ULONG_PTR),
                ]

            class INPUT(ctypes.Structure):
                class _I(ctypes.Union):
                    _fields_ = [("mi", MOUSEINPUT)]

                _anonymous_ = ("i",)
                _fields_ = [("type", wintypes.DWORD), ("i", _I)]

            # Send multiple small wheel events (more reliable than one huge delta)
            step = 1 if clicks > 0 else -1
            for _ in range(abs(clicks)):
                inp = INPUT(
                    type=INPUT_MOUSE,
                    mi=MOUSEINPUT(
                        dx=0,
                        dy=0,
                        mouseData=wintypes.DWORD(WHEEL_DELTA * step),
                        dwFlags=MOUSEEVENTF_WHEEL,
                        time=0,
                        dwExtraInfo=0,
                    ),
                )
                user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
                time.sleep(0.02)
            return
        except Exception:
            pass

        import pyautogui  # type: ignore

        pyautogui.scroll(clicks * 120)

    def drag_xy(self, x1: int, y1: int, x2: int, y2: int, duration_sec: float) -> None:
        """
        Drag from (x1,y1) to (x2,y2). Best-effort using pydirectinput first.
        """
        duration_sec = float(duration_sec)

        # Prefer Win32 SetCursorPos + button down/up for borderless windowed games.
        # Many games treat relative injected mouse moves as low-confidence.
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)

            INPUT_MOUSE = 0
            MOUSEEVENTF_LEFTDOWN = 0x0002
            MOUSEEVENTF_LEFTUP = 0x0004
            MOUSEEVENTF_ABSOLUTE = 0x8000

            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ("dx", wintypes.LONG),
                    ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", wintypes.ULONG_PTR),
                ]

            class INPUT(ctypes.Structure):
                class _I(ctypes.Union):
                    _fields_ = [("mi", MOUSEINPUT)]

                _anonymous_ = ("i",)
                _fields_ = [("type", wintypes.DWORD), ("i", _I)]

            def _send(flags: int) -> None:
                # no move, only button events
                inp = INPUT(
                    type=INPUT_MOUSE,
                    mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=flags, time=0, dwExtraInfo=0),
                )
                n = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
                if n != 1:
                    raise ctypes.WinError(ctypes.get_last_error())

            x1i, y1i, x2i, y2i = int(x1), int(y1), int(x2), int(y2)
            dx_total = x2i - x1i
            dy_total = y2i - y1i

            # Higher step count -> smoother absolute drag
            steps = max(80, int(duration_sec * 120))
            dx_step = dx_total / steps
            dy_step = dy_total / steps

            # Move cursor to start using SetCursorPos (pixel-accurate)
            user32.SetCursorPos(x1i, y1i)
            time.sleep(0.05)
            _send(MOUSEEVENTF_LEFTDOWN)
            # hold for a moment before moving, mimics human drag start
            time.sleep(0.30)

            fx = float(x1i)
            fy = float(y1i)
            for _ in range(steps):
                fx += dx_step
                fy += dy_step
                user32.SetCursorPos(int(round(fx)), int(round(fy)))
                time.sleep(duration_sec / steps)

            time.sleep(0.15)
            _send(MOUSEEVENTF_LEFTUP)
            return
        except Exception:
            pass

        # Fallback to pyautogui dragTo (also holds left button)
        import pyautogui  # type: ignore

        pyautogui.moveTo(int(x1), int(y1))
        pyautogui.dragTo(int(x2), int(y2), duration=duration_sec, button="left")

    def press(self, key: str) -> None:
        try:
            import pydirectinput  # type: ignore

            pydirectinput.press(key)
        except Exception:
            import pyautogui  # type: ignore

            pyautogui.press(key)

    def wait_anchor(self, anchor: Anchor, assets_root: Path, timeout_sec: float) -> bool:
        if isinstance(anchor, AndroidUiaAnchor):
            return False
        deadline = time.time() + timeout_sec
        templ = self._resolve_asset(assets_root, anchor.asset)
        if not templ.exists():
            return False
        while time.time() <= deadline:
            if not self._tmp_dir:
                self._tmp_dir = ensure_dir(Path(os.getenv("TEMP", ".")) / "game_blackbox_runner")
            screen = self._tmp_dir / "screen.png"
            self.screenshot(screen)
            m = match_template(screen, templ, threshold=anchor.threshold)
            if m:
                return True
            time.sleep(0.5)
        return False

    def collect_postmortem(self, out_dir: Path) -> dict[str, str]:
        """
        Best-effort collection of paths explicitly configured by the calling project.
        Nothing is inferred from the runner's own directory, so this works for
        packaged games, source projects, and non-UE games alike.
        """
        artifacts: dict[str, str] = {}
        for index, source in enumerate(self.artifact_sources, start=1):
            if not source.exists() or not source.is_dir():
                continue
            destination_name = f"source_{index}_{source.name}"
            destination = out_dir / "external_artifacts" / destination_name
            if copy_tree_if_exists(source, destination):
                artifacts[f"artifact_source_{index}"] = str(destination.relative_to(out_dir))
        return artifacts

