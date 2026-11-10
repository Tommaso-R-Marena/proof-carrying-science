"""Fail-closed and exact-rational checks for the v11 response-error corner audit."""
from fractions import Fraction
from pathlib import Path
import json
import tempfile
import unittest

from research.llm_claim_harness_v1.core import Source, canonical, sha
from research.llm_claim_harness_v1.ols_uncertainty_v11 import (
    UnsupportedUncertainty, parse_uncertainty_note, make_uncertainty_lean_source,
    run_uncertainty, replay_uncertainty, main,
)

FIX = Path(__file__).parents[1] / "fixtures"
DATA = (FIX / "ols_data.csv").read_bytes()
SPEC = (FIX / "ols_table_spec.json").read_bytes()
NOTE = (FIX / "ols_uncertainty_note_v11.txt").read_bytes()


class FakeLean:
    def __init__(self):
        self.calls = []

    def _check_generated(self, code, truth, scope):
        self.calls.append((code, truth, scope))
        return {"status": scope + "_PROVED", "kernel_checked": True,
                "lean_source_sha256": sha(code.encode()), "lean_source": code}


class MissingLean:
    def _check_generated(self, code, truth, scope):
        return {"status": "KERNEL_UNAVAILABLE", "kernel_checked": False,
                "lean_source_sha256": sha(code.encode()), "lean_source": code}


def src(data=DATA):
    return Source.from_bytes(data)


def note(data=DATA, manifest=SPEC, error="0.10", slope="0.08", intercept="0.14", x="x_cm", y="y_m"):
    return Source.from_bytes((
        f"PCS-OLS-UNCERTAINTY/1\ndata_sha256={sha(data)}\nmanifest_sha256={sha(manifest)}\n"
        f"x={x}\ny={y}\nresponse_error_si={error}\nmax_slope_shift_si={slope}\n"
        f"max_intercept_shift_si={intercept}\n").encode("ascii"))


