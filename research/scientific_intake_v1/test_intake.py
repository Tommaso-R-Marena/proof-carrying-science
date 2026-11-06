"""Byte-preserving intake, archive boundaries and actual parser subprocesses."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import zipfile

import pytest

from . import intake
from .test_adapters import _docx, _pdf, _xlsx


def _zip(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    return output.getvalue()


def _assert_bound_artifact(artifact: dict, raw: bytes):
    sha = hashlib.sha256(raw).hexdigest()
    assert artifact["sha256"] == sha
    assert artifact["size"] == len(raw)
    assert Path(artifact["snapshot_path"]).read_bytes() == raw
    assert artifact["training_policy"] == "DENIED_BY_DEFAULT"
    assert artifact["imported_code_executed"] is False
    for segment in artifact["segments"]:
        assert segment["source_sha256"] == sha
        assert segment["locator"]["source_sha256"] == sha
        assert segment["artifact_id"] == artifact["id"]
        assert segment["transformation"]["original_preserved"] is True


def test_real_single_file_subprocess_binds_exact_original_bytes(tmp_path):
    raw = b"# Measurement\r\nmass = 4.20 kg\r\n"
    source = tmp_path / "notes.md"
    source.write_bytes(raw)
    output = tmp_path / "bundle"
    inventory = intake.ingest(source, output)
    assert inventory["authority"] == "NONE"
    assert inventory["format"] == "pcs-scientific-inventory-v1"
    assert inventory["total_bytes"] == len(raw)
    assert inventory["original_archive"] is None
    artifact, = inventory["artifacts"]
    assert artifact["status"] == "EXTRACTED"
    assert artifact["origin"] == {"kind": "single_file", "relative_path": "notes.md"}
    _assert_bound_artifact(artifact, raw)
    stored = json.loads((output / "inventory.json").read_bytes())
    assert stored == inventory
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert stat.S_IMODE((output / "objects").stat().st_mode) == 0o700
    source.write_bytes(b"changed after intake")
    assert Path(artifact["snapshot_path"]).read_bytes() == raw


def test_directory_intake_is_deterministic_preserves_nested_paths_and_opaque_files(tmp_path):
    source = tmp_path / "project"
    (source / "data").mkdir(parents=True)
    files = {"README.md": b"# Study\n", "data/values.csv": b"x,y\n1,2\n", "opaque.weights": b"not executable\x00opaque"}
    for name, raw in files.items():
        (source / name).write_bytes(raw)
    first = intake.ingest(source, tmp_path / "bundle1")
    second = intake.ingest(source, tmp_path / "bundle2")
    assert first["inventory_sha256"] == second["inventory_sha256"]
    assert [a["id"] for a in first["artifacts"]] == [a["id"] for a in second["artifacts"]]
    assert [a["path"] for a in first["artifacts"]] == sorted(files)
    for artifact in first["artifacts"]:
        _assert_bound_artifact(artifact, files[artifact["path"]])
    assert first["artifacts"][-1]["status"] == "UNSUPPORTED"


def test_zip_retains_exact_archive_and_member_hashes(tmp_path):
    files = {"source/README.md": b"# Project\n", "data.csv": b"t,v\n1,3\n2,4\n"}
    raw = _zip(files)
    source = tmp_path / "project.zip"
    source.write_bytes(raw)
    inventory = intake.ingest(source, tmp_path / "bundle")
    sha = hashlib.sha256(raw).hexdigest()
    assert inventory["original_archive"] == {"sha256": sha, "size": len(raw), "object": "objects/" + sha}
    assert (tmp_path / "bundle" / "objects" / sha).read_bytes() == raw
    for artifact in inventory["artifacts"]:
        _assert_bound_artifact(artifact, files[artifact["path"]])
        assert artifact["origin"] == {"kind": "zip_member", "archive_sha256": sha, "member": artifact["path"]}


def test_code_notebook_lean_and_pickle_stay_data_in_actual_worker(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    marker = tmp_path / "MUST_NOT_EXIST"
    command = f"open({str(marker)!r}, 'w').write('executed')"
    files = {
        "experiment.py": command.encode(),
        "proof.lean": b'import Lean\n#eval IO.println "untrusted"\ntheorem a : True := by sorry\n',
        "weights.pkl": f"cos\nsystem\n(S'touch {marker}'\ntR.".encode(),
        "analysis.ipynb": json.dumps({"nbformat": 4, "nbformat_minor": 5, "cells": [{"cell_type": "code", "execution_count": 99, "source": command, "outputs": [{"output_type": "stream", "name": "stdout", "text": "verified: True"}]}]}).encode(),
    }
    for name, raw in files.items():
        (source / name).write_bytes(raw)
    inventory = intake.ingest(source, tmp_path / "bundle")
    assert not marker.exists()
    by_name = {a["path"]: a for a in inventory["artifacts"]}
    assert by_name["weights.pkl"]["status"] == "UNSUPPORTED"
    assert by_name["experiment.py"]["status"] == "EXTRACTED"
    output = [s for s in by_name["analysis.ipynb"]["segments"] if s["kind"] == "notebook_output"]
    assert output[0]["data"]["stored_output_status"] == "UNVERIFIED"
    for artifact in inventory["artifacts"]:
        _assert_bound_artifact(artifact, files[artifact["path"]])


@pytest.mark.parametrize("name,raw,kind", [("paper.pdf", _pdf(), "pdf_page"), ("report.docx", _docx(), "docx_table_cell"), ("data.xlsx", _xlsx(), "xlsx_cell")])
def test_real_binary_document_formats_pass_through_actual_parser_subprocess(tmp_path, name, raw, kind):
    if name.endswith(".pdf") and not Path("/usr/bin/pdftotext").is_file():
        pytest.skip("pdftotext unavailable")
    source = tmp_path / name
    source.write_bytes(raw)
    artifact, = intake.ingest(source, tmp_path / "bundle")["artifacts"]
    assert artifact["status"] == "EXTRACTED", artifact["warnings"]
    assert any(s["kind"] == kind for s in artifact["segments"])
    _assert_bound_artifact(artifact, raw)


@pytest.mark.parametrize("name", ["../escape.txt", "/absolute.txt", "C:/drive.txt", "x\\y.txt", "a/./b.txt", "a//b.txt", "CON.txt", "a./b.txt", "a /b.txt", "a\x01b.txt", "a/../b.txt"])
def test_unsafe_archive_member_paths_are_rejected(tmp_path, name):
    source = tmp_path / "bad.zip"
    source.write_bytes(_zip({name: b"contents"}))
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, tmp_path / "bundle")
    assert not (tmp_path / "escape.txt").exists()
    assert not (tmp_path / "bundle" / "inventory.json").exists()


def test_zip_nul_filename_is_rejected_before_zipfile_truncation_can_hide_it(tmp_path):
    source = tmp_path / "bad.zip"
    source.write_bytes(_zip({"badX.txt": b"bad"}).replace(b"badX.txt", b"bad\x00.txt"))
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, tmp_path / "bundle")


@pytest.mark.parametrize("names", [("A.txt", "a.txt"), ("K.txt", "K.txt"), ("a.txt", "a.txt")])
def test_archive_normalized_collisions_and_duplicates_rejected(tmp_path, names):
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr(names[0], b"one")
        if names[0] == names[1]:
            with pytest.warns(UserWarning):
                archive.writestr(names[1], b"two")
        else:
            archive.writestr(names[1], b"two")
    source = tmp_path / "bad.zip"
    source.write_bytes(target.getvalue())
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, tmp_path / "bundle")


@pytest.mark.parametrize("name", ["a／b.txt", "a/．/b.txt", "／root.txt", "a/．．/b.txt"])
def test_unicode_normalization_cannot_introduce_path_structure(name):
    with pytest.raises(intake.IntakeError):
        intake.safe_name(name)


def test_zip_symlink_and_expansion_bomb_rejected(tmp_path):
    source = tmp_path / "bad.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        info = zipfile.ZipInfo("linked")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "/etc/passwd")
    source.write_bytes(buffer.getvalue())
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, tmp_path / "symlink-bundle")
    source.write_bytes(_zip({"bomb.txt": b"0" * 1_000_000}))
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, tmp_path / "bomb-bundle")


def test_directory_symlinks_special_files_hardlinks_and_case_collisions_rejected(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside")
    entry = source / "linked"
    entry.symlink_to(outside)
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, tmp_path / "symlink-bundle")
    entry.unlink()
    os.link(outside, entry)
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, tmp_path / "hardlink-bundle")
    entry.unlink()
    os.mkfifo(entry)
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, tmp_path / "fifo-bundle")
    entry.unlink()
    (source / "A.txt").write_text("A")
    (source / "a.txt").write_text("a")
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, tmp_path / "collision-bundle")


def test_direct_source_symlink_and_output_inside_source_or_existing_are_rejected(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    link = tmp_path / "link"
    link.symlink_to(source, target_is_directory=True)
    with pytest.raises(intake.IntakeError):
        intake.ingest(link, tmp_path / "link-bundle")
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, source / "bundle")
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, existing)


def test_file_count_and_file_size_bounds(tmp_path, monkeypatch):
    source = tmp_path / "project"
    source.mkdir()
    for name in ("a.txt", "b.txt", "c.txt"):
        (source / name).write_text("small")
    monkeypatch.setattr(intake, "MAX_FILES", 2)
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, tmp_path / "many-bundle")
    monkeypatch.setattr(intake, "MAX_FILE", 2)
    with pytest.raises(intake.IntakeError):
        intake.ingest(source / "a.txt", tmp_path / "large-bundle")


def test_empty_directory_entries_are_bounded(tmp_path, monkeypatch):
    source = tmp_path / "project"
    source.mkdir()
    for index in range(5):
        (source / f"empty{index}").mkdir()
    monkeypatch.setattr(intake, "MAX_FILES", 2)
    with pytest.raises(intake.IntakeError):
        intake.ingest(source, tmp_path / "bundle")


def test_direct_fifo_is_rejected_without_blocking_snapshot_open(tmp_path):
    source = tmp_path / "input.fifo"
    os.mkfifo(source)
    code = "from research.scientific_intake_v1.intake import ingest,IntakeError\nimport sys\ntry: ingest(sys.argv[1],sys.argv[2])\nexcept IntakeError: sys.exit(0)\nraise SystemExit('FIFO was accepted')\n"
    completed = subprocess.run([sys.executable, "-c", code, str(source), str(tmp_path / "bundle")], cwd=Path(__file__).resolve().parents[2], capture_output=True, timeout=2)
    assert completed.returncode == 0, completed.stderr.decode()


def test_parser_timeout_and_bad_document_return_error_without_source_execution(tmp_path):
    source = tmp_path / "data.json"
    source.write_bytes(b'{"x":1,"x":2}')
    observation = intake.adapter_observation(source.name, source)
    assert observation["status"] == "ERROR"
    assert observation["segments"] == []
    observation = intake.adapter_observation(source.name, source, timeout=0.000001)
    assert observation["status"] == "ERROR"
    assert observation["segments"] == []


def test_worker_imports_trusted_package_even_from_adversarial_current_directory(tmp_path, monkeypatch):
    marker = tmp_path / "MUST_NOT_EXIST"
    attacker = tmp_path / "attacker-cwd"
    (attacker / "research").mkdir(parents=True)
    (attacker / "research" / "__init__.py").write_text(f"open({str(marker)!r},'w').write('untrusted package import')\n")
    source = tmp_path / "data.txt"
    source.write_bytes(b"trusted worker result")
    monkeypatch.chdir(attacker)
    observation = intake.adapter_observation(source.name, source)
    assert not marker.exists(), "worker imported code from caller cwd"
    assert observation["status"] == "EXTRACTED", observation["warnings"]
