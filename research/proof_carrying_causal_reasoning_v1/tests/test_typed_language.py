"""Development controls. Independent challenge texts and labels live separately."""

import unittest
from fractions import Fraction as F
from itertools import product

from research.proof_carrying_causal_reasoning_v1.external.typed_language import (
    CLOSED,
    interpret,
    predict,
    valid_adjustment,
)
from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG


def run(bg, data, query):
    return predict({"background": bg, "given_info": data, "question": query})


class TextBounds(unittest.TestCase):
    def test_joint_bounds_against_exact_vertex_values(self):
        q = "Is the chance of alarm larger when observing rain?"
        for p, a, b in (
            (40, 35, 8),
            (30, 30, 70),
            (10, 22, 5),
            (100, 50, 0),
            (67, 25, 13),
            (50, 0, 0),
        ):
            src = (
                f"The overall probability of rain is {p}%. "
                f"The probability of not rain and alarm is {b}%. "
                f"The probability of rain and alarm is {a}%."
            )
            result = run("", src, q)
            # A direct finite grid oracle enumerates triples of masses. This
            # includes both clipping breakpoints and all enclosing-box vertices.
            ticks = lambda n: range(max(0, 4 * n - 2), min(400, 4 * n + 2) + 1)
            rows = [
                (r, t, u)
                for r, t, u in product(ticks(p), ticks(a), ticks(b))
                if t <= r and u <= 400 - r
            ]
            if not rows or any(r in (0, 400) for r, t, u in rows):
                self.assertIsNone(result["interval"])
            else:
                diffs = [F(t, r) - F(u, 400 - r) for r, t, u in rows]
                self.assertEqual(
                    list(map(F, result["interval"])), [min(diffs), max(diffs)]
                )

    def test_causal_direction_and_confounder(self):
        data = (
            "For those who are humid, the probability of rust is 82%. "
            "For those who are not humid, the probability of rust is 20%."
        )
        q = "Will humid increase the chance of rust?"
        self.assertEqual(
            run("Treatment humid was randomized.", data, q)["prediction"], "yes"
        )
        self.assertEqual(
            run(CLOSED + "Humid has a direct effect on rust.", data, q)["prediction"],
            "yes",
        )
        self.assertIsNone(
            run(CLOSED + "Rust has a direct effect on humid.", data, q)["prediction"]
        )
        self.assertIsNone(
            run(CLOSED + "Weather has a direct effect on humid and rust.", data, q)[
                "prediction"
            ]
        )
        self.assertIsNone(
            run("Treatment humid was not randomized.", data, q)["prediction"]
        )
        self.assertIsNone(
            run(
                "Treatment humid was randomized.",
                data,
                q.replace("humid", "humid or cold"),
            )["prediction"]
        )

    def test_missing_counterfactual_ambiguous_and_distractors(self):
        q = "Is mold less likely than not mold overall?"
        src = (
            "The overall probability of wet is 90%. Among wet, the probability of mold is 60%. "
            "Among not wet, the probability of mold is 0%."
        )
        a = run("", src, q)
        self.assertEqual(a["prediction"], "no")
        self.assertEqual(
            run(
                "The report was printed on Monday.",
                src + " The overall probability of snow is 1%.",
                q,
            )["interval"],
            a["interval"],
        )
        for invalid in [
            src.split(". ")[0] + ".",
            src + " Unless wet is unobserved.",
            src.replace("not wet", "cool"),
        ]:
            self.assertIsNone(run("", invalid, q)["prediction"])
        for text in [
            "Would this unit have mold if it had been wet?",
            q.replace("not mold", "less mold"),
        ]:
            self.assertIsNone(run("", src, text)["prediction"])
        self.assertIsNone(
            run("The probabilities apply only in winter.", src, q)["prediction"]
        )

    def test_rounding_conservative(self):
        a = run(
            "",
            "The overall probability of mold is 50%.",
            "Is mold more likely than not mold overall?",
        )
        self.assertIsNone(a["prediction"])
        self.assertEqual(a["interval"], ["-1/100", "1/100"])

    def test_issuer_boundary(self):
        public = {"background": "", "given_info": "", "question": ""}
        self.assertEqual(
            predict({**public, "answer": "yes"})["reason"], "invalid_public_fields"
        )
        for text in (None, 3, b"background"):
            self.assertEqual(
                predict({**public, "background": text})["reason"],
                "invalid_public_fields",
            )
        self.assertIsNone(
            run(
                "",
                "The overall probability of x is 130%.",
                "Is x more likely than not x overall?",
            )["prediction"]
        )


