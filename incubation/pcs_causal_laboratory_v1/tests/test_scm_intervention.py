from fractions import Fraction

from pcs_causal.benchmarks.synthetic import generate_backdoor_scm, generate_chain_scm
from pcs_causal.scm.interventions import conditioning_is_not_intervention_witness


def test_chain_ate_rational():
    scm, meta = generate_chain_scm()
    ate = scm.ate("X", "Z", 1, 0)
    assert isinstance(ate, Fraction)
    assert meta["true_ate_X_on_Z"] == [ate.numerator, ate.denominator]


def test_conditioning_differs_under_confounding():
    scm, _ = generate_backdoor_scm()
    w = conditioning_is_not_intervention_witness(scm, "X", 1, "Y")
    assert w["conditioning_defined"]
    assert w["distributions_differ"]


def test_backdoor_recovers_ate():
    from pcs_causal.identification.backdoor import (
        apply_backdoor_to_distribution,
        verify_backdoor_set,
    )

    scm, _ = generate_backdoor_scm()
    assert verify_backdoor_set(scm.dag, "X", "Y", ["Z"]).valid
    obs = scm.observational_distribution()
    e1 = apply_backdoor_to_distribution(obs, "X", "Y", 1, ["Z"])
    e0 = apply_backdoor_to_distribution(obs, "X", "Y", 0, ["Z"])
    assert e1 - e0 == scm.ate("X", "Y", 1, 0)
