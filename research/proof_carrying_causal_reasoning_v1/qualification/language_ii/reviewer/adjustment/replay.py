"""Compare graphical adjustment decisions with independent exact four-node world sums."""

import json
from fractions import Fraction
from itertools import combinations, product
from math import prod
from pathlib import Path
from random import Random

from research.proof_carrying_causal_reasoning_v1.external.typed_language import valid_adjustment
from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG

NODES = ("a", "b", "c", "d")
POSSIBLE_EDGES = tuple(combinations(range(4), 2))
WORLDS = tuple(product((0, 1), repeat=4))
SEEDS = (9173, 21011)
DENOMINATOR = 101
HERE = Path(__file__).resolve().parent


def world_masses(parents, seed):
    rng = Random(seed)
    tables = [
        {setting: rng.randrange(1, DENOMINATOR) for setting in product((0, 1), repeat=len(p))}
        for p in parents
    ]
    rows = []
    for world in WORLDS:
        factors = []
        for node, par in enumerate(parents):
            success = tables[node][tuple(world[i] for i in par)]
            factors.append(success if world[node] else DENOMINATOR - success)
        rows.append((world, prod(factors), factors))
    return rows


def arm_values(rows, treatment, outcome, covariates, arm):
    # Removing the natural treatment factor is the surgical-intervention rule.
    intervention = Fraction(
        sum(mass // factors[treatment] for world, mass, factors in rows
            if world[treatment] == arm and world[outcome]),
        DENOMINATOR ** 3,
    )
    standardized = Fraction(0)
    for settings in product((0, 1), repeat=len(covariates)):
        stratum = [(world, mass) for world, mass, _ in rows
                   if tuple(world[node] for node in covariates) == settings]
        followers = [(world, mass) for world, mass in stratum if world[treatment] == arm]
        stratum_mass = Fraction(sum(mass for _, mass in stratum), DENOMINATOR ** 4)
        arm_rate = Fraction(sum(mass for world, mass in followers if world[outcome]),
                            sum(mass for _, mass in followers))
        standardized += stratum_mass * arm_rate
    return intervention, standardized


def replay():
    valid_count = invalid_count = witness_count = 0
    for graph_id in range(64):
        edges = [edge for bit, edge in enumerate(POSSIBLE_EDGES) if graph_id & (1 << bit)]
        graph = CausalDAG.from_edges(NODES, [(NODES[i], NODES[j]) for i, j in edges])
        parents = [tuple(i for i, j in edges if j == node) for node in range(4)]
        populations = [world_masses(parents, seed + graph_id) for seed in SEEDS]
        for treatment, outcome in product(range(4), repeat=2):
            if treatment == outcome:
                continue
            remaining = sorted(set(range(4)) - {treatment, outcome})
            for size in range(3):
                for covariates in combinations(remaining, size):
                    valid = valid_adjustment(graph, NODES[treatment], NODES[outcome],
                                             [NODES[z] for z in covariates])
                    witness = None
                    for seed, rows in zip(SEEDS, populations, strict=True):
                        for arm in (0, 1):
                            target, estimate = arm_values(rows, treatment, outcome, covariates, arm)
                            if target != estimate:
                                witness = (seed + graph_id, arm, str(target), str(estimate))
                    context = (edges, treatment, outcome, covariates)
                    if valid:
                        if witness is not None:
                            raise AssertionError(("accepted adjustment has counterexample", context, witness))
                        valid_count += 1
                    else:
                        invalid_count += 1
                        if witness is None:
                            raise AssertionError(("rejection lacks a numerical witness", context))
                        witness_count += 1
    return {"graphs": 64, "cpt_parameterizations_per_graph": len(SEEDS), "seeds": list(SEEDS),
            "graphical_accepts": valid_count, "graphical_rejects": invalid_count,
            "invalid_sets_with_counterexample": witness_count,
            "graph_query_set_combinations": valid_count + invalid_count}


if __name__ == "__main__":
    result = replay()
    if result != json.loads((HERE / "results.json").read_text(encoding="utf-8")):
        raise AssertionError("recorded adjustment result differs")
    print(json.dumps(result, sort_keys=True))
