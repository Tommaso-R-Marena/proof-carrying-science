import numpy as np

from pcs_causal.discovery.pc import pc_from_dag_oracle
from pcs_causal.estimation.estimators import (
    ate_difference_in_means,
    ate_doubly_robust,
    ate_ipw,
)
from pcs_causal.estimation.positivity import positivity_report
from pcs_causal.graphs.dag import CausalDAG
from pcs_causal.sensitivity.bounds import manski_ate_bounds


def test_diff_in_means_randomized():
    rng = np.random.default_rng(0)
    t = rng.integers(0, 2, size=500)
    y = t * 1.0 + rng.normal(0, 1, size=500)
    r = ate_difference_in_means(y, t)
    assert abs(r.estimate - 1.0) < 0.25


def test_ipw_and_dr_run():
    rng = np.random.default_rng(1)
    n = 800
    x = rng.normal(size=n)
    logits = 0.8 * x
    p = 1 / (1 + np.exp(-logits))
    t = rng.binomial(1, p)
    y = 1.5 * t + 0.5 * x + rng.normal(0, 1, n)
    ipw = ate_ipw(y, t, x)
    dr = ate_doubly_robust(y, t, x)
    assert abs(dr.estimate - 1.5) < 0.4
    pos = positivity_report(t, x)
    assert pos.n == n


def test_pc_oracle_chain():
    g = CausalDAG.from_edges(["X", "Y", "Z"], [("X", "Y"), ("Y", "Z")])
    res = pc_from_dag_oracle(g)
    assert frozenset(("X", "Y")) in res.skeleton_edges
    assert frozenset(("Y", "Z")) in res.skeleton_edges
    assert frozenset(("X", "Z")) not in res.skeleton_edges


def test_manski_bounds_contain_naive():
    rng = np.random.default_rng(2)
    t = rng.integers(0, 2, size=200)
    y = rng.uniform(0, 1, size=200)
    b = manski_ate_bounds(y, t, 0.0, 1.0)
    assert b.lower <= b.upper
    assert b.status.value == "PARTIALLY_IDENTIFIED"
