"""Program inventory aggregator.

Reads sibling report files **if present** in the working tree under the four
known workstream prefixes. Missing files are recorded as ``MISSING`` — this
module never invents test counts or findings from absent reports.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


# Optional: extract an explicit collected-tests line when a sibling inventory
# uses the common "Collected tests: N" pattern. Never invent when absent.
# Matches both `Collected tests: 12` and markdown `**Collected tests:** 12`.
_COLLECTED_RE = re.compile(r"(?im)Collected tests[^\d\n]*(\d+)")


@dataclass(frozen=True)
class ReportPresence:
    path: str
    status: str  # PRESENT | MISSING
    bytes: int | None = None
    collected_tests: int | None = None
    note: str | None = None

    def to_dict(self) -> dict:
        out: dict = {"path": self.path, "status": self.status}
        if self.bytes is not None:
            out["bytes"] = self.bytes
        if self.collected_tests is not None:
            out["collected_tests"] = self.collected_tests
        if self.note is not None:
            out["note"] = self.note
        return out


@dataclass(frozen=True)
class WorkstreamInventory:
    prefix: str
    prefix_present: bool
    reports: tuple[ReportPresence, ...]

    def to_dict(self) -> dict:
        return {
            "prefix": self.prefix,
            "prefix_present": self.prefix_present,
            "reports": [r.to_dict() for r in self.reports],
        }


@dataclass(frozen=True)
class InventoryReport:
    format: str
    repo: str
    workstreams: tuple[WorkstreamInventory, ...]

    def to_dict(self) -> dict:
        present = sum(1 for w in self.workstreams if w.prefix_present)
        return {
            "format": self.format,
            "repo": self.repo,
            "workstream_count": len(self.workstreams),
            "prefixes_present": present,
            "prefixes_missing": len(self.workstreams) - present,
            "workstreams": [w.to_dict() for w in self.workstreams],
            "disclaimer": (
                "Counts and findings are only recorded when sibling report files "
                "are present in this working tree. MISSING means absent — not zero."
            ),
        }


def _probe_report(repo: Path, rel_path: str) -> ReportPresence:
    path = repo / rel_path
    if not path.is_file():
        return ReportPresence(path=rel_path, status="MISSING")
    text = path.read_text(encoding="utf-8", errors="replace")
    collected: int | None = None
    note: str | None = None
    if path.name == "TEST_INVENTORY.md":
        match = _COLLECTED_RE.search(text)
        if match:
            collected = int(match.group(1))
        else:
            note = "PRESENT but no 'Collected tests: N' line found; count not invented"
    return ReportPresence(
        path=rel_path,
        status="PRESENT",
        bytes=path.stat().st_size,
        collected_tests=collected,
        note=note,
    )


def aggregate_inventory(
    *,
    repo: Path | str,
    prefixes: Sequence[str],
    report_names: Sequence[str],
) -> InventoryReport:
    """Aggregate presence of known report files under sibling prefixes."""
    repo_path = Path(repo).resolve()
    workstreams: list[WorkstreamInventory] = []
    for prefix in prefixes:
        prefix_path = repo_path / prefix
        prefix_present = prefix_path.is_dir()
        reports = tuple(
            _probe_report(repo_path, f"{prefix}/{name}") for name in report_names
        )
        # If the prefix directory itself is missing, keep report statuses MISSING
        # but annotate via prefix_present=False.
        workstreams.append(
            WorkstreamInventory(
                prefix=prefix,
                prefix_present=prefix_present,
                reports=reports,
            )
        )
    return InventoryReport(
        format="pcs-independent-program-inventory-v1",
        repo=str(repo_path),
        workstreams=tuple(workstreams),
    )


def write_inventory_report(report: InventoryReport, out_path: Path | str) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def render_inventory_markdown(report: InventoryReport) -> str:
    """Human-readable inventory table (does not invent absent counts)."""
    lines = [
        "# Program inventory (aggregated)",
        "",
        f"Format: `{report.format}`",
        "",
        report.to_dict()["disclaimer"],
        "",
        "| Workstream prefix | Prefix | Report | Status | Collected tests |",
        "| --- | --- | --- | --- | --- |",
    ]
    for ws in report.workstreams:
        prefix_flag = "PRESENT" if ws.prefix_present else "MISSING"
        for r in ws.reports:
            name = Path(r.path).name
            collected = (
                str(r.collected_tests)
                if r.collected_tests is not None
                else ("—" if r.status == "PRESENT" else "MISSING")
            )
            lines.append(
                f"| `{ws.prefix}` | {prefix_flag} | `{name}` | {r.status} | {collected} |"
            )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    from .paths import INVENTORY_REPORT_NAMES, REPO_ROOT, RESULTS, SIBLING_PREFIXES

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--out",
        type=Path,
        default=RESULTS / "program_inventory.json",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=RESULTS / "program_inventory.md",
    )
    args = parser.parse_args(argv)

    report = aggregate_inventory(
        repo=args.repo,
        prefixes=SIBLING_PREFIXES,
        report_names=INVENTORY_REPORT_NAMES,
    )
    write_inventory_report(report, args.out)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.write_text(render_inventory_markdown(report), encoding="utf-8")
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
