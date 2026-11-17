"""The decision package's figures (prospective/DECISION_SUPPORT.json) are what decision_support.py computes."""
import ast
import json
import unittest
from pathlib import Path

from research.claimcheck_v1_1.prospective import decision_support as D

HERE = Path(__file__).resolve().parents[1] / "prospective"
COMMITTED = HERE / "DECISION_SUPPORT.json"
CRITERIA = json.loads((HERE / "criteria.json").read_text(encoding="utf-8"))


class DecisionSupport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = json.loads(json.dumps(D.tables()))

    def test_committed_figures_are_reproducible(self):
        self.assertEqual(json.loads(COMMITTED.read_text(encoding="utf-8")), self.t)

    def test_tolerances_at_the_proposed_floor_agree_with_the_scorer_itself(self):
        cells = [row["by_icc"]["0.25"] for name in ("C1", "C2a") for row in self.t["claim_level_tolerance"][name]]
        self.assertEqual(len(cells), 14)
        self.assertTrue(all(c["verified_by_stats_proportion"] for c in cells))

    def test_five_flags_is_the_least_at_which_c2c_can_pass(self):
        rows = {r["flags"]: r for r in self.t["C2c"]["scorer_rule_ignoring_clustering"]}
        c = CRITERIA["levels"]["supervised_external_pilot"]["criteria"]["C2_misleading_refutations"]["c_among_flags"]
        self.assertGreater(rows[4]["bound_0"], c["max_upper_bound"])
        self.assertLessEqual(rows[5]["bound_0"], c["max_upper_bound"])
        self.assertEqual(c["min_flags_for_evaluation"], 5)
        clustered = {r["flags_per_flagged_paper"]: r for r in self.t["C2c"]["with_design_effect_floor_0_25"]}
        self.assertGreater(clustered[2]["min_flags_none_misleading"], 5)

    def test_scorer_tolerance_differs_from_the_design_tables(self):
        row = next(r for r in self.t["claim_level_tolerance"]["C2a"] if r["papers"] == 120 and r["per_paper"] == "10")
        cell = row["by_icc"]["0.25"]
        self.assertEqual(cell["design_120_style_events_allowed"], 2)        # protocol 10a
        self.assertEqual(cell["events_allowed_by_scorer"], 6)               # score.judge: events deflated, estimate cap binds
        self.assertEqual(cell["binding_condition_at_one_more"], "estimate")

    def test_the_scorer_end_to_end_accepts_six_and_rejects_seven_at_120_papers(self):
        """Synthetic per-paper counts through score.metrics and score.judge: 120 papers, 10 exposed numbers
        and 5 confirmations each, k papers with one misleading flag and one unsupported confirmation."""
        from collections import Counter
        from research.claimcheck_v1_1.prospective import score
        for k, expected in ((6, True), (7, False)):
            papers = {}
            for i in range(120):
                bad = 1 if i < k else 0
                papers[f"p{i}"] = Counter(exposed_true=10, true_claims_total=10, false_claims_total=4, correct_discrepancy=1,
                                          misleading_refutation=bad, unsupported_confirmation=bad, correct_confirmation=5 - bad)
            j = score.judge(score.metrics(papers, icc_floor=CRITERIA["assumptions"]["icc_floor"]), CRITERIA)
            self.assertIs(j["C2_misleading_refutations"]["a_per_exposed_claim"]["met"], expected)
            self.assertIs(j["C1_unsupported_confirmations"]["met"], expected)
            self.assertFalse(j["C2_misleading_refutations"]["b_per_paper"]["met"])   # C2b allows one affected paper

    def test_an_icc_floor_of_one_half_makes_c2a_unattainable_at_60_papers(self):
        for row in (r for r in self.t["claim_level_tolerance"]["C2a"] if r["papers"] == 60):
            self.assertGreater(row["lowest_possible_bound_no_flag_by_icc"]["0.5"], 0.02)
            self.assertEqual(row["by_icc"]["0.5"]["events_allowed_by_scorer"], -1)

    def test_unpaced_free_tier_cannot_reach_the_primary_complete_rule(self):
        for d in self.t["model_calls"]["designs"]:
            self.assertLess(d["if_gemini_answers_only_20_calls_a_day_and_calls_are_not_paced"]["primary_complete_share_at_most"], 0.9)
            self.assertGreater(d["ledger_attempt_budget_needed_per_provider"], max(d["ledger_default_budget"].values()))

    def test_imports_nothing_that_can_reach_a_network(self):
        tree = ast.parse(Path(D.__file__).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(("." * node.level) + (node.module or "") + ":" + ",".join(a.name for a in node.names))
        self.assertEqual(imported, {"argparse", "json", "math", "__future__:annotations", "pathlib:Path", ".:stats"})


if __name__ == "__main__":
    unittest.main()
