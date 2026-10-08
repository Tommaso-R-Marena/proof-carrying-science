from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.public_release_history_audit import matches_in_text, scan


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)


def test_secret_patterns_are_redacted():
    key = b"-----BEGIN " + b"PRIVATE KEY-----\n" + b"not-a-real-key"
    assert "private_key_header" in matches_in_text(key)
    assert matches_in_text(b"ordinary source with no sensitive tokens") == []


def test_full_history_sees_deleted_secret_without_emitting_value(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "PCS Tests")
    secret = "ghp_" + "Q" * 36
    (root / "hidden.txt").write_text(secret)
    _git(root, "add", ".")
    _git(root, "commit", "-m", "test fixture")
    (root / "hidden.txt").unlink()
    _git(root, "add", "-u")
    _git(root, "commit", "-m", "remove fixture")
    report = scan(root)
    assert not report["release_approved"]
    assert not report["preflight_pass"]
    assert any("github_legacy_token" in f["reason"] for f in report["suspected_findings"])
    assert secret not in str(report)
    assert report["reachable_git_objects"] > 0


def test_clean_repository_preflight_is_not_release_approval(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "PCS Tests")
    (root / "readme.txt").write_text("Publicly shareable synthetic example.\n")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "clean")
    report = scan(root)
    assert report["preflight_pass"]
    assert report["candidate_count"] == 0
    assert report["release_approved"] is False
