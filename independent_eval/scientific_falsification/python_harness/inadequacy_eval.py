"""Task 8 — Run inadequacy examples: computational PASS without empirical adequacy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .pcs_cli import certify, verify_certificate


def evaluate_inadequacy_example(project: Path, work: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    out = work / "evidence"
    cert_res = certify(project / "manifest.json", out)
    verify_res = None
    claim_statuses: list[str] = []
    if cert_res.ok and (out / "certificate.json").is_file():
        verify_res = verify_certificate(out / "certificate.json")
        cert = json.loads((out / "certificate.json").read_text(encoding="utf-8"))
        claim_statuses = [
            c.get("assessment", {}).get("status", "UNKNOWN") for c in cert.get("claims", [])
        ]
    computational_pass = bool(
        cert_res.ok
        and verify_res is not None
        and verify_res.ok
        and claim_statuses
        and all(s == "COMPUTATIONALLY_SUPPORTED" for s in claim_statuses)
    )
    return {
        "project": project.name,
        "certify_ok": cert_res.ok,
        "verify_ok": None if verify_res is None else verify_res.ok,
        "claim_statuses": claim_statuses,
        "computational_pass": computational_pass,
        # Explicit non-claim: verification never establishes empirical adequacy.
        "empirical_adequacy_established": False,
        "thesis_held": computational_pass,
        "stdout_tail": cert_res.stdout[-400:],
        "stderr_tail": cert_res.stderr[-400:],
    }


def run_inadequacy_suite(examples_root: Path, work_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for project in sorted(p for p in examples_root.iterdir() if p.is_dir()):
        if not (project / "manifest.json").is_file():
            continue
        rows.append(evaluate_inadequacy_example(project, work_root / project.name))
    return {
        "format": "pcs-independent-eval-inadequacy-report-v1",
        "example_count": len(rows),
        "computational_pass_count": sum(1 for r in rows if r["computational_pass"]),
        "empirical_adequacy_established_count": sum(
            1 for r in rows if r["empirical_adequacy_established"]
        ),
        "examples": rows,
        "note": (
            "All examples are designed so PCS may verify the declared computational "
            "claim while empirical/scientific adequacy remains OPEN."
        ),
    }
