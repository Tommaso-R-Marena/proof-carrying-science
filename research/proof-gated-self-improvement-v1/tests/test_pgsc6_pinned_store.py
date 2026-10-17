"""Host-controller safety tests. Private Lean method is mocked in UNIT tests
for filesystem fault injection only. The separate live CI step invokes real
Lean V6 for complete positive/negative promotion evidence.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pgsc6_reference import decode_certificate
from pgsc6_pinned_store import (
    PinnedPGSC6Store, POLICY_DIGEST, INITIAL_BYTES, IntegrityFailure,
    StaleHead, ProposalRejected, RESEARCH, _read_regular
)

FIXTURES = RESEARCH.parents[1] / "formal" / "fixtures" / "proof_gated" / "v6_certs"
CERTS = tuple((FIXTURES / f"step{i}.pgsc6").read_bytes() for i in (1, 2, 3))


class PGSC6PinnedStoreSafety(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(prefix="pgsc6-store-tests-")
        self.root = Path(self.d.name) / "store"
        self.store = PinnedPGSC6Store.initialize(self.root)

    def tearDown(self):
        self.d.cleanup()

    def _accepted(self, certificate, head):
        # This mock proves only host state behavior, never Lean authorization.
        with patch.object(self.store, "_real_lean_authorizes", return_value=True):
            return self.store.promote(certificate, head)

    def test_fixed_genesis_and_nonreinitialization(self):
        head = self.store.audit()
        self.assertEqual(head.generation, 0)
        self.assertEqual(head.policy_sha256, POLICY_DIGEST)
        self.assertEqual(self.store.snapshot().raw, INITIAL_BYTES)
        self.assertEqual(self.store.snapshot().predict(-9), 0)
        with self.assertRaises(FileExistsError):
            PinnedPGSC6Store.initialize(self.root)

    def test_three_canonical_certificates_replayed_in_store(self):
        head = self.store.audit()
        seen = [head]
        for i, cert in enumerate(CERTS):
            self.assertEqual(decode_certificate(cert).generation, i)
            next_head = self._accepted(cert, head)
            self.assertEqual(next_head.generation, i + 1)
            self.assertEqual(self.store.audit(), next_head)
            self.assertEqual(self.store.snapshot(expected=next_head).raw,
                             decode_certificate(cert).candidate)
            with self.assertRaises(StaleHead):
                self.store.snapshot(expected=head)
            seen.append(next_head)
            head = next_head
        self.assertEqual(self.store.snapshot().predict(20), 5)
        self.assertEqual(len(list((self.root / "receipts").iterdir())), 3)
        with self.assertRaises(StaleHead):
            self._accepted(CERTS[0], seen[0])

    def test_rejects_forged_policy_and_mismatched_certificate_without_running_lean(self):
        head = self.store.audit()
        invalid = [
            CERTS[0].replace(b"|-1000000000|1000000000|",
                             b"|-1000000000|1000000001|", 1),
            CERTS[0].replace(b"|8|32|", b"|8|31|", 1),
            CERTS[0] + b"\n",
            CERTS[0][:-1] + b"0",
            CERTS[1],
        ]
        for bad in invalid:
            with self.subTest(raw=bad[:50]):
                with patch.object(self.store, "_real_lean_authorizes") as fake:
                    with self.assertRaises(ProposalRejected):
                        self.store.promote(bad, head)
                    fake.assert_not_called()
                self.assertEqual(self.store.audit(), head)

    def test_lean_negative_or_bogus_positive_fail_closed(self):
        head = self.store.audit()
        with patch.object(self.store, "_real_lean_authorizes", return_value=False):
            with self.assertRaises(ProposalRejected):
                self.store.promote(CERTS[0], head)
        self.assertEqual(self.store.audit(), head)
        with patch.object(self.store, "_real_lean_authorizes", side_effect=RuntimeError("broken")):
            with self.assertRaises(RuntimeError):
                self.store.promote(CERTS[0], head)
        self.assertEqual(self.store.audit(), head)

    def test_symlink_active_blob_is_refused(self):
        head = self.store.audit()
        p = self.store._model_path(head.active_sha256)
        save = p.read_bytes()
        p.unlink()
        alt = self.root / "other"
        alt.write_bytes(save)
        p.symlink_to(alt)
        with self.assertRaises(IntegrityFailure):
            self.store.audit()

    def test_receipt_corruption_and_orphan_refuse_future_promotions(self):
        head = self._accepted(CERTS[0], self.store.audit())
        receipt = self.root / "receipts" / "00000001.json"
        raw = receipt.read_bytes()
        receipt.write_bytes(raw.replace(b"real-Lean", b"fake-Lean"))
        with self.assertRaises(IntegrityFailure):
            self.store.audit()
        receipt.write_bytes(raw)
        self.assertEqual(self.store.audit(), head)
        (self.root / "receipts" / "00000002.json").write_bytes(raw)
        with self.assertRaises(IntegrityFailure):
            self.store.audit()

    def test_delete_and_rollback_fail_closed_if_head_is_not_consistent(self):
        head = self._accepted(CERTS[0], self.store.audit())
        receipt = self.root / "receipts" / "00000001.json"
        receipt.unlink()
        with self.assertRaises(IntegrityFailure):
            self.store.audit()

    def test_genesis_and_active_substitution_refused(self):
        head = self.store.audit()
        genesis = self.root / "GENESIS.json"
        original = genesis.read_bytes()
        genesis.write_bytes(original.replace(POLICY_DIGEST.encode(), b"0"*64))
        with self.assertRaises(IntegrityFailure):
            self.store.audit()
        genesis.write_bytes(original)
        self.assertEqual(self.store.audit(), head)
        (self.root / "HEAD.json").write_bytes(b'{"generation":0}')
        with self.assertRaises(IntegrityFailure):
            self.store.audit()

    def test_hardlinked_certificate_or_model_rejected(self):
        head = self.store.audit()
        p = self.store._model_path(head.active_sha256)
        q = self.root / "hardlink"
        os.link(p, q)
        with self.assertRaises(IntegrityFailure):
            self.store.audit()

    def test_partial_receipt_before_head_is_fail_closed(self):
        head = self.store.audit()
        # Simulate a crash after writing the new numbered receipt, before
        # atomically replacing HEAD. Never "repair" by blindly accepting it.
        (self.root / "receipts" / "00000001.json").write_bytes(b"{}")
        with self.assertRaises(IntegrityFailure):
            self.store.audit()

    def test_read_only_snapshot_does_not_reopen_mutable_paths(self):
        head = self.store.audit()
        snapshot = self.store.snapshot(expected=head)
        blob = self.store._model_path(head.active_sha256)
        blob.unlink()
        self.assertEqual(snapshot.raw, INITIAL_BYTES)
        self.assertEqual(snapshot.predict(7), 0)
        with self.assertRaises(IntegrityFailure):
            self.store.snapshot()

    def test_candidate_certificates_are_content_addressed(self):
        first = self._accepted(CERTS[0], self.store.audit())
        record = json.loads((self.root / "receipts" / "00000001.json").read_text())
        cpath = self.store._cert_path(record["certificate_sha256"])
        self.assertEqual(cpath.read_bytes(), CERTS[0])
        cpath.write_bytes(CERTS[0] + b"\n")
        with self.assertRaises(IntegrityFailure):
            self.store.audit()


if __name__ == "__main__":
    unittest.main()
