"""The outward verdict follows the kernel-established mathematical status, never a receipt's own summary.

Owner's pre-admission pass (2026-11-17): `policy._decide` used to pick its rules from the receipt's
`result` field, and its checks compared the verdict only with that field.  A receipt whose `result`
contradicted its kernel-checked variants could therefore be confirmed or flagged.  Now
`policy.established_status` recomputes the status from the variants (as the pipeline computes it) and
`policy.binding_problem` ties the claim to the sentence; a receipt that disagrees with either decides
nothing (UNKNOWN) and corroborates nothing.

Genuine receipts come from the real pipeline with a stand-in kernel that accepts every obligation
(as in test_binding_offline); every forgery below edits only what an attacker could edit in a receipt.
Out of scope here, by design: a receipt whose kernel record itself is a consistent lie (an outcome the
kernel never accepted, recorded as accepted).  The policy does not run Lean; the independent replay
re-runs the kernel on the re-derived obligation and refuses it (check_live_v11, tampering case
`forged_outcome`, with the real kernel).
"""
from __future__ import annotations

import copy
import itertools
import unittest
from unittest import mock

from research.claimcheck_v1 import pipeline
from research.claimcheck_v1_1.check_live_v11 import EXPECTED, PROPOSALS, TEXT
from research.claimcheck_v1_1.policy import assess_document, binding_problem, established_status, math_status
from research.claimcheck_v1_1.space import SourceContext
from research.claimcheck_v1_1.tests import test_binding_offline as binding
from research.claimcheck_v1_1.tests.test_binding_offline import accept_all
from research.claimcheck_v1_1.tests.test_v11_offline import DATA, MANIFEST
from research.claimcheck_v1_1.verify import verify

DECIDED = ("CONFIRMATION", "DISCREPANCY_FOR_REVIEW")


def genuine(proposals=PROPOSALS, text=TEXT):
    with mock.patch.object(pipeline, "check_items", side_effect=accept_all):
        return verify(proposals, source_text=text, source_meta={"name": "guard"}, data=DATA, manifest=MANIFEST)["v1_receipts"]


def verdicts(receipts, text=TEXT):
    decisions = assess_document(SourceContext(text, DATA, MANIFEST), receipts)
    return {r["claim_id"]: d for r, d in zip(receipts, decisions)}


def by_id(receipts, claim_id):
    return next(r for r in receipts if r["claim_id"] == claim_id)


