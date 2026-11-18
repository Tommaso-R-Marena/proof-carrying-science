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

    def test_the_design_tables_now_follow_the_scorer(self):
        row = next(r for r in self.t["claim_level_tolerance"]["C2a"] if r["papers"] == 120 and r["per_paper"] == "10")
        cell = row["by_icc"]["0.25"]
        self.assertEqual(cell["draft_2_table_rule_events_allowed"], 2)        # what draft 2's protocol 10a printed
        self.assertEqual(cell["events_allowed_by_scorer"], 6)                 # score.judge: events divided too, estimate cap binds
        self.assertEqual(cell["binding_condition_at_one_more"], "estimate")
        design = json.loads((HERE / "DESIGN_120.json").read_text(encoding="utf-8"))
        d120 = next(d for d in design["designs"] if d["papers"] == 120)["statistics"]
        self.assertEqual(d120["C2a_by_exposed_numbers_per_paper"]["10"]["flags_allowed_alone"], 6)
        joint = {(r["papers"], r["exposed_per_paper"]): r for r in self.t["C2_a_and_b_together"]["rows"]}
        self.assertEqual(d120["C2a_by_exposed_numbers_per_paper"]["10"]["flags_allowed_all_in_one_paper"],
                         joint[(120, 10)]["misleading_flags_allowed_all_in_one_paper"])

    def test_the_scorer_end_to_end_accepts_six_and_rejects_seven_at_120_papers(self):
        """Synthetic records through score.paper_counts and score.evaluate: 120 papers in three contexts, 10 exposed
        numbers and 5 confirmations each; k papers with one misleading flag and one unsupported confirmation."""
        from research.claimcheck_v1_1.prospective import score

        def paper(bad):
            r = [{"variant": "original", "cls": "T", "outcome": "CONFIRMATION" if j < 5 - bad else "REQUIRE_HUMAN_REVIEW", "reading_matches": True}
                 for j in range(5)]
            n_out = (["CONFIRMATION", "DISCREPANCY_FOR_REVIEW"] if bad else []) + ["UNKNOWN"] * (5 - 2 * bad)
            r += [{"variant": "original", "cls": "N", "outcome": o, "reading_matches": False} for o in n_out]
            r += [{"variant": "planted", "cls": "T", "changed": True, "outcome": "DISCREPANCY_FOR_REVIEW", "reading_matches": True}]
            return score.paper_counts(r)
        for k, expected in ((6, True), (7, False)):
            papers = {f"{c}{i:02d}": {"context": c, "order": f"{c}{i:02d}", "primary_complete": True,
                                      "counts": paper(1 if n < k else 0)} for n, (c, i) in enumerate((c, i) for c in "ABC" for i in range(40))}
            j = score.evaluate(papers, CRITERIA, design=120)["criteria"]
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