class UncertaintyTests(unittest.TestCase):
    def test_fixture_note_exact(self):
        self.assertEqual(note().raw, NOTE)

    def test_complete_16_corners_and_exact_envelope(self):
        checker = FakeLean()
        result = run_uncertainty(src(), SPEC, src(NOTE), lean=checker)
        self.assertEqual(result["finite_corner_verdict"], "ALL_CORNERS_WITHIN_THRESHOLDS")
        self.assertTrue(result["kernel_checked"])
        metrics = result["metrics"]
        self.assertEqual(metrics["row_count"], 4)
        self.assertEqual(metrics["complete_corner_count"], 16)
        self.assertEqual(metrics["exact_affine_slope_radius_by_external_python"], "2/25")
        self.assertEqual(metrics["exact_affine_intercept_radius_by_external_python"], "7/50")
        self.assertEqual(len(metrics["corner_flags_by_external_python"]), 16)
        self.assertTrue(all(metrics["corner_flags_by_external_python"]))
        self.assertEqual(result["continuous_response_envelope"], "EXTERNAL_AFFINE_DERIVATION_NOT_KERNEL_PROVED")
        self.assertEqual(result["scientific_status"], "NOT_ASSESSED")
        self.assertEqual(len(checker.calls), 1)

    def test_source_byte_and_vertex_coverage_in_lean(self):
        code, _ = make_uncertainty_lean_source(src(), SPEC, src(NOTE))
        for required in ("pcsOLSRawCSV", "pcsOLSOriginalPairs", "pcsOLSUncertaintyRawNote",
                         "pcsAsciiDecimal (pcsByteSlice pcsOLSUncertaintyRawNote", "pcsOLSResponseCorners",
                         "pcsOLSRobustCorners.map List.length = some 16",
                         "pcsOLSRobustVerdict = some true", "pcsOLSRobustFlags.map List.length = some 16"):
            self.assertIn(required, code)
        self.assertEqual(code.count("pcsOLSRobustFlags.bind (fun flags => flags["), 16)
        for forbidden in ("sorry", "native_decide", "import Mathlib", "axiom ", "unsafe def"):
            self.assertNotIn(forbidden, code)

    def test_counterexample_for_tight_slope_tolerance(self):
        result = run_uncertainty(src(), SPEC, note(slope="0.07"), lean=FakeLean())
        self.assertEqual(result["finite_corner_verdict"], "COUNTEREXAMPLE_CORNER")
        self.assertIsNotNone(result["metrics"]["first_violating_corner_index"])
        self.assertIn("pcsOLSRobustVerdict = some false", result["lean_source"])

    def test_counterexample_for_tight_intercept_tolerance(self):
        result = run_uncertainty(src(), SPEC, note(intercept="0.13"), lean=FakeLean())
        self.assertEqual(result["finite_corner_verdict"], "COUNTEREXAMPLE_CORNER")

    def test_zero_uncertainty(self):
        result = run_uncertainty(src(), SPEC, note(error="0", slope="0", intercept="0"), lean=FakeLean())
        self.assertEqual(result["finite_corner_verdict"], "ALL_CORNERS_WITHIN_THRESHOLDS")

    def test_zero_tolerance_when_uncertainty_nonzero(self):
        result = run_uncertainty(src(), SPEC, note(slope="0", intercept="0"), lean=FakeLean())
        self.assertEqual(result["finite_corner_verdict"], "COUNTEREXAMPLE_CORNER")

    def test_perturbation_of_original_data_rejects_original_note(self):
        bad = DATA.replace(b"300,7", b"300,12")
        with self.assertRaises(UnsupportedUncertainty):
            make_uncertainty_lean_source(src(bad), SPEC, src(NOTE))

    def test_original_dataset_pin_not_bypassable_with_rewritten_note(self):
        bad = DATA.replace(b"300,7", b"300,12")
        with self.assertRaises(ValueError):
            run_uncertainty(src(bad), SPEC, note(bad), lean=FakeLean(), expected_data_sha256=sha(DATA))

    def test_manifest_pin(self):
        with self.assertRaises(ValueError):
            run_uncertainty(src(), SPEC, src(NOTE), lean=FakeLean(), expected_manifest_sha256="0"*64)

    def test_note_pin(self):
        with self.assertRaises(ValueError):
            run_uncertainty(src(), SPEC, src(NOTE), lean=FakeLean(), expected_note_sha256="0"*64)

    def test_missing_kernel_never_promotes(self):
        result = run_uncertainty(src(), SPEC, src(NOTE), lean=MissingLean())
        self.assertFalse(result["kernel_checked"])
        self.assertEqual(result["finite_corner_verdict"], "UNVERIFIED")
        self.assertEqual(result["formal_status"], "KERNEL_UNAVAILABLE")

    def test_default_missing_kernel(self):
        self.assertFalse(run_uncertainty(src(), SPEC, src(NOTE))["kernel_checked"])

    def test_receipt_replay_checks_fresh_kernel(self):
        checker = FakeLean()
        recorded = run_uncertainty(src(), SPEC, src(NOTE), lean=checker)
        out = replay_uncertainty(src(), SPEC, src(NOTE), canonical(recorded)+b"\n", lean=checker)
        self.assertEqual(out["status"], "REPLAYED_OLS_RESPONSE_CORNERS")
        self.assertTrue(out["matched"])
        self.assertEqual(len(checker.calls), 2)

    def test_receipt_replay_rejects_modified_metric(self):
        recorded = run_uncertainty(src(), SPEC, src(NOTE), lean=FakeLean())
        recorded["metrics"]["exact_affine_intercept_radius_by_external_python"] = "0"
        out = replay_uncertainty(src(), SPEC, src(NOTE), canonical(recorded), lean=FakeLean())
        self.assertFalse(out["matched"])

    def test_receipt_replay_refuses_missing_kernel(self):
        recorded = run_uncertainty(src(), SPEC, src(NOTE), lean=FakeLean())
        out = replay_uncertainty(src(), SPEC, src(NOTE), canonical(recorded), lean=MissingLean())
        self.assertEqual(out["status"], "KERNEL_UNAVAILABLE_OR_REJECTED")

    def test_receipt_replay_rejects_rewritten_note(self):
        recorded = run_uncertainty(src(), SPEC, src(NOTE), lean=FakeLean())
        out = replay_uncertainty(src(), SPEC, note(slope="0.09"), canonical(recorded), lean=FakeLean())
        self.assertEqual(out["status"], "RECEIPT_REJECTED")

    def test_no_duplicate_or_suffixed_fields(self):
        for invalid in (NOTE+b"extra=1\n", NOTE+b"\n", NOTE+b"max_slope_shift_si=0.08\n"):
            with self.subTest(invalid=invalid[-24:]), self.assertRaises(UnsupportedUncertainty):
                parse_uncertainty_note(src(invalid), src(), SPEC)

    def test_nonascii_cr_or_null_refused(self):
        for bad in (NOTE+b"\xc2\xb5", NOTE.replace(b"\n", b"\r\n", 1), NOTE.replace(b"0.10", b"0.\0", 1)):
            with self.assertRaises(ValueError):
                parse_uncertainty_note(src(bad), src(), SPEC)

    def test_bad_numbers(self):
        for invalid in ("-0.01", "+1", "1e-2", "0.0000001", "NaN", "infinity", "0; sorry", "01", "1/2", "1000001"):
            with self.subTest(invalid=invalid), self.assertRaises(UnsupportedUncertainty):
                parse_uncertainty_note(note(error=invalid), src(), SPEC)

    def test_wrong_column_rejected(self):
        for invalid in ("x_missing", "x_cm; sorry", "y_m --", "x_cm\nexample"):
            with self.assertRaises(UnsupportedUncertainty):
                parse_uncertainty_note(note(x=invalid), src(), SPEC)

    def test_degenerate_predictor_rejected(self):
        data = b"x_cm,y_m\n0,1\n0,3\n0,5\n0,7\n"
        with self.assertRaises(UnsupportedUncertainty):
            make_uncertainty_lean_source(src(data), SPEC, note(data))

    def test_too_many_records_rejected(self):
        data = b"x_cm,y_m\n" + b"0,1\n100,3\n"*3 + b"200,5\n"
        with self.assertRaisesRegex(UnsupportedUncertainty, "3..6"):
            make_uncertainty_lean_source(src(data), SPEC, note(data))

    def test_too_few_records_rejected(self):
        data = b"x_cm,y_m\n0,1\n100,3\n"
        with self.assertRaisesRegex(UnsupportedUncertainty, "3..6"):
            make_uncertainty_lean_source(src(data), SPEC, note(data))

    def test_invalid_trailing_data_rejected(self):
        data = DATA+b"400,not-a-number\n"
        with self.assertRaises(ValueError):
            make_uncertainty_lean_source(src(data), SPEC, note(data))

    def test_units_change_only_with_new_manifest_and_note(self):
        obj = json.loads(SPEC)
        obj["columns"][0]["unit"] = "m"
        changed_spec = canonical(obj)
        with self.assertRaises(UnsupportedUncertainty):
            make_uncertainty_lean_source(src(), changed_spec, src(NOTE))
        out = run_uncertainty(src(), changed_spec, note(manifest=changed_spec), lean=FakeLean())
        self.assertEqual(out["finite_corner_verdict"], "ALL_CORNERS_WITHIN_THRESHOLDS")
        self.assertEqual(out["metrics"]["exact_affine_slope_radius_by_external_python"], "1/1250")

    def test_6_row_full_64_corner_enumeration(self):
        data = b"x_cm,y_m\n0,1\n100,3\n200,5\n300,7\n400,9\n500,11\n"
        out = run_uncertainty(src(data), SPEC, note(data, slope="1", intercept="1"), lean=FakeLean())
        self.assertEqual(out["metrics"]["complete_corner_count"], 64)
        self.assertTrue(out["metrics"]["all_corners_within_tolerances_by_external_python"])

    def test_3_row_full_8_corner_enumeration(self):
        data = b"x_cm,y_m\n0,1\n100,3\n200,5\n"
        out = run_uncertainty(src(data), SPEC, note(data, slope="1", intercept="1"), lean=FakeLean())
        self.assertEqual(out["metrics"]["complete_corner_count"], 8)

    def test_cli_creates_unverified_receipt_without_lean(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out.json"
            code = main(["--source", str(FIX / "ols_data.csv"), "--table-spec", str(FIX / "ols_table_spec.json"),
                         "--uncertainty-note", str(FIX / "ols_uncertainty_note_v11.txt"),
                         "--out", str(path), "--lean", "__no_such_lean__"])
            self.assertEqual(code, 2)
            outcome = json.loads(path.read_text())
            self.assertFalse(outcome["kernel_checked"])
            self.assertEqual(outcome["finite_corner_verdict"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
