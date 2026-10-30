from heck.canonical import digest_obj
from heck.compose import EvidenceAtom
from heck.falsify import run_attack_campaign
from heck.levels import Level
from heck.theory_ir import TheoryObject, evaluate_theory


def test_theory_closure_requires_discharged_predictions():
    theory = TheoryObject(
        id="transport-pk",
        title="Two-compartment amount conservation + peak prediction",
        assumptions=("finite_cells", "row_stochastic_matrix"),
        formal_leaf_ids=("transport-formal",),
        required_composite_level=Level.EMPIRICAL,
    )
    theory.add_prediction(
        obligation_id="peak",
        prediction={"t_peak_h": 1.0, "c_peak": 2.5},
    )
    atoms = [
        EvidenceAtom(
            id="transport-formal",
            level=Level.FORMAL,
            supported=True,
            claim_id="amount_all_times",
            evidence_sha256=digest_obj({"thm": "amount_all_times"}),
        )
    ]
    open_eval = evaluate_theory(theory, atoms)
    assert open_eval["open_predictive_count"] == 1
    assert open_eval["scientific_closure"] is False

    theory.apply_observation("peak", {"t_peak_h": 1.0, "c_peak": 2.5})
    closed = evaluate_theory(theory, atoms)
    assert closed["scientific_closure"] is True
    assert closed["compose_receipt"]["achieved_level"] == "empirical"
    assert closed["compose_receipt"]["achieved_level"] != "formal"


def test_theory_falsification_blocks_closure():
    theory = TheoryObject(
        id="t",
        title="t",
        assumptions=(),
        formal_leaf_ids=("f",),
    )
    theory.add_prediction(obligation_id="p", prediction={"y": 1})
    atoms = [
        EvidenceAtom("f", Level.FORMAL, True, "c", digest_obj({"f": 1})),
    ]
    theory.apply_observation("p", {"y": 99})
    result = evaluate_theory(theory, atoms)
    assert result["falsified"] is True
    assert result["scientific_closure"] is False


def test_attack_campaign_catches_all():
    report = run_attack_campaign()
    assert report["attacks"] == 8
    assert report["caught"] == 8
    assert report["missed"] == []
    assert report["catch_rate"] == 1.0
