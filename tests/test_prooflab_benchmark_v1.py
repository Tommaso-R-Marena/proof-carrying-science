from __future__ import annotations

import copy
from pathlib import Path

import pytest

from pcs.prooflab_benchmark_v1 import (
    SOURCE_REVISION,
    load,
    source_blob_sha1,
    validate_benchmark,
    validate_checked_in,
)

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "benchmarks/prooflab/pcs_lean_v2_40.json"
PUBLIC = ROOT / "benchmarks/prooflab/prooflab_public_view.json"


def pair():
    return load(PRIVATE), load(PUBLIC)


def test_40_actual_lean_theorems_and_source_pins():
    result = validate_checked_in(ROOT)
    assert result["case_count"] == 40
    assert result["source_modules"] == 6
    assert result["source_cited_edges"] >= 8
    assert result["evaluation"] == 10
    assert "no cross-project" in result["split_warning"]


def test_changed_statement_does_not_pass():
    private, public = pair()
    private["cases"][0]["source_statement"] += " changed"
    with pytest.raises(ValueError, match="Tampered or moved"):
        validate_benchmark(ROOT, private, public)


def test_source_hash_mutation_fails_closed():
    private, public = pair()
    private["cases"][0]["source_blob_sha1"] = "0" * 40
    with pytest.raises(ValueError, match="Source blob"):
        validate_benchmark(ROOT, private, public)


def test_invented_dependency_is_not_accepted():
    private, public = pair()
    private["cases"][0]["cited_theorems"] = ["invented_lemma"]
    with pytest.raises(ValueError, match="Incorrect source-cited"):
        validate_benchmark(ROOT, private, public)


def test_public_export_does_not_leak_private_proof_bodies():
    private, public = pair()
    assert all("source_statement" not in x for x in public["cases"])
    assert all("source_proof_body" not in x for x in public["cases"])
    public["cases"][0]["source_proof_body"] = "by exact True.intro"
    with pytest.raises(ValueError, match="private proof"):
        validate_benchmark(ROOT, private, public)


def test_split_is_source_module_level():
    private, public = pair()
    assert all(case["source_revision"] == SOURCE_REVISION for case in private["cases"])
    private["cases"][0]["split"] = "evaluation"
    with pytest.raises(ValueError, match="held-out"):
        validate_benchmark(ROOT, private, public)


def test_dag_tampering_fails():
    private, public = pair()
    public["cases"][0]["nodes"][0]["needs"] = ["review"]
    with pytest.raises(ValueError, match="Cyclic planning graph"):
        validate_benchmark(ROOT, private, public)
