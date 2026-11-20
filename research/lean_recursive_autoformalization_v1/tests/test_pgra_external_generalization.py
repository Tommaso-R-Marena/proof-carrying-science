"""External generalization harness tests."""
from __future__ import annotations

from pathlib import Path

from corpus import build_frozen_corpus
from external_generalization import run_external_suite
from grammar_extensions import RULE_IDS


def test_full_catalog_still_solves_frozen_corpus():
    from capability import evaluate_corpus

    report = evaluate_corpus(frozenset(RULE_IDS), build_frozen_corpus())
    assert report.loss == 0
    assert len(report.certified) == len(build_frozen_corpus())


def test_external_suite_passes(tmp_path: Path):
    summary = run_external_suite(output=tmp_path / "ext", skip_proofs=False, budget=128)
    assert summary["all_gates_passed"], summary["gates"]
    assert summary["axes"]["lean_learning_v2_formalization"]["supported_rate"] == 1.0
    assert summary["axes"]["ood_paraphrase"]["false_accepts"] == 0
    assert summary["axes"]["ood_paraphrase"]["supported_rate"] == 1.0
    svb = summary["axes"]["svb_abstention"]
    if svb.get("available"):
        assert svb["false_accept"] == 0
    assert summary["pcs_scientific_authority"] is False
