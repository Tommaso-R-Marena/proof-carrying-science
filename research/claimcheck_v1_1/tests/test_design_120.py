"""The design tables (protocol 10a) are reproducible, are what the scorer itself accepts, and their
cost inputs are the measured and planned figures they cite."""
import json
import re
import unittest
from pathlib import Path

from research.claimcheck_v1_1.prospective import design_120, score, stats

HERE = Path(__file__).resolve().parents[1]
COMMITTED = HERE / "prospective" / "DESIGN_120.json"
CRITERIA = json.loads((HERE / "prospective" / "criteria.json").read_text(encoding="utf-8"))
K = CRITERIA["levels"]["supervised_external_pilot"]["criteria"]
FLOOR = CRITERIA["assumptions"]["icc_floor"]
LEDGERS = HERE.parent / "claimcheck_v1" / "benchmark" / "results" / "heldout"
PROTOCOL = (HERE / "prospective" / "PROTOCOL_DRAFT.md").read_text(encoding="utf-8")
PLAN = (HERE / "adjudication" / "RECRUITMENT_AND_ADJUDICATION_PLAN.md").read_text(encoding="utf-8")


def c1_passes(papers, pattern, k):
    sizes = design_120._sizes(pattern, papers)
    return score.c1_met(stats.proportion(design_120.spread(sizes, k), icc_floor=FLOOR), K["C1_unsupported_confirmations"])


def c2a_passes(clusters):
    return score.c2a_met(stats.proportion(clusters, icc_floor=FLOOR), K["C2_misleading_refutations"]["a_per_exposed_claim"])


class DesignTables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = json.loads(json.dumps(design_120.tables()))
        cls.d = {x["papers"]: x for x in cls.t["designs"]}

    def test_committed_tables_are_reproducible(self):
        self.assertEqual(json.loads(COMMITTED.read_text(encoding="utf-8")), self.t)

    def test_c1_rows_are_what_the_scorer_accepts(self):
        for papers in (60, 120):
            for label, pattern in (("2.5", (2, 3)), ("5", (5,))):
                k = self.d[papers]["statistics"]["C1_unsupported_confirmations_allowed_by_confirmations_per_paper"][label]["allowed"]
                self.assertTrue(c1_passes(papers, pattern, k), (papers, label, k))
                self.assertFalse(c1_passes(papers, pattern, k + 1), (papers, label, k + 1))

    def test_c2_rows_are_what_the_scorer_accepts(self):
        for papers in (60, 120):
            for m in ("5", "10"):
                row = self.d[papers]["statistics"]["C2a_by_exposed_numbers_per_paper"][m]
                n = int(m)
                alone = row["flags_allowed_alone"]
                self.assertTrue(c2a_passes(design_120.spread([n] * papers, alone)))
                self.assertFalse(c2a_passes(design_120.spread([n] * papers, alone + 1)))
                one = row["flags_allowed_all_in_one_paper"]
                if row["affected_papers_allowed"] >= 1:
                    self.assertTrue(c2a_passes([(one if i == 0 else 0, n) for i in range(papers)]))
                    self.assertFalse(c2a_passes([(one + 1 if i == 0 else 0, n) for i in range(papers)]))
                self.assertEqual(row["affected_papers_allowed"], stats.max_events_for_bound(papers, K["C2_misleading_refutations"]["b_per_paper"]["max_paper_level_upper_bound"]))

    def test_the_protocol_table_prints_these_rows(self):
        s60, s120 = self.d[60]["statistics"], self.d[120]["statistics"]
        c2 = lambda s, m, k: s["C2a_by_exposed_numbers_per_paper"][m][k]
        row = f"| C2 (a and b together): misleading flags allowed, spread / all in one paper, 5 or 10 exposed numbers per paper | " \
              f"{c2(s60, '5', 'flags_allowed_spread')} / {c2(s60, '5', 'flags_allowed_all_in_one_paper')} or " \
              f"{c2(s60, '10', 'flags_allowed_spread')} / {c2(s60, '10', 'flags_allowed_all_in_one_paper')} | " \
              f"{c2(s120, '5', 'flags_allowed_spread')} / {c2(s120, '5', 'flags_allowed_all_in_one_paper')} or " \
              f"{c2(s120, '10', 'flags_allowed_spread')} / {c2(s120, '10', 'flags_allowed_all_in_one_paper')} |"
        self.assertIn(row, PROTOCOL)
        c1 = lambda s, k: s["C1_unsupported_confirmations_allowed_by_confirmations_per_paper"][k]["allowed"]
        self.assertIn(f"| C1: unsupported confirmations allowed (all three conditions), 2.5 / 5 confirmations in every paper | "
                      f"{c1(s60, '2.5')} / {c1(s60, '5')} | {c1(s120, '2.5')} / {c1(s120, '5')} |", PROTOCOL)

    def test_token_figures_are_the_v1_ledgers_per_successful_call(self):
        per = {"prompt": [], "output": []}
        for f in LEDGERS.glob("prefetch_ledger*.json"):
            d = json.loads(f.read_text(encoding="utf-8"))
            for p in ("gemini", "openrouter"):
                ok = d["network_calls"][p] - d["failures"][p]
                if ok:
                    per["prompt"].append(round(d["prompt_tokens"][p] / ok))
                    per["output"].append(round(d["output_tokens"][p] / ok))
        self.assertEqual(design_120.PROMPT_TOKENS, (min(per["prompt"]), max(per["prompt"])))
        self.assertEqual(design_120.OUTPUT_TOKENS, (min(per["output"]), max(per["output"])))

    def test_adjudication_hours_follow_the_plans_rates(self):
        reading = [int(x) for x in re.search(r"reading methods, opening the data \| (\d+) to (\d+) min", PLAN).groups()]
        per_number = [float(x) for x in re.search(r"\| (\d+(?:\.\d+)?) to (\d+(?:\.\d+)?) min per number", PLAN).groups()]
        numbers = int(re.search(r"about (\d+) numbers", PLAN).group(1))
        self.assertEqual(design_120.ADJUDICATOR_MINUTES_PER_PAPER, tuple(r + numbers * n for r, n in zip(reading, per_number)))
        self.assertEqual(self.d[120]["costs"]["adjudication_person_hours_two_labels_per_number"], [140.0, 230.0])
        self.assertIn("57.5", PLAN)


if __name__ == "__main__":
    unittest.main()
