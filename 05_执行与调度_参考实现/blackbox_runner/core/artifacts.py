from __future__ import annotations

import shutil
from pathlib import Path

from blackbox_runner.core.io import ensure_dir


def copy_tree_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    ensure_dir(dst.parent)
    if dst.exists():
        # merge by copying children
        for child in src.iterdir():
            target = dst / child.name
            if child.is_dir():
                shutil.copytree(child, target, dirs_exist_ok=True)
            else:
                ensure_dir(target.parent)
                shutil.copy2(child, target)
        return True
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return True

