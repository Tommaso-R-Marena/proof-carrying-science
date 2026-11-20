"""Continual self-repair controller tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from continual_self_repair import (
    Proposal,
    adversarial_removal_probe,
    continual_self_repair,
    diagnose_reject,
    repair_proposal,
)
from corpus import build_frozen_corpus
from dual_recursive_v3 import accept_dual
from proof_coupled_v2 import DEFAULT_PROOF_TARGETS


@pytest.fixture(scope="module")
def corpus():
    return build_frozen_corpus()


def test_diagnose_proof_side_partial_failure():
    decision = {
        "reason": "REJECT:proof_gate proof=REJECT:no_new_kernel_proof",
        "formalization": {"accepted": True, "reason": "ACCEPT:reference_only", "gained": ["ext_neither_nor"]},
        "proof": {"accepted": False, "reason": "REJECT:no_new_kernel_proof", "gained": []},
    }
    d = diagnose_reject(decision)
    assert d.failing_side == "proof"
    assert d.suggested_strategy == "combine_with_proof_expander"


def test_diagnose_rule_removal():
    d = diagnose_reject(
        {
            "reason": "REJECT:rule_removal_or_nonmonotonic",
            "formalization": {"accepted": False, "reason": "REJECT:rule_removal_forbidden"},
            "proof": {"accepted": False, "reason": "REJECT:rule_removal_or_nonmonotonic"},
        }
    )
    assert d.failing_side == "monotonicity"
    assert d.suggested_strategy == "reject_rule_removal_forever"


def test_repair_combines_proof_expander(corpus):
    active = frozenset()
    failed = Proposal(
        rules=frozenset({"rule_neither_nor"}),
        kind="catalog",
        strategy="next_catalog_rule",
    )
    diagnosis = diagnose_reject(
        {
            "reason": "REJECT:proof_gate proof=REJECT:no_new_kernel_proof",
            "formalization": {"accepted": True, "reason": "ACCEPT:reference_only", "gained": ["x"]},
            "proof": {"accepted": False, "reason": "REJECT:no_new_kernel_proof", "gained": []},
        }
    )
    repair = repair_proposal(active, failed, diagnosis, tried=set())
    assert repair is not None
    assert repair.kind == "repair"
    assert "rule_neither_nor" in repair.rules
    assert any(r in repair.rules for r in (
        "rule_unique_exists", "rule_plus_times_words", "rule_zero_word", "rule_is_equal_to"
    ))


def test_adversarial_removal_rejected(corpus):
    active = frozenset({"rule_unique_exists"})
    probe = adversarial_removal_probe(active)
    assert probe is not None
    decision = accept_dual(active, probe.rules, corpus, DEFAULT_PROOF_TARGETS, budget=64)
    assert not decision["accepted"]
    d = diagnose_reject(decision)
    assert d.failing_side == "monotonicity"


def test_continual_self_repair_recovers(tmp_path: Path, corpus):
    out = tmp_path / "continual"
    summary = continual_self_repair(
        output=out,
        max_episodes=16,
        max_repairs_per_proposal=4,
        budget=96,
        inject_adversarial_removal=True,
        use_store=True,
    )
    assert summary["accepts"] >= 2
    assert summary["repairs_succeeded"] >= 1 or summary["adversarial_rejected"] >= 1
    assert summary["rising_fitting_proved_on_accepts"] is True
    assert summary["pcs_scientific_authority"] is False
    assert summary["automatic_deployment"] is False
    assert (out / "continual_self_repair_summary.json").exists()
    assert (out / "journal.json").exists()
    assert (out / "store" / "HEAD.json").exists()
