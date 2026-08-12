from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from blackbox_runner.core.io import ensure_dir
from blackbox_runner.core.popup_handlers import PopupRule, try_handle_popups
from blackbox_runner.core.timeutil import now_ms, monotonic_ms
from blackbox_runner.core.types import Anchor, Case, RunResult, Step, StepAction, StepResult


class Driver(Protocol):
    platform: str

    def start(self) -> None: ...
    def stop(self) -> None: ...

    def screenshot(self, out_path: Path) -> None: ...
    def click_anchor(self, anchor: Anchor, assets_root: Path) -> None: ...
    def click_xy(self, x: int, y: int) -> None: ...
    def drag_xy(self, x1: int, y1: int, x2: int, y2: int, duration_sec: float) -> None: ...
    def mouse_down(self, x: int | None = None, y: int | None = None) -> None: ...
    def move_xy(self, x: int, y: int, duration_sec: float) -> None: ...
    def mouse_up(self) -> None: ...
    def scroll(self, clicks: int) -> None: ...
    def press(self, key: str) -> None: ...
    def wait_anchor(self, anchor: Anchor, assets_root: Path, timeout_sec: float) -> bool: ...
    def sleep(self, seconds: float) -> None: ...
    def collect_postmortem(self, out_dir: Path) -> dict[str, str]: ...


@dataclass(frozen=True)
class RunContext:
    run_id: str
    out_dir: Path
    steps_dir: Path
    assets_root: Path


def _new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def run_case(driver: Driver, case: Case, results_root: Path, assets_root: Path) -> RunResult:
    run_id = _new_run_id()
    out_dir = ensure_dir(results_root / run_id)
    steps_dir = ensure_dir(out_dir / "steps")
    ctx = RunContext(run_id=run_id, out_dir=out_dir, steps_dir=steps_dir, assets_root=assets_root)

    started_at = now_ms()
    start_mono = monotonic_ms()
    step_results: list[StepResult] = []
    ok = True

    driver.start()
    try:
        # Always capture initial screenshot
        try:
            p = steps_dir / "000_start.png"
            driver.screenshot(p)
        except Exception:
            pass

        for idx, step in enumerate(case.steps, start=1):
            # best-effort: dismiss known popups (user can add assets later)
            _ = try_handle_popups(driver, assets_root=assets_root, rules=_default_popup_rules())
            sr = _run_step(driver, ctx, idx, step)
            step_results.append(sr)
            if not sr.ok:
                ok = False
                break

            # global success/fail early stop (optional)
            if case.fail and driver.wait_anchor(case.fail, assets_root=ctx.assets_root, timeout_sec=0.1):
                ok = False
                step_results.append(
                    StepResult(
                        name="__fail_anchor__",
                        action="wait_anchor",
                        ok=False,
                        started_at_ms=now_ms(),
                        ended_at_ms=now_ms(),
                        error="Fail anchor detected",
                    )
                )
                break
            if case.success and driver.wait_anchor(case.success, assets_root=ctx.assets_root, timeout_sec=0.1):
                ok = True
                break

            if (monotonic_ms() - start_mono) / 1000.0 > case.max_duration_sec:
                ok = False
                step_results.append(
                    StepResult(
                        name="__timeout__",
                        action="timeout",
                        ok=False,
                        started_at_ms=now_ms(),
                        ended_at_ms=now_ms(),
                        error=f"Case exceeded max_duration_sec={case.max_duration_sec}",
                    )
                )
                break
    except Exception as e:  # noqa: BLE001
        ok = False
        step_results.append(
            StepResult(
                name="__exception__",
                action="exception",
                ok=False,
                started_at_ms=now_ms(),
                ended_at_ms=now_ms(),
                error=repr(e),
            )
        )
    finally:
        artifacts = driver.collect_postmortem(out_dir)
        try:
            p = steps_dir / "999_end.png"
            driver.screenshot(p)
        except Exception:
            pass
        try:
            driver.stop()
        except Exception:
            pass

    ended_at = now_ms()
    return RunResult(
        run_id=run_id,
        platform=driver.platform,
        case_name=case.name,
        ok=ok,
        started_at_ms=started_at,
        ended_at_ms=ended_at,
        steps=step_results,
        artifacts=artifacts,
    )


def _default_popup_rules() -> list[PopupRule]:
    """
    Rules refer to optional template assets; if absent, handling will be skipped.
    Projects may add their own popup rules and template images through their adapter layer.
    """
    # Intentionally empty by default to avoid hard failures if assets don't exist.
    return []