class GraphText(unittest.TestCase):
    def test_adjustment_examples(self):
        q = "To understand how power affects heat, is it more correct to use the Method 1 than Method 2?"
        data = (
            "Method 1: We look directly at how power correlates with heat in general. "
            "Method 2: We look at this correlation case by case according to flow."
        )
        for edges, expected in [
            ("Flow has a direct effect on power and heat.", "no"),
            (
                "Power has a direct effect on flow. Flow has a direct effect on heat.",
                "yes",
            ),
            (
                "Power has a direct effect on flow. Heat has a direct effect on flow.",
                "yes",
            ),
            (
                "Power has a direct effect on flow and heat.",
                None,
            ),  # irrelevant descendant may be a valid adjustment
            ("Flow has a direct effect on power and heat. Flow is unobserved.", None),
            (
                "Power has a direct effect on flow. Flow has a direct effect on power and heat.",
                None,
            ),
        ]:
            self.assertEqual(run(CLOSED + edges, data, q)["prediction"], expected)
        self.assertIsNone(
            run(
                CLOSED + "Flow has a direct effect on power and heat.",
                data.replace("power correlates with heat", "flow correlates with heat"),
                q,
            )["prediction"]
        )

    def test_explicit_typed_slots(self):
        claim = interpret(
            {
                "background": "Treatment cyan was randomized.",
                "given_info": "Among cyan, the probability of ochre is 70%. Among not cyan, the probability of ochre is 30%.",
                "question": "Does setting cyan to true rather than false decrease the probability of ochre?",
            }
        )
        self.assertEqual(
            (claim.kind, claim.treatment, claim.outcome, claim.direction, claim.arms),
            ("intervention", "cyan", "ochre", "decrease", (True, False)),
        )
        self.assertEqual(
            [(f.event, f.condition, f.percent) for f in claim.facts],
            [("ochre", "cyan", 70), ("ochre", "not cyan", 30)],
        )

    def test_supported_adjustments_against_independent_binary_standardization(self):
        # Independently enumerate rational laws for every three-node ordered
        # DAG, every endpoint pair and both possible covariate choices. Each
        # invalid set must have an explicit population-law counterexample.
        for mask in range(8):
            nodes = ("a", "b", "c")
            edges = [
                e
                for i, e in enumerate([("a", "b"), ("a", "c"), ("b", "c")])
                if (mask >> i) & 1
            ]
            graph = CausalDAG.from_edges(nodes, edges)
            parents = {n: sorted(graph.parents(n)) for n in nodes}

            def weight(w, do, nodes=nodes, parents=parents):
                p = F(1)
                for i, n in enumerate(nodes):
                    if n == do:
                        continue
                    j = sum((1 << k) * w[v] for k, v in enumerate(parents[n]))
                    prob = F(1 + (i + 3 * j) % 9, 11)
                    p *= prob if w[n] else 1 - prob
                return p

            worlds = [dict(zip(nodes, bits)) for bits in product(range(2), repeat=3)]
            obs = [(w, weight(w, None)) for w in worlds]
            for x, y in product(nodes, repeat=2):
                if x == y:
                    continue
                arm = [
                    sum(weight(w, x) for w in worlds if w[x] == t and w[y])
                    for t in range(2)
                ]
                for z in ((), tuple(set(nodes) - {x, y})):
                    std = []
                    for t in range(2):
                        total = 0
                        for u in product(range(2), repeat=len(z)):
                            stratum = [
                                (w, v) for w, v in obs if tuple(w[n] for n in z) == u
                            ]
                            at = [(w, v) for w, v in stratum if w[x] == t]
                            total += (
                                sum(v for _, v in stratum)
                                * sum(v for w, v in at if w[y])
                                / sum(v for _, v in at)
                            )
                        std.append(total)
                    self.assertEqual(
                        valid_adjustment(graph, x, y, z), std == arm, (edges, x, y, z)
                    )
