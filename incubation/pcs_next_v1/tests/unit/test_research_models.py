from pcs_next_v1.research.proof_gated.models import ScalarIntModel, greedy_scalar_search, no_forgetting_guard

def test_greedy_and_guard():
    base = ScalarIntModel(0, 0)
    data = [(1, 2), (2, 4), (3, 6)]
    out = greedy_scalar_search(base, data, a_range=range(0, 3), b_range=range(0, 2), domain_guard=range(-2, 3))
    assert out["best_loss"] <= 0 + sum(y*y for _, y in data)
    ok, bad = no_forgetting_guard(ScalarIntModel(1, 0), ScalarIntModel(1, 5), range(0, 3), max_pointwise_increase=0)
    assert ok is False and bad
