"""v9 OLS source-byte regression tests; mocked Lean is never kernel evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from research.llm_claim_harness_v1.core import Source, canonical, sha
from research.llm_claim_harness_v1.ols_integrated_v9 import (
    make_ols_lean_source, run_ols, replay_ols, main, UnsupportedOLS,
)
from research.llm_claim_harness_v1.table_evidence import UnsupportedTable

FIX = Path(__file__).resolve().parents[1] / "fixtures"
DATA = (FIX / "ols_data.csv").read_bytes()
SPEC = (FIX / "ols_table_spec.json").read_bytes()
PROPOSAL = (FIX / "ols_proposal.json").read_bytes()


class FakeLean:
    def __init__(self):
        self.calls = []

    def _check_generated(self, code, truth, scope):
        self.calls.append((code, truth, scope))
        return {"status": scope + "_PROVED", "kernel_checked": True,
                "lean_source": code, "lean_source_sha256": sha(code.encode())}


def source(raw=DATA):
    return Source.from_bytes(raw)


def claim(**updates):
    value = json.loads(PROPOSAL)
    value.update(updates)
    return canonical(value)


class OLSTests(unittest.TestCase):
    def test_complete_ols_in_one_proof_file(self):
        code, metrics = make_ols_lean_source(source(), SPEC, PROPOSAL)
        self.assertEqual([m["metric"] for m in metrics], ["slope", "intercept", "sse"])
        self.assertEqual([m["computed_exact_si_by_external_python"] for m in metrics], ["2", "1", "0"])
        self.assertTrue(all(m["candidate_matches_by_external_python"] for m in metrics))
        self.assertIn("pcsCSVFields pcsOLSRawCSV", code)
        self.assertIn("pcsOLSDelta", code)
        self.assertIn("pcsOLSFit", code)
        self.assertIn("pcsOLSMetric pcsOLSOriginalFit 0", code)
        self.assertIn("pcsCSVAllNumeric pcsOLSCSVRecords 4 2 = true", code)
        self.assertIn("pcsOLSCSVRecords.length = 5", code)
        self.assertIn("pcsOLSOriginalFit.isSome = true", code)
        self.assertIn("by decide +kernel", code)
        self.assertEqual(code.count("example :"), 10)
        self.assertNotIn("sorry", code)
        self.assertNotIn("native_decide", code)
        self.assertNotIn("import ", code)

    def test_single_lean_invocation_and_unreviewed_semantics(self):
        checker = FakeLean()
        result = run_ols(source(), SPEC, PROPOSAL, lean=checker)
        self.assertEqual(len(checker.calls), 1)
        self.assertEqual(checker.calls[0][2], "OLS_INTEGRATED")
        self.assertEqual(result["formal_status"], "OLS_INTEGRATED_PROVED")
        self.assertTrue(result["kernel_checked"])
        self.assertEqual(result["semantic_fidelity"], "UNREVIEWED")
        self.assertEqual(result["scientific_status"], "NOT_ASSESSED")
        self.assertEqual(result["submitted_rows"], 4)

    def test_actual_lean_missing_is_never_certification(self):
        self.assertEqual(run_ols(source(), SPEC, PROPOSAL)["formal_status"], "KERNEL_UNAVAILABLE")
        self.assertFalse(run_ols(source(), SPEC, PROPOSAL)["kernel_checked"])

    def test_forged_slope_intercept_sse_become_refutations(self):
        for metric in ("slope", "intercept", "sse"):
            cfg = json.loads(PROPOSAL)
            cfg["reported"][metric] = "3"
            code, report = make_ols_lean_source(source(), SPEC, canonical(cfg))
            target = next(r for r in report if r["metric"] == metric)
            self.assertFalse(target["candidate_matches_by_external_python"])
            self.assertIn(f"pcsOLSMetric pcsOLSOriginalFit {target['lean_metric_index']}", code)
            self.assertIn(" = some false := by decide +kernel", code)

    def test_nonzero_residual_statistic(self):
        altered = DATA.replace(b"300,7", b"300,8")
        result = run_ols(source(altered), SPEC, PROPOSAL, lean=FakeLean())
        metric = {r["metric"]:r for r in result["metrics"]}
        self.assertNotEqual(metric["sse"]["computed_exact_si_by_external_python"], "0")
        self.assertFalse(metric["sse"]["candidate_matches_by_external_python"])

    def test_exact_unit_scaling_changes_slope(self):
        cfg = json.loads(SPEC)
        cfg["columns"][0]["unit"] = "m"
        result = run_ols(source(), canonical(cfg), PROPOSAL, lean=FakeLean())
        self.assertEqual(result["metrics"][0]["computed_exact_si_by_external_python"], "1/50")
        self.assertFalse(result["metrics"][0]["candidate_matches_by_external_python"])

    def test_degenerate_design_refuses_before_lean(self):
        check = FakeLean()
        degenerate = DATA.replace(b"100,3", b"0,3").replace(b"200,5", b"0,5").replace(b"300,7", b"0,7")
        with self.assertRaisesRegex(UnsupportedOLS, "degenerate"):
            run_ols(source(degenerate), SPEC, PROPOSAL, lean=check)
        self.assertEqual(check.calls, [])

    def test_single_record_refused(self):
        reduced = DATA.split(b"\n")[0] + b"\n0,1\n"
        with self.assertRaisesRegex(UnsupportedOLS, "two"):
            run_ols(source(reduced), SPEC, PROPOSAL, lean=FakeLean())

    def test_additional_and_missing_column_refused(self):
        for data in [DATA.replace(b"x_cm,y_m", b"y_m,x_cm"), DATA.replace(b"200,5", b"200")]:
            with self.assertRaises(UnsupportedTable):
                run_ols(source(data), SPEC, PROPOSAL, lean=FakeLean())

    def test_corrupted_later_record_never_partial_lean(self):
        checker = FakeLean()
        for data in [DATA.replace(b"300,7", b"300,NaN"), DATA + b"500,"
                     , DATA.replace(b"100,3", b"100,=3")]:
            with self.subTest(data=data), self.assertRaises(UnsupportedTable):
                run_ols(source(data), SPEC, PROPOSAL, lean=checker)
        self.assertEqual(checker.calls, [])

    def test_changed_row_changes_proof_source(self):
        a = run_ols(source(), SPEC, PROPOSAL, lean=FakeLean())
        b = run_ols(source(DATA.replace(b"100,3", b"100,4")), SPEC, PROPOSAL, lean=FakeLean())
        self.assertNotEqual(a["data_sha256"], b["data_sha256"])
        self.assertNotEqual(a["lean_source_sha256"], b["lean_source_sha256"])

    def test_external_data_pin_detects_row_selection(self):
        checker = FakeLean()
        truncated = DATA.split(b"\n")[0] + b"\n" + DATA.split(b"\n")[1] + b"\n" + DATA.split(b"\n")[2] + b"\n"
        with self.assertRaisesRegex(ValueError, "pin"):
            run_ols(source(truncated), SPEC, PROPOSAL, lean=checker, expected_data_sha256=sha(DATA))
        self.assertEqual(checker.calls, [])

    def test_external_manifest_pin_detects_unit_reassignment(self):
        cfg = json.loads(SPEC)
        cfg["columns"][0]["unit"] = "m"
        with self.assertRaisesRegex(ValueError, "pin"):
            run_ols(source(), canonical(cfg), PROPOSAL, expected_manifest_sha256=sha(SPEC))

    def test_external_proposal_pin_detects_claim_substitution(self):
        altered = json.loads(PROPOSAL)
        altered["reported"]["slope"] = "3"
        with self.assertRaisesRegex(ValueError, "pin"):
            run_ols(source(), SPEC, canonical(altered), expected_proposal_sha256=sha(PROPOSAL))

    def test_invalid_sha_refused(self):
        for value in (None, "Z"*64, "0"*63, True):
            if value is None: continue
            with self.assertRaisesRegex(ValueError, "SHA256"):
                run_ols(source(), SPEC, PROPOSAL, expected_data_sha256=value)

    def test_missing_or_duplicate_reported_field(self):
        cfg = json.loads(PROPOSAL)
        del cfg["reported"]["sse"]
        with self.assertRaises(UnsupportedOLS):
            run_ols(source(), SPEC, canonical(cfg))
        malformed = PROPOSAL.decode().replace('"slope":', '"slope": "42", "slope":', 1)
        with self.assertRaises(UnsupportedTable):
            run_ols(source(), SPEC, malformed.encode())

    def test_json_numeric_values_not_accepted(self):
        cfg = json.loads(PROPOSAL)
        cfg["reported"]["sse"] = 0
        with self.assertRaises(UnsupportedOLS):
            run_ols(source(), SPEC, canonical(cfg))

    def test_negative_sse_proposal_refused(self):
        cfg = json.loads(PROPOSAL)
        cfg["reported"]["sse"] = "-1"
        with self.assertRaises(UnsupportedOLS):
            run_ols(source(), SPEC, canonical(cfg))

    def test_unsafe_symbols_and_injection_refused(self):
        for x in ("x_cm; sorry", "__import__('os')", "x_cm\nexample", 123):
            cfg = json.loads(PROPOSAL)
            cfg["x"] = x
            with self.subTest(x=x), self.assertRaises(UnsupportedOLS):
                run_ols(source(), SPEC, canonical(cfg))

    def test_unsupported_numeric_format_refused(self):
        for value in ("1e2", "NaN", "inf", "+2", "1/0", "1.00000001", "0 -- sorry"):
            cfg = json.loads(PROPOSAL)
            cfg["reported"]["slope"] = value
            with self.subTest(value=value), self.assertRaises(UnsupportedOLS):
                run_ols(source(), SPEC, canonical(cfg))

    def test_zero_x_variance_is_not_silently_inferred(self):
        data = b"x_cm,y_m\n0,1\n0,2\n0,3\n"
        with self.assertRaises(UnsupportedOLS):
            run_ols(source(data), SPEC, PROPOSAL)

    def test_more_than_eight_rows_refused(self):
        rows = b"x_cm,y_m\n" + b"0,1\n1,2\n"*5
        with self.assertRaisesRegex(UnsupportedOLS, "eight"):
            run_ols(source(rows), SPEC, PROPOSAL)

    def test_rational_proposal(self):
        cfg = json.loads(PROPOSAL)
        cfg["reported"]["slope"] = "4/2"
        result = run_ols(source(), SPEC, canonical(cfg), lean=FakeLean())
        self.assertTrue(result["metrics"][0]["candidate_matches_by_external_python"])

    def test_manifest_units_and_scientific_claim_not_promoted(self):
        report = run_ols(source(), SPEC, PROPOSAL, lean=FakeLean())
        self.assertEqual(report["pins_origin"], "CALLER_SUPPLIED_NOT_INDEPENDENTLY_AUTHENTICATED")
        self.assertEqual(report["authority"], "EXPERIMENTAL_NOT_PCS_V06_AUTHORITY")
        self.assertEqual(report["scientific_status"], "NOT_ASSESSED")
        self.assertIn("model suitability", report["scope"].lower())

    def test_receipt_replay_unchanged(self):
        old = run_ols(source(), SPEC, PROPOSAL, lean=FakeLean(), expected_data_sha256=sha(DATA))
        replay = replay_ols(source(), SPEC, PROPOSAL, canonical(old)+b"\n", lean=FakeLean(), expected_data_sha256=sha(DATA))
        self.assertEqual(replay["status"], "REPLAYED_INTEGRATED_OLS")
        self.assertTrue(replay["matched"])

    def test_receipt_replay_forgery_rejected(self):
        old = run_ols(source(), SPEC, PROPOSAL, lean=FakeLean())
        for key, value in (("kernel_checked", False), ("scientific_status", "CERTIFIED"),
                           ("lean_source", "example : True := by trivial"), ("formal_status", "PRODUCTION")):
            modified = copy.deepcopy(old)
            modified[key] = value
            result = replay_ols(source(), SPEC, PROPOSAL, canonical(modified), lean=FakeLean())
            self.assertEqual(result["status"], "RECEIPT_REJECTED")

    def test_receipt_replay_requires_fresh_kernel(self):
        old = run_ols(source(), SPEC, PROPOSAL, lean=FakeLean())
        result = replay_ols(source(), SPEC, PROPOSAL, canonical(old))
        self.assertEqual(result["status"], "KERNEL_UNAVAILABLE_OR_REJECTED")
        self.assertFalse(result["matched"])

    def test_replay_rejects_changed_data_before_lean(self):
        old = run_ols(source(), SPEC, PROPOSAL, lean=FakeLean())
        fake = FakeLean()
        replay = replay_ols(source(DATA.replace(b"100,3", b"100,4")), SPEC, PROPOSAL,
                            canonical(old), lean=fake)
        self.assertEqual(replay["status"], "RECEIPT_REJECTED")
        self.assertEqual(fake.calls, [])

    def test_cli_fails_closed_without_lean(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/"receipt.json"
            rc = main(["--source", str(FIX/"ols_data.csv"), "--table-spec", str(FIX/"ols_table_spec.json"),
                       "--ols-proposal", str(FIX/"ols_proposal.json"), "--out", str(out),
                       "--lean", "__pcs_missing_lean__"])
            self.assertEqual(rc, 2)
            self.assertFalse(json.loads(out.read_text())["kernel_checked"])

    def test_negative_controls_are_not_fake_kernel_results(self):
        raw = make_ols_lean_source(source(), SPEC, PROPOSAL)[0]
        self.assertIn("pcsOLSOriginalFit = some", raw)
        self.assertIn("pcsOLSMetric pcsOLSOriginalFit 1", raw)
        self.assertNotIn("def pcsOLSOriginalFit : Option PCSOLS := some", raw)


if __name__ == "__main__":
    unittest.main()
