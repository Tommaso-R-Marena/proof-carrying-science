"""The draft-2 evaluator (prospective/score.py) against criteria.json, on synthetic fixtures only.

Checks that the evaluator implements the protocol's rules, including the adversarial cases the
owner asked about: ambiguous numbers cannot raise reliability, one misleading flag fails the
paper-level test at 60 papers, too few flags make C2 not evaluable, a short sample is not evaluable.
No prospective paper, label or outcome is involved."""
import json
import re
import unittest
from collections import Counter
from pathlib import Path

from research.claimcheck_v1_1.prospective import score, stats

HERE = Path(__file__).resolve().parents[1] / "prospective"
CRITERIA = json.loads((HERE / "criteria.json").read_text(encoding="utf-8"))
PROTOCOL = (HERE / "PROTOCOL_DRAFT.md").read_text(encoding="utf-8")
FLOOR = CRITERIA["assumptions"]["icc_floor"]


def paper(*, conf=4, unsupported=0, flags=0, misleading=0, true=10, false=2, nd=6, amb=0, exposed=10, misflag_on_amb=0):
    c = Counter()
    c["correct_confirmation"] = conf - unsupported
    c["unsupported_confirmation"] = unsupported
    c["correct_discrepancy"] = flags - misleading
    c["misleading_refutation"] = misleading
    c["true_claims_total"], c["false_claims_total"], c["not_derivable_total"], c["ambiguous_total"] = true, false, nd, amb
    c["exposed_true"], c["exposed_not_derivable"], c["exposed_ambiguous"] = exposed - min(exposed, amb), 0, min(exposed, amb)
    c["abstained_on_true"] = true - (conf - unsupported)
    return c


def run(papers):
    m = score.metrics({f"p{i}": c for i, c in enumerate(papers)}, icc_floor=FLOOR)
    return m, score.judge(m, CRITERIA)


class CriteriaAgreeWithProtocol(unittest.TestCase):
    def test_sample_sizes_are_the_same_everywhere(self):
        need = CRITERIA["levels"]["supervised_external_pilot"]["minimum_sample"]
        self.assertEqual((need["papers"], need["scientific_contexts"], need["papers_per_context"]), (60, 3, 20))
        self.assertIn("20 eligible papers per stratum", PROTOCOL)
        self.assertIn("**240 calls**", PROTOCOL)
        self.assertNotIn("About 120 model calls", PROTOCOL)

    def test_thresholds_quoted_in_the_protocol_are_the_machine_readable_ones(self):
        c = CRITERIA["levels"]["supervised_external_pilot"]["criteria"]
        self.assertEqual(c["C2_misleading_refutations"]["b_per_paper"]["max_paper_level_upper_bound"], 0.05)
        self.assertEqual(c["C2_misleading_refutations"]["c_among_flags"]["max_upper_bound"], 0.5)
        self.assertEqual(c["C3_useful_coverage"]["min_estimate"], 0.25)
        self.assertIsNone(c["D1_discrepancy_detection"]["wording_rule"]["flag_recall_lower_bound_needed_to_describe_the_tool_as_finding_errors"])
        for needle in ("upper bound ≤ 50 %", "estimate ≥ 25 %; lower bound ≥ 15 %", "upper bound ≤ 5 %"):
            self.assertIn(needle, PROTOCOL)

    def test_the_power_table_in_the_protocol_is_what_the_code_computes(self):
        rows = {r["papers"]: r for r in stats.power_table(0.05)}
        self.assertEqual(rows[60]["affected_papers_allowed"], 0)
        self.assertAlmostEqual(rows[60]["chance_of_passing_by_true_paper_level_rate"]["0.01"], 0.547, places=3)
        self.assertEqual(rows[120]["affected_papers_allowed"], 1)
        self.assertIn("74 % / 55 % / 30 % / 4.6 %", PROTOCOL)


