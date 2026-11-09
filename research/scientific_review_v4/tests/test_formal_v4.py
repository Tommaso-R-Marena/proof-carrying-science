"""Real Lean compilation, exact axiom census, and source/compiler negatives."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from research.scientific_review_v4 import formal
from research.scientific_understanding_v2.verify_formal import (
    inspect_source as shared_inspect_source, parse_axiom_audit as shared_parse_axiom_audit,
)


def test_shared_inspection_and_parser_are_reused_unmodified():
    assert formal.inspect_source is shared_inspect_source
    assert formal.parse_axiom_audit is shared_parse_axiom_audit
    checked = formal.inspect_source(formal.SOURCE, formal.REQUIRED_THEOREMS)
    assert checked["source_sha256"] == formal.REVIEWED_SOURCE_SHA256
    assert checked["forbidden_tokens"] == []
    assert checked["unexpected_imports"] == []
    assert checked["theorem_declarations"] == list(formal.REQUIRED_THEOREMS)
    assert checked["required_theorems_present"] is True


def test_parser_retains_nonpermitted_axioms():
    output = "'A.one' does not depend on any axioms\n'A.two' depends on axioms: [propext, Classical.choice]\n"
    parsed = formal.parse_axiom_audit(output)
    assert parsed["one"]["empty"] is True
    assert parsed["two"]["axioms"] == ["propext", "Classical.choice"]


def test_missing_compiler_keeps_all_refinements_open(tmp_path):
    result = formal.verify(tmp_path / "absent-lean")
    assert result["status"] == "UNKNOWN"
    assert result["authority"] is False
    for field in ("scientific_meaning", "python_lean_refinement", "python_fraction_refinement",
                  "key_join_refinement", "source_correspondence", "empirical_refinement"):
        assert result[field] == "OPEN"
    assert "returncode" not in result


def test_missing_source_is_unknown(tmp_path):
    result = formal.verify(source=tmp_path / "absent-source.lean")
    assert result["status"] == "UNKNOWN"
    assert result["authority"] is False
    assert "source_sha256" not in result


def test_pcs_lean_environment_is_honored(monkeypatch, tmp_path):
    absent = tmp_path / "explicit-unavailable-lean"
    monkeypatch.setenv("PCS_LEAN", str(absent))
    result = formal.verify()
    assert result["status"] == "UNKNOWN"
    assert result["compiler_path"] == str(absent)


@pytest.fixture(scope="module")
def actual_receipt():
    if not formal.DEFAULT_LEAN.is_file():
        pytest.skip("Lean compiler unavailable; residual formal obligation remains OPEN")
    # No stub executable, mocked subprocess or positive fixture receipt.
    return formal.verify(formal.DEFAULT_LEAN)


def test_actual_lean_compiles_nine_exact_statements(actual_receipt):
    result = actual_receipt
    assert result["status"] == "VERIFIED", result
    assert result["returncode"] == result["compiler_version_returncode"] == 0
    assert "version 4.28.0," in result["compiler_version"]
    assert result["theorem_count"] == result["axiom_audit_count"] == 9
    assert result["theorem_census_exact"] is True
    assert result["axiom_census_exact"] is True
    assert result["all_declared_theorems_audited"] is True
    assert result["all_declared_axiom_audits_permitted"] is True
    assert result["all_declared_axiom_audits_empty"] is False
    assert result["allowed_lean_axioms"] == ["propext"]
    assert set(result["axiom_audit"]) == set(formal.REQUIRED_THEOREMS)
    assert {name: row["axioms"] for name, row in result["axiom_audit"].items()} == formal.EXPECTED_AXIOMS
    assert result["source_matches_reviewed_sha256"] is True
    for field in ("source_stable_during_compile", "compiler_stable_during_compile",
                  "shared_library_stable_during_compile", "harness_stable_during_compile"):
        assert result[field] is True
    assert result["authority"] is False
    assert result["scientific_meaning"] == result["python_lean_refinement"] == "OPEN"
    assert result["command"][-3:] == ["-M1024", "-j1", str(formal.SOURCE)]


def test_actual_receipt_binds_reviewed_source_compiler_and_harness(actual_receipt):
    result = actual_receipt
    assert result["source_sha256"] == formal.REVIEWED_SOURCE_SHA256
    assert result["harness_sha256"] == hashlib.sha256(Path(formal.__file__).read_bytes()).hexdigest()
    for field in ("source_sha256", "compiler_sha256", "compiler_shared_library_sha256",
                  "harness_sha256", "shared_harness_sha256", "stdout_sha256", "stderr_sha256"):
        assert len(result[field]) == 64
        assert int(result[field], 16) >= 0
    assert result["stdout_sha256"] == hashlib.sha256(result["stdout"].encode()).hexdigest()


def test_fresh_repeated_compilation_is_deterministic(actual_receipt):
    repeated = formal.verify(formal.DEFAULT_LEAN)
    assert repeated["status"] == "VERIFIED", repeated
    assert {key: value for key, value in repeated.items() if key != "checked_at_utc"} == {
        key: value for key, value in actual_receipt.items() if key != "checked_at_utc"}


def test_compilable_source_corruption_refutes_review_binding(actual_receipt, tmp_path):
    corrupted = tmp_path / "Residuals.lean"
    corrupted.write_bytes(formal.SOURCE.read_bytes() + b"\n-- unreviewed source mutation\n")
    result = formal.verify(formal.DEFAULT_LEAN, source=corrupted)
    assert result["returncode"] == 0  # This is a real compiler run on changed bytes.
    assert result["axiom_census_exact"] is True
    assert result["status"] == "REFUTED"
    assert result["source_matches_reviewed_sha256"] is False
    assert result["authority"] is False


def test_actual_compiler_refuses_broken_proof(actual_receipt, tmp_path):
    corrupted = tmp_path / "Residuals.lean"
    source = formal.SOURCE.read_text().replace(
        "pair.observedKey = pair.predictedKey := pair.keysEqual",
        "pair.observedKey = pair.predictedKey := False.elim (by rfl)")
    assert source != formal.SOURCE.read_text()
    corrupted.write_text(source)
    result = formal.verify(formal.DEFAULT_LEAN, source=corrupted)
    assert result["status"] == "REFUTED"
    assert result["returncode"] != 0
    assert result["authority"] is False


def test_missing_print_audit_is_refuted_after_actual_compile(actual_receipt, tmp_path):
    corrupted = tmp_path / "Residuals.lean"
    corrupted.write_text(formal.SOURCE.read_text().replace(
        "#print axioms square_nonnegative\n", ""))
    result = formal.verify(formal.DEFAULT_LEAN, source=corrupted)
    assert result["returncode"] == 0
    assert result["status"] == "REFUTED"
    assert result["axiom_audit_count"] == 8
    assert result["axiom_census_exact"] is False
    assert result["all_declared_theorems_audited"] is False


def test_native_decide_is_explicitly_forbidden(actual_receipt, tmp_path):
    corrupted = tmp_path / "Residuals.lean"
    corrupted.write_text(formal.SOURCE.read_text() + "\nexample : 1 = 1 := by native_decide\n")
    result = formal.verify(formal.DEFAULT_LEAN, source=corrupted)
    assert "native_decide" in result["forbidden_tokens"]
    assert result["status"] == "REFUTED"
    assert result["authority"] is False
