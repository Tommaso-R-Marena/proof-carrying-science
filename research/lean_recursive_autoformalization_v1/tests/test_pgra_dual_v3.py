"""PGRA v3 dual formalize+prove gate and holdout-blind recursion."""
from __future__ import annotations

from pathlib import Path

import pytest

from corpus import build_frozen_corpus
from dual_recursive_v3 import (
    accept_dual,
    fitting_corpus,
    fitting_proof_ids,
    holdout_corpus,
    recursive_dual,
)
from formal_bridge import CaseStatus, lean_accept, python_accept, typecheck_core
from grammar_extensions import RULE_IDS
from proof_coupled_v2 import DEFAULT_PROOF_TARGETS


@pytest.fixture(scope="module")
def corpus():
    return build_frozen_corpus()


def test_new_rules_in_catalog():
    assert "rule_zero_word" in RULE_IDS
    assert "rule_is_equal_to" in RULE_IDS
    assert len(RULE_IDS) == 8


def test_corpus_includes_new_extension_items(corpus):
    ids = {item["id"] for item in corpus}
    assert "ext_zero_word" in ids
    assert "ext_is_equal_to" in ids
    assert "dup_ext_zero" in ids
    assert "dup_ext_is_equal" in ids
    assert len(corpus) == 28


def test_fitting_excludes_holdout(corpus):
    fit = fitting_corpus(corpus)
    hold = holdout_corpus(corpus)
    assert fit and hold
    assert {i["id"] for i in fit}.isdisjoint({i["id"] for i in hold})
    assert all(i["split"] != "holdout" for i in fit)


def test_dual_accepts_unique_on_fitting(corpus):
    decision = accept_dual(
        frozenset(),
        frozenset({"rule_unique_exists"}),
        corpus,
        DEFAULT_PROOF_TARGETS,
        budget=96,
    )
    assert decision["accepted"], decision["reason"]
    assert decision["formalization"]["accepted"]
    assert decision["proof"]["accepted"]
    assert decision["automatic_deployment"] is False
    assert decision["pcs_scientific_authority"] is False


def test_dual_rejects_rule_removal(corpus):
    decision = accept_dual(
        frozenset({"rule_unique_exists"}),
        frozenset(),
        corpus,
        DEFAULT_PROOF_TARGETS,
        budget=64,
    )
    assert not decision["accepted"]


def test_dual_rejects_holdout_only_rule_without_fitting_gain(corpus):
    """rule_distinct_forall only unlocks holdout proof targets in the default set."""
    fit_ids = set(fitting_proof_ids(corpus, DEFAULT_PROOF_TARGETS))
    assert "ext_distinct_forall" not in fit_ids
    decision = accept_dual(
        frozenset(),
        frozenset({"rule_distinct_forall"}),
        corpus,
        DEFAULT_PROOF_TARGETS,
        budget=64,
    )
    # Formalization may also fail to expand on fitting (no fitting distinct items).
    assert not decision["accepted"]


def test_recursive_dual_rises_without_harvest(tmp_path: Path, corpus):
    out = tmp_path / "dual_v3"
    summary = recursive_dual(
        output=out,
        max_generations=4,
        budget=96,
        harvest_lemmas=False,
    )
    assert summary["accepted_generations"] >= 2
    assert summary["rising_fitting_proved"] is True
    assert summary["rising_fitting_certified"] is True
    assert summary["holdout_proved_nondecreasing"] is True
    assert summary["pcs_scientific_authority"] is False
    assert (out / "dual_recursive_summary.json").exists()


def test_formal_bridge_points_at_research_lean():
    tc = typecheck_core(timeout=180)
    assert tc.returncode == 0, tc.stderr[-2000:]
    old = (CaseStatus.FAIL, CaseStatus.ABSTAIN)
    new = (CaseStatus.SUPPORTED, CaseStatus.ABSTAIN)
    assert python_accept(old, new)
    verdict = lean_accept(old, new, timeout=180)
    assert verdict.accepted, (verdict.stdout, verdict.stderr[-1000:])


def test_proof_coupled_lean_module_builds():
    from formal_bridge import build_modules

    built = build_modules(["PCS.V2.ProofGatedProofCoupled"], timeout=180)
    assert built.returncode == 0, (built.stdout[-1500:], built.stderr[-1500:])
