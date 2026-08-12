from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from blackbox_runner.core.types import Case


def load_case(case_path: str) -> Case:
    p = Path(case_path)
    raw: Any = yaml.safe_load(p.read_text(encoding="utf-8"))
    return Case.model_validate(raw)

