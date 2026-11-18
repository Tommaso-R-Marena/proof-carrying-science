"""Adversarial PGRA tests: regressions, tampering, stale CAS heads."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.lean_recursive_autoformalization_v1.capability import evaluate_corpus
from research.lean_recursive_autoformalization_v1.corpus import (
    build_frozen_corpus,
    load_tasks,
    verify_tasks_binding,
    write_protocol,
)
from research.lean_recursive_autoformalization_v1.gate import accept
from research.lean_recursive_autoformalization_v1.grammar_extensions import RULE_IDS
from research.lean_recursive_autoformalization_v1.recursive_loop import (
    adversarial_drop_proposer,
    adversarial_noop_proposer,
    automatic_search,
)
from research.lean_recursive_autoformalization_v1.store import (
    FormalizationPromotionStore,
    IntegrityFailure,
    ProposalRejected,
    StaleHead,
)


CORPUS = build_frozen_corpus()


def test_adversarial_rule_removal_rejected() -> None:
    old = frozenset({"rule_unique_exists", "rule_neither_nor", "rule_exactly_when"})
    for candidate in adversarial_drop_proposer(old):
        decision = accept(old, candidate, CORPUS)
        assert decision.accepted is False
        assert decision.reason == "REJECT:rule_removal_forbidden"


def test_adversarial_noop_rejected() -> None:
    old = frozenset({"rule_unique_exists"})
    for candidate in adversarial_noop_proposer(old):
        decision = accept(old, candidate, CORPUS)
        assert decision.accepted is False
        assert decision.reason == "REJECT:no_new_certified_capability"


def test_adversarial_fake_expansion_without_loss_decrease() -> None:
    full = frozenset(RULE_IDS)
    decision = accept(full, full, CORPUS)
    assert decision.accepted is False
    assert decision.reason == "REJECT:no_new_certified_capability"
    assert decision.new_loss == decision.old_loss == 0


def test_abstention_regression_preserved_under_full_rules() -> None:
    empty = evaluate_corpus(frozenset(), CORPUS)
    full = evaluate_corpus(frozenset(RULE_IDS), CORPUS)
    abstain_ids = {i["id"] for i in CORPUS if i["target"] == "abstain"}
    assert abstain_ids <= empty.certified_abstain
    assert abstain_ids <= full.certified_abstain
    decision = accept(frozenset(), frozenset(RULE_IDS), CORPUS)
    assert decision.accepted is True
    for item_id in abstain_ids:
        assert item_id in decision.preserved or item_id in decision.new_certified


def test_corpus_tampering_detected(tmp_path: Path) -> None:
    protocol = write_protocol(tmp_path)
    tasks_path = tmp_path / "tasks.json"
    good_sha = protocol["tasks_sha256"]
    items = verify_tasks_binding(tasks_path, good_sha)
    assert len(items) == 24
    raw = json.loads(tasks_path.read_text())
    raw["items"][0]["english"] = "TAMPERED STATEMENT THAT SHOULD FAIL BINDING."
    tasks_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ValueError, match="tampering"):
        verify_tasks_binding(tasks_path, good_sha)
    tasks_path.write_text(
        json.dumps(
            {
                "format": "pcs-pgra-tasks-v1",
                "frozen": True,
                "items": [{"id": "x"}],
                "pcs_scientific_authority": True,
                "automatic_deployment": False,
            },
            indent=2,
        )
        + "\n"
    )
    with pytest.raises(ValueError, match="pcs_scientific_authority"):
        load_tasks(tasks_path)


def test_store_cas_stale_head(tmp_path: Path) -> None:
    store = FormalizationPromotionStore.initialize(tmp_path / "store", frozenset())
    head, _ = store.read_active()
    store.promote(frozenset({"rule_unique_exists"}), head, CORPUS)
    with pytest.raises(StaleHead):
        store.promote(
            frozenset({"rule_unique_exists", "rule_neither_nor"}),
            head,
            CORPUS,
        )


def test_store_rejects_ungated_proposal(tmp_path: Path) -> None:
    store = FormalizationPromotionStore.initialize(tmp_path / "store2", frozenset())
    head, _ = store.read_active()
    with pytest.raises(ProposalRejected):
        store.promote(frozenset(), head, CORPUS)


def test_store_tamper_blob_fail_closed(tmp_path: Path) -> None:
    store = FormalizationPromotionStore.initialize(tmp_path / "store3", frozenset())
    head, _ = store.read_active()
    store.promote(frozenset({"rule_unique_exists"}), head, CORPUS)
    store.audit()
    blob = next((tmp_path / "store3" / "blobs").glob("*.pgra"))
    data = blob.read_bytes()
    blob.unlink()
    blob.write_bytes(data[:-1] + (b"X" if not data.endswith(b"X") else b"Y"))
    with pytest.raises(IntegrityFailure):
        FormalizationPromotionStore(tmp_path / "store3").audit()


def test_adversarial_proposer_in_search_rejected() -> None:
    corpus = build_frozen_corpus()
    summary = automatic_search(
        corpus=corpus,
        start_rules=frozenset({"rule_unique_exists"}),
        store_root=None,
        max_generations=3,
        proposer=adversarial_drop_proposer,
    )
    assert summary["accepted_generations"] == 0


def test_package_sources_never_claim_authority() -> None:
    root = Path(__file__).resolve().parents[1]
    for path in list(root.rglob("*.py")) + list(root.rglob("*.md")):
        if "tests" in path.parts:
            continue
        text = path.read_text()
        assert "automatic_deployment = True" not in text
        assert "PCS_SCIENTIFIC_AUTHORITY = True" not in text
        assert '"pcs_scientific_authority": true' not in text
        assert '"automatic_deployment": true' not in text
