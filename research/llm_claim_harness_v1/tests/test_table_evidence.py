"""Adversarial and full-path tests for explicitly configured CSV evidence v5."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.llm_claim_harness_v1.core import Source, sha
from research.llm_claim_harness_v1.__main__ import main
from research.llm_claim_harness_v1.table_evidence import (
    UnsupportedTable, parse_table_spec, parse_table_rows, row_claim, run_table,
)
from research.llm_claim_harness_v1.typed import make_typed_lean_source

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CONFIG = json.loads((FIXTURES / "table_spec.json").read_text())
DATA = (FIXTURES / "table_data.csv").read_bytes()


def manifest(config=None):
    return json.dumps(CONFIG if config is None else config, sort_keys=True).encode("utf-8")


def source(data=DATA):
    return Source.from_bytes(data)


class FakeLean:
    def __init__(self):
        self.calls = []

    def check_typed(self, claim):
        code, truth = make_typed_lean_source(claim)
        self.calls.append((code, truth))
        return {"status": "TYPED_QTY_PROVED" if truth else "TYPED_QTY_REFUTED",
                "kernel_checked": True, "lean_source_sha256": sha(code.encode()), "lean_source": code}


class ManifestTests(unittest.TestCase):
    def test_spec_happy_path(self):
        spec = parse_table_spec(manifest())
        self.assertEqual(len(spec.columns), 3)
        self.assertEqual(len(spec.assertions), 2)
        self.assertEqual(spec.columns[1].unit, "m/s^2")
        self.assertEqual(spec.raw_sha256, sha(manifest()))

    def test_invalid_schema(self):
        for change in [{"schema": "unknown"}, {"schema": None}, {"columns": []}, {"assertions": []}]:
            with self.subTest(change=change), self.assertRaises(UnsupportedTable):
                parse_table_spec(manifest({**CONFIG, **change}))

    def test_unknown_top_level_fields(self):
        with self.assertRaisesRegex(UnsupportedTable, "schema"):
            parse_table_spec(manifest({**CONFIG, "model_generated": True}))

    def test_duplicate_object_key(self):
        payload = b'{"schema":"pcs-tabular-evidence-v5-research","schema":"pcs-tabular-evidence-v5-research","columns":[],"assertions":[]}'
        with self.assertRaisesRegex(UnsupportedTable, "duplicate JSON key"):
            parse_table_spec(payload)

    def test_nonfinite(self):
        with self.assertRaises(UnsupportedTable):
            parse_table_spec(manifest()[:-1] + b',"extra":NaN}')

    def test_invalid_encoding_and_empty(self):
        for payload in (b"", b"\xff", b" " * 8193, b"not json"):
            with self.subTest(payload=payload[:10]), self.assertRaises(UnsupportedTable):
                parse_table_spec(payload)

    def test_column_malformed(self):
        for column in [
            {"name": "bad-name", "unit": "kg"}, {"name": "mass", "unit": "rainbow"},
            {"name": "mass", "unit": "kg", "scale": 2}, {"name": False, "unit": "kg"},
            {"name": "mass", "unit": "degC"}, {"name": "mass", "unit": "kg^99"},
        ]:
            with self.subTest(column=column), self.assertRaises(UnsupportedTable):
                bad = copy.deepcopy(CONFIG)
                bad["columns"][0] = column
                parse_table_spec(manifest(bad))

    def test_duplicate_column_names(self):
        bad = copy.deepcopy(CONFIG)
        bad["columns"][1]["name"] = "mass"
        with self.assertRaises(UnsupportedTable):
            parse_table_spec(manifest(bad))

    def test_max_columns(self):
        bad = copy.deepcopy(CONFIG)
        bad["columns"] = [{"name": f"c{i}", "unit": "1"} for i in range(25)]
        with self.assertRaisesRegex(UnsupportedTable, "column count"):
            parse_table_spec(manifest(bad))

    def test_assertion_injection_and_duplicates(self):
        bad = copy.deepcopy(CONFIG)
        bad["assertions"][0]["expression"] = "mass = mass\n# sorry"
        with self.assertRaises(UnsupportedTable):
            parse_table_spec(manifest(bad))
        bad = copy.deepcopy(CONFIG)
        bad["assertions"][1]["id"] = bad["assertions"][0]["id"]
        with self.assertRaises(UnsupportedTable):
            parse_table_spec(manifest(bad))
        bad = copy.deepcopy(CONFIG)
        bad["assertions"][0]["proof"] = "by sorry"
        with self.assertRaises(UnsupportedTable):
            parse_table_spec(manifest(bad))

    def test_too_many_assertions(self):
        bad = copy.deepcopy(CONFIG)
        bad["assertions"] = [{"id": f"c{i}", "expression": "mass = mass"} for i in range(5)]
        with self.assertRaises(UnsupportedTable):
            parse_table_spec(manifest(bad))


class CSVTests(unittest.TestCase):
    def setUp(self):
        self.spec = parse_table_spec(manifest())

    def test_original_byte_offsets(self):
        s = source()
        rows = parse_table_rows(s, self.spec)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].number, 1)
        self.assertEqual(s.raw[rows[0].start:rows[0].end], b"2,3,6")
        self.assertEqual(s.raw[rows[1].start:rows[1].end], b"4,2,9")
        for row in rows:
            for cell in row.cells:
                self.assertEqual(s.raw[cell.start:cell.end].decode(), cell.value)
                self.assertEqual(cell.receipt()["raw_value_sha256"], sha(cell.value.encode()))

    def test_crlf_offsets(self):
        s = source(DATA.replace(b"\n", b"\r\n"))
        rows = parse_table_rows(s, self.spec)
        self.assertEqual(s.raw[rows[1].start:rows[1].end], b"4,2,9")
        self.assertEqual(rows[1].cells[2].value, "9")

    def test_no_trailing_newline(self):
        self.assertEqual(len(parse_table_rows(source(DATA.rstrip(b"\n")), self.spec)), 2)

    def test_exact_numeric_rejection(self):
        for malformed in [b"NaN", b"Inf", b"1e-3", b"=1+1", b"+2", b"-", b"", b" 2", b"2 ",
                          b"0x10", b".5", b"01", b"2.0000001", b"1/2", b"2;3"]:
            with self.subTest(malformed=malformed), self.assertRaises(UnsupportedTable):
                parse_table_rows(source(DATA.replace(b"2,3,6", malformed + b",3,6")), self.spec)

    def test_csv_injection_and_quotes(self):
        for payload in (b'"2",3,6', b"'2',3,6", b"\t2,3,6", b"2,3,6;rm", b"2,3,6\r\r\n"):
            with self.subTest(payload=payload), self.assertRaises(UnsupportedTable):
                parse_table_rows(source(DATA.replace(b"2,3,6", payload)), self.spec)

    def test_duplicate_header(self):
        with self.assertRaises(UnsupportedTable):
            parse_table_rows(source(DATA.replace(b"mass,acceleration,reported_force", b"mass,mass,reported_force")), self.spec)

    def test_reordered_columns(self):
        bad = DATA.replace(b"mass,acceleration,reported_force", b"acceleration,mass,reported_force")
        with self.assertRaisesRegex(UnsupportedTable, "header"):
            parse_table_rows(source(bad), self.spec)

    def test_missing_extra_cells(self):
        for line in (b"2,3", b"2,3,6,4"):
            with self.assertRaises(UnsupportedTable):
                parse_table_rows(source(DATA.replace(b"2,3,6", line)), self.spec)

    def test_blank_line_and_header_only(self):
        for data in (DATA.replace(b"2,3,6", b""), DATA.split(b"\n")[0] + b"\n"):
            with self.assertRaises(UnsupportedTable):
                parse_table_rows(source(data), self.spec)

    def test_row_budget(self):
        csv = DATA.split(b"\n")[0] + b"\n" + b"2,3,6\n" * 17
        with self.assertRaisesRegex(UnsupportedTable, "row count"):
            parse_table_rows(source(csv), self.spec)

    def test_utf8_non_ascii_rejected(self):
        with self.assertRaises(UnsupportedTable):
            parse_table_rows(source(DATA + "é".encode("utf-8")), self.spec)

    def test_invalid_last_row_prevents_any_lean(self):
        bad = source(DATA + b"1,2,bad\n")
        fake = FakeLean()
        with self.assertRaises(UnsupportedTable):
            run_table(bad, manifest(), lean=fake)
        self.assertEqual(fake.calls, [])


class FormalBoundaryTests(unittest.TestCase):
    def test_full_ast_and_outcomes(self):
        fake = FakeLean()
        receipt = run_table(source(), manifest(), lean=fake)
        self.assertEqual(len(fake.calls), 4)
        self.assertEqual([truth for _, truth in fake.calls], [True, True, False, True])
        self.assertIn("pcsMul", fake.calls[0][0])
        self.assertIn("pcsCompare", fake.calls[0][0])
        self.assertNotIn("sorry", fake.calls[0][0])
        self.assertEqual(receipt["counts"]["kernel_checked"], 4)
        self.assertEqual(receipt["schema_version"], "pcs-tabular-evidence-v5-research")
        self.assertTrue(all(r["status"] == "SEMANTIC_REVIEW_REQUIRED" for r in receipt["claims"]))
        self.assertTrue(all(r["scientific_status"] == "NOT_ASSESSED" for r in receipt["claims"]))
        self.assertFalse(receipt["template_human_review_verified"])

    def test_without_lean_cannot_verify(self):
        receipt = run_table(source(), manifest())
        self.assertEqual(receipt["counts"]["kernel_checked"], 0)
        self.assertTrue(all(r["formal_status"] == "KERNEL_UNAVAILABLE" for r in receipt["claims"]))

    def test_data_change_recomputes_ast_and_hash(self):
        a = run_table(source(), manifest(), lean=FakeLean())
        b = run_table(source(DATA.replace(b"4,2,9", b"5,2,9")), manifest(), lean=FakeLean())
        self.assertNotEqual(a["data_sha256"], b["data_sha256"])
        self.assertNotEqual(a["claims"][2]["ast_sha256"], b["claims"][2]["ast_sha256"])
        self.assertEqual(a["claims"][0]["ast_sha256"], b["claims"][0]["ast_sha256"])
        self.assertNotEqual(a["claims"][2]["csv_row_sha256"], b["claims"][2]["csv_row_sha256"])

    def test_manifest_unit_change_recomputes_dimension_or_rejects(self):
        bad = copy.deepcopy(CONFIG)
        bad["columns"][1]["unit"] = "m"
        fake = FakeLean()
        with self.assertRaises(UnsupportedTable):
            run_table(source(), manifest(bad), lean=fake)
        self.assertEqual(fake.calls, [])

    def test_manifest_formula_change_changes_hash(self):
        spec2 = copy.deepcopy(CONFIG)
        spec2["assertions"][0]["expression"] = "mass * acceleration != reported_force"
        a = run_table(source(), manifest(), lean=FakeLean())
        b = run_table(source(), manifest(spec2), lean=FakeLean())
        self.assertNotEqual(a["manifest_sha256"], b["manifest_sha256"])
        self.assertNotEqual(a["claims"][0]["template_expression_sha256"], b["claims"][0]["template_expression_sha256"])

    def test_unknown_column_in_formula_rejected(self):
        bad = copy.deepcopy(CONFIG)
        bad["assertions"][0]["expression"] = "mass * hidden_variable = reported_force"
        fake = FakeLean()
        with self.assertRaises(UnsupportedTable):
            run_table(source(), manifest(bad), lean=fake)
        self.assertEqual(fake.calls, [])

    def test_dimensional_mismatch_is_global_rejection(self):
        bad = copy.deepcopy(CONFIG)
        bad["assertions"][0]["expression"] = "mass + acceleration = reported_force"
        fake = FakeLean()
        with self.assertRaises(UnsupportedTable):
            run_table(source(), manifest(bad), lean=fake)
        self.assertEqual(fake.calls, [])

    def test_division_by_zero_global_rejection(self):
        bad = copy.deepcopy(CONFIG)
        bad["assertions"][0]["expression"] = "mass / (mass - mass) = reported_force"
        fake = FakeLean()
        with self.assertRaises(UnsupportedTable):
            run_table(source(), manifest(bad), lean=fake)
        self.assertEqual(fake.calls, [])

    def test_model_generated_lean_rejected(self):
        bad = copy.deepcopy(CONFIG)
        bad["assertions"][0]["expression"] = "mass = mass := by sorry"
        with self.assertRaises(UnsupportedTable):
            run_table(source(), manifest(bad), lean=FakeLean())

    def test_quantity_conversion_exact(self):
        config = copy.deepcopy(CONFIG)
        config["columns"] = [{"name": "x", "unit": "cm"}, {"name": "y", "unit": "m"}]
        config["assertions"] = [{"id": "length", "expression": "x = y"}]
        receipt = run_table(source(b"x,y\n100,1\n99,1\n"), manifest(config), lean=FakeLean())
        self.assertEqual([r["lhs_si"] for r in receipt["claims"]], ["1", "99/100"])
        self.assertEqual([r["formal_status"] for r in receipt["claims"]], ["TYPED_QTY_PROVED", "TYPED_QTY_REFUTED"])

    def test_evidence_linked_cell_hashes_and_spans(self):
        r = run_table(source(), manifest(), lean=FakeLean())
        for item in r["claims"]:
            cells = item["cell_anchors"]
            for cell in cells:
                start, end = cell["source_span"].values()
                self.assertEqual(sha(DATA[start:end]), cell["raw_value_sha256"])
            self.assertEqual(item["data_sha256"], r["data_sha256"])
            self.assertEqual(item["manifest_sha256"], r["manifest_sha256"])

    def test_single_row_typed_claim_generation(self):
        spec = parse_table_spec(manifest())
        row = parse_table_rows(source(), spec)[0]
        claim = row_claim(row, spec, spec.assertions[0])
        self.assertEqual(claim.lhs.quantity.value, 6)
        self.assertEqual(claim.rhs.quantity.value, 6)


class CLITests(unittest.TestCase):
    def test_deterministic_table_cli(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipt.json"
            rc = main(["--mode", "table", "--primary", "deterministic", "--source", str(FIXTURES / "table_data.csv"),
                       "--table-spec", str(FIXTURES / "table_spec.json"), "--out", str(path)])
            self.assertEqual(rc, 0)
            receipt = json.loads(path.read_text())
            self.assertEqual(len(receipt["claims"]), 4)
            self.assertEqual(receipt["counts"]["kernel_checked"], 0)

    def test_external_provider_forbidden(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipt.json"
            rc = main(["--mode", "table", "--primary", "gemini", "--allow-external", "--source", str(FIXTURES / "table_data.csv"),
                       "--table-spec", str(FIXTURES / "table_spec.json"), "--out", str(path)])
            self.assertEqual(rc, 1)
            self.assertFalse(path.exists())

    def test_missing_manifest_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipt.json"
            rc = main(["--mode", "table", "--primary", "deterministic", "--source", str(FIXTURES / "table_data.csv"),
                       "--out", str(path)])
            self.assertEqual(rc, 1)
            self.assertFalse(path.exists())

    def test_require_lean_nonzero_without_executable(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipt.json"
            rc = main(["--mode", "table", "--primary", "deterministic", "--source", str(FIXTURES / "table_data.csv"),
                       "--table-spec", str(FIXTURES / "table_spec.json"), "--lean", "__pcs_missing_lean_executable__",
                       "--require-lean", "--out", str(path)])
            self.assertEqual(rc, 2)
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text())["counts"]["kernel_checked"], 0)

    def test_no_network_in_table_mode(self):
        with tempfile.TemporaryDirectory() as td:
            with patch("research.llm_claim_harness_v1.providers.UrlLibTransport.post", side_effect=AssertionError("network")):
                rc = main(["--mode", "table", "--source", str(FIXTURES / "table_data.csv"),
                           "--table-spec", str(FIXTURES / "table_spec.json"), "--out", str(Path(td) / "receipt.json")])
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
