"""Exact observational and interventional inference against complete enumeration."""
import random
from fractions import Fraction
from itertools import product

import pytest

from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG, GraphError
from research.proof_carrying_causal_reasoning_v1.kernel.scm import BinarySCM


def generated(n, seed, density):
    rng = random.Random(seed)
    names = [f"v{j}" for j in rng.sample(range(3*n), n)]
    edges = []
    mechs = {}
    for i, name in enumerate(names):
        parents = [p for p in names[:i] if rng.random() < density]
        edges.extend((p, name) for p in parents)
        table = {bits: Fraction(rng.randrange(8), 7)
                 for bits in product((0, 1), repeat=len(parents))}
        mechs[name] = lambda env, parents=parents, table=table: table[tuple(env[p] for p in parents)]
    return BinarySCM(CausalDAG.from_edges(names, edges), mechs), names


def test_conflicting_observations_have_empty_intersection():
    scm = BinarySCM(CausalDAG.from_edges(["x"], []), {"x": lambda _: Fraction(1, 4)})
    assert scm.conditional({"x": 0}, {"x": 1}) == 0
    assert scm.conditional({"x": 1}, {"x": 1}) == 1


@pytest.mark.parametrize("density", [0, 0.25, 0.7, 1])
def test_generated_models_against_complete_table(density):
    for n in range(2, 7):
        for seed in range(3):
            base, names = generated(n, seed, density)
            for intervention in ({}, {names[0]: seed % 2}, {names[-1]: 0, names[1]: 1}):
                scm = base.intervene(intervention)
                order = scm.graph.topological_order()
                table = scm.observational_table()
                for ev in ({}, {names[0]: 1}, {names[-1]: 1}, {names[0]: 0, names[-1]: 1}):
                    expected = sum(m for bits, m in table.items()
                                   if all(bits[order.index(k)] == v for k, v in ev.items()))
                    assert scm.p_obs(ev) == expected


def test_reject_invalid_probability_even_in_unreachable_parent_row():
    graph = CausalDAG.from_edges(["x", "y"], [("x", "y")])
    scm = BinarySCM(graph, {"x": lambda _: Fraction(0), "y": lambda e: Fraction(2*e["x"])})
    with pytest.raises(GraphError):
        scm.p_obs({"x": 0})
