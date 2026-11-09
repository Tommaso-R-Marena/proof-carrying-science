"""Offline tests for complete, note-bound finite leave-one-out OLS checks."""
import json
import tempfile
from fractions import Fraction
import unittest
from pathlib import Path

from research.llm_claim_harness_v1.core import Source, canonical, sha
from research.llm_claim_harness_v1.ols_stability_v10 import (
    UnsupportedStability, parse_stability_note, make_stability_lean_source,
    run_stability, replay_stability, main,
)

FIX = Path(__file__).parents[1] / "fixtures"
DATA = (FIX / "ols_data.csv").read_bytes()
SPEC = (FIX / "ols_table_spec.json").read_bytes()
NOTE = (FIX / "ols_stability_note_v10.txt").read_bytes()


class FakeLean:
    def __init__(self):
        self.calls = []

    def _check_generated(self, code, truth, scope):
        self.calls.append((code, truth, scope))
        return {"status": scope + "_PROVED", "kernel_checked": True,
                "lean_source": code, "lean_source_sha256": sha(code.encode())}


class MissingLean:
    def _check_generated(self, code, truth, scope):
        return {"status": "KERNEL_UNAVAILABLE", "kernel_checked": False,
                "lean_source": code, "lean_source_sha256": sha(code.encode())}


def source(data=DATA):
    return Source.from_bytes(data)


def note(data=DATA, manifest=SPEC, slope="0.10", intercept="0.10", x="x_cm", y="y_m"):
    result = (
        f"PCS-OLS-LOO/1\ndata_sha256={sha(data)}\nmanifest_sha256={sha(manifest)}\n"
        f"x={x}\ny={y}\nmax_slope_delta={slope}\nmax_intercept_delta={intercept}\n"
    )
    return Source.from_bytes(result.encode())


