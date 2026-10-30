"""Tests for the case-insensitive path collision scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from python_harness.collision_scanner import scan_path_collisions, write_collision_report


def test_no_collision_on_distinct_names(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "CHECKLIST.json").write_text("{}", encoding="utf-8")
    (tmp_path / "a" / "README.md").write_text("ok", encoding="utf-8")
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "checklist.json").write_text("{}", encoding="utf-8")

    report = scan_path_collisions(tmp_path)
    assert report.file_count == 3
    assert not report.has_collisions
    assert report.collision_groups == ()


def test_detects_checklist_case_collision(tmp_path: Path) -> None:
    """Reproduce the Workstream D class of bug: CHECKLIST.json vs checklist.json."""
    pkg = tmp_path / "external_lab" / "package"
    pkg.mkdir(parents=True)
    # On a case-sensitive FS both names can coexist; that is exactly the hazard.
    upper = pkg / "CHECKLIST.json"
    lower = pkg / "checklist.json"
    upper.write_text('{"schema":"upper"}', encoding="utf-8")
    # If the platform collapsed the names, skip — scanner still works on distinct trees.
    if lower.exists() and lower.resolve() == upper.resolve():
        pytest.skip("filesystem is case-insensitive; cannot create dual names")
    lower.write_text('{"schema":"lower"}', encoding="utf-8")

    report = scan_path_collisions(tmp_path)
    assert report.has_collisions
    assert len(report.collision_groups) == 1
    group = report.collision_groups[0]
    assert group.collision_count == 2
    assert "CHECKLIST.json" in " ".join(group.paths)
    assert "checklist.json" in " ".join(group.paths)


def test_detects_directory_component_case_collision(tmp_path: Path) -> None:
    """Colliding relative paths that differ only in a directory letter case."""
    # Create two files with relative paths that casefold equal.
    # On Linux we can create Foo/x and foo/y as distinct dirs; collision is
    # only reported when the *full relative path* casefolds equal, so we
    # still use same-dir filename collision for the primary assertion, and
    # additionally plant a synthetic pair via nested identical leaf names
    # under dirs that differ only by case when possible.
    d1 = tmp_path / "Dir"
    d2 = tmp_path / "dir"
    d1.mkdir()
    try:
        d2.mkdir()
    except FileExistsError:
        pytest.skip("filesystem is case-insensitive; cannot create Dir vs dir")
    (d1 / "note.txt").write_text("a", encoding="utf-8")
    (d2 / "NOTE.txt").write_text("b", encoding="utf-8")
    # Dir/note.txt vs dir/NOTE.txt — casefold keys equal.
    report = scan_path_collisions(tmp_path)
    assert report.has_collisions
    keys = {g.key for g in report.collision_groups}
    assert any(k.endswith("note.txt") for k in keys)


def test_write_collision_report_roundtrip(tmp_path: Path) -> None:
    (tmp_path / "only.txt").write_text("x", encoding="utf-8")
    report = scan_path_collisions(tmp_path)
    out = tmp_path / "out" / "report.json"
    write_collision_report(report, out)
    text = out.read_text(encoding="utf-8")
    assert "pcs-independent-path-collision-scan-v1" in text
    assert '"has_collisions": false' in text


def test_skips_pycache(tmp_path: Path) -> None:
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "mod.cpython-312.pyc").write_bytes(b"\0")
    (tmp_path / "keep.py").write_text("x=1\n", encoding="utf-8")
    report = scan_path_collisions(tmp_path)
    assert report.file_count == 1
