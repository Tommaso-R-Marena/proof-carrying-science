"""Tests for independent protocol/adversarial evaluation (Workstream A)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
HARNESS = ROOT / "python_harness"
sys.path.insert(0, str(ROOT))

AUTHORITY = REPO / "formal" / ".lake" / "build" / "bin" / "pcs-lean-authority"


def _require_authority_for_corpus() -> None:
    if AUTHORITY.is_file() and os.access(AUTHORITY, os.X_OK):
        return
    pytest.skip("pcs-lean-authority required for corpus generation/verification attempts")


def test_rust_jcs_unit_tests():
    if shutil.which("cargo") is None:
        pytest.skip("cargo unavailable")
    proc = subprocess.run(
        ["cargo", "test"],
        cwd=ROOT / "rust_jcs_ref",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_jcs_differential_runs(tmp_path):
    if shutil.which("cargo") is None:
        pytest.skip("cargo unavailable")
    from python_harness.jcs_differential import run_differential
    from python_harness import paths as p

    # redirect results
    p.RESULTS = tmp_path / "results"
    report = run_differential(tmp_path / "results" / "jcs_differential.json")
    assert report["vector_count"] >= 10
    assert (tmp_path / "results" / "jcs_differential.json").is_file()


def test_zip_differential_runs(tmp_path):
    from python_harness.zip_differential import run_zip_differential
    from python_harness import paths as p

    p.RESULTS = tmp_path / "results"
    report = run_zip_differential(tmp_path / "zipwork")
    assert report["case_count"] >= 8


def test_resource_bounds_bounded(tmp_path):
    from python_harness.resource_bounds import run_resource_bounds
    from python_harness import paths as p

    p.RESULTS = tmp_path / "results"
    report = run_resource_bounds(tmp_path / "res")
    assert report["measurement_count"] >= 6
    assert report["limits"]["max_object_keys"] == 5000


def test_policy_confusion_same_validity(tmp_path):
    _require_authority_for_corpus()
    from python_harness.policy_confusion import run_policy_confusion
    from python_harness import paths as p

    p.RESULTS = tmp_path / "results"
    report = run_policy_confusion(tmp_path / "policy")
    assert report["pcs_valid"] is True
    assert len(report["reviewers"]) == 2
    assert report["reviewers"][0]["pcs_valid"] == report["reviewers"][1]["pcs_valid"]
    assert report["reviewers"][0]["unsafe_scientific_acceptance_inference"] is False
    assert report["reviewers"][1]["unsafe_scientific_acceptance_inference"] is True


def test_adversarial_corpus_at_least_100_with_attempted_verify(tmp_path):
    _require_authority_for_corpus()
    from python_harness.adversarial_corpus import generate_corpus
    from python_harness import paths as p

    p.RESULTS = tmp_path / "results"
    p.FIXTURES = tmp_path / "fixtures"
    summary = generate_corpus(tmp_path / "fixtures" / "adversarial" / "corpus")
    assert summary["case_count"] >= 100
    attempted = sum(1 for c in summary["cases"] if c["verification"].get("attempted"))
    assert attempted >= 100
    assert summary["positive_accepted"] >= 1
    # Negatives must be rejected after attempted verify (not merely unconstructed)
    assert summary["negatives_rejected_after_attempted_verify"] >= 80
    # Any false accept is a recorded defect; fail the eval suite.
    assert summary["false_accepts"] == [], summary["false_accepts"]


def test_intake_chronology_distinguishes_frozen_at(tmp_path):
    _require_authority_for_corpus()
    from python_harness.intake_chronology import run_intake_chronology
    from python_harness import paths as p

    p.RESULTS = tmp_path / "results"
    report = run_intake_chronology(tmp_path / "intake")
    assert report["scenario_count"] >= 2
    assert report["pass"] is True
    ids = {s["id"] for s in report["scenarios"]}
    assert "forged_frozen_at_still_hash_valid" in ids
    assert "substituted_intake_new_hash" in ids
    forged = next(s for s in report["scenarios"] if s["id"] == "forged_frozen_at_still_hash_valid")
    assert forged["intake_semantic_hash_unchanged"] is True
