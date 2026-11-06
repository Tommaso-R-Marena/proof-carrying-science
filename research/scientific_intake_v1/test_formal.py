"""Actual Lean replay and source binding; no mocked proof/axiom responses."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from . import verify_formal


@pytest.fixture(scope="module")
def replay(tmp_path_factory):
    if verify_formal.lean_path() is None:
        pytest.skip("Lean unavailable: formal capability is explicitly unavailable")
    target = tmp_path_factory.mktemp("formal-receipt") / "receipt.json"
    receipt = verify_formal.verify(output=target)
    assert receipt["status"] == "VERIFIED", receipt.get("reason")
    assert json.loads(target.read_text()) == receipt
    return receipt


def test_actual_lean_build_and_all_five_axiom_reports(replay):
    assert replay["build"]["actual_compilation"] is True
    assert replay["build"]["exit_code"] == 0
    assert set(replay["axiom_audit"]) == set(verify_formal.THEOREMS)
    assert all(axioms == [] for axioms in replay["axiom_audit"].values())
    assert len(replay["build"]["proof_object_sha256"]) == 64
    for theorem in verify_formal.THEOREMS:
        assert f"'{theorem}' does not depend on any axioms" in replay["actual_axiom_output"]


def test_actual_replay_receipt_binds_checked_source_verifier_and_compiler(replay):
    assert replay["source"]["sha256"] == hashlib.sha256(verify_formal.SOURCE.read_bytes()).hexdigest()
    assert replay["verifier_sha256"] == hashlib.sha256(Path(verify_formal.__file__).read_bytes()).hexdigest()
    compiler = Path(replay["toolchain"]["path"])
    assert replay["toolchain"]["sha256"] == hashlib.sha256(compiler.read_bytes()).hexdigest()
    assert "version 4.28.0" in replay["toolchain"]["version"]


def test_formal_scope_is_explicitly_conditional_and_has_no_production_authority(replay):
    assert replay["production_authority"] == "NONE"
    assert any("every source input" in assumption for assumption in replay["assumptions"])
    assert any("fixed pure function" in assumption for assumption in replay["assumptions"])
    assert any("Python" in limitation and "unproved" in limitation for limitation in replay["limitations"])
    assert any("Host integrity" in limitation for limitation in replay["limitations"])


def test_missing_explicit_lean_is_unavailable_and_never_claims_a_replay(tmp_path):
    receipt = verify_formal.verify(lean=tmp_path / "no-such-lean")
    assert receipt["status"] == "UNAVAILABLE"
    assert "build" not in receipt
    assert "axiom_audit" not in receipt
    assert receipt["production_authority"] == "NONE"
