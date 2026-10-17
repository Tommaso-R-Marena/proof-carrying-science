from pcs_next_v1.falsification.challenges import challenge_data_leakage, challenge_causal_overclaim

def test_leakage_and_causal():
    assert challenge_data_leakage(["1"], ["1"]).outcome == "OBSERVED_FAILURE"
    assert challenge_causal_overclaim("X causes Y", "association").outcome == "OBSERVED_FAILURE"
