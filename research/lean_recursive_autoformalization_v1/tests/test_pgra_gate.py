"""Prove-by-tests the PGRA reference gate and extension roundtrips."""
from __future__ import annotations

from pathlib import Path

from research.lean_recursive_autoformalization_v1 import (
    AUTOMATIC_DEPLOYMENT,
    PCS_AUTHORITY,
    PCS_SCIENTIFIC_AUTHORITY,
)
from research.lean_recursive_autoformalization_v1.capability import (
    evaluate_case,
    evaluate_corpus,
    formalize_with_rules,
)
from research.lean_recursive_autoformalization_v1.corpus import build_frozen_corpus
from research.lean_recursive_autoformalization_v1.gate import (
    POLICY,
    accept,
    check,
    digest,
)
from research.lean_recursive_autoformalization_v1.grammar_extensions import RULE_IDS


CORPUS = build_frozen_corpus()
EXTENSION_ITEMS = {
    item["required_rules"][0]: item
    for item in CORPUS
    if item.get("class") == "extension_supported"
    and len(item.get("required_rules") or []) == 1
    and item["id"].startswith("ext_")
}


def test_authority_flags_false() -> None:
    assert PCS_AUTHORITY is False
    assert PCS_SCIENTIFIC_AUTHORITY is False
    assert AUTOMATIC_DEPLOYMENT is False
    assert POLICY["pcs_scientific_authority"] is False
    assert POLICY["automatic_deployment"] is False


def test_full_catalog_solves_frozen_corpus() -> None:
    report = evaluate_corpus(frozenset(RULE_IDS), CORPUS)
    assert report.loss == 0
    assert len(report.certified) == len(CORPUS)
    assert not report.wrong
    assert not report.failed_supported
    assert not report.failed_abstain


def test_empty_rules_abstain_and_base() -> None:
    report = evaluate_corpus(frozenset(), CORPUS)
    assert report.loss > 0
    abstain_ids = {i["id"] for i in CORPUS if i["target"] == "abstain"}
    assert abstain_ids <= report.certified_abstain
    for item in CORPUS:
        if item.get("required_rules"):
            assert report.outcomes[item["id"]] == "unsupported_fail"


def test_extension_roundtrip_each_rule() -> None:
    for rule_id, item in EXTENSION_ITEMS.items():
        result = formalize_with_rules(item["english"], frozenset({rule_id}))
        case = evaluate_case(frozenset({rule_id}), item)
        assert case.outcome == "certified_supported", (rule_id, case)
        assert case.roundtrip_ok is True
        assert case.ir_digest == item["expected_ir_digest"]
        assert case.lean == item["expected_lean"]
        assert result["status"] in {"supported", "ambiguous"}


def test_exhaustive_small_lattice_single_rule_additions() -> None:
    empty = frozenset()
    for rule_id in RULE_IDS:
        decision = accept(empty, frozenset({rule_id}), CORPUS)
        assert decision.accepted is True, (rule_id, decision.reason)
        assert decision.new_loss < decision.old_loss
        assert decision.gained
        assert decision.reason.startswith("ACCEPT")


def test_exhaustive_pairwise_monotonic_transitions() -> None:
    first = "rule_unique_exists"
    mid = frozenset({first})
    for rule_id in RULE_IDS:
        if rule_id == first:
            continue
        decision = accept(mid, mid | {rule_id}, CORPUS)
        assert decision.accepted is True, (rule_id, decision.reason)
        assert mid <= frozenset(decision.new_rules)


def test_reject_identical_rules() -> None:
    rules = frozenset({"rule_neither_nor"})
    decision = check(rules, rules, CORPUS)
    assert decision.accepted is False
    assert decision.reason == "REJECT:no_new_certified_capability"


def test_reject_rule_removal() -> None:
    old = frozenset({"rule_unique_exists", "rule_neither_nor"})
    new = frozenset({"rule_unique_exists"})
    decision = accept(old, new, CORPUS)
    assert decision.accepted is False
    assert decision.reason == "REJECT:rule_removal_forbidden"


def test_digest_prefix_stable() -> None:
    assert len(digest({"x": 1})) == 64
    assert digest({"a": 1}) != digest({"a": 2})


def test_no_authority_true_in_package_sources() -> None:
    root = Path(__file__).resolve().parents[1]
    forbidden = (
        '"pcs_scientific_authority": true',
        "'pcs_scientific_authority': True",
        '"automatic_deployment": true',
        "'automatic_deployment': True",
        "pcs_scientific_authority=True",
        "automatic_deployment=True",
    )
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text()
        for needle in forbidden:
            assert needle not in text, (path, needle)