class Evaluator(unittest.TestCase):
    def test_a_clean_sixty_paper_run_with_flags_meets_c1_to_c3(self):
        m, j = run([paper(flags=1)] * 60)
        self.assertTrue(j["C1_unsupported_confirmations"]["met"], j["C1_unsupported_confirmations"])
        self.assertTrue(j["C2_misleading_refutations"]["met"], j["C2_misleading_refutations"])
        self.assertTrue(j["C3_useful_coverage"]["met"], j["C3_useful_coverage"])
        self.assertAlmostEqual(m["unsupported_confirmations_among_confirmations"]["design_effect"], 1 + 3 * FLOOR)

    def test_one_misleading_flag_fails_the_paper_level_test_at_sixty_papers(self):
        _m, j = run([paper(flags=1, misleading=1)] + [paper(flags=1)] * 59)
        self.assertFalse(j["C2_misleading_refutations"]["b_per_paper"]["met"])
        self.assertFalse(j["C2_misleading_refutations"]["met"])
        _m, j = run([paper(flags=1, misleading=1)] + [paper(flags=1)] * 119)
        self.assertTrue(j["C2_misleading_refutations"]["b_per_paper"]["met"])     # 120 papers tolerate one

    def test_too_few_flags_make_c2_not_evaluable_and_the_pilot_confirmation_only(self):
        _m, j = run([paper(flags=0)] * 56 + [paper(flags=1)] * 4)
        self.assertFalse(j["C2_misleading_refutations"]["evaluable"])
        self.assertFalse(j["C2_misleading_refutations"]["met"])
        self.assertTrue(j["C1_unsupported_confirmations"]["met"])

    def test_ambiguous_numbers_cannot_raise_coverage(self):
        m0, j0 = run([paper(flags=1)] * 60)
        m1, j1 = run([paper(flags=1, amb=3)] * 60)                    # same confirmations, three hard numbers called ambiguous
        self.assertLess(m1["coverage_of_true_statements"]["estimate"], m0["coverage_of_true_statements"]["estimate"])
        self.assertEqual(m1["coverage_of_true_statements_ambiguous_removed"]["estimate"], m0["coverage_of_true_statements"]["estimate"])

    def test_too_many_ambiguous_numbers_make_everything_not_evaluable(self):
        _m, j = run([paper(flags=1, amb=6)] * 60)                     # 6 of 24 labelled numbers = 25 % > 20 %
        for k in ("C1_unsupported_confirmations", "C2_misleading_refutations", "C3_useful_coverage"):
            self.assertFalse(j[k]["evaluable"], k)
            self.assertFalse(j[k]["met"], k)

    def test_short_sample_and_too_few_confirmations(self):
        _m, j = run([paper(flags=1)] * 59)
        self.assertFalse(j["C1_unsupported_confirmations"]["evaluable"])
        _m, j = run([paper(conf=2, flags=1)] * 60)                    # 120 confirmations < 150
        self.assertFalse(j["C1_unsupported_confirmations"]["evaluable"])

    def test_one_unsupported_confirmation_and_cluster_size(self):
        # protocol 10: about four confirmations per paper, about 150 in all: one unsupported fails C1
        papers = [paper(conf=4, flags=1)] * 37 + [paper(conf=4, unsupported=1, flags=1)] + [paper(conf=0, flags=1)] * 22
        m, j = run(papers)
        self.assertEqual(m["unsupported_confirmations_among_confirmations"]["opportunities"], 152)
        self.assertFalse(j["C1_unsupported_confirmations"]["met"])
        self.assertGreater(j["C1_unsupported_confirmations"]["conservative_upper_bound"], 0.05)
        # the same count spread three per paper passes: the tolerance depends on how confirmations cluster
        papers = [paper(conf=3, flags=1)] * 50 + [paper(conf=3, unsupported=1, flags=1)] + [paper(conf=0, flags=1)] * 9
        m, j = run(papers)
        self.assertEqual(m["unsupported_confirmations_among_confirmations"]["opportunities"], 153)
        self.assertTrue(j["C1_unsupported_confirmations"]["met"], j["C1_unsupported_confirmations"])

    def test_detection_wording_is_withheld_while_the_owner_has_not_set_a_level(self):
        _m, j = run([paper(flags=2, false=2)] * 60)                   # every false number flagged
        self.assertTrue(j["D1_discrepancy_detection"]["necessary_condition_met"])
        self.assertFalse(j["D1_discrepancy_detection"]["may_be_described_as_finding_errors"])


if __name__ == "__main__":
    unittest.main()
