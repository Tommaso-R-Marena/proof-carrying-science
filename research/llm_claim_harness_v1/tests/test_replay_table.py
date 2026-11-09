"""Untrusted receipt replay tests: do not trust model, receipt or stored proof flags."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from research.llm_claim_harness_v1.core import Source, canonical
from research.llm_claim_harness_v1.replay_table import InvalidReceipt, main, parse_receipt, replay_table
from research.llm_claim_harness_v1.table_evidence import run_table
from research.llm_claim_harness_v1.tests.test_table_evidence import FakeLean, DATA, manifest


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.source = Source.from_bytes(DATA)
        self.manifest = manifest()
        self.initial = run_table(self.source, self.manifest, lean=FakeLean())
        self.bytes = canonical(self.initial) + b"\n"

    def test_exact_replay(self):
        r = replay_table(self.source, self.manifest, self.bytes, lean=FakeLean())
        self.assertEqual(r["status"], "REPLAYED_MATHEMATICAL_RECEIPT")
        self.assertTrue(r["matched"])
        self.assertEqual(r["kernel_replayed"], 4)
        self.assertEqual(r["scientific_status"], "NOT_ASSESSED")

    def test_replayed_missing_kernel_never_accepts_stored_success(self):
        r = replay_table(self.source, self.manifest, self.bytes)
        self.assertEqual(r["status"], "KERNEL_UNAVAILABLE_OR_REJECTED")
        self.assertFalse(r["matched"])
        self.assertEqual(r["kernel_replayed"], 0)

    def test_refuses_altered_claim_status(self):
        modified = copy.deepcopy(self.initial)
        modified["claims"][2]["formal_status"] = "TYPED_QTY_PROVED"
        r = replay_table(self.source, self.manifest, canonical(modified), lean=FakeLean())
        self.assertEqual(r["status"], "RECEIPT_REJECTED")

    def test_refuses_spoofed_kernel_bit(self):
        modified = copy.deepcopy(self.initial)
        modified["claims"][0]["kernel_checked"] = False
        r = replay_table(self.source, self.manifest, canonical(modified), lean=FakeLean())
        self.assertEqual(r["status"], "RECEIPT_REJECTED")

    def test_refuses_edited_proof_source(self):
        modified = copy.deepcopy(self.initial)
        modified["claims"][0]["lean_source"] += "\n-- metadata altered"
        r = replay_table(self.source, self.manifest, canonical(modified), lean=FakeLean())
        self.assertEqual(r["status"], "RECEIPT_REJECTED")

    def test_refuses_edited_cell_hash(self):
        modified = copy.deepcopy(self.initial)
        modified["claims"][1]["cell_anchors"][0]["raw_value_sha256"] = "0" * 64
        r = replay_table(self.source, self.manifest, canonical(modified), lean=FakeLean())
        self.assertEqual(r["status"], "RECEIPT_REJECTED")

    def test_refuses_data_change_before_lean(self):
        fake = FakeLean()
        source = Source.from_bytes(DATA.replace(b"4,2,9", b"5,2,9"))
        r = replay_table(source, self.manifest, self.bytes, lean=fake)
        self.assertEqual(r["status"], "RECEIPT_REJECTED")
        self.assertEqual(fake.calls, [])

    def test_refuses_manifest_change_before_lean(self):
        m = json.loads(self.manifest)
        m["columns"][0]["unit"] = "g"
        fake = FakeLean()
        r = replay_table(self.source, manifest(m), self.bytes, lean=fake)
        self.assertEqual(r["status"], "RECEIPT_REJECTED")
        self.assertEqual(fake.calls, [])

    def test_refuses_authority_promotion(self):
        modified = copy.deepcopy(self.initial)
        modified["authority"] = "PRODUCTION_PCS_V06_AUTHORITY"
        self.assertEqual(replay_table(self.source, self.manifest, canonical(modified), lean=FakeLean())["status"], "RECEIPT_REJECTED")

    def test_refuses_extra_replayed_claim(self):
        modified = copy.deepcopy(self.initial)
        modified["claims"].append(modified["claims"][0])
        self.assertEqual(replay_table(self.source, self.manifest, canonical(modified), lean=FakeLean())["status"], "RECEIPT_REJECTED")

    def test_refuses_incorrect_claim_count(self):
        modified = copy.deepcopy(self.initial)
        modified["counts"]["kernel_checked"] = 10
        self.assertEqual(replay_table(self.source, self.manifest, canonical(modified), lean=FakeLean())["status"], "RECEIPT_REJECTED")

    def test_refuses_noncanonical_byte_encoding(self):
        for bad in (json.dumps(self.initial, indent=2).encode(), b" " + self.bytes, self.bytes + b"\n"):
            with self.subTest(bad=bad[:10]), self.assertRaises(InvalidReceipt):
                parse_receipt(bad)

    def test_refuses_duplicate_key_and_nan(self):
        with self.assertRaises(InvalidReceipt):
            parse_receipt(b'{"a":1,"a":2}')
        with self.assertRaises(InvalidReceipt):
            parse_receipt(b'{"x":NaN}')

    def test_refuses_large_receipt(self):
        with self.assertRaisesRegex(InvalidReceipt, "size"):
            parse_receipt(b"x" * 2_000_001)

    def test_cli_missing_lean_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            src = path / "data.csv"
            spec = path / "spec.json"
            receipt = path / "receipt.json"
            outcome = path / "replay.json"
            src.write_bytes(DATA)
            spec.write_bytes(self.manifest)
            receipt.write_bytes(self.bytes)
            rc = main(["--source", str(src), "--table-spec", str(spec), "--receipt", str(receipt),
                       "--out", str(outcome), "--lean", "__pcs_missing_lean_executable__"])
            self.assertEqual(rc, 2)
            self.assertEqual(json.loads(outcome.read_text())["status"], "KERNEL_UNAVAILABLE_OR_REJECTED")


if __name__ == "__main__":
    unittest.main()
