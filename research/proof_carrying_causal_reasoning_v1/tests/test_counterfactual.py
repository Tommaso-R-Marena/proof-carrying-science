"""Twin-network counterfactuals, ID synthesizer, and T11 certificates."""

from __future__ import annotations

import unittest
from fractions import Fraction

from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG
from research.proof_carrying_causal_reasoning_v1.kernel.scm import BinarySCM
from research.proof_carrying_causal_reasoning_v1.kernel.counterfactual import (
    counterfactual_probability,
)
from research.proof_carrying_causal_reasoning_v1.kernel.identify import (
    synthesize_identification,
)
from research.proof_carrying_causal_reasoning_v1.kernel.certificate import (
    CausalClaim,
    check_claim,
    parse_model_claim,
)
from research.proof_carrying_causal_reasoning_v1.tasks.battery import load_tasks
from research.proof_carrying_causal_reasoning_v1.experiment import (
    check_task_claim,
    run_controls,
    run_oracle_sanity,
)


def _lean_confounder_scm() -> BinarySCM:
    g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
    return BinarySCM(
        g,
        {
            "Z": lambda _p: Fraction(1, 2),
            "X": lambda p: (1 + p.get("Z", 0)) / Fraction(4),
            "Y": lambda p: (1 + p.get("X", 0) + 2 * p.get("Z", 0)) / Fraction(8),
        },
    )


class TestCounterfactualKernel(unittest.TestCase):
    def test_consistency(self):
        scm = _lean_confounder_scm()
        cf = counterfactual_probability(
            scm, outcome="Y", treatment="X", treatment_value=1, evidence={"X": 1}
        )
        obs = scm.conditional({"Y": 1}, {"X": 1})
        self.assertEqual(cf.probability, obs)
        self.assertEqual(cf.probability, Fraction(5, 12))

    def test_cf_ne_do_under_confounding(self):
        scm = _lean_confounder_scm()
        cf = counterfactual_probability(
            scm, outcome="Y", treatment="X", treatment_value=1, evidence={"X": 0}
        )
        do_p = scm.interventional_expectation("Y", {"X": 1})
        self.assertEqual(cf.probability, Fraction(7, 20))
        self.assertEqual(do_p, Fraction(3, 8))
        self.assertNotEqual(cf.probability, do_p)

    def test_no_confounder_cf_equals_do(self):
        g = CausalDAG.from_edges(["X", "Y"], [("X", "Y")])
        scm = BinarySCM(
            g,
            {
                "X": lambda _p: Fraction(1, 2),
                "Y": lambda p: (Fraction(1, 4) + Fraction(1, 2) * p.get("X", 0)),
            },
        )
        cf = counterfactual_probability(
            scm, outcome="Y", treatment="X", treatment_value=1, evidence={"X": 0}
        )
        do_p = scm.interventional_expectation("Y", {"X": 1})
        self.assertEqual(cf.probability, do_p)


class TestIdentifySynthesizer(unittest.TestCase):
    def test_backdoor_confounder(self):
        g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
        plan = synthesize_identification(
            g, treatment="X", outcome="Y", preferred=["backdoor"]
        )
        self.assertEqual(plan.strategy, "backdoor")
        self.assertEqual(plan.adjustment_set, ("Z",))

    def test_frontdoor(self):
        g = CausalDAG.from_edges(
            ["U", "X", "M", "Y"],
            [("U", "X"), ("U", "Y"), ("X", "M"), ("M", "Y")],
        )
        plan = synthesize_identification(
            g, treatment="X", outcome="Y", preferred=["frontdoor", "backdoor"]
        )
        self.assertEqual(plan.strategy, "frontdoor")
        self.assertEqual(plan.mediators, ("M",))

    def test_instrument(self):
        g = CausalDAG.from_edges(
            ["U", "Z", "X", "Y"],
            [("Z", "X"), ("X", "Y"), ("U", "X"), ("U", "Y")],
        )
        plan = synthesize_identification(g, treatment="X", outcome="Y")
        self.assertEqual(plan.strategy, "instrument")
        self.assertEqual(plan.instrument, "Z")

    def test_counterfactual_plan(self):
        g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
        plan = synthesize_identification(
            g, treatment="X", outcome="Y", query_kind="counterfactual"
        )
        self.assertEqual(plan.strategy, "counterfactual")


class TestCounterfactualCertificate(unittest.TestCase):
    def test_accept_exact_claim(self):
        scm = _lean_confounder_scm()
        claim = CausalClaim(
            task_id="cf",
            treatment="X",
            outcome="Y",
            asserts_identifiable=True,
            adjustment_set=frozenset(),
            claimed_p_do="7/20",
            asserts_association_equals_effect=False,
            strategy="counterfactual",
            evidence=(("X", 0),),
            treatment_value=1,
        )
        v = check_claim(
            claim,
            scm.graph,
            scm,
            true_identifiable=True,
            allowed_strategies=("counterfactual",),
        )
        self.assertTrue(v.accepted)
        self.assertEqual(v.verdict, "identified_under_assumptions")
        self.assertIsNotNone(v.counterfactual)

    def test_reject_interventional_trap(self):
        scm = _lean_confounder_scm()
        claim = CausalClaim(
            task_id="cf",
            treatment="X",
            outcome="Y",
            asserts_identifiable=True,
            adjustment_set=frozenset(),
            claimed_p_do="3/8",
            asserts_association_equals_effect=False,
            strategy="counterfactual",
            evidence=(("X", 0),),
            treatment_value=1,
        )
        v = check_claim(
            claim,
            scm.graph,
            scm,
            true_identifiable=True,
            allowed_strategies=("counterfactual",),
        )
        self.assertFalse(v.accepted)
        self.assertEqual(v.verdict, "intervention_mismatch")

    def test_parse_evidence(self):
        text = (
            '{"treatment":"X","outcome":"Y","asserts_identifiable":true,'
            '"strategy":"counterfactual","adjustment_set":[],'
            '"evidence":{"X":0},"treatment_value":1,"claimed_p_do":"7/20"}'
        )
        claim = parse_model_claim("T11", text)
        self.assertEqual(claim.strategy, "counterfactual")
        self.assertEqual(claim.evidence, (("X", 0),))
        self.assertEqual(claim.claimed_p_do, "7/20")


class TestT11Battery(unittest.TestCase):
    def test_controls_and_oracle(self):
        tasks = load_tasks(["T11"])
        self.assertEqual(len(tasks), 1)
        controls = run_controls(tasks)
        self.assertTrue(controls["ok"], controls.get("mismatches"))
        oracle = run_oracle_sanity(tasks)
        self.assertTrue(oracle["ok"], oracle)

    def test_control0_accepts(self):
        task = load_tasks(["T11"])[0]
        v = check_task_claim(task, task.control_claims[0])
        self.assertTrue(v.accepted)
        self.assertIn("PcsPccr.SCMCounterfactual", " ".join(v.formal_bindings))


if __name__ == "__main__":
    unittest.main()
