from pcs_causal.nonident.witness_search import classic_confounding_witness
from pcs_causal.nonident.witness_verifier import verify_witness


def test_classic_witness_verifies():
    w = classic_confounding_witness()
    v = verify_witness(w)
    assert v.accepted
    assert v.obs_tv == 0
    assert v.interv_tv != 0


def test_forged_witness_rejected():
    w = classic_confounding_witness()
    # Tamper: use same model twice
    from pcs_causal.nonident.witness_verifier import NonIdentWitness

    forged = NonIdentWitness(
        model_a=w.model_a,
        model_b=w.model_a,
        treatment=w.treatment,
        outcome=w.outcome,
        treatment_value=w.treatment_value,
        observed_vars=w.observed_vars,
    )
    v = verify_witness(forged)
    assert not v.accepted
