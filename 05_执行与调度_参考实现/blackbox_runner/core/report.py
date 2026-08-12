from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from blackbox_runner.core.io import ensure_dir
from blackbox_runner.core.types import RunResult


def write_report_json(out_dir: Path, result: RunResult) -> Path:
    ensure_dir(out_dir)
    p = out_dir / "report.json"
    p.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return p


@dataclass(frozen=True)
class JUnitTestCase:
    name: str
    classname: str
    time_sec: float
    ok: bool
    message: str | None = None


def write_junit_xml(out_dir: Path, suite_name: str, cases: Iterable[JUnitTestCase]) -> Path:
    """
    Minimal JUnit XML (no external deps).
    """
    import xml.etree.ElementTree as ET

    ensure_dir(out_dir)
    p = out_dir / "junit.xml"

    cases_list = list(cases)
    total = len(cases_list)
    failures = sum(0 if c.ok else 1 for c in cases_list)
    time_total = sum(c.time_sec for c in cases_list)

    testsuite = ET.Element(
        "testsuite",
        {
            "name": suite_name,
            "tests": str(total),
            "failures": str(failures),
            "errors": "0",
            "time": f"{time_total:.3f}",
        },
    )

    for c in cases_list:
        tc = ET.SubElement(
            testsuite,
            "testcase",
            {"name": c.name, "classname": c.classname, "time": f"{c.time_sec:.3f}"},
        )
        if not c.ok:
            failure = ET.SubElement(tc, "failure", {"message": c.message or "failed"})
            failure.text = c.message or "failed"

    tree = ET.ElementTree(testsuite)
    tree.write(p, encoding="utf-8", xml_declaration=True)
    return p

