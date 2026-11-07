"""Development-only source binding and fail-closed materialization tests."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import pytest

from research.scientific_semantics_v3 import corpus


def test_source_freeze_hash_and_development_identity():
    frozen = corpus.source_freeze()
    assert len(frozen["sources"]) == 16
    assert {x["id"] for x in corpus.projects()} == {"kholodenko2000", "nist_hahn1"}
    assert frozen["total_fixture_bytes"] < 1024 * 1024


def test_materialization_is_exact_and_never_training(tmp_path):
    result = corpus.materialize(tmp_path / "projects")
    assert len(result) == 2
    for case in result:
        folder = Path(case["root"])
        assert json.loads((folder / "project.json").read_text())["training_authorized"] is False
        for artifact in case["artifacts"]:
            assert hashlib.sha256((folder / artifact["path"]).read_bytes()).hexdigest() == artifact["sha256"]
    with pytest.raises(corpus.CorpusError, match="overwrite"):
        corpus.materialize(tmp_path / "projects")


def test_final_optin_precedes_source_reads(tmp_path):
    with pytest.raises(corpus.CorpusError, match="post-freeze"):
        corpus.materialize(tmp_path / "final", "final")
    assert not (tmp_path / "final").exists()


def test_tampered_development_is_rejected_before_output(tmp_path):
    staging = tmp_path / "staging"
    shutil.copytree(corpus.BASE / "fixtures" / "development", staging / "fixtures" / "development")
    file = staging / "fixtures/development/nist_hahn1/Hahn1.dat"
    raw = file.read_bytes()
    file.write_bytes(b"X" + raw[1:])
    with pytest.raises(corpus.CorpusError, match="bytes changed"):
        corpus.materialize(tmp_path / "projects", source_root=staging)
    assert not (tmp_path / "projects").exists()


def test_symlink_source_rejected(tmp_path):
    staging = tmp_path / "staging"
    shutil.copytree(corpus.BASE / "fixtures" / "development", staging / "fixtures" / "development")
    file = staging / "fixtures/development/nist_hahn1/Hahn1.dat"
    saved = tmp_path / "original.dat"
    file.rename(saved)
    file.symlink_to(saved)
    with pytest.raises(corpus.CorpusError, match="symlink"):
        corpus.materialize(tmp_path / "projects", source_root=staging)
