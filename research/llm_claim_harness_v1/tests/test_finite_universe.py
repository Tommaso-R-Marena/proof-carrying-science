"""Offline, adversarial v6 finite-universe evidence tests; fake Lean is not a kernel proof."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from research.llm_claim_harness_v1.core import Source, canonical, sha
from research.llm_claim_harness_v1.finite_universe import (
    LEAN_FINITE_AGGREGATOR, SCHEMA, _prepared, make_finite_lean_source,
    replay_finite_universe, run_finite_universe, main,
)
from research.llm_claim_harness_v1.pipeline import LeanChecker
from research.llm_claim_harness_v1.table_evidence import UnsupportedTable

HERE = Path(__file__).resolve().parents[1] / "fixtures"
DATA = (HERE / "table_data.csv").read_bytes()
MANIFEST = (HERE / "table_spec.json").read_bytes()


class FakeLean:
    """Test double only, NEVER real proof evidence."""
    def __init__(self):
        self.calls = []

    def _check_generated(self, code, truth, scope):
        self.calls.append((code, truth, scope))
        return {"status": scope + ("_PROVED" if truth else "_REFUTED"),
                "kernel_checked": True, "lean_source_sha256": sha(code.encode()),
                "lean_source": code, "tested_relation": "source" if truth else "negation_of_source"}


def source(data=DATA):
    return Source.from_bytes(data)


def spec(config=None):
    if config is None:
        return MANIFEST
    return canonical(config)


class FiniteUniverseTests(unittest.TestCase):
    def test_two_aggregates_and_first_failing_row(self):
        lean = FakeLean()
        receipt = run_finite_universe(source(), spec(), lean=lean)
        self.assertEqual([c["formal_status"] for c in receipt["claims"]],
                         ["FINITE_UNIVERSE_REFUTED", "FINITE_UNIVERSE_PROVED"])
        self.assertEqual([x[1] for x in lean.calls], [False, True])
        self.assertEqual(receipt["counts"]["kernel_checked_aggregate_statements"], 2)
        self.assertEqual(receipt["counts"]["total_obligations"], 4)
        self.assertEqual(receipt["universe_size"], 2)
        first, second = receipt["claims"]
        self.assertEqual(first["first_counterexample"]["row_number"], 2)
        self.assertEqual(source().raw[first["first_counterexample"]["csv_row_span"]["start"]:
                                       first["first_counterexample"]["csv_row_span"]["end"]], b"4,2,9")
        self.assertIsNone(second["first_counterexample"])
        self.assertFalse(first["finite_relation_true_by_external_exact_arithmetic"])
        self.assertTrue(second["finite_relation_true_by_external_exact_arithmetic"])
        self.assertEqual([x[2] for x in lean.calls], ["FINITE_UNIVERSE"] * 2)
        self.assertTrue(all(c["scientific_status"] == "NOT_ASSESSED" for c in receipt["claims"]))
        self.assertEqual(receipt["template_origin"], "CALLER_SUPPLIED_UNATTESTED")
        self.assertNotIn("scientifically_certified", receipt)

    def test_formal_script_recalculates_all_terms_and_witness(self):
        _, rows, prepared = _prepared(source(), MANIFEST)
        code, truth, first_bad = make_finite_lean_source(prepared[0][1])
        self.assertFalse(truth)
        self.assertEqual(first_bad, 1)
        self.assertIn("def pcsAllChecks", code)
        self.assertIn("pcsMul", code)
        self.assertIn("pcsCompare", code)
        self.assertIn("List (Option Bool)", code)
        self.assertIn("= some false := by decide +kernel", code)
        self.assertIn("= 2 := by decide +kernel", code)
        self.assertGreaterEqual(code.count("example :"), 3)
        self.assertNotIn("sorry", code)
        self.assertNotIn("native_decide", code)
        self.assertNotIn("import ", code)
        self.assertEqual(code.count("pcsCompare"), 6)  # 1 definition; row terms in both goals plus counterexample

    def test_happy_all_true(self):
        data = DATA.replace(b"4,2,9", b"4,2,8")
        checked = run_finite_universe(source(data), MANIFEST, lean=FakeLean())
        self.assertTrue(all(c["formal_status"] == "FINITE_UNIVERSE_PROVED" for c in checked["claims"]))
        self.assertTrue(all(c["first_counterexample"] is None for c in checked["claims"]))
        self.assertTrue(all(c["finite_relation_true_by_external_exact_arithmetic"] for c in checked["claims"]))

    def test_first_counterexample_is_first_in_order_not_chosen(self):
        header = DATA.split(b"\n")[0]
        bad = header + b"\n2,3,7\n4,2,9\n"
        got = run_finite_universe(source(bad), MANIFEST, lean=FakeLean())
        self.assertEqual(got["claims"][0]["first_counterexample"]["row_number"], 1)

    def test_preserves_duplicate_observations_by_row_position(self):
        header = DATA.split(b"\n")[0]
        dat = header + b"\n2,3,6\n2,3,6\n2,3,6\n"
        r = run_finite_universe(source(dat), MANIFEST, lean=FakeLean())
        self.assertEqual(r["universe_size"], 3)
        self.assertEqual([x["row_number"] for x in r["row_anchors"]], [1, 2, 3])
        self.assertEqual(r["counts"]["total_obligations"], 6)

    def test_reordering_and_subsetting_change_universe(self):
        header, a, b = DATA.strip().split(b"\n")
        original = run_finite_universe(source(), MANIFEST, lean=FakeLean())
        reordered = run_finite_universe(source(header + b"\n" + b + b"\n" + a + b"\n"), MANIFEST, lean=FakeLean())
        subset = run_finite_universe(source(header + b"\n" + a + b"\n"), MANIFEST, lean=FakeLean())
        self.assertNotEqual(original["data_sha256"], reordered["data_sha256"])
        self.assertNotEqual(original["row_anchors"], reordered["row_anchors"])
        self.assertNotEqual(original["data_sha256"], subset["data_sha256"])
        self.assertNotEqual(original["universe_size"], subset["universe_size"])
        self.assertNotEqual(original["claims"][0]["formal_status"], subset["claims"][0]["formal_status"])
        # This intentionally shows the limit: a cherry-picked *different artifact*
        # can have an all-rows success, unless an external root pins the data hash.
        self.assertEqual(subset["claims"][0]["formal_status"], "FINITE_UNIVERSE_PROVED")

    def test_external_sha_pin_prevents_modified_or_cropped_artifact(self):
        pinned_hash = source().digest
        result = run_finite_universe(source(), MANIFEST, lean=FakeLean(), expected_data_sha256=pinned_hash)
        self.assertEqual(result["expected_data_sha256"], pinned_hash)
        self.assertEqual(result["data_pin_origin"], "CALLER_SUPPLIED_UNAUTHENTICATED")
        for changed in (DATA.replace(b"4,2,9", b"4,2,8"), DATA.split(b"\n")[0] + b"\n2,3,6\n"):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "commitment"):
                run_finite_universe(source(changed), MANIFEST, lean=FakeLean(), expected_data_sha256=pinned_hash)

    def test_invalid_external_sha_pin_rejected(self):
        for value in ("x" * 64, "A" * 64, "", "0" * 63, "0" * 65, True):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "SHA-256"):
                run_finite_universe(source(), MANIFEST, lean=FakeLean(), expected_data_sha256=value)

    def test_replay_requires_same_external_data_pin(self):
        pinned_hash = source().digest
        old = run_finite_universe(source(), MANIFEST, lean=FakeLean(), expected_data_sha256=pinned_hash)
        without_pin = replay_finite_universe(source(), MANIFEST, canonical(old), lean=FakeLean())
        self.assertEqual(without_pin["status"], "RECEIPT_REJECTED")
        with_pin = replay_finite_universe(source(), MANIFEST, canonical(old), lean=FakeLean(), expected_data_sha256=pinned_hash)
        self.assertEqual(with_pin["status"], "REPLAYED_FINITE_UNIVERSE")

    def test_crlf_grounding(self):
        data = DATA.replace(b"\n", b"\r\n")
        receipt = run_finite_universe(source(data), MANIFEST, lean=FakeLean())
        row_span = receipt["claims"][0]["first_counterexample"]["csv_row_span"]
        self.assertEqual(data[row_span["start"]:row_span["end"]], b"4,2,9")

    def test_manifest_change_recomputes_hash_and_obligations(self):
        cfg = json.loads(MANIFEST)
        cfg["assertions"][0]["expression"] = "reported_force = mass * acceleration"
        x = run_finite_universe(source(), MANIFEST, lean=FakeLean())
        y = run_finite_universe(source(), spec(cfg), lean=FakeLean())
        self.assertNotEqual(x["manifest_sha256"], y["manifest_sha256"])
        self.assertNotEqual(x["claims"][0]["expression_sha256"], y["claims"][0]["expression_sha256"])
        self.assertNotEqual(x["claims"][0]["lean_source_sha256"], y["claims"][0]["lean_source_sha256"])

    def test_rejects_malformed_later_row_before_any_lean(self):
        data = DATA + b"1,4,NaN\n"
        fake = FakeLean()
        with self.assertRaises(UnsupportedTable):
            run_finite_universe(source(data), MANIFEST, lean=fake)
        self.assertEqual(fake.calls, [])

    def test_rejects_dimension_change_before_lean(self):
        cfg = json.loads(MANIFEST)
        cfg["columns"][1]["unit"] = "s"
        fake = FakeLean()
        with self.assertRaises(UnsupportedTable):
            run_finite_universe(source(), spec(cfg), lean=fake)
        self.assertEqual(fake.calls, [])

    def test_rejects_proof_injection_before_lean(self):
        cfg = json.loads(MANIFEST)
        cfg["assertions"][0]["expression"] = "mass * acceleration = reported_force; by sorry"
        fake = FakeLean()
        with self.assertRaises(UnsupportedTable):
            run_finite_universe(source(), spec(cfg), lean=fake)
        self.assertEqual(fake.calls, [])

    def test_missing_lean_does_not_certify(self):
        receipt = run_finite_universe(source(), MANIFEST)
        self.assertEqual([c["formal_status"] for c in receipt["claims"]], ["KERNEL_UNAVAILABLE"] * 2)
        self.assertEqual(receipt["counts"]["kernel_checked_aggregate_statements"], 0)
        self.assertTrue(all(not c["kernel_checked"] for c in receipt["claims"]))

    def test_replay_full_exact_match(self):
        fake = FakeLean()
        prior = run_finite_universe(source(), MANIFEST, lean=fake)
        result = replay_finite_universe(source(), MANIFEST, canonical(prior) + b"\n", lean=FakeLean())
        self.assertTrue(result["matched"])
        self.assertEqual(result["status"], "REPLAYED_FINITE_UNIVERSE")

    def test_replay_rejects_modified_receipt(self):
        original = run_finite_universe(source(), MANIFEST, lean=FakeLean())
        for path, value in [("data_sha256", "deadbeef"), ("scientific_status", "CERTIFIED"),
                            ("universe_size", 1), ("authority", "PCS_V06_AUTHORITY")]:
            with self.subTest(path=path):
                altered = copy.deepcopy(original)
                altered[path] = value
                result = replay_finite_universe(source(), MANIFEST, canonical(altered), lean=FakeLean())
                self.assertFalse(result["matched"])
                self.assertEqual(result["status"], "RECEIPT_REJECTED")

    def test_replay_rejects_forged_counterexample(self):
        original = run_finite_universe(source(), MANIFEST, lean=FakeLean())
        altered = copy.deepcopy(original)
        altered["claims"][0]["first_counterexample"]["row_number"] = 1
        result = replay_finite_universe(source(), MANIFEST, canonical(altered), lean=FakeLean())
        self.assertEqual(result["status"], "RECEIPT_REJECTED")

    def test_replay_rejects_forged_kernel_and_source(self):
        original = run_finite_universe(source(), MANIFEST, lean=FakeLean())
        altered = copy.deepcopy(original)
        altered["claims"][0]["lean_source"] = "example : True := by trivial"
        result = replay_finite_universe(source(), MANIFEST, canonical(altered), lean=FakeLean())
        self.assertEqual(result["status"], "RECEIPT_REJECTED")

    def test_replay_missing_real_kernel_must_fail(self):
        original = run_finite_universe(source(), MANIFEST, lean=FakeLean())
        result = replay_finite_universe(source(), MANIFEST, canonical(original))
        self.assertEqual(result["status"], "KERNEL_UNAVAILABLE_OR_REJECTED")
        self.assertFalse(result["matched"])

    def test_replay_wrong_dataset_or_manifest_blocks_lean(self):
        orig = run_finite_universe(source(), MANIFEST, lean=FakeLean())
        fake = FakeLean()
        wrong = source(DATA.replace(b"4,2,9", b"4,2,8"))
        result = replay_finite_universe(wrong, MANIFEST, canonical(orig), lean=fake)
        self.assertEqual(result["status"], "RECEIPT_REJECTED")
        self.assertEqual(fake.calls, [])
        cfg = json.loads(MANIFEST)
        cfg["assertions"][0]["expression"] = "mass * acceleration != reported_force"
        result = replay_finite_universe(source(), spec(cfg), canonical(orig), lean=fake)
        self.assertEqual(result["status"], "RECEIPT_REJECTED")
        self.assertEqual(fake.calls, [])

    def test_replay_rejects_noncanonical_bytes(self):
        original = run_finite_universe(source(), MANIFEST, lean=FakeLean())
        text = json.dumps(original, indent=2).encode()
        with self.assertRaises(ValueError):
            replay_finite_universe(source(), MANIFEST, text, lean=FakeLean())

    def test_cli_returns_2_without_lean(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt_path = Path(tmp) / "result.json"
            status = main(["--source", str(HERE / "table_data.csv"),
                           "--table-spec", str(HERE / "table_spec.json"),
                           "--out", str(receipt_path), "--lean", "__no_such_lean__"])
            self.assertEqual(status, 2)
            self.assertTrue(receipt_path.exists())

    def test_no_empty_universe_vacuous_certification(self):
        header = DATA.split(b"\n")[0] + b"\n"
        with self.assertRaises(UnsupportedTable):
            run_finite_universe(source(header), MANIFEST, lean=FakeLean())

    def test_out_of_bounds_dataset(self):
        header = DATA.split(b"\n")[0] + b"\n"
        with self.assertRaises(UnsupportedTable):
            run_finite_universe(source(header + b"2,3,6\n" * 17), MANIFEST, lean=FakeLean())


if __name__ == "__main__":
    unittest.main()
