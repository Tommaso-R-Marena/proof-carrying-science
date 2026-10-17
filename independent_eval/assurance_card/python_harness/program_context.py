"""Optional program-context digests (non-authority).

Attaches content digests of sibling independent-eval result summaries when the
caller supplies paths. Never runs verify; never elevates inspection to
authority; never invents missing files as PASS.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .hashing import sha256_file

# Preferred filenames under an --attach-results directory (first match wins).
PREFERRED_SUMMARY_NAMES: tuple[str, ...] = (
    "SUMMARY.json",
    "falsification_scorecard.json",
    "workstream_c_summary.json",
    "residual_trust.json",
    "interpreter_matrix.json",
    "aristotle_candidates.json",
)

PROGRAM_CONTEXT_DISCLAIMER = (
    "Program context digests are optional inspection-adjacent metadata. "
    "They are not authority, do not issue ACCEPT/PASS, and do not certify "
    "science, residual-trust closure, or merge readiness."
)


def _discover_files(path: Path) -> list[Path]:
    """Resolve a path to one or more digestable JSON/Markdown files."""
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    found: list[Path] = []
    for name in PREFERRED_SUMMARY_NAMES:
        candidate = path / name
        if candidate.is_file():
            found.append(candidate)
    # Also accept results/SUMMARY.json one level down (common layout).
    results_dir = path / "results"
    if results_dir.is_dir():
        for name in PREFERRED_SUMMARY_NAMES:
            candidate = results_dir / name
            if candidate.is_file() and candidate not in found:
                found.append(candidate)
    return found


def attach_program_context(
    attach_paths: list[str | Path] | None,
) -> dict[str, Any]:
    """Build a program_context block from caller-supplied paths.

    Missing paths are recorded as ABSENT (not PASS). Digests are SHA-256 of
    file bytes. No network, no verify, no mutation of authority lane.
    """
    entries: list[dict[str, Any]] = []
    warnings: list[str] = []

    for raw in attach_paths or []:
        path = Path(raw)
        resolved = str(path.resolve()) if path.exists() else str(path)
        if not path.exists():
            entries.append(
                {
                    "requested": str(raw),
                    "resolved": resolved,
                    "status": "ABSENT",
                    "files": [],
                }
            )
            warnings.append(f"attach path ABSENT: {raw}")
            continue

        files = _discover_files(path)
        if not files:
            entries.append(
                {
                    "requested": str(raw),
                    "resolved": str(path.resolve()),
                    "status": "ABSENT",
                    "files": [],
                    "reason": "no preferred summary files found",
                }
            )
            warnings.append(f"no preferred summary under {raw}")
            continue

        file_records = []
        for f in files:
            file_records.append(
                {
                    "path": str(f.resolve()),
                    "name": f.name,
                    "sha256": sha256_file(f),
                    "size_bytes": f.stat().st_size,
                }
            )
        entries.append(
            {
                "requested": str(raw),
                "resolved": str(path.resolve()),
                "status": "PRESENT",
                "files": file_records,
            }
        )

    present = sum(1 for e in entries if e.get("status") == "PRESENT")
    absent = sum(1 for e in entries if e.get("status") == "ABSENT")
    return {
        "format": "pcs-assurance-card-program-context-v1",
        "is_authority": False,
        "issues_accept": False,
        "disclaimer": PROGRAM_CONTEXT_DISCLAIMER,
        "entries": entries,
        "summary": {
            "requested": len(entries),
            "present": present,
            "absent": absent,
        },
        "warnings": warnings,
    }
