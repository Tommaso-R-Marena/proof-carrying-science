"""These tests exercise the POSIX storage protocol. Most use a fake positive
oracle to test atomicity; ONLY GitHub's end-to-end job uses the real Lean gate.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from proof_gate import Model, wire_bytes
from promotion_v2 import (
    ResearchPromotionStore, Head, IntegrityFailure, ProposalRejected,
    StaleHead, blob_hash, canonical, strict_json, receipt_hash
)

INITIAL = Model(True, 0, 0)
STEP1 = Model(True, 1, 1)
STEP2 = Model(True, 2, 1)

class PromotionStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pgsi-store-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "protected-store"
        self.store = ResearchPromotionStore.initialize(
            self.root, Path("/nonexistent-lean"), INITIAL)
        self.calls = 0

    def approve_mock(self, old: Path, candidate: Path, formal: Path) -> bool:
        # NOT a Lean oracle. Verifies that the store gives file paths to the
        # injected callback; transaction-only tests depend on it.
        self.calls += 1
        self.assertTrue(old.is_file())
        self.assertTrue(candidate.is_file())
        self.assertEqual(formal, Path("/nonexistent-lean"))
        return True

    def test_genesis_and_exact_blob_address(self):
        head, raw = self.store.read_active()
        self.assertEqual(head.generation, 0)
        self.assertEqual(head.active_sha256, blob_hash(wire_bytes(INITIAL)))
        self.assertEqual(raw, wire_bytes(INITIAL))
        self.assertEqual(self.store.audit(), head)

    def test_double_promotion_and_audit_chain_with_mock_oracle(self):
        a = self.store.snapshot()
        b = self.store.promote(wire_bytes(STEP1), a, self.approve_mock)
        c = self.store.promote(wire_bytes(STEP2), b, self.approve_mock)
        self.assertEqual(c.generation, 2)
        self.assertEqual(self.store.read_active()[1], wire_bytes(STEP2))
        self.assertNotEqual(b.last_receipt_sha256, c.last_receipt_sha256)
        self.assertEqual(self.calls, 2)
        self.assertEqual(self.store.audit(), c)

    def test_stale_generation_rejected_before_gate(self):
        a = self.store.snapshot()
        self.store.promote(wire_bytes(STEP1), a, self.approve_mock)
        with self.assertRaises(StaleHead):
            self.store.promote(wire_bytes(STEP2), a, self.approve_mock)
        self.assertEqual(self.calls, 1)

    def test_forged_expected_policy_rejected(self):
        a = self.store.snapshot()
        forged = Head(a.generation, a.active_sha256, "e"*64, a.last_receipt_sha256)
        with self.assertRaises(StaleHead):
            self.store.promote(wire_bytes(STEP1), forged, self.approve_mock)

    def test_negative_gate_does_not_commit(self):
        initial = self.store.snapshot()
        with self.assertRaises(ProposalRejected):
            self.store.promote(wire_bytes(STEP1), initial, lambda *_: False)
        self.assertEqual(self.store.snapshot(), initial)
        self.assertEqual(self.store.audit(), initial)

    def test_lean_missing_rejects_real_gate(self):
        initial = self.store.snapshot()
        with self.assertRaises(ProposalRejected):
            self.store.promote(wire_bytes(STEP1), initial)
        self.assertEqual(self.store.snapshot(), initial)

    def test_mutation_of_candidate_while_verifier_runs_is_detected(self):
        initial = self.store.snapshot()
        def fake_race(old, candidate, formal):
            # Corrupt the candidate *after* it is staged; fake "true" cannot
            # force promotion because hash validation is repeated afterward.
            candidate.write_bytes(b"PGSI1|R|30|30")
            return True
        with self.assertRaises(IntegrityFailure):
            self.store.promote(wire_bytes(STEP1), initial, fake_race)
        self.assertEqual(self.store.snapshot(), initial)
        with self.assertRaises(IntegrityFailure):
            self.store.audit() if False else self.store._blob(
                blob_hash(wire_bytes(STEP1)))

    def test_corrupted_active_model_is_detected(self):
        h = self.store.snapshot()
        self.store._blob_path(h.active_sha256).write_bytes(wire_bytes(STEP1))
        with self.assertRaises(IntegrityFailure):
            self.store.snapshot()

    def test_direct_head_tampering_fails_closed(self):
        h = self.store.snapshot()
        obj = h.__dict__.copy()
        obj["policy_sha256"] = "e"*64
        (self.root / "HEAD.json").write_bytes(canonical(obj))
        with self.assertRaises(IntegrityFailure):
            self.store.snapshot()

    def test_noncanonical_and_duplicate_json_fail(self):
        for raw in (b'{"x":1, "y":2}', b'{"x":1,"x":1}',
                    b'{"x":NaN}', b'{"a":1}\n'):
            with self.assertRaises(IntegrityFailure):
                strict_json(raw)

    def test_active_blob_symlink_rejected(self):
        h = self.store.snapshot()
        p = self.store._blob_path(h.active_sha256)
        data = p.read_bytes()
        p.unlink()
        substitute = Path(self.temp.name) / "redirect"
        substitute.write_bytes(data)
        p.symlink_to(substitute)
        with self.assertRaises(IntegrityFailure):
            self.store.snapshot()

    def test_active_blob_hardlink_rejected(self):
        h = self.store.snapshot()
        p = self.store._blob_path(h.active_sha256)
        alias = Path(self.temp.name) / "alias"
        os.link(p, alias)
        with self.assertRaises(IntegrityFailure):
            self.store.snapshot()

    def test_reinitialize_existing_root_refused(self):
        with self.assertRaises(FileExistsError):
            ResearchPromotionStore.initialize(self.root, Path("/nothing"), STEP1)

    def test_stale_and_missing_receipts_rejected(self):
        h = self.store.snapshot()
        newer = self.store.promote(wire_bytes(STEP1), h, self.approve_mock)
        self.assertEqual(self.store.audit(), newer)
        (self.root / "receipts" / "00000001.json").unlink()
        with self.assertRaises(IntegrityFailure):
            self.store.audit()

    def test_simple_head_rollback_detected_by_future_receipt(self):
        original = (self.root / "HEAD.json").read_bytes()
        self.store.promote(wire_bytes(STEP1), self.store.snapshot(), self.approve_mock)
        (self.root / "HEAD.json").write_bytes(original)
        with self.assertRaises(IntegrityFailure):
            self.store.audit()

    def test_crash_before_head_swap_is_fail_closed_orphan(self):
        old = self.store.snapshot()
        with patch("promotion_v2._replace_head", side_effect=RuntimeError("simulated crash")):
            with self.assertRaisesRegex(RuntimeError, "simulated crash"):
                self.store.promote(wire_bytes(STEP1), old, self.approve_mock)
        self.assertEqual(self.store.snapshot(), old)
        with self.assertRaises(IntegrityFailure):
            self.store.audit()

    def test_receipt_modification_detected(self):
        old = self.store.snapshot()
        self.store.promote(wire_bytes(STEP1), old, self.approve_mock)
        receipt = self.root / "receipts" / "00000001.json"
        obj = json.loads(receipt.read_text())
        obj["verification"] = "untrusted_override"
        receipt.write_bytes(canonical(obj))
        with self.assertRaises(IntegrityFailure):
            self.store.audit()

    def test_candidate_input_is_exact_and_size_bounded(self):
        old = self.store.snapshot()
        for candidate in (b"", b"x" * 999, "PGSI1|R|1|1"):
            with self.subTest(candidate=str(candidate)[:20]):
                with self.assertRaises(IntegrityFailure):
                    self.store.promote(candidate, old, self.approve_mock)
        self.assertEqual(self.calls, 0)


    def test_tampered_receipt_blocks_future_promotions(self):
        original = self.store.snapshot()
        first = self.store.promote(wire_bytes(STEP1), original, self.approve_mock)
        receipt = self.root / "receipts" / "00000001.json"
        receipt.write_bytes(b'{"forged":true}')
        with self.assertRaises(IntegrityFailure):
            self.store.promote(wire_bytes(STEP2), first, self.approve_mock)
        self.assertEqual(self.store.snapshot(), first)
        self.assertEqual(self.calls, 1)

    def test_concurrent_compare_and_swap_only_one_wins(self):
        from concurrent.futures import ThreadPoolExecutor
        initial = self.store.snapshot()
        def attempt(m):
            try:
                return self.store.promote(wire_bytes(m), initial, self.approve_mock)
            except StaleHead:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt, m) for m in (STEP1, STEP2)]
            outcomes = [f.result() for f in futures]
        self.assertEqual(sum(x is not None for x in outcomes), 1)
        self.assertEqual(self.store.audit().generation, 1)
        self.assertEqual(self.calls, 1)

if __name__ == "__main__":
    unittest.main()
