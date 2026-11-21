"""agreement.py on synthetic returns (no human judgement exists; these sheets are invented)."""
import csv
import tempfile
import unittest
from pathlib import Path

from research.claimcheck_v1_1.adjudication import agreement as A


def write_return(root: Path, rater: str, classes: dict[str, list[str]], minutes: dict[str, tuple[float, float]]) -> None:
    for paper, labels in classes.items():
        d = root / rater / paper
        d.mkdir(parents=True)
        with (d / "sheet.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["item", "printed_number", "class_T_F_N_A"])
            for i, c in enumerate(labels, 1):
                w.writerow([f"{paper}-{i:02d}", "1.0", c])
    with (root / rater / "time_log.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["paper", "minutes_reading", "minutes_classifying", "notes"])
        for paper, (r, c) in minutes.items():
            w.writerow([paper, r, c, ""])


class Agreement(unittest.TestCase):
    def test_kappa_matches_a_hand_computation(self):
        # 10 numbers; the raters agree on 8.  Marginals: rater 1 T6 F2 N1 A1, rater 2 T6 F1 N2 A1.
        r1 = ["T", "T", "T", "T", "T", "T", "F", "F", "N", "A"]
        r2 = ["T", "T", "T", "T", "T", "T", "F", "N", "N", "A"]
        po, pe = 0.9, (0.6 * 0.6 + 0.2 * 0.1 + 0.1 * 0.2 + 0.1 * 0.1)
        self.assertAlmostEqual(A.kappa(list(zip(r1, r2))), (po - pe) / (1 - pe))

    def test_returns_are_analysed_end_to_end(self):
        root = Path(tempfile.mkdtemp())
        write_return(root, "adj1", {"p1": ["T", "T", "F", "A"], "p2": ["N", "T", "T"]}, {"p1": (15, 30), "p2": (10, 20)})
        write_return(root, "adj2", {"p1": ["T", "F", "F", "A"], "p2": ["N", "T", ""]}, {"p1": (20, 40), "p2": (10, 25)})
        r = A.analyse(root, resamples=200)
        self.assertEqual((r["papers"], r["numbers"]), (2, 7))
        self.assertEqual(r["raw_agreement"], round(5 / 7, 4))
        self.assertEqual([x["item"] for x in r["for_the_resolver"]], ["p1-02", "p2-03"])
        self.assertEqual(r["invalid_or_missing_classes"], ["p2-03"])         # a blank class is reported, not guessed
        self.assertEqual(r["a_share"]["both"], round(2 / 14, 4))
        self.assertEqual(r["minutes_per_paper"]["adj1"]["median"], 37.5)
        self.assertIsNotNone(r["kappa_interval_95_bootstrap_over_papers"])

    def test_one_return_is_not_enough(self):
        root = Path(tempfile.mkdtemp())
        write_return(root, "adj1", {"p1": ["T"]}, {"p1": (1, 1)})
        with self.assertRaises(SystemExit):
            A.analyse(root)


if __name__ == "__main__":
    unittest.main()
