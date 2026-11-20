"""Adversarial / hygiene tests: wrong strategies, out-of-bound claims, Lean bridge."""

from __future__ import annotations

import unittest
from fractions import Fraction

from research.proof_carrying_causal_reasoning_v1.experiment import (
    all_research_tasks,
    check_task_claim,
)
from research.proof_carrying_causal_reasoning_v1.kernel.certificate import CausalClaim
from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG
from research.proof_carrying_causal_reasoning_v1.kernel.instrument import (
    balke_pearl_bounds,
)
from research.proof_carrying_causal_reasoning_v1.kernel.scm import BinarySCM


class TestAdversarialStrategies(unittest.TestCase):
    def test_frontdoor_rejected_on_iv_task(self):
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
            strategy="frontdoor",
        )
        v = check_task_claim(t, claim)
        self.assertFalse(v.accepted)

    def test_instrument_rejected_on_frontdoor_task(self):
        tasks = {t.task_id: t for t in all_research_tasks()}
        t = tasks["T09"]
        claim = CausalClaim(
            task_id="T09",
            treatment="X",
            outcome="Y",
            asserts_identifiable=False,
            adjustment_set=frozenset(["M"]),
            claimed_p_do=None,
            asserts_association_equals_effect=False,
            strategy="instrument",
        )
        v = check_task_claim(t, claim)
        self.assertFalse(v.accepted)

    def test_claimed_p_do_outside_iv_bounds_rejected(self):
        tasks = {t.task_id: t for t in all_research_tasks()}
        t = tasks["T10"]
        bp = balke_pearl_bounds(t.scm, "X", "Y", "Z")
        # Pick a value just above the upper bound (or 1 if already at 1).
        bad = bp.p_do_upper + Fraction(1, 1000)
        if bad > 1:
            bad = bp.p_do_lower - Fraction(1, 1000)
        claim = CausalClaim(
            task_id="T10",
            treatment="X",
            outcome="Y",
            asserts_identifiable=False,
            adjustment_set=frozenset(["Z"]),
            claimed_p_do=f"{bad.numerator}/{bad.denominator}",
            asserts_association_equals_effect=False,
            strategy="instrument",
        )
        v = check_task_claim(t, claim)
        self.assertFalse(v.accepted)
        self.assertEqual(v.verdict, "intervention_mismatch")

    def test_claimed_p_do_inside_iv_bounds_accepted(self):
        tasks = {t.task_id: t for t in all_research_tasks()}
        t = tasks["T10"]
        bp = balke_pearl_bounds(t.scm, "X", "Y", "Z")
        mid = (bp.p_do_lower + bp.p_do_upper) / 2
        claim = CausalClaim(
            task_id="T10",
            treatment="X",
            outcome="Y",
            asserts_identifiable=False,
            adjustment_set=frozenset(["Z"]),
            claimed_p_do=f"{mid.numerator}/{mid.denominator}",
            asserts_association_equals_effect=False,
            strategy="instrument",
        )
        v = check_task_claim(t, claim)
        self.assertTrue(v.accepted)
        self.assertEqual(v.verdict, "bounds_certified")
        self.assertTrue(any("inside certified" in r for r in v.reasons))


class TestFrontDoorLeanBridge(unittest.TestCase):
    """Match SCMFrontDoor.lean closed forms."""

    def test_frontdoor_closed_forms(self):
        g = CausalDAG.from_edges(
            ["U", "X", "M", "Y"],
            [("U", "X"), ("U", "Y"), ("X", "M"), ("M", "Y")],
        )

        def pU(_):
            return Fraction(1, 2)

        def pX(parents):
            return Fraction(1 + parents["U"], 4)

        def pM(parents):
            return Fraction(1 + parents["X"], 4)

        def pY(parents):
            return Fraction(1 + parents["M"] + 2 * parents["U"], 8)

        scm = BinarySCM(g, {"U": pU, "X": pX, "M": pM, "Y": pY})
        self.assertEqual(
            scm.interventional_expectation("Y", {"X": 1}), Fraction(5, 16)
        )
        self.assertEqual(
            scm.interventional_expectation("Y", {"X": 0}), Fraction(9, 32)
        )
        self.assertEqual(scm.ate("X", "Y"), Fraction(1, 32))
        fd = scm.frontdoor_estimate("X", "Y", 1, ["M"])
        self.assertEqual(fd, Fraction(5, 16))
        obs = scm.observational_expectation("Y", {"X": 1})
        self.assertEqual(obs, Fraction(17, 48))
        self.assertNotEqual(obs, Fraction(5, 16))


if __name__ == "__main__":
    unittest.main()
