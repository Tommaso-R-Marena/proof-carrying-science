"""Fault-injection tests for protected PGSC6 authorization intents.

Private Lean invocation is MOCKED here ONLY to explore crash-state
transitions and attack surfaces. A separate live GitHub test re-runs the
actual Lean V6 checker in every recovered committed transaction.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from pgsc6_journaled_recovery import JournaledPGSC6
from pgsc6_external_anchor import ExternallyAnchoredPGSC6
from pgsc6_pinned_store import (
    RESEARCH, IntegrityFailure, StaleHead, ProposalRejected,
)
from promotion_v2 import canonical

CERTS = tuple(
    (RESEARCH.parents[1] / "formal" / "fixtures" / "proof_gated" /
     "v6_certs" / f"step{i}.pgsc6").read_bytes() for i in (1, 2, 3)
)


class InterruptedCommitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pgsc6-crash-")
        root = Path(self.tmp.name)
        self.store = root / "models"
        self.anchor = root / "authority"
        self.ctrl = JournaledPGSC6.initialize(self.store, self.anchor)

    def tearDown(self):
        self.tmp.cleanup()

    def _commit(self, cert, expected, fault=None):
        def crash(at):
            if at == fault:
                raise RuntimeError("simulated crash:" + at)
        with patch.object(self.ctrl.store, "_real_lean_authorizes", return_value=True):
            if fault is None:
                return self.ctrl.promote(cert, expected)
            with patch.object(self.ctrl, "_phase_hook", side_effect=crash):
                return self.ctrl.promote(cert, expected)

    def _recover(self):
        with patch.object(self.ctrl.store, "_real_lean_authorizes", return_value=True):
            return self.ctrl.recover()

    def test_no_pending_genesis_and_regular_promotion(self):
        head = self.ctrl.audit()
        self.assertEqual(head.generation, 0)
        self.assertEqual(self._recover(), "clean")
        next_head = self._commit(CERTS[0], head)
        self.assertEqual(next_head.generation, 1)
        self.assertFalse(self.ctrl.pending_path.exists())
        self.assertEqual(self.ctrl.audit(), next_head)
        self.assertEqual(self._recover(), "clean")

    def test_crash_after_intent_can_abort_only_with_exact_old_history(self):
        old = self.ctrl.audit()
        with self.assertRaisesRegex(RuntimeError, "intent_durable"):
            self._commit(CERTS[0], old, "intent_durable")
        self.assertEqual(self.ctrl.store.audit(), old)
        self.assertTrue(self.ctrl.pending_path.is_file())
        for call in (self.ctrl.audit, self.ctrl.snapshot):
            with self.assertRaises(IntegrityFailure):
                call()
        with self.assertRaises(IntegrityFailure):
            self._commit(CERTS[0], old)
        self.assertEqual(self._recover(), "aborted_before_commit")
        self.assertEqual(self.ctrl.audit(), old)
        head1 = self._commit(CERTS[0], old)
        self.assertEqual(head1.generation, 1)

    def test_crash_after_store_promote_rolls_forward_only_if_real_gate_rechecks(self):
        old = self.ctrl.audit()
        with self.assertRaisesRegex(RuntimeError, "store_committed"):
            self._commit(CERTS[0], old, "store_committed")
        self.assertEqual(self.ctrl.store.audit().generation, 1)
        self.assertEqual(self.ctrl._checkpoint_locked().head(), old)
        with self.assertRaises(IntegrityFailure):
            self.ctrl.snapshot()
        with patch.object(self.ctrl.store, "_real_lean_authorizes", return_value=False):
            with self.assertRaisesRegex(IntegrityFailure, "reauthorize"):
                self.ctrl.recover()
        with patch.object(self.ctrl.store, "_real_lean_authorizes", return_value=True):
            self.assertEqual(self.ctrl.recover(), "completed_one_committed_step")
        self.assertEqual(self.ctrl.audit().generation, 1)
        self.assertFalse(self.ctrl.pending_path.exists())

    def test_crash_after_anchor_commit_cleans_but_requires_evidence(self):
        old = self.ctrl.audit()
        with self.assertRaisesRegex(RuntimeError, "anchor_committed"):
            self._commit(CERTS[0], old, "anchor_committed")
        self.assertEqual(self.ctrl.store.audit().generation, 1)
        self.assertEqual(self.ctrl._checkpoint_locked().head().generation, 1)
        with self.assertRaises(IntegrityFailure):
            self.ctrl.audit()
        with patch.object(self.ctrl.store, "_real_lean_authorizes", return_value=False):
            with self.assertRaises(IntegrityFailure):
                self.ctrl.recover()
        self.assertEqual(self._recover(), "cleaned_committed_intent")
        self.assertEqual(self.ctrl.audit().generation, 1)

    def test_recovery_can_be_followed_by_another_generation(self):
        old = self.ctrl.audit()
        with self.assertRaises(RuntimeError):
            self._commit(CERTS[0], old, "store_committed")
        self._recover()
        first = self.ctrl.audit()
        second = self._commit(CERTS[1], first)
        self.assertEqual(second.generation, 2)
        self.assertEqual(self.ctrl.snapshot().head, second)

    def test_forged_candidate_cannot_recover_journal(self):
        old = self.ctrl.audit()
        with self.assertRaises(RuntimeError):
            self._commit(CERTS[0], old, "store_committed")
        receipt = self.store / "receipts" / "00000001.json"
        original = receipt.read_bytes()
        receipt.write_bytes(original.replace(b"real-Lean", b"fake-Lean"))
        with self.assertRaises(IntegrityFailure):
            self._recover()
        receipt.write_bytes(original)
        self.assertEqual(self._recover(), "completed_one_committed_step")

    def test_mutating_protected_intent_fail_closes(self):
        old = self.ctrl.audit()
        with self.assertRaises(RuntimeError):
            self._commit(CERTS[0], old, "intent_durable")
        path = self.ctrl.pending_path
        original = path.read_bytes()
        for modified in (original+b"\n", original.replace(b"pgsc6", b"pgsc5", 1)):
            path.write_bytes(modified)
            with self.assertRaises(IntegrityFailure):
                self._recover()
        path.write_bytes(original)
        self.assertEqual(self._recover(), "aborted_before_commit")

    def test_replaced_model_store_and_pending_intent_do_not_accept_rollback(self):
        first = self._commit(CERTS[0], self.ctrl.audit())
        backup = Path(self.tmp.name) / "previous-model-store"
        shutil.copytree(self.store, backup)
        with self.assertRaises(RuntimeError):
            self._commit(CERTS[1], first, "store_committed")
        # With protected journal=gen1->gen2 and anchor=gen1, replacing store
        # with old valid gen1 snapshot loses evidence gen2 ever existed.
        # This outcome is NOT safe globally without external commit witness.
        shutil.rmtree(self.store)
        shutil.copytree(backup, self.store)
        self.assertEqual(self.ctrl.store.audit(), first)
        self.assertEqual(self._recover(), "aborted_before_commit")
        self.assertEqual(self.ctrl.audit(), first)

    def test_stale_generation_no_intent_written(self):
        original = self.ctrl.audit()
        next_head = self._commit(CERTS[0], original)
        with self.assertRaises(StaleHead):
            self._commit(CERTS[1], original)
        self.assertFalse(self.ctrl.pending_path.exists())
        self.assertEqual(self.ctrl.audit(), next_head)

    def test_crash_with_orphan_receipts_never_auto_recovers(self):
        first = self._commit(CERTS[0], self.ctrl.audit())
        with self.assertRaises(RuntimeError):
            self._commit(CERTS[1], first, "intent_durable")
        (self.store / "receipts" / "00000002.json").write_bytes(b"{}")
        with self.assertRaises(IntegrityFailure):
            self._recover()
        self.assertTrue(self.ctrl.pending_path.exists())


if __name__ == "__main__":
    unittest.main()
