"""Proof-coupled PGRA v2 tests (kernel-proved expansion)."""
from __future__ import annotations

from pathlib import Path

import pytest

from corpus import build_frozen_corpus
from grammar_extensions import RULE_IDS
from proof_coupled_v2 import (
    DEFAULT_PROOF_TARGETS,
    accept_proof_coupled,
    evaluate_proof_corpus,
    recursive_proof_coupled,
)


@pytest.fixture(scope="module")
def corpus():
    return build_frozen_corpus()


def test_baseline_proves_base_targets(corpus):
    ev = evaluate_proof_corpus(frozenset(), corpus, DEFAULT_PROOF_TARGETS)
    assert ev["proved_count"] >= 2
    assert "base_nat_eq" in ev["proved"] or "base_nat_add" in ev["proved"]
    assert ev["pcs_scientific_authority"] is False


def test_plus_rule_expands_kernel_proofs(corpus):
    old = frozenset()
    new = frozenset({"rule_plus_times_words"})
    decision = accept_proof_coupled(old, new, corpus, DEFAULT_PROOF_TARGETS)
    assert decision["accepted"], decision["reason"]
    assert decision["new_loss"] < decision["old_loss"]
    assert any("plus" in g or g.startswith("ext_plus") or g.startswith("dup_ext_plus") for g in decision["gained"])
    assert decision["automatic_deployment"] is False


def test_rule_removal_rejected_for_proofs(corpus):
    active = frozenset({"rule_plus_times_words"})
    decision = accept_proof_coupled(active, frozenset(), corpus, DEFAULT_PROOF_TARGETS)
    assert not decision["accepted"]


def test_recursive_proof_coupled_rises(tmp_path: Path, corpus):
    out = tmp_path / "proof_v2"
    summary = recursive_proof_coupled(output=out, max_generations=4, budget=96)
    assert summary["accepted_generations"] >= 2
    assert summary["rising_proved"] is True
    assert summary["pcs_scientific_authority"] is False
    assert (out / "proof_coupled_summary.json").exists()


def test_v7_census_restored_after_lean_relocation():
    """Moving ProofGatedFormalization* out of formal/PCS/V2 restores the frozen census."""
    from research.integration_v1.source_gate import check_profile

    result = check_profile()
    assert result["V7_modules"] == 38
    assert "V7 module discovery differs from the exact audited source profile" not in result["failures"]
