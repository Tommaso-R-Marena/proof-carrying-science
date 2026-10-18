"""Actual Git inputs: no substituted audit outcomes."""
from pathlib import Path
import subprocess

from python_harness.nonoverlap_auditor import audit_branch_nonoverlap
from python_harness.preflight import run_preflight
from python_harness import paths


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def test_requested_base_is_the_actual_diff_base(tmp_path):
    git(tmp_path, "init", "-b", "fixture")
    git(tmp_path, "config", "user.name", "Local regression fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    (tmp_path / "first").write_text("base\n")
    git(tmp_path, "add", "first")
    git(tmp_path, "commit", "-m", "base")
    base = git(tmp_path, "rev-parse", "HEAD")
    git(tmp_path, "checkout", "-b", "feature")
    (tmp_path / "second").write_text("feature\n")
    git(tmp_path, "add", "second")
    git(tmp_path, "commit", "-m", "feature")
    result = audit_branch_nonoverlap(("feature",), repo=tmp_path, base=base)
    assert not result.errors
    assert result.changed_files == {"feature": ("second",)}
    same = audit_branch_nonoverlap(("feature",), repo=tmp_path, base="feature")
    assert not same.errors and same.changed_files == {"feature": ()}


def test_missing_branch_is_inconclusive_not_success(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "RESULTS", tmp_path / "results")
    report = run_preflight(check_collisions=False, check_residual_trust=False,
                           branches=("pcs-regression-definitely-absent-branch",))
    assert report["conclusive"] is False
    assert report["pass"] is False
    assert report["gates"]["branch_nonoverlap"]["pass"] is False


def test_empty_requested_branch_inventory_is_inconclusive(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "RESULTS", tmp_path / "results")
    report = run_preflight(check_collisions=False, check_residual_trust=False,
                           branches=())
    assert report["conclusive"] is False and report["pass"] is False
