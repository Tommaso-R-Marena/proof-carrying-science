import random
import unittest
from fractions import Fraction
from itertools import product

from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG
from research.proof_carrying_causal_reasoning_v1.kernel.elimination import exact_mass
from research.proof_carrying_causal_reasoning_v1.kernel.scm import BinarySCM


class Elimination(unittest.TestCase):
    def test_independent_whole_world_sum(self):
        rng = random.Random(31702)
        for size in range(2, 8):
            names = tuple(chr(97 + i) for i in range(size))
            for prob in (0, 0.2, 0.6, 1):
                parents = {
                    n: [v for v in names[:i] if rng.random() < prob]
                    for i, n in enumerate(names)
                }
                tables = {
                    n: {
                        bits: Fraction(rng.randrange(5), 4)
                        for bits in product(range(2), repeat=len(ps))
                    }
                    for n, ps in parents.items()
                }

                def mechanism(n, tables=tables, parents=parents):
                    return lambda assignment: tables[n][
                        tuple(assignment[p] for p in parents[n])
                    ]

                scm = BinarySCM(
                    CausalDAG.from_parents(parents), {n: mechanism(n) for n in names}
                )
                for do in ({}, {names[0]: 0}, {names[-1]: 1, names[0]: 1}):
                    # Independent direct summation of the truncated factorization.
                    law = []
                    for bits in product(range(2), repeat=size):
                        env = dict(zip(names, bits, strict=True))
                        if any(env[k] != v for k, v in do.items()):
                            continue
                        weight = 1
                        for n in names:
                            if n in do:
                                continue
                            p = tables[n][tuple(env[v] for v in parents[n])]
                            weight *= p if env[n] else 1 - p
                        law.append((env, weight))
                    for ev in (
                        {},
                        {names[0]: 0},
                        {names[-1]: 1},
                        {names[0]: 1, names[-1]: 0},
                    ):
                        expected = sum(
                            w
                            for env, w in law
                            if all(env[n] == v for n, v in ev.items())
                        )
                        self.assertEqual(exact_mass(scm, ev, do).probability, expected)

    def test_limits_and_unreachable_rows(self):
        graph = CausalDAG.from_parents({"a": (), "b": (), "c": ("a", "b")})
        root = lambda _: Fraction(1, 2)
        scm = BinarySCM(graph, {"a": root, "b": root, "c": root})
        with self.assertRaises(ValueError):
            exact_mass(scm, {"c": 0}, max_bucket_variables=1)
        for wrong in ({"missing": 0}, {"a": 2}, {"a": 0.0}):
            with self.assertRaises(ValueError):
                exact_mass(scm, wrong)
        for invalid in (Fraction(-1), Fraction(3, 2), 0.5):
            bad = BinarySCM(
                graph,
                {
                    "a": root,
                    "b": root,
                    "c": lambda env, v=invalid: v if env["a"] else 0,
                },
            )
            with self.assertRaises(ValueError):
                exact_mass(bad, {"a": 0}, {"c": 0})
        self.assertEqual(exact_mass(scm, {"c": 0}, {"c": 1}).probability, 0)
        self.assertEqual(exact_mass(scm, {"c": 1}, {"c": 1}).probability, 1)
