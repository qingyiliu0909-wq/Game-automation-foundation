from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    win = "win"
    android = "android"


class AnchorKind(str, Enum):
    image = "image"  # template image match on screenshot
    android_uia = "android_uia"  # uiautomator2 selector


class ImageAnchor(BaseModel):
    kind: Literal["image"] = "image"
    asset: str = Field(..., description="Path to a template image below the configured assets directory (or absolute).")
    threshold: float = Field(0.85, ge=0.0, le=1.0)


class AndroidUiaAnchor(BaseModel):
    kind: Literal["android_uia"] = "android_uia"
    # Keep it simple: allow either resource-id or text (or both)
    resource_id: Optional[str] = None
    text: Optional[str] = None
    description: Optional[str] = None


Anchor = ImageAnchor | AndroidUiaAnchor


class StepAction(str, Enum):
    click = "click"
    tap = "tap"  # alias of click, mainly for android mental model
    click_pos = "click_pos"  # click on absolute screen coordinates (x,y)
    drag = "drag"  # drag from (x1,y1) to (x2,y2)
    mouse_down = "mouse_down"  # press and hold left mouse button (optionally at x,y)
    move_pos = "move_pos"  # move mouse cursor to x,y (no click)
    mouse_up = "mouse_up"  # release left mouse button
    scroll = "scroll"  # mouse wheel scroll (positive up, negative down)
    scroll_until_anchor = "scroll_until_anchor"  # scroll repeatedly until anchor appears, then click it
    press = "press"
    wait_anchor = "wait_anchor"
    sleep = "sleep"
    screenshot = "screenshot"


class Step(BaseModel):
    name: str
    action: StepAction
    anchor: Optional[Anchor] = None
    x: Optional[int] = None  # for click_pos
    y: Optional[int] = None  # for click_pos
    x2: Optional[int] = None  # for drag
    y2: Optional[int] = None  # for drag
    duration_sec: Optional[float] = None  # for drag
    scroll: Optional[int] = None  # for scroll (wheel "clicks")
    max_scrolls: Optional[int] = None  # for scroll_until_anchor
    key: Optional[str] = None  # for press
    seconds: Optional[float] = None  # for sleep / wait timeout
    retries: int = 0
    retry_interval_sec: float = 1.0
    meta: dict[str, Any] = Field(default_factory=dict)


class Case(BaseModel):
    name: str
    version: int = 1
    # Optional common anchors for success/fail
    success: Optional[Anchor] = None
    fail: Optional[Anchor] = None
    max_duration_sec: int = 1800
    steps: list[Step]


class StepResult(BaseModel):
    name: str
    action: str
    ok: bool
    started_at_ms: int
    ended_at_ms: int
    error: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)  # logical name -> relative path


class RunResult(BaseModel):
    run_id: str
    platform: str
    case_name: str
    ok: bool
    started_at_ms: int
    ended_at_ms: int
    steps: list[StepResult]
    artifacts: dict[str, str] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)

