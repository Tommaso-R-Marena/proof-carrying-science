"""Corpus design checks, without substituting a fake executable for Lean."""
from collections import Counter
from research.scientific_receiver_v1.differential import corpus, corpus_sha256
from research.scientific_receiver_v1.reference import assess


def test_preregistered_corpus_independent_expected_outcomes():
    cases = corpus()
    assert len(cases) == 10774
    assert sum(case.expected for case in cases) == 778
    assert len(Counter(case.family for case in cases)) == 44
    assert corpus_sha256(cases) == "04658b54ac7ded872719176800e18d7339a030755c759a902e14666e15fca950"
    for case in cases:
        decision = assess(case.raw)
        assert decision.accepted is case.expected, (case.name, decision.reason)


def test_seed_controls_case_data():
    assert corpus_sha256(corpus(seed=1,count=2)) != corpus_sha256(corpus(seed=2,count=2))
