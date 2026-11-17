"""Unit tests for the exact finite causal kernel and certificates."""

from __future__ import annotations

import unittest
from fractions import Fraction

from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG, GraphError
from research.proof_carrying_causal_reasoning_v1.kernel.d_separation import d_separated
from research.proof_carrying_causal_reasoning_v1.kernel.backdoor import verify_backdoor_set
from research.proof_carrying_causal_reasoning_v1.kernel.scm import BinarySCM, bernoulli, logistic_from_parents
from research.proof_carrying_causal_reasoning_v1.kernel.certificate import parse_model_claim, check_claim
from research.proof_carrying_causal_reasoning_v1.experiment import (
    all_research_tasks,
    run_controls,
    run_oracle_sanity,
    check_task_claim,
)
from research.proof_carrying_causal_reasoning_v1.programs.pipeline import (
    program_interventional_rate,
    _routing_program,
)


class TestDAG(unittest.TestCase):
    def test_cycle_rejected(self):
        with self.assertRaises(GraphError):
            CausalDAG.from_edges(["A", "B"], [("A", "B"), ("B", "A")])

    def test_mutilate(self):
        g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
        g2 = g.mutilate(["X"])
        self.assertNotIn(("Z", "X"), g2.edges)
        self.assertIn(("X", "Y"), g2.edges)


class TestDSeparation(unittest.TestCase):
    def test_confounder(self):
        g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
        self.assertFalse(d_separated(g, ["X"], ["Y"], []))
        self.assertFalse(d_separated(g, ["X"], ["Y"], ["Z"]))  # causal path remains

    def test_collider(self):
        g = CausalDAG.from_edges(["X", "Y", "C"], [("X", "C"), ("Y", "C")])
        self.assertTrue(d_separated(g, ["X"], ["Y"], []))
        self.assertFalse(d_separated(g, ["X"], ["Y"], ["C"]))


class TestBackdoor(unittest.TestCase):
    def test_confounder_adjust(self):
        g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
        self.assertTrue(verify_backdoor_set(g, "X", "Y", ["Z"]).valid)
        self.assertFalse(verify_backdoor_set(g, "X", "Y", []).valid)

    def test_mediator_forbidden(self):
        g = CausalDAG.from_edges(["X", "M", "Y"], [("X", "M"), ("M", "Y")])
        self.assertTrue(verify_backdoor_set(g, "X", "Y", []).valid)
        self.assertFalse(verify_backdoor_set(g, "X", "Y", ["M"]).valid)

    def test_unknown_adjustment_var(self):
        g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
        res = verify_backdoor_set(g, "X", "Y", ["Z1"])
        self.assertFalse(res.valid)
        self.assertIn("unknown", res.reasons[0])


class TestSCM(unittest.TestCase):
    def test_association_ne_causation(self):
        g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
        scm = BinarySCM(
            g,
            {
                "Z": bernoulli(Fraction(1, 2)),
                "X": logistic_from_parents({"Z": Fraction(1, 2)}, Fraction(1, 4)),
                "Y": logistic_from_parents(
                    {"X": Fraction(1, 4), "Z": Fraction(1, 2)}, Fraction(1, 8)
                ),
            },
        )
        analysis = scm.analyze_effect("X", "Y")
        self.assertIsNotNone(analysis.observational_association)
        self.assertNotEqual(analysis.observational_association, scm.ate("X", "Y"))
        est = scm.backdoor_estimate("X", "Y", 1, ["Z"])
        truth = scm.interventional_expectation("Y", {"X": 1})
        self.assertEqual(est, truth)

    def test_spurious(self):
        g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y")])
        scm = BinarySCM(
            g,
            {
                "Z": bernoulli(Fraction(1, 2)),
                "X": logistic_from_parents({"Z": Fraction(3, 5)}, Fraction(1, 10)),
                "Y": logistic_from_parents({"Z": Fraction(3, 5)}, Fraction(1, 10)),
            },
        )
        self.assertEqual(scm.ate("X", "Y"), 0)
        self.assertNotEqual(scm.analyze_effect("X", "Y").observational_association, 0)


class TestCertificate(unittest.TestCase):
    def test_parse_and_accept(self):
        text = '{"treatment":"X","outcome":"Y","asserts_identifiable":true,' \
               '"adjustment_set":["Z"],"claimed_p_do":null,' \
               '"asserts_association_equals_effect":false}'
        claim = parse_model_claim("T01", text)
        tasks = {t.task_id: t for t in all_research_tasks()}
        v = check_task_claim(tasks["T01"], claim)
        self.assertTrue(v.accepted)

    def test_malformed(self):
        claim = parse_model_claim("T01", "not json")
        tasks = {t.task_id: t for t in all_research_tasks()}
        v = check_task_claim(tasks["T01"], claim)
        self.assertFalse(v.accepted)
        self.assertEqual(v.verdict, "malformed")


class TestSuite(unittest.TestCase):
    def test_controls(self):
        payload = run_controls()
        self.assertTrue(payload["ok"], msg=payload.get("mismatches"))

    def test_oracle(self):
        payload = run_oracle_sanity()
        self.assertTrue(payload["ok"], msg=payload.get("rows"))

    def test_program_enumeration(self):
        noise_vars = ["traffic", "feature_flag", "n_cache", "n_load", "n_lat"]
        p1 = program_interventional_rate(
            _routing_program, noise_vars, "latency", {"feature_flag": 1}
        )
        p0 = program_interventional_rate(
            _routing_program, noise_vars, "latency", {"feature_flag": 0}
        )
        self.assertIsInstance(p1 - p0, Fraction)


if __name__ == "__main__":
    unittest.main()