class StabilityTests(unittest.TestCase):
    def test_positive_complete_case(self):
        checker = FakeLean()
        result = run_stability(source(), SPEC, source(NOTE), lean=checker)
        self.assertTrue(result["kernel_checked"])
        self.assertEqual(result["finite_loo_verdict"], "ALL_DELETIONS_WITHIN_THRESHOLDS")
        self.assertEqual(result["metrics"]["complete_record_count"], 4)
        self.assertEqual(len(result["metrics"]["per_deletion"]), 4)
        self.assertEqual({r["deleted_row"] for r in result["metrics"]["per_deletion"]}, {1,2,3,4})
        self.assertTrue(all(r["within_threshold_by_external_python"] for r in result["metrics"]["per_deletion"]))
        self.assertEqual(result["scientific_status"], "NOT_ASSESSED")
        self.assertEqual(result["meaning_status"], "SEMANTIC_REVIEW_REQUIRED")
        self.assertEqual(len(checker.calls), 1)
        self.assertEqual(checker.calls[0][2], "OLS_LOO")

    def test_lean_script_binds_note_bytes_and_all_deletions(self):
        code, record = make_stability_lean_source(source(), SPEC, source(NOTE))
        self.assertIn("pcsOLSLOOFits", code)
        self.assertIn("pcsOLSRawCSV", code)
        self.assertIn("pcsOLSOriginalPairs", code)
        self.assertIn("pcsByteSlice pcsOLSLOORawNote", code)
        self.assertIn("pcsOLSStabilityVerdict = some true", code)
        self.assertIn("pcsOLSStabilityFlags.map List.length = some 4", code)
        self.assertIn("pcsCSVAllNumeric pcsOLSCSVRecords 4 2 = true", code)
        self.assertEqual(code.count("pcsOLSStabilityFlags.bind (fun fs => fs["), 4)
        self.assertEqual(len(record["threshold_source_spans"]), 2)
        self.assertNotIn("sorry", code)
        self.assertNotIn("native_decide", code)
        self.assertNotIn("import Mathlib", code)

    def test_falsification_when_single_row_is_influential(self):
        altered = DATA.replace(b"300,7", b"300,20")
        cfg = note(altered, slope="0.1", intercept="0.1")
        checker = FakeLean()
        out = run_stability(source(altered), SPEC, cfg, lean=checker)
        self.assertEqual(out["finite_loo_verdict"], "COUNTEREXAMPLE_TO_ALL_DELETIONS")
        self.assertIsNotNone(out["metrics"]["first_counterexample_row"])
        self.assertIn("pcsOLSStabilityVerdict = some false", checker.calls[0][0])
        self.assertIn("= some (some false) := by decide +kernel", checker.calls[0][0])

    def test_all_rows_considered_even_if_last_is_malformed(self):
        checker = FakeLean()
        altered = DATA + b"400,undefined\n"
        with self.assertRaises(ValueError):
            run_stability(source(altered), SPEC, note(altered), lean=checker)
        self.assertFalse(checker.calls)

    def test_dataset_omission_requires_new_source_note_and_pin(self):
        checker = FakeLean()
        truncated = DATA.split(b"300,7")[0]
        with self.assertRaises(UnsupportedStability):
            run_stability(source(truncated), SPEC, source(NOTE), lean=checker)
        self.assertFalse(checker.calls)
        with self.assertRaises(ValueError):
            run_stability(source(truncated), SPEC, note(truncated), lean=checker,
                          expected_data_sha256=sha(DATA))

    def test_missing_kernel_not_promoted(self):
        out = run_stability(source(), SPEC, source(NOTE), lean=MissingLean())
        self.assertEqual(out["formal_status"], "KERNEL_UNAVAILABLE")
        self.assertEqual(out["finite_loo_verdict"], "UNVERIFIED")
        self.assertFalse(out["kernel_checked"])

    def test_missing_no_native_lean(self):
        out = run_stability(source(), SPEC, source(NOTE))
        self.assertFalse(out["kernel_checked"])
        self.assertEqual(out["finite_loo_verdict"], "UNVERIFIED")

    def test_parse_canonical_offsets(self):
        parsed = parse_stability_note(source(NOTE), source(), SPEC)
        self.assertEqual(parsed.thresholds, (Fraction(1, 10), Fraction(1, 10)))
        for text, (start,end) in zip(parsed.originals, parsed.spans):
            self.assertEqual(NOTE[start:end], text.encode())

    def test_reject_modified_note_hash(self):
        for bad in [NOTE.replace(b"data_sha256=", b"data_sha256=1"),
                    NOTE.replace(b"manifest_sha256=", b"manifest_sha256=F")]:
            with self.assertRaises(UnsupportedStability):
                parse_stability_note(source(bad), source(), SPEC)

    def test_refuse_added_declaration_or_prose_suffix(self):
        for bad in [NOTE + b"extra=unsafe\n", NOTE + b"\n", NOTE + b"meaning=certified\n"]:
            with self.assertRaises(UnsupportedStability):
                parse_stability_note(source(bad), source(), SPEC)

    def test_reject_duplicate_field(self):
        bad = NOTE.replace(b"max_slope_delta=0.10\n", b"max_slope_delta=0.10\nmax_slope_delta=0.10\n")
        with self.assertRaises(UnsupportedStability):
            parse_stability_note(source(bad), source(), SPEC)

    def test_reject_out_of_order_fields(self):
        bad = NOTE.replace(b"max_slope_delta=0.10\nmax_intercept_delta=0.10\n",
                           b"max_intercept_delta=0.10\nmax_slope_delta=0.10\n")
        with self.assertRaises(UnsupportedStability):
            parse_stability_note(source(bad), source(), SPEC)

    def test_injection_cannot_enter_lean(self):
        for name in ("x_cm; sorry", "x_cm\nexample", "x_cm -- forged"):
            with self.subTest(name=name), self.assertRaises(UnsupportedStability):
                make_stability_lean_source(source(), SPEC, note(x=name))

    def test_invalid_thresholds(self):
        for value in ("-0.1", "1/2", "1e3", "+1", "NaN", "0 -- sorry", "1000001", "0.1234567", "inf"):
            with self.subTest(value=value), self.assertRaises(UnsupportedStability):
                parse_stability_note(note(slope=value), source(), SPEC)

    def test_accept_zero_threshold_for_exact_line(self):
        result = run_stability(source(), SPEC, note(slope="0", intercept="0"), lean=FakeLean())
        self.assertEqual(result["finite_loo_verdict"], "ALL_DELETIONS_WITHIN_THRESHOLDS")

    def test_lead_zero_not_accepted(self):
        with self.assertRaises(UnsupportedStability):
            parse_stability_note(note(slope="00.1"), source(), SPEC)

    def test_partial_loo_degenerate_raises(self):
        data = b"x_cm,y_m\n0,1\n0,2\n100,3\n"
        with self.assertRaisesRegex(UnsupportedStability, "deleting row"):
            make_stability_lean_source(source(data), SPEC, note(data))

    def test_two_rows_unsupported(self):
        data = b"x_cm,y_m\n0,1\n100,3\n"
        with self.assertRaisesRegex(UnsupportedStability, "3..8"):
            make_stability_lean_source(source(data), SPEC, note(data))

    def test_nine_rows_unsupported(self):
        data = b"x_cm,y_m\n" + b"0,1\n100,3\n" * 4 + b"200,5\n"
        with self.assertRaisesRegex(UnsupportedStability, "3..8"):
            make_stability_lean_source(source(data), SPEC, note(data))

    def test_accurate_units_must_match_original_schema(self):
        cfg = json.loads(SPEC)
        cfg["columns"][0]["unit"] = "m"
        manifest = canonical(cfg)
        with self.assertRaises(UnsupportedStability):
            run_stability(source(), manifest, source(NOTE), lean=FakeLean())
        out = run_stability(source(), manifest, note(DATA, manifest), lean=FakeLean())
        self.assertEqual(out["finite_loo_verdict"], "ALL_DELETIONS_WITHIN_THRESHOLDS")
        self.assertEqual(out["metrics"]["per_deletion"][0]["slope_exact_si"], "1/50")

    def test_reject_corrupt_csv_header(self):
        modified = DATA.replace(b"x_cm,y_m", b"x_cm,y_mm")
        with self.assertRaises(ValueError):
            run_stability(source(modified), SPEC, note(modified), lean=FakeLean())

    def test_exact_bounds_not_floating_point(self):
        changed = DATA.replace(b"300,7", b"300,8")
        result = run_stability(source(changed), SPEC, note(changed, slope="0.000001", intercept="0.000001"), lean=FakeLean())
        self.assertEqual(result["finite_loo_verdict"], "COUNTEREXAMPLE_TO_ALL_DELETIONS")
        self.assertTrue(all("/" not in row["deleted_row"].__str__() for row in result["metrics"]["per_deletion"]))

    def test_replay_rechecks_all_output(self):
        fake = FakeLean()
        original = run_stability(source(), SPEC, source(NOTE), lean=fake)
        replay = replay_stability(source(), SPEC, source(NOTE), canonical(original) + b"\n", lean=fake)
        self.assertTrue(replay["matched"])
        self.assertEqual(replay["status"], "REPLAYED_OLS_LOO")
        self.assertEqual(len(fake.calls), 2)

    def test_replay_refuses_modified_receipt(self):
        original = run_stability(source(), SPEC, source(NOTE), lean=FakeLean())
        original["metrics"]["first_counterexample_row"] = 1
        replay = replay_stability(source(), SPEC, source(NOTE), canonical(original), lean=FakeLean())
        self.assertFalse(replay["matched"])
        self.assertEqual(replay["status"], "RECEIPT_REJECTED")

    def test_replay_refuses_missing_lean(self):
        original = run_stability(source(), SPEC, source(NOTE), lean=FakeLean())
        replay = replay_stability(source(), SPEC, source(NOTE), canonical(original), lean=MissingLean())
        self.assertEqual(replay["status"], "KERNEL_UNAVAILABLE_OR_REJECTED")

    def test_replay_refuses_other_note(self):
        original = run_stability(source(), SPEC, source(NOTE), lean=FakeLean())
        result = replay_stability(source(), SPEC, note(slope="0.2"), canonical(original), lean=FakeLean())
        self.assertFalse(result["matched"])
        self.assertEqual(result["status"], "RECEIPT_REJECTED")

    def test_pin_checks_fail_before_lean(self):
        fake = FakeLean()
        for kw in ({"expected_data_sha256": "0"*64}, {"expected_manifest_sha256": "0"*64},
                   {"expected_note_sha256": "0"*64}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                run_stability(source(), SPEC, source(NOTE), lean=fake, **kw)
        self.assertFalse(fake.calls)

    def test_non_ascii_and_cr_refused(self):
        for bad in (NOTE.replace(b"0.10", "π".encode(), 1), NOTE.replace(b"\n", b"\r\n", 1), NOTE+b"\x00"):
            with self.assertRaises(ValueError):
                parse_stability_note(source(bad), source(), SPEC)

    def test_cli_without_lean_creates_truthful_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/"out.json"
            rc=main(["--source", str(FIX/"ols_data.csv"), "--table-spec", str(FIX/"ols_table_spec.json"),
                     "--stability-note", str(FIX/"ols_stability_note_v10.txt"), "--out", str(out),
                     "--lean", "__pcs_missing_lean_executable__"])
            self.assertEqual(rc, 2)
            self.assertEqual(json.loads(out.read_text())["finite_loo_verdict"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
