from __future__ import annotations

from pathlib import Path

import pytest

from pcs.pilot_closeout import (
    PilotCloseoutError,
    apply_closeout_plan,
    build_closeout_plan,
    validate_receipt,
)


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "pilot-workspace"
    root.mkdir()
    (root / "retain.txt").write_text("retain", encoding="utf-8")
    (root / "delete.txt").write_text("delete", encoding="utf-8")
    nested = root / "nested"
    nested.mkdir()
    (nested / "delete-too.txt").write_text("delete-too", encoding="utf-8")
    return root


def test_closeout_requires_every_file_to_be_classified(tmp_path):
    root = _workspace(tmp_path)
    with pytest.raises(PilotCloseoutError, match="every regular file"):
        build_closeout_plan(
            root,
            pilot_id="PCS-PILOT-0001",
            retain_paths=["retain.txt"],
            delete_paths=["delete.txt"],
        )


def test_closeout_plan_rejects_overlap(tmp_path):
    root = _workspace(tmp_path)
    with pytest.raises(PilotCloseoutError, match="both RETAIN and DELETE"):
        build_closeout_plan(
            root,
            pilot_id="PCS-PILOT-0001",
            retain_paths=["retain.txt", "delete.txt"],
            delete_paths=["delete.txt", "nested/delete-too.txt"],
        )


def test_closeout_rejects_symlink_workspace_entries(tmp_path):
    root = _workspace(tmp_path)
    target = tmp_path / "outside.txt"
    target.write_text("outside", encoding="utf-8")
    link = root / "link.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this test platform")
    with pytest.raises(PilotCloseoutError, match="symlinks are prohibited"):
        build_closeout_plan(
            root,
            pilot_id="PCS-PILOT-0001",
            retain_paths=["retain.txt", "link.txt"],
            delete_paths=["delete.txt", "nested/delete-too.txt"],
        )


def test_closeout_aborts_if_any_file_changes_after_plan(tmp_path):
    root = _workspace(tmp_path)
    plan = build_closeout_plan(
        root,
        pilot_id="PCS-PILOT-0001",
        retain_paths=["retain.txt"],
        delete_paths=["delete.txt", "nested/delete-too.txt"],
    )
    (root / "delete.txt").write_text("changed", encoding="utf-8")
    with pytest.raises(PilotCloseoutError, match="changed after planning"):
        apply_closeout_plan(
            root,
            plan,
            confirm_plan_sha256=plan["plan_sha256"],
            applied_at="2026-10-05T00:00:00+00:00",
        )
    assert (root / "delete.txt").exists()
    assert (root / "nested" / "delete-too.txt").exists()


def test_closeout_requires_exact_confirmation_hash(tmp_path):
    root = _workspace(tmp_path)
    plan = build_closeout_plan(
        root,
        pilot_id="PCS-PILOT-0001",
        retain_paths=["retain.txt"],
        delete_paths=["delete.txt", "nested/delete-too.txt"],
    )
    with pytest.raises(PilotCloseoutError, match="confirmation hash"):
        apply_closeout_plan(
            root,
            plan,
            confirm_plan_sha256="0" * 64,
            applied_at="2026-10-05T00:00:00+00:00",
        )


def test_closeout_deletes_only_planned_files_and_binds_receipt(tmp_path):
    root = _workspace(tmp_path)
    plan = build_closeout_plan(
        root,
        pilot_id="PCS-PILOT-0001",
        retain_paths=["retain.txt"],
        delete_paths=["delete.txt", "nested/delete-too.txt"],
    )
    receipt = apply_closeout_plan(
        root,
        plan,
        confirm_plan_sha256=plan["plan_sha256"],
        applied_at="2026-10-05T00:00:00+00:00",
    )
    checked = validate_receipt(receipt)

    assert (root / "retain.txt").read_text(encoding="utf-8") == "retain"
    assert not (root / "delete.txt").exists()
    assert not (root / "nested" / "delete-too.txt").exists()
    assert checked["plan_sha256"] == plan["plan_sha256"]
    assert [entry["path"] for entry in checked["deleted"]] == [
        "delete.txt",
        "nested/delete-too.txt",
    ]
    assert [entry["path"] for entry in checked["retained"]] == ["retain.txt"]
    assert len(checked["receipt_sha256"]) == 64


def test_closeout_rejects_new_unplanned_file_at_apply_time(tmp_path):
    root = _workspace(tmp_path)
    plan = build_closeout_plan(
        root,
        pilot_id="PCS-PILOT-0001",
        retain_paths=["retain.txt"],
        delete_paths=["delete.txt", "nested/delete-too.txt"],
    )
    (root / "unexpected.txt").write_text("new", encoding="utf-8")
    with pytest.raises(PilotCloseoutError, match="file set changed"):
        apply_closeout_plan(
            root,
            plan,
            confirm_plan_sha256=plan["plan_sha256"],
            applied_at="2026-10-05T00:00:00+00:00",
        )


def test_closeout_rejects_unsafe_relative_paths(tmp_path):
    root = _workspace(tmp_path)
    with pytest.raises(PilotCloseoutError, match="unsafe closeout path"):
        build_closeout_plan(
            root,
            pilot_id="PCS-PILOT-0001",
            retain_paths=["../outside.txt"],
            delete_paths=["delete.txt", "nested/delete-too.txt", "retain.txt"],
        )
