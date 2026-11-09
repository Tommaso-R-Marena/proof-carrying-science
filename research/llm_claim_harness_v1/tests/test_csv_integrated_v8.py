"""v8 integrated byte-to-formal-all-rows tests (mocks are NOT kernel evidence)."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from research.llm_claim_harness_v1.core import Source, sha, canonical
from research.llm_claim_harness_v1.csv_integrated_v8 import (
    make_integrated_lean_source, run_integrated, replay_integrated, main,
)
from research.llm_claim_harness_v1.table_evidence import UnsupportedTable

FIX = Path(__file__).resolve().parents[1] / "fixtures"
DATA = (FIX / "table_data.csv").read_bytes()
SPEC = (FIX / "table_spec.json").read_bytes()


def source(data=DATA):
    return Source.from_bytes(data)


class FakeLean:
    def __init__(self):
        self.calls = []

    def _check_generated(self, code, truth, scope):
        self.calls.append((code, truth, scope))
        return {"status": scope + "_PROVED", "kernel_checked": True,
                "lean_source_sha256": sha(code.encode("utf-8")), "lean_source": code}


class IntegratedCSVTests(unittest.TestCase):
    def test_one_source_checks_header_shape_cells_and_every_claim(self):
        code, reports = make_integrated_lean_source(source(), SPEC)
        self.assertEqual(len(reports), 2)
        self.assertEqual([r["expected_relation_by_external_python"] for r in reports], [False, True])
        self.assertEqual([r["first_counterexample_row"] for r in reports], [2, None])
        self.assertIn("def pcsCSVFields", code)
        self.assertIn("pcsCSVRecords.head?", code)
        self.assertIn("pcsCSVValidWidths pcsCSVRecords 3 = true", code)
        self.assertIn("pcsCSVAllNumeric pcsCSVRecords 2 3 = true", code)
        self.assertIn("pcsCSVRecords.length = 3", code)
        self.assertIn("pcsAllChecks pcsCSVClaim_0) = some false", code)
        self.assertIn("pcsAllChecks pcsCSVClaim_1) = some true", code)
        self.assertIn("pcsCSVClaim_0[1]? = some (some false)", code)
        self.assertIn("pcsCSVQuantity pcsCSVRecords 1 2", code)
        self.assertIn("by decide +kernel", code)
        self.assertNotIn("sorry", code)
        self.assertNotIn("native_decide", code)
        self.assertNotIn("import ", code)
        self.assertEqual(code.count("example :"), 9)  # shape4, per-claim2+2, counterexample1

    def test_no_precomputed_source_magnitudes_as_proof_binding_leaves(self):
        code, _ = make_integrated_lean_source(source(), SPEC)
        self.assertIn("pcsCSVRead", code)
        self.assertIn("pcsAsciiDecimal", code)
        self.assertIn("pcsCSVQuantity pcsCSVRecords 0 0", code)
        self.assertNotIn("pcsLit ((9 : Rat) / (1 : Rat))", code)
        self.assertNotIn("pcsByteSlice pcsRawBytes", code)

    def test_one_lean_invocation_not_one_per_cell_or_row(self):
        checker = FakeLean()
        receipt = run_integrated(source(), SPEC, lean=checker)
        self.assertEqual(len(checker.calls), 1)
        self.assertEqual(checker.calls[0][2], "INTEGRATED_CSV")
        self.assertEqual(receipt["formal_status"], "INTEGRATED_CSV_PROVED")
        self.assertTrue(receipt["kernel_checked"])
        self.assertEqual(receipt["scientific_status"], "NOT_ASSESSED")
        self.assertEqual(receipt["semantic_fidelity"], "UNREVIEWED")
        self.assertEqual(receipt["submitted_record_count"], 2)
        self.assertEqual(len(receipt["claims"]), 2)
        self.assertIn("external", receipt["scope"].lower())

    def test_absent_kernel_never_certifies(self):
        receipt = run_integrated(source(), SPEC)
        self.assertEqual(receipt["formal_status"], "KERNEL_UNAVAILABLE")
        self.assertFalse(receipt["kernel_checked"])

    def test_altered_last_record_recomputes_evidence_and_outcome(self):
        changed = DATA.replace(b"4,2,9", b"4,2,8")
        a = run_integrated(source(), SPEC, lean=FakeLean())
        b = run_integrated(source(changed), SPEC, lean=FakeLean())
        self.assertNotEqual(a["data_sha256"], b["data_sha256"])
        self.assertNotEqual(a["lean_source_sha256"], b["lean_source_sha256"])
        self.assertFalse(a["claims"][0]["expected_relation_by_external_python"])
        self.assertTrue(b["claims"][0]["expected_relation_by_external_python"])
        self.assertIsNone(b["claims"][0]["first_counterexample_row"])

    def test_no_omitted_rows_within_submitted_data(self):
        truncated = DATA.split(b"\n")[0] + b"\n2,3,6\n"
        a, _ = make_integrated_lean_source(source(), SPEC)
        b, _ = make_integrated_lean_source(source(truncated), SPEC)
        self.assertIn("pcsCSVRecords.length = 3", a)
        self.assertIn("pcsCSVRecords.length = 2", b)
        self.assertNotEqual(a, b)
        self.assertEqual(run_integrated(source(truncated), SPEC, lean=FakeLean())["claims"][0]["expected_relation_by_external_python"], True)

    def test_data_pin_rejects_subset_and_reordered_rows(self):
        fixed = source().digest
        reordered = DATA.split(b"\n")[0] + b"\n4,2,9\n2,3,6\n"
        truncated = DATA.split(b"\n")[0] + b"\n2,3,6\n"
        fake = FakeLean()
        for changed in [truncated, reordered, DATA.replace(b"4,2,9", b"4,2,8")]:
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "pin"):
                run_integrated(source(changed), SPEC, lean=fake, expected_data_sha256=fixed)
        self.assertEqual(fake.calls, [])

    def test_manifest_pin_rejects_changed_unit_or_equation(self):
        pinned = sha(SPEC)
        cfg = json.loads(SPEC)
        fake = FakeLean()
        for change in ("unit", "equation"):
            config = copy.deepcopy(cfg)
            if change == "unit":
                config["columns"][0]["unit"] = "g"
            else:
                config["assertions"][0]["expression"] = "reported_force = mass * acceleration"
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "pin"):
                run_integrated(source(), canonical(config), lean=fake, expected_manifest_sha256=pinned)
        self.assertEqual(fake.calls, [])

    def test_both_pins_recorded_but_not_attested(self):
        result = run_integrated(source(), SPEC, lean=FakeLean(), expected_data_sha256=sha(DATA),
                                expected_manifest_sha256=sha(SPEC))
        self.assertEqual(result["commitment_origin"], "CALLER_PINNED_UNAUTHENTICATED")
        self.assertEqual(result["expected_data_sha256"], sha(DATA))
        self.assertEqual(result["expected_manifest_sha256"], sha(SPEC))

    def test_bad_digest_early_rejection(self):
        fake = FakeLean()
        for pin in ("Z" * 64, "A" * 64, "0" * 63, True, ""):
            with self.subTest(pin=pin), self.assertRaisesRegex(ValueError, "SHA256 pin"):
                run_integrated(source(), SPEC, lean=fake, expected_data_sha256=pin)
        self.assertEqual(fake.calls, [])

    def test_csv_crlf_and_no_final_newline_allowed(self):
        for data in (DATA.replace(b"\n", b"\r\n"), DATA.rstrip(b"\n"), DATA.replace(b"\n", b"\r\n").rstrip(b"\r\n")):
            with self.subTest(data=data):
                code, claims = make_integrated_lean_source(source(data), SPEC)
                self.assertIn("pcsDropFinalCR", code)
                self.assertEqual(claims[0]["first_counterexample_row"], 2)

    def test_precondition_validation_precedes_kernel(self):
        fake = FakeLean()
        for data in (DATA + b"2,NaN,3\n", DATA + b"2,3\n", DATA + b"2,3,4,5\n",
                     DATA.replace(b"2,3,6", b"2,3,=6"), DATA.replace(b"4,2,9", b"4,2,sorry"),
                     DATA.replace(b"mass,acceleration", b"acceleration,mass")):
            with self.subTest(data=data), self.assertRaises((ValueError, UnsupportedTable)):
                run_integrated(source(data), SPEC, lean=fake)
        self.assertEqual(fake.calls, [])

    def test_manifest_injection_rejected_before_kernel(self):
        fake = FakeLean()
        cfg = json.loads(SPEC)
        cfg["assertions"][0]["expression"] = "mass * acceleration = reported_force; by admit"
        with self.assertRaises((ValueError, UnsupportedTable)):
            run_integrated(source(), canonical(cfg), lean=fake)
        self.assertEqual(fake.calls, [])

    def test_duplicate_manifest_json_fields_rejected(self):
        text = SPEC.decode().replace('"columns":', '"columns":[],"columns":', 1)
        with self.assertRaises(UnsupportedTable):
            run_integrated(source(), text.encode(), lean=FakeLean())

    def test_late_bad_row_refuses_partial_lean(self):
        fake = FakeLean()
        raw = DATA + b"5,3,unavailable\n"
        with self.assertRaises(UnsupportedTable):
            run_integrated(source(raw), SPEC, lean=fake)
        self.assertEqual(fake.calls, [])

    def test_source_and_cell_budgets_enforced(self):
        fake = FakeLean()
        config = json.loads(SPEC)
        config["columns"].extend({"name": f"c{i}", "unit": "1"} for i in range(7))
        row = b",".join([b"2", b"3", b"6"] + [b"111111"] * 7)
        larger = b",".join(col["name"].encode() for col in config["columns"]) + b"\n" + (row + b"\n") * 16
        with self.assertRaisesRegex(ValueError, "bound"):
            run_integrated(source(larger), canonical(config), lean=fake)
        self.assertEqual(fake.calls, [])

    def test_replay_success_exact_bytes(self):
        prior = run_integrated(source(), SPEC, lean=FakeLean(), expected_data_sha256=sha(DATA))
        result = replay_integrated(source(), SPEC, canonical(prior)+b"\n", lean=FakeLean(),
                                   expected_data_sha256=sha(DATA))
        self.assertTrue(result["matched"])
        self.assertEqual(result["status"], "REPLAYED_INTEGRATED_CSV")

    def test_replay_requires_its_original_pins(self):
        prior = run_integrated(source(), SPEC, lean=FakeLean(), expected_data_sha256=sha(DATA))
        fake = FakeLean()
        result = replay_integrated(source(), SPEC, canonical(prior), lean=fake)
        self.assertEqual(result["status"], "RECEIPT_REJECTED")
        self.assertEqual(fake.calls, [])

    def test_replay_forged_claim_or_proof_rejected(self):
        prior = run_integrated(source(), SPEC, lean=FakeLean())
        for path, value in [("formal_status", "PRODUCTION_CERTIFIED"),
                            ("scientific_status", "CERTIFIED"),
                            ("kernel_checked", False),
                            ("lean_source", "example : True := by trivial")]:
            fake = FakeLean()
            mod = copy.deepcopy(prior)
            mod[path] = value
            result = replay_integrated(source(), SPEC, canonical(mod), lean=fake)
            self.assertFalse(result["matched"])
            self.assertEqual(result["status"], "RECEIPT_REJECTED")
        mod = copy.deepcopy(prior)
        mod["claims"][0]["first_counterexample_row"] = 1
        self.assertEqual(replay_integrated(source(), SPEC, canonical(mod), lean=FakeLean())["status"],
                         "RECEIPT_REJECTED")

    def test_replay_changes_do_not_call_kernel(self):
        old = run_integrated(source(), SPEC, lean=FakeLean())
        fake = FakeLean()
        changed = source(DATA.replace(b"4,2,9", b"4,2,8"))
        self.assertEqual(replay_integrated(changed, SPEC, canonical(old), lean=fake)["status"],
                         "RECEIPT_REJECTED")
        self.assertEqual(fake.calls, [])

    def test_replay_unavailable_kernel_fails(self):
        old = run_integrated(source(), SPEC, lean=FakeLean())
        status = replay_integrated(source(), SPEC, canonical(old))["status"]
        self.assertEqual(status, "KERNEL_UNAVAILABLE_OR_REJECTED")

    def test_replay_requires_canonical_json(self):
        old = run_integrated(source(), SPEC, lean=FakeLean())
        with self.assertRaises(ValueError):
            replay_integrated(source(), SPEC, json.dumps(old, indent=2).encode(), lean=FakeLean())

    def test_cli_without_lean_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "receipt.json"
            code = main(["--source", str(FIX / "table_data.csv"), "--table-spec", str(FIX / "table_spec.json"),
                         "--out", str(out), "--lean", "__pcs_nonexistent_lean__"])
            self.assertEqual(code, 2)
            self.assertFalse(json.loads(out.read_text())["kernel_checked"])

    def test_no_llm_generated_code_in_integrated_path(self):
        code, _ = make_integrated_lean_source(source(), SPEC)
        self.assertNotIn("BEGIN_UNTRUSTED", code)
        self.assertNotIn("admit", code)
        self.assertNotIn("--!", code)
        self.assertEqual(code.count("def pcsOriginalCSVBytes"), 1)

    def test_unit_coefficient_applied_inside_lean(self):
        cfg = json.loads(SPEC)
        cfg["columns"][0]["unit"] = "g"
        code, _ = make_integrated_lean_source(source(), canonical(cfg))
        self.assertIn("((1 : Rat) / (1000 : Rat))", code)
        self.assertIn("pcsCSVQuantity pcsCSVRecords 0 0", code)
        self.assertNotIn("PCS_V06_AUTHORITY", code)


if __name__ == "__main__":
    unittest.main()
