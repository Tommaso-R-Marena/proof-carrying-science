"""Optional bridge to Workstream F Assurance Card (discover + subprocess).

This module never vendors Assurance Card code. When the sibling tree
``independent_eval/assurance_card`` is PRESENT in the working tree (or
``PCS_ASSURANCE_CARD_ROOT``), it runs F's offline card CLI as a subprocess.
When ABSENT, it records ABSENT and exits without inventing a card or PASS.

Never issues ACCEPT/PASS. Inspection/workbench remains non-authority.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BRIDGE_DISCLAIMER = (
    "Workstream D export_assurance_card is a discover-and-subprocess bridge only. "
    "It does not vendor Assurance Card logic, does not issue ACCEPT/PASS, and does "
    "not certify science. ABSENT sibling trees are recorded as ABSENT, not PASS."
)

# Exit codes: 0 = card exported; 3 = sibling ABSENT (honest non-success, not a crash);
# 2 = usage / invocation error after sibling was PRESENT.
EXIT_OK = 0
EXIT_ERROR = 2
EXIT_ABSENT = 3


def _repo_root() -> Path:
    # reviewer_adoption/workbench/this_file → parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def discover_assurance_card_root(
    explicit: str | Path | None = None,
) -> dict[str, Any]:
    """Locate Workstream F package root. ABSENT ≠ PASS."""
    # An explicit or environment-pinned component is authoritative for discovery.
    # A missing pin must remain ABSENT even when another sibling is installed.
    env = os.environ.get("PCS_ASSURANCE_CARD_ROOT")
    if explicit is not None:
        candidates = [Path(explicit)]
    elif env:
        candidates = [Path(env)]
    else:
        candidates = [_repo_root() / "independent_eval" / "assurance_card"]

    tried: list[str] = []
    for cand in candidates:
        tried.append(str(cand))
        card_mod = cand / "python_harness" / "card.py"
        if cand.is_dir() and card_mod.is_file():
            return {
                "status": "PRESENT",
                "root": str(cand.resolve()),
                "card_module": str(card_mod.resolve()),
                "tried": tried,
                "disclaimer": BRIDGE_DISCLAIMER,
            }
    return {
        "status": "ABSENT",
        "root": None,
        "card_module": None,
        "tried": tried,
        "disclaimer": BRIDGE_DISCLAIMER,
        "reason": (
            "Workstream F assurance_card not found in working tree. "
            "Checkout feature/independent-eval-assurance-card-c8bb or set "
            "PCS_ASSURANCE_CARD_ROOT / --assurance-card-root."
        ),
    }


def run_assurance_card_export(
    *,
    evidence: str | Path,
    out: str | Path,
    fmt: str = "both",
    skip_verify: bool = False,
    generated_at: str | None = None,
    attach_results: list[str] | None = None,
    assurance_card_root: str | Path | None = None,
    runner: Any | None = None,
) -> dict[str, Any]:
    """Discover F and subprocess-export a card. Never invents PASS on ABSENT."""
    discovery = discover_assurance_card_root(assurance_card_root)
    record: dict[str, Any] = {
        "format": "pcs-reviewer-adoption-assurance-card-bridge-v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workbench_issues_accept": False,
        "bridge_is_not_authority": True,
        "disclaimer": BRIDGE_DISCLAIMER,
        "discovery": discovery,
        "evidence": str(evidence),
        "out": str(out),
        "card_format_requested": fmt,
    }

    if discovery["status"] != "PRESENT":
        record["export_status"] = "ABSENT"
        record["returncode"] = None
        record["ok"] = False
        return record

    root = Path(discovery["root"])
    # F's CLI cwd is the assurance_card root — pass absolute paths so caller
    # evidence (often under reviewer_adoption/) resolves correctly.
    evidence_abs = str(Path(evidence).resolve())
    out_abs = str(Path(out).resolve())
    record["evidence"] = evidence_abs
    record["out"] = out_abs
    argv = [
        sys.executable,
        "-m",
        "python_harness.card",
        "--evidence",
        evidence_abs,
        "--out",
        out_abs,
        "--format",
        fmt,
    ]
    if skip_verify:
        argv.append("--skip-verify")
    if generated_at:
        argv.extend(["--generated-at", generated_at])
    for path in attach_results or []:
        argv.extend(["--attach-results", str(Path(path).resolve())])

    env = os.environ.copy()
    # Prefer F's package on PYTHONPATH without mutating caller site-packages.
    prior = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(root) + (os.pathsep + prior if prior else "")

    run = runner or subprocess.run
    try:
        proc = run(
            argv,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        record["export_status"] = "ERROR"
        record["ok"] = False
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["argv"] = argv
        return record

    record["argv"] = argv
    record["returncode"] = getattr(proc, "returncode", None)
    record["stdout_tail"] = (getattr(proc, "stdout", None) or "")[-4000:]
    record["stderr_tail"] = (getattr(proc, "stderr", None) or "")[-4000:]
    record["ok"] = record["returncode"] == 0
    record["export_status"] = "EXPORTED" if record["ok"] else "ERROR"
    return record


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m independent_eval.reviewer_adoption.workbench.export_assurance_card",
        description=(
            "Discover Workstream F Assurance Card and export via subprocess. "
            "ABSENT sibling → exit 3 (not PASS)."
        ),
    )
    p.add_argument("--evidence", required=True, help="Evidence dir or certificate path")
    p.add_argument("--out", required=True, help="Output stem for card JSON/HTML")
    p.add_argument("--format", choices=("html", "json", "both"), default="both")
    p.add_argument("--skip-verify", action="store_true")
    p.add_argument("--generated-at", default=None, help="Optional fixed UTC stamp")
    p.add_argument(
        "--attach-results",
        action="append",
        default=[],
        help="Forwarded to F --attach-results (repeatable)",
    )
    p.add_argument(
        "--assurance-card-root",
        default=None,
        help="Explicit path to independent_eval/assurance_card (or set env)",
    )
    p.add_argument(
        "--bridge-record",
        default=None,
        help="Optional path to write bridge JSON record",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    record = run_assurance_card_export(
        evidence=args.evidence,
        out=args.out,
        fmt=args.format,
        skip_verify=bool(args.skip_verify),
        generated_at=args.generated_at,
        attach_results=list(args.attach_results or []),
        assurance_card_root=args.assurance_card_root,
    )
    if args.bridge_record:
        path = Path(args.bridge_record)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"WROTE_BRIDGE_RECORD {path}")

    status = record.get("export_status")
    print(
        f"BRIDGE_STATUS {status} discovery={record['discovery']['status']} "
        f"workbench_issues_accept=false"
    )
    if status == "ABSENT":
        print(record["discovery"].get("reason") or "assurance_card ABSENT")
        return EXIT_ABSENT
    if status == "EXPORTED":
        print(record.get("stdout_tail") or "")
        return EXIT_OK
    print(record.get("stderr_tail") or record.get("error") or "export error", file=sys.stderr)
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
