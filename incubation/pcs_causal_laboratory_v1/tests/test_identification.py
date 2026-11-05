from pcs_causal.benchmarks.adversarial import run_adversarial_suite
from pcs_causal.graphs.dag import CausalDAG
from pcs_causal.identification.backdoor import verify_backdoor_set
from pcs_causal.identification.frontdoor import check_frontdoor


def test_adversarial_suite():
    results = run_adversarial_suite()
    assert all(results.values()), results


def test_frontdoor_classic():
    # X → M → Y with U confounding X and Y but not through M improperly
    # Classic frontdoor: X→M→Y, and U→X, U→Y (unobserved). On observed DAG without U:
    # observed: X→M→Y. Frontdoor with M.
    g = CausalDAG.from_edges(["X", "M", "Y"], [("X", "M"), ("M", "Y")])
    res = check_frontdoor(g, "X", "Y", ["M"])
    assert res.valid


def test_frontdoor_fails_without_mediation():
    g = CausalDAG.from_edges(["X", "M", "Y"], [("X", "Y"), ("X", "M")])
    res = check_frontdoor(g, "X", "Y", ["M"])
    assert not res.valid


def test_invalid_adjustment_counterexample():
    g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
    assert not verify_backdoor_set(g, "X", "Y", []).valid
