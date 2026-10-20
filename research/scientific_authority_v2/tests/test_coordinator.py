from dataclasses import replace
from fractions import Fraction
import shutil
import unittest
from unittest.mock import patch

from research.authorization_history_v1 import history
from research.scientific_witness_v1.protocol import decode_anchor
from research.scientific_authority_v2.coordinator import ScientificAuthority, AuthorityRejected, recover
from .support import Fixture, record


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.f = Fixture(); self.addCleanup(self.f.close)

    def authority(self, anchor=None):
        f = self.f
        return ScientificAuthority(f.local, f.root, anchor or f.anchor, f.config, f.client)

    def test_actual_verified_witnessed_admission_and_typed_statuses(self):
        authority = self.authority()
        snapshot = authority.submit(self.f.signed())
        self.assertEqual(snapshot.artifact.result.final_a, Fraction(7, 2))
        self.assertEqual(snapshot.anchor.generation, 1)
        self.assertFalse(snapshot.scientific_acceptance or snapshot.production_authority
                         or snapshot.model_promotion_authority)
        self.assertEqual(snapshot.independent_administration, "UNVERIFIED")
        self.assertEqual(snapshot.historical_math_status, "HISTORICALLY_REPLAYED")
        self.assertEqual(self.authority(snapshot.anchor).current().artifact.raw, snapshot.artifact.raw)

    def test_bad_science_never_changes_local_or_witness_commitment(self):
        authority = self.authority()
        before = self.f.local.read_bytes()
        with self.assertRaises(ValueError):
            authority.submit(self.f.signed(name="wrong-total"))
        self.assertEqual(self.f.local.read_bytes(), before)
        self.assertEqual(decode_anchor(self.f.client.checkpoint()["anchor"]), self.f.anchor)
        self.assertIsNone(self.f.client.checkpoint()["pending"])

    def test_audit_domain_limits_reject_before_witness_prepare(self):
        authority = self.authority()
        with patch.object(self.f.client, "prepare", side_effect=AssertionError("must not prepare")):
            with self.assertRaises(ValueError):
                authority.submit(self.f.signed(event_id=b"x" * 257))
        self.assertEqual(authority.current().anchor, self.f.anchor)

    def test_prepared_and_locally_committed_states_are_ineligible_until_finalized(self):
        f = self.f; raw = f.signed()
        f.client.prepare(raw)
        with self.assertRaises(AuthorityRejected): self.authority()
        with self.assertRaises(AuthorityRejected): recover(f.local, f.root, f.config, f.client)
        local = history.History(f.local, f.root, f.anchor).append(raw)
        with self.assertRaises(AuthorityRejected): self.authority(local)
        recovered = recover(f.local, f.root, f.config, f.client, resolve_pending=True)
        self.assertTrue(recovered.resolved_pending)
        self.assertFalse(recovered.new_authorization_created)
        self.assertEqual(self.authority(recovered.anchor).current().anchor.generation, 1)

    def test_finalized_without_local_commit_requires_exact_reconstruction(self):
        f = self.f; raw = f.signed()
        f.client.prepare(raw)
        from research.scientific_witness_v1.protocol import digest
        f.client.finalize(digest(raw))
        with self.assertRaises(AuthorityRejected): self.authority()
        recovered = recover(f.local, f.root, f.config, f.client)
        self.assertEqual(recovered.materialized_finalized_events, 1)
        self.assertFalse(recovered.new_authorization_created)
        self.assertEqual(self.authority(recovered.anchor).current().anchor.generation, 1)

    def test_whole_producer_store_rollback_is_detected_and_unknown_fork_refuses(self):
        f = self.f
        backup = f.out / "genesis.sqlite"; shutil.copyfile(f.local, backup)
        snapshot = self.authority().submit(f.signed())
        shutil.copyfile(backup, f.local)
        with self.assertRaises(AuthorityRejected): self.authority()
        recovered = recover(f.local, f.root, f.config, f.client)
        self.assertEqual(recovered.anchor, snapshot.anchor)
        shutil.copyfile(backup, f.local)
        history.History(f.local, f.root, f.anchor).append(f.signed(event_id=b"unwitnessed-fork"))
        before = f.local.read_bytes()
        with self.assertRaises(AuthorityRejected): recover(f.local, f.root, f.config, f.client)
        self.assertEqual(f.local.read_bytes(), before)

    def test_unavailable_witness_does_not_turn_cached_receipt_into_current_authority(self):
        f = self.f; authority = self.authority(); snapshot = authority.submit(f.signed())
        f.stop()
        with self.assertRaises(ValueError): authority.current()
        self.assertEqual(snapshot.artifact.result.final_a, Fraction(7, 2))
