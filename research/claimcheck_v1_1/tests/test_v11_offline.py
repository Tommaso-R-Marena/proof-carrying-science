"""Offline tests of the v1.1 policy layer (no Lean, no network).

Arithmetic comes from the untrusted oracle here (marked receipts); the live tests in
``check_live_v11.py`` repeat the essential cases with the real kernel.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from research.claimcheck_v1.spec import sha256_hex
from research.claimcheck_v1_1.binding import bound, canonical_literal, foreign_unit, part_of_a_date
from research.claimcheck_v1_1.dev.common import oracle_receipts_raw
from research.claimcheck_v1_1.policy import OUTWARD, assess_document
from research.claimcheck_v1_1.space import SourceContext, decoy_offsets
from research.claimcheck_v1_1.verify import build_record, verify, write_bundle_v11

HERE = Path(__file__).resolve().parent
ROWS = [("A", "f", "12.31", "101.2", 3), ("A", "f", "13.87", "104.9", 4), ("A", "m", "15.02", "110.3", 6), ("A", "m", "16.44", "113.8", 2),
        ("B", "f", "11.95", "99.7", 5), ("B", "f", "14.26", "107.1", 7), ("B", "m", "17.63", "118.4", 3), ("B", "m", "18.09", "121.6", 4),
        ("B", "m", "NA", "116.0", 5), ("A", "f", "13.10", "103.3", 6), ("B", "f", "12.77", "102.5", 2), ("A", "m", "16.91", "115.2", 4)]
DATA = ("id,site,sex,mass,length,age\n" + "".join(f"{i + 1},{s},{x},{m},{ln},{a}\n" for i, (s, x, m, ln, a) in enumerate(ROWS))).encode()
MANIFEST = {"sha256": sha256_hex(DATA), "na_tokens": ["", "NA"], "row_unit": ["individual"],
            "columns": {"mass": {"unit": "g", "aliases": ["body mass"]}, "length": {"unit": "mm", "aliases": ["body length"]}, "age": {"aliases": ["age"]}},
            "values": {"site": {"A": ["site A"], "B": ["site B"]}, "sex": {"f": ["females"], "m": ["males"]}}}
# mass: mean 14.7591 over 11 values, median 14.26, min 11.95, max 18.09, sd 2.2022, sem 0.6640


def run(sentences: list[str], proposals: list[tuple[int, dict]], manifest=None, oracle_siblings=True):
    text = "\n\n".join(sentences)
    props = [{"quote": sentences[i], "spec": spec} for i, spec in proposals]
    m = manifest or MANIFEST
    receipts = oracle_receipts_raw(text, DATA, m, props)
    return receipts, assess_document(SourceContext(text, DATA, m), receipts, oracle_siblings=oracle_siblings)


def verdicts(sentences, proposals, **kw):
    return [d["verdict"] for d in run(sentences, proposals, **kw)[1]]


class Policy(unittest.TestCase):
    S1 = "Mean body mass was 14.76 g (range 11.95–18.09 g) across the 12 individuals."

    def test_a_bound_multi_digit_match_is_confirmed(self):
        self.assertEqual(verdicts([self.S1], [(0, {"stat": "mean", "reported": "14.76", "column": "mass"})]), ["CONFIRMATION"])
        self.assertEqual(verdicts([self.S1], [(0, {"stat": "min", "reported": "11.95", "column": "mass"}),
                                               (0, {"stat": "max", "reported": "18.09", "column": "mass"})]), ["CONFIRMATION", "CONFIRMATION"])

    def test_count_needs_row_unit_wording(self):
        s = "Records were available for 12 individuals."
        self.assertEqual(verdicts([s], [(0, {"stat": "count", "reported": "12"})]), ["CONFIRMATION"])
        no_unit = {k: v for k, v in MANIFEST.items() if k != "row_unit"}
        self.assertEqual(verdicts([s], [(0, {"stat": "count", "reported": "12"})], manifest=no_unit), ["REQUIRE_HUMAN_REVIEW"])
        # where the sentence also names a column with a missing value, "12" could be the rows or the 11 values: two of 90 comparable numbers
        self.assertEqual(verdicts([self.S1], [(0, {"stat": "count", "reported": "12"})]), ["REQUIRE_HUMAN_REVIEW"])

    def test_a_one_digit_number_is_never_confirmed_on_its_own(self):
        s = "The median age was 4 in this sample."
        receipts, decisions = run([s], [(0, {"stat": "median", "reported": "4", "column": "age"})])
        self.assertEqual(receipts[0]["result"], "PROVED")
        self.assertEqual(decisions[0]["verdict"], "REQUIRE_HUMAN_REVIEW")

    def test_wording_must_be_attached_to_the_number(self):
        s = "Mean body mass differed between sites, and 14.76 was recorded in the field book for body mass."
        receipts, decisions = run([s], [(0, {"stat": "mean", "reported": "14.76", "column": "mass"})])
        self.assertEqual(receipts[0]["result"], "PROVED")           # v1 accepts: the word "mean" is somewhere in the sentence
        self.assertEqual(decisions[0]["verdict"], "REQUIRE_HUMAN_REVIEW")

    def test_mismatch_alone_is_never_flagged(self):
        s = "Mean body mass was 15.40 g in this sample."
        receipts, decisions = run([s], [(0, {"stat": "mean", "reported": "15.40", "column": "mass"})])
        self.assertEqual(receipts[0]["result"], "REFUTED")
        self.assertEqual(decisions[0]["verdict"], "REQUIRE_HUMAN_REVIEW")
        self.assertEqual(decisions[0]["mathematical_status"], "MISMATCH_PROVED")     # the mathematical result is preserved

    def test_corroborated_mismatch_is_a_discrepancy_for_review(self):
        s = "Mean body mass was 15.40 g (range 11.95–18.09 g)."
        receipts, decisions = run([s], [(0, {"stat": "mean", "reported": "15.40", "column": "mass"})])
        self.assertEqual(decisions[0]["verdict"], "DISCREPANCY_FOR_REVIEW")
        self.assertTrue(decisions[0]["corroborated_by"])

    def test_rounding_convention_is_not_a_discrepancy(self):
        s = "Mean body mass was 14.75 g (range 11.95–18.09 g)."        # exact 14.7591: less than one unit off in the last digit
        receipts, decisions = run([s], [(0, {"stat": "mean", "reported": "14.75", "column": "mass"})])
        self.assertEqual(receipts[0]["result"], "REFUTED")
        self.assertEqual(decisions[0]["verdict"], "REQUIRE_HUMAN_REVIEW")
        self.assertFalse(next(f for f in decisions[0]["findings"] if f["rule"] == "beyond_rounding_convention")["passed"])

    def test_count_mismatch_is_never_flagged(self):
        s = "Mean body mass was 14.76 g (range 11.95–18.09 g) across the 14 individuals."
        receipts, decisions = run([s], [(0, {"stat": "count", "reported": "14"})])
        self.assertEqual(receipts[0]["result"], "REFUTED")
        self.assertEqual(decisions[0]["verdict"], "REQUIRE_HUMAN_REVIEW")

    def test_mismatch_explained_by_another_reading_is_not_flagged(self):
        s = "Median body mass was 14.76 g, the mean was similar (range 11.95–18.09 g)."
        receipts, decisions = run([s], [(0, {"stat": "median", "reported": "14.76", "column": "mass"})])
        self.assertEqual(receipts[0]["result"], "REFUTED")
        self.assertEqual(decisions[0]["verdict"], "REQUIRE_HUMAN_REVIEW")

    def test_printed_sample_size_that_differs_blocks_a_flag(self):
        s = "Mean body mass was 15.40 g (range 11.95–18.09 g, n = 30)."
        self.assertEqual(verdicts([s], [(0, {"stat": "mean", "reported": "15.40", "column": "mass"})]), ["REQUIRE_HUMAN_REVIEW"])

    def test_out_of_grammar_wording_blocks_a_flag(self):
        s = "The adjusted mean body mass was 15.40 g (range 11.95–18.09 g)."
        self.assertEqual(verdicts([s], [(0, {"stat": "mean", "reported": "15.40", "column": "mass"})]), ["REQUIRE_HUMAN_REVIEW"])

    def test_plus_minus_without_a_name_blocks_a_flag(self):
        s = "Mean body mass was 14.76 ± 1.90 g (range 11.95–18.09 g)."
        receipts, decisions = run([s], [(0, {"stat": "sd", "reported": "1.90", "column": "mass"})])
        self.assertEqual(receipts[0]["result"], "REFUTED")
        self.assertEqual(decisions[0]["verdict"], "REQUIRE_HUMAN_REVIEW")

    def test_numeric_threshold_and_self_referential_selections_are_not_eligible(self):
        s = "Mean body mass was 16.37 g for individuals older than 3 (range 11.95–18.09 g)."
        for cond in ({"kind": "num", "column": "age", "cmp": "gt", "value": "3"}, {"kind": "text_ne", "column": "site", "value": "A"},
                     {"kind": "text_eq", "column": "mass", "value": "16.44"}):
            receipts, decisions = run([s], [(0, {"stat": "mean", "reported": "16.37", "column": "mass", "filter": [cond]})])
            self.assertNotIn(decisions[0]["verdict"], ("CONFIRMATION", "DISCREPANCY_FOR_REVIEW"), cond)

    def test_group_selection_by_named_label_is_eligible(self):
        s = "Mean body mass of females was 13.04 g."
        self.assertEqual(verdicts([s], [(0, {"stat": "mean", "reported": "13.04", "column": "mass",
                                              "filter": [{"kind": "text_eq", "column": "sex", "value": "f"}]})]), ["CONFIRMATION"])

    def test_incompatible_or_unverifiable_unit_blocks(self):
        s = "The mean temperature was 14.76 °C while body mass was recorded."
        self.assertEqual(verdicts([s], [(0, {"stat": "mean", "reported": "14.76", "column": "mass"})]), ["REQUIRE_HUMAN_REVIEW"])
        s2 = "The mean age was 4.25 years."
        receipts, decisions = run([s2], [(0, {"stat": "mean", "reported": "4.25", "column": "age"})])
        self.assertEqual(receipts[0]["result"], "PROVED")
        self.assertEqual(decisions[0]["verdict"], "REQUIRE_HUMAN_REVIEW")      # the manifest declares no unit for age: fail closed

    def test_dates_and_identifiers_are_not_quantities(self):
        self.assertTrue(part_of_a_date("from 22 July 2015 to 13 August 2016", 13, 17))
        self.assertTrue(part_of_a_date("on 13/08/2016 we", 3, 5))
        self.assertFalse(part_of_a_date("a mean of 2015 units", 10, 14))
        self.assertFalse(canonical_literal("006"))
        self.assertTrue(canonical_literal("0.06"))

    def test_a_one_digit_number_is_not_confirmed_even_beside_a_confirmed_sibling(self):
        s = "Mean body mass was 14.76 ± 0.7 SE g (range 11.95–18.09 g)."
        receipts, decisions = run([s], [(0, {"stat": "sem", "reported": "0.7", "column": "mass"}),
                                         (0, {"stat": "mean", "reported": "14.76", "column": "mass"})])
        self.assertEqual(receipts[0]["result"], "PROVED")
        self.assertEqual([d["verdict"] for d in decisions], ["REQUIRE_HUMAN_REVIEW", "CONFIRMATION"])

    def test_an_interval_that_is_not_the_range_is_not_read_as_min_and_max(self):
        w = "The mean age was 5.1 (median = 4, interquartile range: IQR = 3–6), with lifespans ranging between 3 and 14 years."
        i = w.index("3–6")
        self.assertIsNone(bound("min", w, i, i + 1, {}))
        self.assertIsNone(bound("max", w, i + 2, i + 3, {}))

    def test_v11_never_upgrades_v1(self):
        s = [self.S1, "Mean body mass was 15.40 g (range 11.95–18.09 g).", "The median age was 4 in this sample."]
        props = [(0, {"stat": "mean", "reported": "14.76", "column": "mass"}), (0, {"stat": "mean", "reported": "14.76", "column": "length"}),
                 (1, {"stat": "mean", "reported": "15.40", "column": "mass"}), (2, {"stat": "median", "reported": "4", "column": "age"}),
                 (2, {"stat": "mean", "reported": "9.99", "column": "age"}), (0, {"stat": "sum", "reported": "12", "column": "mass"})]
        receipts, decisions = run(s, props)
        for r, d in zip(receipts, decisions):
            self.assertIn(d["verdict"], OUTWARD)
            if d["verdict"] == "CONFIRMATION":
                self.assertEqual(r["result"], "PROVED")
            if d["verdict"] == "DISCREPANCY_FOR_REVIEW":
                self.assertEqual(r["result"], "REFUTED")
            if r["result"] == "UNKNOWN":
                self.assertIn(d["verdict"], ("REQUIRE_HUMAN_REVIEW", "UNKNOWN"))


class Pieces(unittest.TestCase):
    def test_decoys_are_comparable_numbers(self):
        self.assertEqual(len(decoy_offsets(Fraction(5), Fraction(1, 2))), 8)            # 1..9 without 5: rate at least 1/9
        self.assertEqual(len(decoy_offsets(Fraction("6.07"), Fraction(1, 200))), 100)
        self.assertEqual(decoy_offsets(Fraction(0), Fraction(1, 2)), [])
        ks = decoy_offsets(Fraction(12), Fraction(1, 2))
        self.assertTrue(all(10 <= 12 + k <= 99 for k in ks) and len(ks) == 89)

    def test_positional_binding(self):
        w = "mean ± SE: 78.4 ± 1.6 (range: 12.0 – 167.0, n = 124)"
        i = w.index("78.4")
        self.assertIsNotNone(bound("mean", w, i, i + 4, {}))
        self.assertIsNone(bound("sem", w, i, i + 4, {}))                 # the number before ± is the centre
        j = w.index("1.6")
        self.assertIsNotNone(bound("sem", w, j, j + 3, {}))
        self.assertIsNone(bound("mean", w, j, j + 3, {}))
        a, b = w.index("12.0"), w.index("167.0")
        self.assertIsNotNone(bound("min", w, a, a + 4, {}))
        self.assertIsNone(bound("max", w, a, a + 4, {}))
        self.assertIsNotNone(bound("max", w, b, b + 5, {}))
        n = w.index("124")
        self.assertEqual(bound("count", w, n, n + 3, {}), "n =")
        self.assertIsNone(bound("count", w, a, a + 4, {}))

    def test_foreign_unit(self):
        self.assertIsNotNone(foreign_unit("count", "kept for 12 days", 11, None))
        self.assertIsNone(foreign_unit("mean", "was 14.76 g overall", 9, "g"))
        self.assertIsNotNone(foreign_unit("mean", "was 14.76 mm overall", 9, "g"))
        self.assertIsNone(foreign_unit("mean", "was 14.76 overall", 9, None))


class Records(unittest.TestCase):
    def test_record_layers_and_no_kernel_means_unknown(self):
        s = Policy.S1
        with tempfile.TemporaryDirectory() as tmp:
            result = verify([("c001", {"quote": s, "spec": {"stat": "mean", "reported": "14.76", "column": "mass"}}, "test")],
                            source_text=s, source_meta={"name": "t"}, data=DATA, manifest=MANIFEST, run_lean=False)
            rec = result["records"][0]
            self.assertEqual(rec["outward"]["verdict"], "UNKNOWN")                      # no kernel: nothing is established
            self.assertEqual(rec["mathematical"]["status"], "NOT_ESTABLISHED")
            self.assertIsNone(rec["mathematical"]["kernel_run"])
            self.assertEqual(rec["scientific"]["status"], "NOT_ASSESSED")
            self.assertFalse(rec["source_reading"]["reviewed_by_a_person"])
            index = write_bundle_v11(Path(tmp) / "b", result, source_text=s, data=DATA, manifest=MANIFEST, source_name="t", data_name="d.csv")
            self.assertEqual(index["counts"]["UNKNOWN"], 1)
            self.assertNotIn("is wrong", json.dumps(result["records"]).replace("does not show that the paper is wrong", ""))

    def test_attestation_is_recorded_but_changes_nothing(self):
        s = "The median age was 4 in this sample."
        receipts, decisions = run([s], [(0, {"stat": "median", "reported": "4", "column": "age"})])
        plain = build_record(receipts[0], decisions[0], selection=None, kernel_run=None)
        attested = build_record(receipts[0], decisions[0], selection=None, kernel_run=None,
                                human_review={"reviewer": "A. Person", "statement": "yes", "identity_verified_by_pcs": False})
        self.assertEqual(plain["outward"]["verdict"], attested["outward"]["verdict"])
        self.assertFalse(attested["source_reading"]["reviewed_by_a_person"])
        self.assertIsNotNone(attested["source_reading"]["human_review_on_record"])


class Runner(unittest.TestCase):
    RUNNER = HERE.parent / "claimcheck_kernel_runner.py"

    def _run(self, text: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.lean"
            path.write_text(text, encoding="utf-8")
            proc = subprocess.run([sys.executable, str(self.RUNNER), str(path), "--lean", "/nonexistent/lean"], capture_output=True, text=True)
            return json.loads(proc.stdout), proc.returncode

    def test_runner_rejects_before_running_lean(self):
        checker = (HERE.parents[1] / "claimcheck_v1" / "formal" / "ClaimCheck.lean").read_text(encoding="utf-8")
        marker = "\n-- ===== generated obligations (data numeral, claims, expected outcomes) =====\n"
        tail = ("open PCS.ClaimCheck\n\ndef pcs_src : Source := ⟨0x610a, 2⟩\n\ntheorem pcs_claim_0 : run pcs_src pcs_c0 = .undefined .x :=\n"
                "  run_of_runAll pcs_batch 0 rfl rfl\n#print axioms pcs_claim_0\n")
        for text, why in (("theorem x : True := trivial", "not a ClaimCheck proof file"),
                          (checker + "\n-- edited" + marker + tail, "not the reviewed checker"),
                          (checker + marker + tail + "\ntheorem y : False := by sorry\n", "forbidden token")):
            report, code = self._run(text)
            self.assertFalse(report["accepted"])
            self.assertNotEqual(code, 0)
            self.assertIn(why, report["why_not"])
        report, code = self._run(checker + marker + tail)                                # well formed, but no Lean available
        self.assertFalse(report["accepted"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
