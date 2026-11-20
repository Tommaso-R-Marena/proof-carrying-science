"""Front-door identification + Lean/Python numeric bridge tests."""

from __future__ import annotations

import unittest
from fractions import Fraction

from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG
from research.proof_carrying_causal_reasoning_v1.kernel.frontdoor import (
    verify_frontdoor_set,
    find_frontdoor_sets,
)
from research.proof_carrying_causal_reasoning_v1.kernel.backdoor import verify_backdoor_set
from research.proof_carrying_causal_reasoning_v1.kernel.scm import (
    BinarySCM,
    bernoulli,
    logistic_from_parents,
)
from research.proof_carrying_causal_reasoning_v1.experiment import (
    run_controls,
    run_oracle_sanity,
    check_task_claim,
    all_research_tasks,
)
from research.proof_carrying_causal_reasoning_v1.kernel.certificate import CausalClaim


class TestFrontDoor(unittest.TestCase):
    def setUp(self):
        self.g = CausalDAG.from_edges(
            ["U", "X", "M", "Y"],
            [("U", "X"), ("U", "Y"), ("X", "M"), ("M", "Y")],
        )
        self.scm = BinarySCM(
            self.g,
            {
                "U": bernoulli(Fraction(1, 2)),
                "X": logistic_from_parents({"U": Fraction(1, 2)}, Fraction(1, 4)),
                "M": logistic_from_parents({"X": Fraction(1, 2)}, Fraction(1, 4)),
                "Y": logistic_from_parents(
                    {"M": Fraction(1, 3), "U": Fraction(1, 3)}, Fraction(1, 6)
                ),
            },
        )

    def test_frontdoor_M_valid(self):
        self.assertTrue(verify_frontdoor_set(self.g, "X", "Y", ["M"]).valid)

    def test_frontdoor_empty_invalid(self):
        self.assertFalse(verify_frontdoor_set(self.g, "X", "Y", []).valid)

    def test_frontdoor_U_invalid(self):
        self.assertFalse(verify_frontdoor_set(self.g, "X", "Y", ["U"]).valid)

    def test_backdoor_empty_fails(self):
        self.assertFalse(verify_backdoor_set(self.g, "X", "Y", []).valid)

    def test_backdoor_U_works(self):
        self.assertTrue(verify_backdoor_set(self.g, "X", "Y", ["U"]).valid)

    def test_frontdoor_matches_intervention(self):
        est = self.scm.frontdoor_estimate("X", "Y", 1, ["M"])
        truth = self.scm.interventional_expectation("Y", {"X": 1})
        self.assertIsNotNone(est)
        self.assertEqual(est, truth)

    def test_find_frontdoor(self):
        sets = find_frontdoor_sets(self.g, "X", "Y")
        self.assertTrue(any(r.mediators == frozenset(["M"]) for r in sets))


class TestLeanPythonBridge(unittest.TestCase):
    """Match SCMConfounder.lean closed forms."""

    def test_confounder_closed_forms(self):
        # Mechanisms from SCMConfounder.lean:
        # P(Z=1)=1/2, P(X=1|Z)=(1+z)/4, P(Y=1|X,Z)=(1+x+2z)/8
        g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])

        def pZ(_parents):
            return Fraction(1, 2)

        def pX(parents):
            z = parents["Z"]
            return Fraction(1 + z, 4)

        def pY(parents):
            x, z = parents["X"], parents["Z"]
            return Fraction(1 + x + 2 * z, 8)

        scm = BinarySCM(
            g,
            {
                "Z": pZ,
                "X": pX,
                "Y": pY,
            },
        )
        p_do = scm.interventional_expectation("Y", {"X": 1})
        self.assertEqual(p_do, Fraction(3, 8))
        p_do0 = scm.interventional_expectation("Y", {"X": 0})
        self.assertEqual(p_do0, Fraction(1, 4))
        self.assertEqual(scm.ate("X", "Y"), Fraction(1, 8))
        bd = scm.backdoor_estimate("X", "Y", 1, ["Z"])
        self.assertEqual(bd, Fraction(3, 8))
        # Observational conditional 5/12
        p_obs = scm.observational_expectation("Y", {"X": 1})
        self.assertEqual(p_obs, Fraction(5, 12))
        self.assertNotEqual(p_obs, p_do)


class TestSuiteExtended(unittest.TestCase):
    def test_controls_include_t09(self):
        payload = run_controls()
        self.assertTrue(payload["ok"], msg=payload.get("mismatches"))
        ids = {r["task_id"] for r in payload["rows"]}
        self.assertIn("T09", ids)

    def test_oracle(self):
        self.assertTrue(run_oracle_sanity()["ok"])

    def test_t09_frontdoor_claim(self):
        tasks = {t.task_id: t for t in all_research_tasks()}
        t = tasks["T09"]
        claim = CausalClaim(
            task_id="T09",
            treatment="X",
            outcome="Y",
            asserts_identifiable=True,
            adjustment_set=frozenset(["M"]),
            claimed_p_do=None,
            asserts_association_equals_effect=False,
            strategy="frontdoor",
        )
        v = check_task_claim(t, claim)
        self.assertTrue(v.accepted)


if __name__ == "__main__":
    unittest.main()
