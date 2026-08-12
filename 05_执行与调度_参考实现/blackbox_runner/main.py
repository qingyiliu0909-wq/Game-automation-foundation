from __future__ import annotations

import argparse
import os
from pathlib import Path

from blackbox_runner.core.case_loader import load_case
from blackbox_runner.core.orchestrator import run_case
from blackbox_runner.core.report import JUnitTestCase, write_junit_xml, write_report_json
from blackbox_runner.core.timeutil import monotonic_ms
from blackbox_runner.platform.android_driver import AndroidDriver
from blackbox_runner.platform.win_driver import WindowsDriver


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--platform", choices=["win", "android"], required=True)
    p.add_argument("--case", required=True, help="Path to case yaml")
    p.add_argument("--results", default=str(_repo_root() / "results"))
    p.add_argument("--assets", default=str(Path(__file__).resolve().parent / "assets"))
    p.add_argument("--junit", action="store_true")

    # Windows
    p.add_argument("--exe", help="Game exe path (optional if you attach to existing window)")
    p.add_argument("--title", default="", help="Window title regex/substring for pywinauto attach")
    p.add_argument(
        "--artifact-source",
        action="append",
        default=[],
        help="Directory to collect when the run ends; may be specified more than once.",
    )

    # Android
    p.add_argument("--device", default="", help="adb serial")
    p.add_argument("--package", default="", help="Android package name (optional)")

    return p.parse_args()


def main() -> int:
    args = parse_args()
    case = load_case(args.case)

    results_root = Path(args.results)
    assets_root = Path(args.assets)

    if args.platform == "win":
        driver = WindowsDriver(
            exe_path=args.exe or None,
            title_hint=args.title or None,
            artifact_sources=[Path(p) for p in args.artifact_source],
        )
    else:
        driver = AndroidDriver(device_serial=args.device or None, package_name=args.package or None)

    t0 = monotonic_ms()
    result = run_case(driver, case=case, results_root=results_root, assets_root=assets_root)
    out_dir = results_root / result.run_id
    write_report_json(out_dir, result)

    if args.junit:
        dur = (monotonic_ms() - t0) / 1000.0
        tc = JUnitTestCase(
            name=case.name,
            classname=f"blackbox_runner.{args.platform}",
            time_sec=dur,
            ok=result.ok,
            message=None if result.ok else "failed",
        )
        write_junit_xml(out_dir, suite_name="game-blackbox-runner", cases=[tc])

    print(str(out_dir))
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

