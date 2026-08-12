from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def ensure_dir(p: str | Path) -> Path:
    path = Path(p)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")

