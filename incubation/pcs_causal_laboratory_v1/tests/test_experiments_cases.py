from pcs_causal.benchmarks.synthetic import generate_backdoor_scm
from pcs_causal.cases.biology_synth import drug_response_confounding_case
from pcs_causal.experiments.design import select_best_intervention
from pcs_causal.nonident.witness_search import classic_confounding_witness


def test_experiment_distinguishes_witness_models():
    w = classic_confounding_witness()
    prop = select_best_intervention(
        w.model_a,
        w.model_b,
        candidates=[{"X": 0}, {"X": 1}],
        measure=["Y"],
        costs=[1.0, 1.0],
    )
    assert prop.tv_distance > 0
    assert prop.to_dict()["simulated_only"] is True


def test_drug_case_naive_misleading():
    case = drug_response_confounding_case()
    assert case["severity_adjustment_valid"]
    assert not case["empty_adjustment_valid"]
    assert not case["naive_equals_ate"]


def test_backdoor_scm_meta():
    _, meta = generate_backdoor_scm()
    assert meta["valid_adjustment"] == ["Z"]
