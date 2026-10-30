from pcs_epistemic.dialectic import (
    agreement_core,
    dialectic_report,
    distinguishing,
    dispute_frontier,
    merge_ensembles,
)


FORMAL = {"id": "mass_conserved", "required_class": "formal", "required_evidence": ["e_f"]}
PEAK = {"id": "cmax_bound", "required_class": "computational", "required_evidence": ["e_c"]}

MODEL_A = {
    "model_id": "one_compartment",
    "claims": [FORMAL, PEAK],
    "evidence": [
        {"id": "e_f", "class": "formal", "accepted": True},
        {"id": "e_c", "class": "computational", "accepted": True},
    ],
}

MODEL_B = {
    "model_id": "two_compartment",
    "claims": [FORMAL, PEAK],
    "evidence": [
        {"id": "e_f", "class": "formal", "accepted": True},
        {"id": "e_c", "class": "computational", "accepted": False},
    ],
}


def test_agreement_core_and_dispute():
    models = [MODEL_A, MODEL_B]
    candidates = [FORMAL, PEAK]
    assert agreement_core(models, candidates) == [FORMAL]
    assert dispute_frontier(models, candidates) == [PEAK]
    assert distinguishing(models, PEAK)
    assert not distinguishing(models, FORMAL)


def test_merge_preserves_dispute():
    merged = merge_ensembles([MODEL_A], [MODEL_B])
    report = dialectic_report(merged, [FORMAL, PEAK])
    assert report["agreement_core"] == ["mass_conserved"]
    assert report["dispute_frontier"] == ["cmax_bound"]
    assert report["scientific_authority"] is False
