"""Real Lean and real co-signatures; injected faults are rejection tests only."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from research.authorization_history_v1 import history
from research.scientific_receiver_v1 import host
from research.scientific_history_v1.receiver import (
    IntakeRejected, POLICY, ScientificReceivingLedger, checker_identity,
)


HERE = Path(__file__).resolve().parent
SCIENCE = HERE.parent / "scientific_receiver_v1"
FIXTURES = SCIENCE / "fixtures"


def real_config():
    executable = Path(os.environ.get("PCS_SCIENTIFIC_LEAN", "/workspace/.onboarding/tools/lean-4.28.0-linux/bin/lean"))
    main = Path(os.environ.get("PCS_SCIENTIFIC_MAIN", "/workspace/pcs-scientific-receiver-v1/research/scientific_receiver_v1/formal/Main.lean"))
    cwd = Path(os.environ.get("PCS_SCIENTIFIC_CWD", str(main.parent)))
    assert subprocess.check_output([str(executable), "--version"], text=True).startswith("Lean (version 4.28.0,")
    lean_path = os.environ.get("LEAN_PATH")
    if not lean_path:
        lean_path = json.loads(Path("/workspace/.onboarding/receiver-final-qualified-profile-v3/environment.json").read_bytes())["LEAN_PATH"]
    # Explicit partial fixture inventory: no complete loader/root attestation.
    sources = tuple(sorted((cwd / "PCSScientificReceiver").glob("*.lean")))
    assert main.read_bytes() == (SCIENCE / "formal/Main.lean").read_bytes()
    for source in sources:
        assert source.read_bytes() == (SCIENCE / "formal/PCSScientificReceiver" / source.name).read_bytes()
    dependency_roots = [Path(part) / "PCSScientificReceiver" for part in lean_path.split(os.pathsep)
                        if (Path(part) / "PCSScientificReceiver/Receiver.olean").is_file()]
    dependencies = tuple(sorted(dependency_roots[0].glob("*.olean"))) if dependency_roots else ()
    assert sources and dependencies, "Actual Lean source/import environment required; no mocked positive fallback"
    return host.operator_config_for_lean(
        executable=executable, main=main, cwd=cwd, lean_path=lean_path,
        source_files=(*sources, HERE / "receiver.py"), dependency_files=dependencies,
        toolchain="Lean 4.28.0; partial research fixture source/import inventory, not full root attestation")


def crash_worker(path, root, anchor, config, envelope, marker, after_commit):
    ledger = ScientificReceivingLedger(path, root, anchor, config)
    append = ledger._history.append

    def exit_after_real_verification(raw):
        if after_commit:
            append(raw)
        Path(marker).write_text("actual mathematical verification completed; committed=" + str(after_commit))
        os._exit(72 if after_commit else 71)

    ledger._history.append = exit_after_real_verification
    ledger.submit(envelope)


class ScientificHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = real_config()
        cls.genesis = (FIXTURES / "zero-step.wire").read_bytes()
        cls.candidate = (FIXTURES / "one-step.wire").read_bytes()

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "history.sqlite"
        # Two real fresh research keys; neither is independently protected/administered.
        self.authority, self.witness = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
        self.root = history.Root(self.authority.public_key().public_bytes_raw(),
                                 self.witness.public_key().public_bytes_raw(), POLICY,
                                 checker_identity(self.config), b"genesis", self.genesis)
        history.History.create(self.path, self.root)
        self.anchor = history.initial(self.root)
        self.ledger = ScientificReceivingLedger(self.path, self.root, self.anchor, self.config)

    def signed(self, raw=None, *, event_id=b"one", **changes):
        payload = history.proposed_payload(self.root, self.anchor, event_id=event_id,
                                           candidate=self.candidate if raw is None else raw, certificate=b"")
        payload = replace(payload, **changes)
        return history.Envelope(payload, self.authority.sign(payload.signing_bytes()),
                                self.witness.sign(payload.signing_bytes())).encode()

    def test_actual_valid_append_current_restart_and_frozen_results(self):
        snapshot = self.ledger.submit(self.signed())
        self.assertEqual(snapshot.candidate, self.candidate)
        self.assertEqual(snapshot.result.final_a, Fraction(7, 2))
        self.assertEqual(snapshot.result.total, Fraction(7))
        self.assertEqual(snapshot.result.step_count, 1)
        self.assertEqual(snapshot.raw_sha256, hashlib.sha256(self.candidate).hexdigest())
        self.assertFalse(snapshot.scientific_acceptance or snapshot.production_authority or snapshot.promotion_authority)
        self.assertIs(self.ledger.current(), snapshot)
        with self.assertRaises(FrozenInstanceError):
            snapshot.result.final_a = Fraction(0)
        reopened = ScientificReceivingLedger(self.path, self.root, snapshot.anchor, self.config)
        self.assertEqual(reopened.current(), snapshot)

    def test_truly_cosigned_invalid_scientific_claim_does_not_change_db(self):
        before = self.path.read_bytes()
        for name in ("wrong-total", "wrong-environment", "physical-intermediate-negative"):
            with self.subTest(fixture=name), self.assertRaises(IntakeRejected):
                self.ledger.submit(self.signed((FIXTURES / (name + ".wire")).read_bytes()))
            self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.ledger.current().anchor, self.anchor)

    def test_reserved_certificate_and_cosigned_wrong_scopes_reject_before_science(self):
        for changes in ({"certificate": b"untrusted-receipt"}, {"policy": b"other"},
                        {"checker": bytes(32)}, {"authority": bytes(32)}, {"witness": bytes(32)}):
            with patch.object(self.ledger._service, "verify_bytes", side_effect=AssertionError("must not verify")):
                with self.assertRaises(IntakeRejected):
                    self.ledger.submit(self.signed(**changes))
        self.assertEqual(self.ledger.current().anchor, self.anchor)

    def test_operator_root_must_bind_exact_profile_and_policy(self):
        changed_config = replace(self.config, timeout_seconds=59)
        self.assertEqual(checker_identity(self.config), hashlib.sha256(host._canonical(self.config.identity())).digest())
        with patch.object(host, "ReceiverService", side_effect=AssertionError("must not start")):
            for root, config in ((replace(self.root, policy=b"wrong"), self.config),
                                 (self.root, changed_config), (replace(self.root, checker=bytes(32)), self.config)):
                with self.assertRaises(IntakeRejected):
                    ScientificReceivingLedger(self.path, root, self.anchor, config)

    def test_submitter_cannot_supply_mutable_bytes_path_or_verifier(self):
        for value in (bytearray(self.signed()), self.path):
            with self.assertRaises(IntakeRejected):
                self.ledger.submit(value)
        with self.assertRaises(TypeError):
            self.ledger.submit(self.signed(), verifier=lambda _: True)

    def test_unsigned_candidate_tampering_never_launches_scientific_service(self):
        envelope = history.Envelope.decode(self.signed())
        tampered = replace(envelope, payload=replace(envelope.payload, candidate=self.genesis)).encode()
        before = self.path.read_bytes()
        with patch.object(self.ledger._service, "verify_bytes", side_effect=AssertionError("must not verify")):
            with self.assertRaises(history.Rejected):
                self.ledger.submit(tampered)
        self.assertEqual(self.path.read_bytes(), before)

    def test_bad_signatures_stale_and_replayed_intents_never_launch_scientific_service(self):
        stale = ScientificReceivingLedger(self.path, self.root, self.anchor, self.config)
        raw = self.signed()
        envelope = history.Envelope.decode(raw)
        with patch.object(self.ledger._service, "verify_bytes", side_effect=AssertionError("must not verify")):
            for bad in (replace(envelope, authority_signature=bytes(64)),
                        replace(envelope, witness_signature=bytes(64))):
                with self.assertRaises(history.Rejected):
                    self.ledger.submit(bad.encode())
        self.ledger.submit(raw)
        for ledger in (self.ledger, stale):
            with patch.object(ledger._service, "verify_bytes", side_effect=AssertionError("must not verify")):
                with self.assertRaises(history.Rejected):
                    ledger.submit(raw)

    def test_real_positive_for_other_raw_bytes_cannot_substitute(self):
        verify = self.ledger._service.verify_bytes
        before = self.path.read_bytes()
        with patch.object(self.ledger._service, "verify_bytes", side_effect=lambda _: verify(self.genesis)):
            with self.assertRaises(IntakeRejected):
                self.ledger.submit(self.signed())
        self.assertEqual(self.path.read_bytes(), before)

    def test_two_actual_verified_intents_race_then_only_one_sqlite_cas_commits(self):
        other = ScientificReceivingLedger(self.path, self.root, self.anchor, self.config)
        barrier = Barrier(2)
        originals = [ledger._service.verify_bytes for ledger in (self.ledger, other)]

        def verify_then_wait(index, raw):
            receipt = originals[index](raw)
            self.assertIs(receipt["receipt"]["accepted"], True)
            barrier.wait(timeout=30)
            return receipt

        signed = [self.signed(event_id=b"one"), self.signed(event_id=b"two")]
        with patch.object(self.ledger._service, "verify_bytes", side_effect=lambda raw: verify_then_wait(0, raw)), \
                patch.object(other._service, "verify_bytes", side_effect=lambda raw: verify_then_wait(1, raw)), \
                ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(ledger.submit, raw) for ledger, raw in zip((self.ledger, other), signed)]
            outcomes = []
            for future in futures:
                try:
                    outcomes.append(future.result(timeout=60))
                except history.Rejected:
                    outcomes.append(None)
        self.assertEqual(sum(item is not None for item in outcomes), 1)
        winner = next(item for item in outcomes if item is not None)
        self.assertEqual(winner.anchor.generation, 1)
        audit = history.History(self.path, self.root, winner.anchor).snapshot()
        self.assertEqual(len(audit.envelopes), 1)
        loser = other if outcomes[0] is not None else self.ledger
        with self.assertRaises(history.Rejected):
            loser.current()

    def test_current_audits_tampered_db_and_old_snapshot_never_reopens_it(self):
        snapshot = self.ledger.submit(self.signed())
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE head SET incumbent=?", (b"replaced",))
        with self.assertRaises(history.Rejected):
            self.ledger.current()
        self.assertEqual(snapshot.candidate, self.candidate)
        self.assertEqual(snapshot.result.final_a, Fraction(7, 2))

    def test_restart_rechecks_science_instead_of_trusting_signed_history(self):
        # The lower-level unchanged history authenticates intent, not mathematics.
        raw = self.signed((FIXTURES / "wrong-total.wire").read_bytes())
        authorized = history.History(self.path, self.root, self.anchor).append(raw)
        with self.assertRaises(IntakeRejected):
            ScientificReceivingLedger(self.path, self.root, authorized, self.config)

    def test_initial_incumbent_also_requires_actual_mathematical_verification(self):
        bad = (FIXTURES / "wrong-total.wire").read_bytes()
        root = replace(self.root, genesis_incumbent=bad)
        path = self.path.with_name("bad-genesis.sqlite")
        history.History.create(path, root)
        with self.assertRaises(IntakeRejected):
            ScientificReceivingLedger(path, root, history.initial(root), self.config)

    def test_valid_current_can_follow_invalid_cosigned_past_without_historical_audit(self):
        bad = (FIXTURES / "wrong-total.wire").read_bytes()
        self.assertIs(host.ReceiverService(self.config).verify_bytes(bad)["receipt"]["accepted"], False)
        lower_level = history.History(self.path, self.root, self.anchor)
        bad_anchor = lower_level.append(self.signed(bad))
        payload = history.proposed_payload(self.root, bad_anchor, event_id=b"valid-successor",
                                           candidate=self.candidate, certificate=b"")
        signed = history.Envelope(payload, self.authority.sign(payload.signing_bytes()),
                                   self.witness.sign(payload.signing_bytes())).encode()
        final = lower_level.append(signed)
        reopened = ScientificReceivingLedger(self.path, self.root, final, self.config)
        self.assertEqual(reopened.current().candidate, self.candidate)
        self.assertFalse(reopened.current().historical_scientific_audit)
        self.assertEqual(lower_level.snapshot().envelopes[0].payload.candidate, bad)

    def test_write_failure_after_actual_verify_returns_no_new_snapshot(self):
        before = self.path.read_bytes()
        with patch.object(self.ledger._history, "append", side_effect=sqlite3.OperationalError("negative-only write fault")) as append:
            with self.assertRaises(sqlite3.OperationalError):
                self.ledger.submit(self.signed())
            self.assertEqual(append.call_count, 1)  # Reached only after actual verified result.
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.ledger.current().anchor, self.anchor)

    def test_lost_return_after_real_commit_cannot_continue_without_explicit_recovery(self):
        raw = self.signed()
        append = self.ledger._history.append

        def commit_then_fail(captured):
            append(captured)
            raise OSError("negative-only lost return after actual commit")

        with patch.object(self.ledger._history, "append", side_effect=commit_then_fail):
            with self.assertRaises(OSError):
                self.ledger.submit(raw)
        advanced = self.ledger._history.expected_anchor
        next_payload = history.proposed_payload(self.root, advanced, event_id=b"two",
                                                candidate=self.genesis, certificate=b"")
        successor = history.Envelope(next_payload, self.authority.sign(next_payload.signing_bytes()),
                                      self.witness.sign(next_payload.signing_bytes())).encode()
        with self.assertRaises(IntakeRejected):
            self.ledger.current()
        with patch.object(self.ledger._service, "verify_bytes", side_effect=AssertionError("must recover")):
            with self.assertRaises(IntakeRejected):
                self.ledger.submit(successor)
        recovered = history.recover(self.path, self.root, previous=self.anchor, expected_envelope=raw)
        restarted = ScientificReceivingLedger(self.path, self.root, recovered, self.config)
        self.assertEqual(restarted.current().anchor.generation, 1)

    def test_actual_process_crash_after_verify_and_after_commit_explicit_recovery(self):
        context = multiprocessing.get_context("spawn")
        signed = self.signed()
        before = self.path.read_bytes()
        for committed in (False, True):
            marker = self.path.with_name("verified-" + str(committed))
            worker = context.Process(target=crash_worker, args=(self.path, self.root, self.anchor,
                                     self.config, signed, marker, committed))
            worker.start()
            worker.join(timeout=90)
            if worker.is_alive():
                worker.terminate()
                worker.join()
                self.fail("Actual-verifier crash fixture exceeded time bound")
            self.assertEqual(worker.exitcode, 72 if committed else 71)
            self.assertTrue(marker.is_file())
            if not committed:
                self.assertEqual(self.path.read_bytes(), before)
            else:
                with self.assertRaises(history.Rejected):
                    ScientificReceivingLedger(self.path, self.root, self.anchor, self.config)
            recovered = history.recover(self.path, self.root, previous=self.anchor, expected_envelope=signed)
            reopened = ScientificReceivingLedger(self.path, self.root, recovered, self.config)
            self.assertEqual(reopened.current().anchor.generation, int(committed))


if __name__ == "__main__":
    unittest.main(verbosity=2)