class Guard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipts = genuine()
        cls.base = verdicts(cls.receipts)

    def forged(self, claim_id, edit, receipts=None):
        rs = copy.deepcopy(receipts or self.receipts)
        edit(by_id(rs, claim_id))
        return verdicts(rs), rs

    # ---- the genuine case is unchanged -----------------------------------------------------------
    def test_genuine_verdicts_and_statuses(self):
        for claim_id, (verdict, status) in EXPECTED.items():
            self.assertEqual(self.base[claim_id]["verdict"], verdict, claim_id)
            self.assertEqual(self.base[claim_id]["mathematical_status"], status, claim_id)
        for r in self.receipts:
            self.assertEqual(established_status(r), (math_status(r), None), r["claim_id"])
            self.assertIsNone(binding_problem(r, MANIFEST), r["claim_id"])

    # ---- the reported gap: a mutable `result` field ---------------------------------------------
    def test_a_flipped_result_decides_nothing(self):
        out, _ = self.forged("c001", lambda r: r.update(result="REFUTED"))      # kernel: match
        self.assertEqual(out["c001"]["verdict"], "UNKNOWN")
        self.assertEqual(out["c001"]["mathematical_status"], "NOT_ESTABLISHED")
        out, _ = self.forged("c002", lambda r: r.update(result="PROVED"))       # kernel: mismatch
        self.assertEqual(out["c002"]["verdict"], "UNKNOWN")

    def test_no_combination_of_summary_fields_decides_except_the_genuine_one(self):
        results = ("PROVED", "REFUTED", "UNKNOWN", "UNREVIEWED", None)
        statuses = ("PROVED", "REFUTED", "UNKNOWN", None)
        conditionals = (None, {"note": "forged"})
        reasons = ("checked", "statistic_undefined", "ambiguous_convention")
        tried = 0
        for claim_id in ("c001", "c002"):
            genuine_receipt = by_id(self.receipts, claim_id)
            g = (genuine_receipt.get("result"), genuine_receipt["q1_mathematics"].get("status"),
                 genuine_receipt["q1_mathematics"].get("conditional"), genuine_receipt.get("reason"))
            for combo in itertools.product(results, statuses, conditionals, reasons):
                def edit(r, combo=combo):
                    r["result"], r["q1_mathematics"]["status"], cond, r["reason"] = combo
                    if cond is None:
                        r["q1_mathematics"].pop("conditional", None)
                    else:
                        r["q1_mathematics"]["conditional"] = cond
                out, _ = self.forged(claim_id, edit)
                tried += 1
                if combo != g:
                    self.assertNotIn(out[claim_id]["verdict"], DECIDED, (claim_id, combo))
                else:
                    self.assertEqual(out[claim_id]["verdict"], self.base[claim_id]["verdict"])
        self.assertEqual(tried, 2 * 5 * 4 * 2 * 3)

    # ---- forged, downgraded or missing kernel evidence -----------------------------------------
    def test_forged_or_downgraded_variants_decide_nothing(self):
        def not_accepted(r):
            r["q1_mathematics"]["variants"][0]["lean"]["kernel_accepted"] = False

        def no_variants(r):
            r["q1_mathematics"]["variants"] = []

        def status_without_kernel(r):
            v = r["q1_mathematics"]["variants"][0]
            v["status"] = "REFUTED" if v["status"] == "PROVED" else "PROVED"

        def undefined_outcome(r):
            r["q1_mathematics"]["variants"][0]["predicted_outcome"] = {"defined": False, "reason": "degenerate"}

        def malformed(r):
            r["q1_mathematics"]["variants"][0]["lean"] = "accepted"

        for claim_id in ("c001", "c002"):
            for edit in (not_accepted, no_variants, status_without_kernel, undefined_outcome, malformed):
                out, _ = self.forged(claim_id, edit)
                self.assertEqual(out[claim_id]["verdict"], "UNKNOWN", (claim_id, edit.__name__))

    # ---- the claim must be the sentence's ---------------------------------------------------------
    def test_a_claim_about_another_number_or_statistic_decides_nothing(self):
        def other_number(r):
            r["claim"]["spec"]["reported"] = "14.75"                      # the printed literal is 14.76

        def other_statistic(r):
            r["q1_mathematics"]["variants"][0]["stat"] = "median"

        for edit in (other_number, other_statistic):
            out, _ = self.forged("c001", edit)
            self.assertEqual(out["c001"]["verdict"], "UNKNOWN", edit.__name__)

    def test_a_dropped_standard_deviation_convention_decides_nothing(self):
        receipts = genuine(binding.PROPOSALS, binding.TEXT)
        sd = by_id(receipts, "c003")                                       # n - 1 matches, n does not
        self.assertEqual(verdicts(receipts, binding.TEXT)["c003"]["verdict"], "REQUIRE_HUMAN_REVIEW")

        def drop(r):
            q1 = r["q1_mathematics"]
            q1["variants"] = [v for v in q1["variants"] if v["status"] == "PROVED"]
            q1.pop("conditional", None)
            q1["status"], r["result"], r["reason"] = "PROVED", "PROVED", "checked"
        rs = copy.deepcopy(receipts)
        drop(by_id(rs, "c003"))
        self.assertEqual(established_status(by_id(rs, "c003"))[1], None, "the forgery is internally consistent")
        self.assertIsNotNone(binding_problem(by_id(rs, "c003"), MANIFEST))
        self.assertEqual(verdicts(rs, binding.TEXT)["c003"]["verdict"], "UNKNOWN")
        self.assertEqual(sd["q1_mathematics"]["variants"][1]["stat"], "sd_pop")

    # ---- an inconsistent receipt corroborates nothing --------------------------------------------
    def test_forged_siblings_cannot_support_a_discrepancy(self):
        self.assertTrue(self.base["c002"]["corroborated_by"])
        rs = copy.deepcopy(self.receipts)
        siblings = [r for r in rs if r["claim_id"].startswith("s")]
        for r in siblings:
            r["q1_mathematics"]["variants"][0]["lean"]["kernel_accepted"] = False   # summary still says PROVED
        out = verdicts(rs)
        self.assertNotEqual(out["c002"]["verdict"], "DISCREPANCY_FOR_REVIEW")
        self.assertEqual(out["c002"]["corroborated_by"], [])
        for r in siblings:
            self.assertEqual(out[r["claim_id"]]["verdict"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