def _run_step(driver: Driver, ctx: RunContext, idx: int, step: Step) -> StepResult:
    started = now_ms()
    artifacts: dict[str, str] = {}

    def snap(tag: str) -> None:
        p = ctx.steps_dir / f"{idx:03d}_{tag}.png"
        driver.screenshot(p)
        artifacts[tag] = str(p.relative_to(ctx.out_dir))

    attempt = 0
    last_err: str | None = None

    while True:
        attempt += 1
        try:
            if step.action in (StepAction.click, StepAction.tap):
                if not step.anchor:
                    raise ValueError("click/tap requires anchor")
                snap("before_click")
                driver.click_anchor(step.anchor, assets_root=ctx.assets_root)
                snap("after_click")
            elif step.action == StepAction.click_pos:
                if step.x is None or step.y is None:
                    raise ValueError("click_pos requires x and y")
                snap("before_click_pos")
                driver.click_xy(int(step.x), int(step.y))
                snap("after_click_pos")
            elif step.action == StepAction.drag:
                if step.x is None or step.y is None or step.x2 is None or step.y2 is None:
                    raise ValueError("drag requires x,y,x2,y2")
                dur = float(step.duration_sec or 0.5)
                snap("before_drag")
                driver.drag_xy(int(step.x), int(step.y), int(step.x2), int(step.y2), dur)
                snap("after_drag")
            elif step.action == StepAction.mouse_down:
                snap("before_mouse_down")
                driver.mouse_down(step.x, step.y)
                snap("after_mouse_down")
            elif step.action == StepAction.move_pos:
                if step.x is None or step.y is None:
                    raise ValueError("move_pos requires x and y")
                dur = float(step.duration_sec or 0.8)
                snap("before_move_pos")
                driver.move_xy(int(step.x), int(step.y), dur)
                snap("after_move_pos")
            elif step.action == StepAction.mouse_up:
                snap("before_mouse_up")
                driver.mouse_up()
                snap("after_mouse_up")
            elif step.action == StepAction.scroll:
                clicks = int(step.scroll or 0)
                if clicks == 0:
                    raise ValueError("scroll requires non-zero scroll value")
                snap("before_scroll")
                driver.scroll(clicks)
                snap("after_scroll")
            elif step.action == StepAction.scroll_until_anchor:
                if not step.anchor:
                    raise ValueError("scroll_until_anchor requires anchor")
                clicks = int(step.scroll or 0)
                if clicks == 0:
                    raise ValueError("scroll_until_anchor requires non-zero scroll value")
                max_scrolls = int(step.max_scrolls or 20)
                if max_scrolls <= 0:
                    raise ValueError("scroll_until_anchor requires max_scrolls > 0")
                # optionally move mouse to x,y first
                if step.x is not None and step.y is not None:
                    driver.move_xy(int(step.x), int(step.y), float(step.duration_sec or 0.2))

                snap("before_scroll_until")
                found = False
                for i in range(max_scrolls):
                    # quick probe before scrolling (handles case already visible)
                    if driver.wait_anchor(step.anchor, assets_root=ctx.assets_root, timeout_sec=0.1):
                        found = True
                        break
                    driver.scroll(clicks)
                    # small settle delay; UIs often update on next frame
                    driver.sleep(float(step.retry_interval_sec or 0.2))
                if not found and driver.wait_anchor(step.anchor, assets_root=ctx.assets_root, timeout_sec=0.2):
                    found = True
                snap("after_scroll_until")
                if not found:
                    raise TimeoutError(f"anchor not found after max_scrolls={max_scrolls}")
                # Click the anchor once found
                driver.click_anchor(step.anchor, assets_root=ctx.assets_root)
            elif step.action == StepAction.press:
                if not step.key:
                    raise ValueError("press requires key")
                driver.press(step.key)
            elif step.action == StepAction.wait_anchor:
                if not step.anchor:
                    raise ValueError("wait_anchor requires anchor")
                timeout = float(step.seconds or 10)
                found = driver.wait_anchor(step.anchor, assets_root=ctx.assets_root, timeout_sec=timeout)
                snap("wait_anchor")
                if not found:
                    raise TimeoutError(f"anchor not found within {timeout}s")
            elif step.action == StepAction.sleep:
                driver.sleep(float(step.seconds or 1))
            elif step.action == StepAction.screenshot:
                snap(step.meta.get("tag", "screenshot"))
            else:
                raise ValueError(f"Unknown action: {step.action}")

            ended = now_ms()
            return StepResult(
                name=step.name,
                action=step.action.value,
                ok=True,
                started_at_ms=started,
                ended_at_ms=ended,
                artifacts=artifacts,
            )
        except Exception as e:  # noqa: BLE001
            last_err = repr(e)
            if attempt > (step.retries + 1):
                ended = now_ms()
                return StepResult(
                    name=step.name,
                    action=step.action.value,
                    ok=False,
                    started_at_ms=started,
                    ended_at_ms=ended,
                    error=last_err,
                    artifacts=artifacts,
                )
            driver.sleep(step.retry_interval_sec)

