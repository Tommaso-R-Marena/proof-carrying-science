"""Research-only independent checkpoint fault-injection tests.

The private Lean invocation is mocked ONLY to isolate the store/checkpoint
protocol in these Python unit tests. A separate CI live test uses actual Lean.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pgsc6_external_anchor import ExternallyAnchoredPGSC6, ExternalCheckpoint
from pgsc6_pinned_store import (
    PinnedPGSC6Store, RESEARCH, IntegrityFailure, StaleHead, ProposalRejected,
)
from pgsc6_reference import decode_certificate
from promotion_v2 import canonical

CERTS = tuple(
    (RESEARCH.parents[1] / "formal" / "fixtures" / "proof_gated" /
     "v6_certs" / f"step{i}.pgsc6").read_bytes() for i in (1, 2, 3)
)


class IndependentAnchorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pgsc6-anchor-")
        self.base = Path(self.temp.name)
        self.store_path = self.base / "model-store"
        self.anchor_path = self.base / "separate-trust"
        self.ctrl = ExternallyAnchoredPGSC6.initialize(
            self.store_path, self.anchor_path
        )

    def tearDown(self):
        self.temp.cleanup()

    def promote_mocked_host_only(self, raw, expected):
        with patch.object(self.ctrl.store, "_real_lean_authorizes",
                          return_value=True):
            return self.ctrl.promote(raw, expected)

    def test_independent_genesis_and_nonreinitialization(self):
        head = self.ctrl.audit()
        self.assertEqual(head.generation, 0)
        self.assertEqual(self.ctrl.snapshot(expected=head).head, head)
        with self.assertRaises(IntegrityFailure):
            ExternallyAnchoredPGSC6.initialize(self.store_path, self.anchor_path)
        with self.assertRaises(IntegrityFailure):
            ExternallyAnchoredPGSC6(self.store_path, self.store_path)

    def test_prevents_anchor_inside_store(self):
        with self.assertRaises(IntegrityFailure):
            ExternallyAnchoredPGSC6(self.store_path, self.store_path / "protected")
        with self.assertRaises(IntegrityFailure):
            ExternallyAnchoredPGSC6(self.store_path,
                                    self.base / "protected" / "..")

    def test_mocked_host_only_three_steps_and_replays(self):
        head = self.ctrl.audit()
        for i, raw in enumerate(CERTS):
            next_head = self.promote_mocked_host_only(raw, head)
            self.assertEqual(next_head.generation, i+1)
            self.assertEqual(next_head, self.ctrl.audit())
            self.assertEqual(self.ctrl.snapshot(expected=next_head).raw,
                             decode_certificate(raw).candidate)
            with self.assertRaises(StaleHead):
                self.ctrl.snapshot(expected=head)
            head = next_head
        with self.assertRaises(StaleHead):
            self.promote_mocked_host_only(CERTS[0], self.ctrl.store.audit().__class__(
                0, head.active_sha256, head.policy_sha256, head.last_receipt_sha256))

    def test_real_full_store_rollback_is_undetectable_without_anchor(self):
        initial = self.ctrl.audit()
        head1 = self.promote_mocked_host_only(CERTS[0], initial)
        # Complete and individually valid snapshot of prior HEAD, objects and
        # receipts. No symlinks or abnormal files: existing store audit passes.
        stored_backup = self.base / "backed-up-valid-model-store"
        shutil.copytree(self.store_path, stored_backup)
        head2 = self.promote_mocked_host_only(CERTS[1], head1)
        self.assertEqual(self.ctrl.audit(), head2)
        shutil.rmtree(self.store_path)
        shutil.copytree(stored_backup, self.store_path)
        self.assertEqual(self.ctrl.store.audit(), head1)  # vulnerability demonstrated
        with self.assertRaisesRegex(IntegrityFailure, "independent checkpoint"):
            self.ctrl.audit()
        with self.assertRaises(IntegrityFailure):
            self.ctrl.snapshot()
        with self.assertRaises(IntegrityFailure):
            self.promote_mocked_host_only(CERTS[1], head1)

    def test_invalid_certificate_never_advances_anchor(self):
        old = self.ctrl.audit()
        original = (self.anchor_path / "CHECKPOINT.json").read_bytes()
        for mutated in (CERTS[0] + b"\n", CERTS[1], b"", CERTS[0] + b"|1"):
            with self.subTest(mutated=mutated[:20]):
                with patch.object(self.ctrl.store, "_real_lean_authorizes") as mock:
                    with self.assertRaises(ProposalRejected):
                        self.ctrl.promote(mutated, old)
                    mock.assert_not_called()
                self.assertEqual(self.ctrl.audit(), old)
                self.assertEqual((self.anchor_path / "CHECKPOINT.json").read_bytes(),
                                 original)

    def test_crash_after_store_commit_before_checkpoint_is_fail_closed(self):
        before = self.ctrl.audit()
        anchor_bytes = (self.anchor_path / "CHECKPOINT.json").read_bytes()
        with patch.object(self.ctrl.store, "_real_lean_authorizes",
                          return_value=True):
            with patch("pgsc6_external_anchor._replace_head",
                       side_effect=OSError("simulated power failure")):
                with self.assertRaises(OSError):
                    self.ctrl.promote(CERTS[0], before)
        self.assertEqual(self.ctrl.store.audit().generation, 1)
        self.assertEqual((self.anchor_path / "CHECKPOINT.json").read_bytes(), anchor_bytes)
        with self.assertRaises(IntegrityFailure):
            self.ctrl.audit()
        with self.assertRaises(IntegrityFailure):
            self.ctrl.snapshot()

    def test_checkpoint_policy_or_identity_substitution_rejected(self):
        initial = self.ctrl.audit()
        path = self.anchor_path / "CHECKPOINT.json"
        raw = path.read_bytes()
        for wrong in (
            raw.replace(b"pgsc6-independent-checkpoint-v1",
                        b"pgsc6-untrusted-checkpoint-v1"),
            raw.replace(str(self.store_path).encode(), b"/tmp/other-store"),
            raw.replace(initial.policy_sha256.encode(), b"0" * 64),
        ):
            path.write_bytes(wrong)
            with self.assertRaises(IntegrityFailure):
                self.ctrl.audit()
            path.write_bytes(raw)
        self.assertEqual(self.ctrl.audit(), initial)

    def test_missing_checkpoint_refuses_even_valid_model_history(self):
        self.assertEqual(self.ctrl.audit().generation, 0)
        (self.anchor_path / "CHECKPOINT.json").unlink()
        with self.assertRaises(IntegrityFailure):
            self.ctrl.audit()

    def test_symlink_and_hardlink_checkpoint_rejected(self):
        cp = self.anchor_path / "CHECKPOINT.json"
        save = cp.read_bytes()
        cp.unlink()
        elsewhere = self.base / "external-contents"
        elsewhere.write_bytes(save)
        cp.symlink_to(elsewhere)
        with self.assertRaises(IntegrityFailure):
            self.ctrl.audit()
        cp.unlink()
        cp.write_bytes(save)
        linked = self.base / "checkpoint-linked"
        import os
        os.link(cp, linked)
        with self.assertRaises(IntegrityFailure):
            self.ctrl.audit()

    def test_same_privilege_anchor_replacement_is_not_protection(self):
        old = self.ctrl.audit()
        old_anchor = (self.anchor_path / "CHECKPOINT.json").read_bytes()
        head1 = self.promote_mocked_host_only(CERTS[0], old)
        backup = self.base / "old-store"
        # use genesis model history checkpoint (not head1)
        # all records from first completed generation are removed.
        (self.anchor_path / "CHECKPOINT.json").write_bytes(old_anchor)
        receipts = self.store_path / "receipts"
        for item in receipts.iterdir():
            item.unlink()
        (self.store_path / "HEAD.json").write_bytes(canonical(old.__dict__))
        self.assertEqual(self.ctrl.audit(), old)
        self.assertNotEqual(old, head1)
        # This is an explicit counterexample showing why independently
        # protected anchor credentials and storage matter.


if __name__ == "__main__":
    unittest.main()
