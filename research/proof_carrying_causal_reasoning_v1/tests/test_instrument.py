"""Instrumental variable + Balke–Pearl bounds tests."""

from __future__ import annotations

import unittest
from fractions import Fraction

from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG
from research.proof_carrying_causal_reasoning_v1.kernel.instrument import (
    verify_instrument,
    balke_pearl_bounds,
)
from research.proof_carrying_causal_reasoning_v1.kernel.scm import (
    BinarySCM,
    bernoulli,
    logistic_from_parents,
)
from research.proof_carrying_causal_reasoning_v1.experiment import (
    all_research_tasks,
    check_task_claim,
    run_controls,
)
from research.proof_carrying_causal_reasoning_v1.kernel.certificate import (
    CausalClaim,
    FORMAL_BINDINGS,
)


class TestInstrument(unittest.TestCase):
    def setUp(self):
        self.g = CausalDAG.from_edges(
            ["U", "Z", "X", "Y"],
            [("Z", "X"), ("X", "Y"), ("U", "X"), ("U", "Y")],
        )
        self.scm = BinarySCM(
            self.g,
            {
                "U": bernoulli(Fraction(1, 2)),
                "Z": bernoulli(Fraction(1, 2)),
                "X": logistic_from_parents(
                    {"Z": Fraction(1, 3), "U": Fraction(1, 3)}, Fraction(1, 6)
                ),
                "Y": logistic_from_parents(
                    {"X": Fraction(1, 4), "U": Fraction(1, 3)}, Fraction(1, 8)
                ),
            },
        )

    def test_z_is_instrument(self):
        self.assertTrue(verify_instrument(self.g, "X", "Y", "Z").valid)

    def test_u_not_instrument(self):
        self.assertFalse(verify_instrument(self.g, "X", "Y", "U").valid)

    def test_exclusion_edge_blocks(self):
        g = CausalDAG.from_edges(
            ["Z", "X", "Y"],
            [("Z", "X"), ("X", "Y"), ("Z", "Y")],
        )
        self.assertFalse(verify_instrument(g, "X", "Y", "Z").valid)

    def test_bounds_cover_truth(self):
        bp = balke_pearl_bounds(self.scm, "X", "Y", "Z")
        truth = self.scm.interventional_expectation("Y", {"X": 1})
        ate = self.scm.ate("X", "Y")
        self.assertLessEqual(bp.p_do_lower, truth)
        self.assertLessEqual(truth, bp.p_do_upper)
        self.assertLessEqual(bp.p_do_lower, bp.p_do_upper)
        self.assertLessEqual(bp.ate_lower, ate)
        self.assertLessEqual(ate, bp.ate_upper)
        self.assertFalse(bp.point_identified)

    def test_point_identified_when_x_equals_z(self):
        """Deterministic compliance X:=Z → Wald / response types collapse."""
        g = CausalDAG.from_edges(
            ["U", "Z", "X", "Y"],
            [("Z", "X"), ("X", "Y"), ("U", "Y")],
        )

        def pZ(_):
            return Fraction(1, 2)

        def pX(parents):
            # X = Z almost surely
            return Fraction(1) if parents["Z"] == 1 else Fraction(0)

        def pU(_):
            return Fraction(1, 2)

        def pY(parents):
            x, u = parents["X"], parents["U"]
            return Fraction(1 + x + u, 4)

        scm = BinarySCM(g, {"U": pU, "Z": pZ, "X": pX, "Y": pY})
        self.assertTrue(verify_instrument(g, "X", "Y", "Z").valid)
        bp = balke_pearl_bounds(scm, "X", "Y", "Z")
        truth = scm.interventional_expectation("Y", {"X": 1})
        self.assertTrue(bp.point_identified)
        self.assertEqual(bp.p_do_lower, bp.p_do_upper)
        self.assertEqual(bp.p_do_lower, truth)

    def test_t10_control(self):
        tasks = {t.task_id: t for t in all_research_tasks()}
        t = tasks["T10"]
        v = check_task_claim(t, t.control_claims[0])
        self.assertTrue(v.accepted)
        self.assertEqual(v.verdict, "bounds_certified")
        self.assertIsNotNone(v.bounds)
        self.assertIn("instrument_exogeneity", " ".join(v.assumptions))
        self.assertTrue(any("InstrumentInd" in b for b in v.formal_bindings))
        self.assertEqual(
            list(v.formal_bindings), list(FORMAL_BINDINGS["instrument"])
        )

    def test_t10_overclaim_point_id(self):
        tasks = {t.task_id: t for t in all_research_tasks()}
        t = tasks["T10"]
        claim = CausalClaim(
            task_id="T10",
            treatment="X",
            outcome="Y",
            asserts_identifiable=True,
            adjustment_set=frozenset(["Z"]),
            claimed_p_do=None,
            asserts_association_equals_effect=False,
            strategy="instrument",
        )
        v = check_task_claim(t, claim)
        self.assertFalse(v.accepted)

    def test_t10_wrong_instrument_rejected(self):
        tasks = {t.task_id: t for t in all_research_tasks()}
        t = tasks["T10"]
        claim = CausalClaim(
            task_id="T10",
            treatment="X",
            outcome="Y",
            asserts_identifiable=False,
            adjustment_set=frozenset(["U"]),
            claimed_p_do=None,
            asserts_association_equals_effect=False,
            strategy="instrument",
        )
        v = check_task_claim(t, claim)
        self.assertFalse(v.accepted)

    def test_controls_suite(self):
        self.assertTrue(run_controls()["ok"])


if __name__ == "__main__":
    unittest.main()
