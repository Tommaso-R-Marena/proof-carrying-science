"""Workflow discovery evaluation (Task 10) — read-only vs `pcs discover-v06`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .pcs_cli import discover_v06, load_json


def selected_check_types(discovery_report: dict[str, Any]) -> set[str]:
    types: set[str] = set()
    # Prefer manifest draft selected checks.
    draft = discovery_report.get("manifest_draft") or discovery_report.get("draft")
    if isinstance(draft, dict):
        for check in draft.get("checks", []):
            if isinstance(check, dict) and check.get("type"):
                types.add(str(check["type"]))
    # Also inspect recommendations above threshold if embedded.
    for rec in discovery_report.get("recommendations", []):
        check = rec.get("check") if isinstance(rec, dict) else None
        if isinstance(check, dict) and check.get("type"):
            # Only count if selected into draft when draft present.
            if draft is None:
                types.add(str(check["type"]))
    return types


def evaluate_project(
    project: Path,
    *,
    expected_types: list[str],
    abstain: bool,
    work: Path,
    minimum_confidence: float = 0.95,
) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    draft_path = work / "pcs-manifest.draft.json"
    report_path = work / "pcs-discovery.json"
    result = discover_v06(
        project,
        output=draft_path,
        report=report_path,
        minimum_confidence=minimum_confidence,
        force=True,
    )
    out: dict[str, Any] = {
        "project": project.name,
        "cli_ok": result.ok,
        "argv": result.argv,
        "stdout_tail": result.stdout[-500:],
        "stderr_tail": result.stderr[-500:],
    }
    if not result.ok:
        out["error"] = "discover-v06 failed"
        out["precision"] = None
        out["recall"] = None
        out["abstention_correct"] = None
        return out

    report = load_json(report_path) if report_path.is_file() else {}
    if draft_path.is_file():
        draft = load_json(draft_path)
        report = {**report, "manifest_draft": draft}

    predicted = selected_check_types(report)
    expected = set(expected_types)

    tp = len(predicted & expected)
    fp = len(predicted - expected)
    fn = len(expected - predicted)
    precision = tp / (tp + fp) if (tp + fp) else (1.0 if not expected and not predicted else 0.0)
    recall = tp / (tp + fn) if (tp + fn) else (1.0 if not expected else 0.0)

    # Abstention: no selected checks when ground truth says abstain.
    did_abstain = len(predicted) == 0
    if abstain:
        abstention_correct: bool | None = did_abstain
    else:
        # Non-abstain projects: abstention is incorrect if we expected checks.
        abstention_correct = (not did_abstain) if expected else True

    out.update(
        {
            "predicted_check_types": sorted(predicted),
            "expected_check_types": sorted(expected),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "did_abstain": did_abstain,
            "abstain_expected": abstain,
            "abstention_correct": abstention_correct,
        }
    )
    return out


def run_discovery_benchmark(
    projects_root: Path,
    ground_truth_path: Path,
    work_root: Path,
) -> dict[str, Any]:
    gt = load_json(ground_truth_path)
    rows: list[dict[str, Any]] = []
    for name, spec in gt["projects"].items():
        project = projects_root / name
        row = evaluate_project(
            project,
            expected_types=list(spec.get("expected_check_types", [])),
            abstain=bool(spec.get("abstain", False)),
            work=work_root / name,
            minimum_confidence=float(gt.get("minimum_confidence", 0.95)),
        )
        rows.append(row)

    usable = [r for r in rows if r.get("precision") is not None]
    macro_p = sum(r["precision"] for r in usable) / len(usable) if usable else 0.0
    macro_r = sum(r["recall"] for r in usable) / len(usable) if usable else 0.0
    abstain_rows = [r for r in rows if r.get("abstain_expected")]
    abstain_acc = (
        sum(1 for r in abstain_rows if r.get("abstention_correct")) / len(abstain_rows)
        if abstain_rows
        else None
    )

    return {
        "format": "pcs-independent-eval-discovery-benchmark-v1",
        "detector": "pcs discover-v06",
        "projects": rows,
        "macro_precision": macro_p,
        "macro_recall": macro_r,
        "abstention_accuracy": abstain_acc,
        "project_count": len(rows),
        "cli_success_count": sum(1 for r in rows if r.get("cli_ok")),
    }


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
