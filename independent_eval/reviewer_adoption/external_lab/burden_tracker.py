"""Log manual external-lab configuration steps to JSONL.

Usage:
  python -m independent_eval.reviewer_adoption.external_lab.burden_tracker \\
    --package .../external_lab/package --log /tmp/burden.jsonl --list-steps

  python -m independent_eval.reviewer_adoption.external_lab.burden_tracker \\
    --package .../external_lab/package --log /tmp/burden.jsonl \\
    --step install_python --minutes 15 --notes "..."
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Canonical checklist — mirrors package docs; keep in sync with SETUP/WORKFLOW.
DEFAULT_STEPS: list[dict[str, str]] = [
    {
        "id": "read_setup",
        "title": "Read SETUP.md and confirm offline constraints",
        "doc": "SETUP.md",
    },
    {
        "id": "provision_python",
        "title": "Provision Python 3.11+ environment (lab-local)",
        "doc": "SETUP.md",
    },
    {
        "id": "locate_examples",
        "title": "Locate read-only example pointers (do not copy large trees)",
        "doc": "WORKFLOW.md",
    },
    {
        "id": "run_verify_docs",
        "title": "Follow VERIFY.md against a local evidence fixture",
        "doc": "VERIFY.md",
    },
    {
        "id": "attempt_repro",
        "title": "Attempt REPRO.md steps on lab hardware; record divergences",
        "doc": "REPRO.md",
    },
    {
        "id": "record_limitations",
        "title": "Document environment limitations per LIMITATIONS.md",
        "doc": "LIMITATIONS.md",
    },
    {
        "id": "troubleshoot",
        "title": "Apply TROUBLESHOOTING.md if blocked; log time spent",
        "doc": "TROUBLESHOOTING.md",
    },
    {
        "id": "judge_success_failure",
        "title": "Classify outcome using SUCCESS_FAILURE.md (no invented authority)",
        "doc": "SUCCESS_FAILURE.md",
    },
]


def load_steps(package_dir: Path) -> list[dict[str, str]]:
    """Load checklist from package/CHECKLIST.json if present, else defaults."""
    checklist = package_dir / "CHECKLIST.json"
    if checklist.is_file():
        data = json.loads(checklist.read_text(encoding="utf-8"))
        steps = data.get("steps") or []
        return [dict(s) for s in steps]
    return [dict(s) for s in DEFAULT_STEPS]


def list_steps(package_dir: Path) -> str:
    steps = load_steps(package_dir)
    lines = ["External-lab configuration checklist (manual burden):", ""]
    for i, step in enumerate(steps, start=1):
        lines.append(f"  {i}. [{step.get('id')}] {step.get('title')}  (doc: {step.get('doc')})")
    lines.append("")
    lines.append("Log a completed step with --step <id> --minutes N [--notes TEXT]")
    return "\n".join(lines)


def append_log(
    log_path: Path,
    *,
    step_id: str,
    minutes: float | None,
    notes: str | None,
    package_dir: Path,
) -> dict[str, Any]:
    steps = {s["id"]: s for s in load_steps(package_dir)}
    known = step_id in steps
    record = {
        "schema": "pcs.independent_eval.external_lab.burden_log.v1",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "step_id": step_id,
        "step_known": known,
        "step_title": (steps.get(step_id) or {}).get("title"),
        "minutes": minutes,
        "notes": notes,
        "package_dir": str(package_dir),
        "completed_external_lab_validation": False,
        "note": (
            "Burden log entry only. Does not claim completed external-lab validation "
            "or PCS ACCEPT/PASS."
        ),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Track manual config burden for the external-lab challenge kit."
    )
    parser.add_argument(
        "--package",
        required=True,
        help="Path to external_lab/package directory",
    )
    parser.add_argument(
        "--log",
        required=True,
        help="JSONL log path for burden entries",
    )
    parser.add_argument(
        "--list-steps",
        action="store_true",
        help="Print the configuration checklist and exit",
    )
    parser.add_argument("--step", help="Checklist step id to log as completed/attempted")
    parser.add_argument("--minutes", type=float, help="Minutes spent on the step")
    parser.add_argument("--notes", default=None, help="Free-text notes")
    args = parser.parse_args(argv)

    package_dir = Path(args.package)
    if not package_dir.is_dir():
        print(f"package directory not found: {package_dir}", file=sys.stderr)
        return 2

    if args.list_steps:
        print(list_steps(package_dir))
        return 0

    if not args.step:
        print("provide --list-steps or --step <id>", file=sys.stderr)
        return 2

    record = append_log(
        Path(args.log),
        step_id=args.step,
        minutes=args.minutes,
        notes=args.notes,
        package_dir=package_dir,
    )
    print(json.dumps(record, indent=2, sort_keys=True))
    print(f"appended {args.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
