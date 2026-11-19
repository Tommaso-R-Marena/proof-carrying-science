"""Recursive improvement ≥2 generations on the frozen corpus."""
from __future__ import annotations

import json
from pathlib import Path

from research.lean_recursive_autoformalization_v1.corpus import (
    PROTOCOL_FORMAT,
    build_frozen_corpus,
    write_protocol,
)
from research.lean_recursive_autoformalization_v1.grammar_extensions import RULE_IDS
from research.lean_recursive_autoformalization_v1.recursive_loop import (
    automatic_search,
    write_results,
)
from research.lean_recursive_autoformalization_v1.store import FormalizationPromotionStore


def test_recursive_at_least_two_generations_rising_certified(tmp_path: Path) -> None:
    corpus = build_frozen_corpus()
    store_root = tmp_path / "store"
    summary = automatic_search(
        corpus=corpus,
        store_root=store_root,
        max_generations=8,
    )
    assert summary["accepted_generations"] >= 2
    assert summary["automatic_deployment"] is False
    assert summary["pcs_scientific_authority"] is False
    assert summary["pcs_authority"] is False
    counts = summary["certified_counts"]
    assert len(counts) >= 3
    for i in range(len(counts) - 1):
        assert counts[i] < counts[i + 1]
    assert summary["rising_certified"] is True
    head, rules = FormalizationPromotionStore(store_root).read_active()
    assert head.generation == summary["accepted_generations"]
    assert set(rules) == set(summary["final_rules"])
    FormalizationPromotionStore(store_root).audit()


def test_write_results_protocol_frozen(tmp_path: Path) -> None:
    corpus = build_frozen_corpus()
    summary = automatic_search(corpus=corpus, max_generations=3)
    out = tmp_path / "results"
    write_results(out, summary, corpus)
    protocol = json.loads((out / "protocol.json").read_text())
    assert protocol["format"] == PROTOCOL_FORMAT
    assert protocol["frozen"] is True
    assert protocol["pcs_scientific_authority"] is False
    assert protocol["automatic_deployment"] is False
    tasks = json.loads((out / "tasks.json").read_text())
    assert tasks["frozen"] is True
    assert len(tasks["items"]) == 31
    gens = json.loads((out / "generations.json").read_text())
    assert gens["certified_counts"] == summary["certified_counts"]
    assert (out / "SHA256.json").exists()
    assert (out / "summary.json").exists()


def test_protocol_write_standalone(tmp_path: Path) -> None:
    protocol = write_protocol(tmp_path)
    assert protocol["frozen"] is True
    assert protocol["format"] == PROTOCOL_FORMAT


def test_reexport_module() -> None:
    from pcs.experimental.prover import recursive_autoformalization_v1 as reexport

    assert reexport.PCS_AUTHORITY is False
    assert reexport.AUTOMATIC_DEPLOYMENT is False
    assert set(reexport.RULE_IDS) == set(RULE_IDS)
    summary = reexport.automatic_search(max_generations=2)
    assert summary["accepted_generations"] >= 2


def test_ranker_cycle_graceful(tmp_path: Path) -> None:
    from research.lean_recursive_autoformalization_v1.ranker_cycle import run_ranker_cycle

    report = run_ranker_cycle(tmp_path / "ranker")
    assert report["automatic_deployment"] is False
    assert report["pcs_scientific_authority"] is False
    assert report["status"] in {"completed", "skipped_torch_unavailable"}
    if report["status"] == "completed":
        assert report["candidate_promoted"] is False
