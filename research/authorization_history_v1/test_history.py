"""Real cryptography/SQLite attack fixtures, never a scientific-checker fixture."""

from dataclasses import replace
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from research.authorization_history_v1 import history as h


def _fixture():
    # Fresh research keys live in this process; no protected/independent admin claim.
    authority = Ed25519PrivateKey.generate()
    witness = Ed25519PrivateKey.generate()
    root = h.Root(authority.public_key().public_bytes_raw(), witness.public_key().public_bytes_raw(),
                  b"policy/research-v1", b"checker/identity-only-not-executed", b"genesis", b"model-0")
    return authority, witness, root


def _sign(payload, authority, witness):
    return h.Envelope(payload, authority.sign(payload.signing_bytes()),
                      witness.sign(payload.signing_bytes())).encode()


def _concurrent_worker(path, root, anchor, envelope, barrier, results):
    store = h.History(Path(path), root, anchor)
    barrier.wait(timeout=15)
    try:
        results.put(("committed", store.append(envelope)))
    except h.Rejected:
        results.put(("rejected", None))


def _crash_worker(path, root, anchor, envelope, point):
    store = h.History(Path(path), root, anchor)
    original = h._connect

    def connect(database):
        connection = original(database)

        def trace(statement):
            if (point == "receipt-before-head" and statement.startswith("UPDATE head SET")):
                os._exit(71)
            if point == "before-commit" and statement == "COMMIT":
                os._exit(72)

        connection.set_trace_callback(trace)
        return connection

    h._connect = connect
    store.append(envelope)
    os._exit(73)  # Immediately after actual COMMIT, before external publication.


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "history.sqlite"
        self.authority, self.witness, self.root = _fixture()
        self.store = h.History.create(self.path, self.root)
        self.genesis = h.initial(self.root)

    def payload(self, *, anchor=None, event_id=b"event-1", candidate=b"model-1", certificate=b"opaque-cert\x00bytes"):
        return h.proposed_payload(self.root, anchor or self.store.expected_anchor,
                                  event_id=event_id, candidate=candidate, certificate=certificate)

    def sign(self, payload):
        return _sign(payload, self.authority, self.witness)

    def sql(self, statement, parameters=()):
        with sqlite3.connect(self.path) as connection:
            connection.execute(statement, parameters)

    def test_real_ed25519_full_byte_roundtrip_and_reopen(self):
        payload = self.payload(candidate=b"\x00\xffmodel\n", certificate=b"\x80\x00certificate")
        raw = self.sign(payload)
        self.assertEqual(h.Envelope.decode(raw).encode(), raw)
        committed = self.store.append(raw)
        snapshot = h.History(self.path, self.root, committed).snapshot()
        self.assertEqual(snapshot.anchor.incumbent, payload.candidate)
        self.assertEqual(snapshot.envelopes[0].payload.certificate, payload.certificate)
        self.assertEqual(len(snapshot.envelopes), 1)

    def test_every_payload_field_tamper_rejects_without_mutation(self):
        payload = self.payload()
        envelope = h.Envelope.decode(self.sign(payload))
        for field in h.PAYLOAD_BYTES + ("expected_generation", "next_generation"):
            with self.subTest(field=field):
                value = getattr(payload, field)
                changed = value + b"x" if type(value) is bytes else value + 1
                if field == "expected_chain_digest":
                    changed = bytes([value[0] ^ 1]) + value[1:]
                raw = replace(envelope, payload=replace(payload, **{field: changed})).encode()
                with self.assertRaises(h.Rejected):
                    self.store.append(raw)
                self.assertEqual(self.store.snapshot().anchor, self.genesis)

    def test_signed_wrong_scope_cas_links_and_generation_reject(self):
        payload = self.payload()
        changes = {"authority": os.urandom(32), "witness": os.urandom(32),
                   "policy": b"untrusted-policy", "checker": b"untrusted-checker",
                   "expected_chain_digest": bytes(32),
                   "previous_id": b"fork", "expected_incumbent": b"wrong-model",
                   "expected_generation": 2, "next_generation": 0,
                   "event_id": self.root.genesis_id}
        for field, value in changes.items():
            with self.subTest(field=field):
                with self.assertRaises(h.Rejected):
                    self.store.append(self.sign(replace(payload, **{field: value})))
                self.assertEqual(self.store.snapshot().anchor, self.genesis)

    def test_each_signature_is_required_and_same_payload_required(self):
        envelope = h.Envelope.decode(self.sign(self.payload()))
        other_payload = self.payload(candidate=b"other")
        variants = [replace(envelope, authority_signature=bytes(64)),
                    replace(envelope, witness_signature=bytes(64)),
                    replace(envelope, witness_signature=self.authority.sign(envelope.payload.signing_bytes())),
                    replace(envelope, witness_signature=self.witness.sign(other_payload.signing_bytes())),
                    replace(envelope, authority_signature=self.authority.sign(envelope.payload.encode()))]
        for variant in variants:
            with self.subTest(signature=variant.authority_signature[:8].hex()):
                with self.assertRaises(h.Rejected):
                    self.store.append(variant.encode())
        with self.assertRaises(h.Rejected):
            replace(self.root, witness=self.root.authority)

    def test_replay_and_duplicate_id_reject_but_explicit_old_bytes_allowed(self):
        raw = self.sign(self.payload())
        self.store.append(raw)
        with self.assertRaises(h.Rejected):
            self.store.append(raw)
        with self.assertRaises(h.Rejected):
            self.store.append(self.sign(self.payload(event_id=b"event-1")))
        # Generation rollback differs from authorizing older model bytes anew.
        old_model = self.sign(self.payload(event_id=b"event-2", candidate=self.root.genesis_incumbent))
        final = self.store.append(old_model)
        self.assertEqual(final.generation, 2)
        self.assertEqual(final.incumbent, self.root.genesis_incumbent)

    def test_strict_canonical_wire_rejects_ambiguity_and_unknown_fields(self):
        raw = self.sign(self.payload())
        value = json.loads(raw)
        variants = [raw + b"\n", b" " + raw, raw.replace(b'"format":', b'"format":"x","format":', 1),
                    json.dumps(value, indent=2).encode(), raw.replace(b'"next_generation":1', b'"next_generation":true'),
                    raw.replace(b'"next_generation":1', b'"next_generation":1.0')]
        unknown = dict(value, ignored="evil")
        variants.append(h._canonical(unknown))
        unknown_class = json.loads(raw)
        unknown_class["payload"]["event_class"] = "policy-activation"
        variants.append(h._canonical(unknown_class))
        uppercase = json.loads(raw)
        uppercase["authority_signature"] = uppercase["authority_signature"].upper()
        variants.append(h._canonical(uppercase))
        for variant in variants:
            with self.subTest(raw=variant[:100]):
                with self.assertRaises(h.Rejected):
                    self.store.append(variant)
        for invalid_generation in (True, -1, 1.0, 1 << 63):
            with self.assertRaises(h.Rejected):
                replace(self.payload(), next_generation=invalid_generation)
        with self.assertRaises(h.Rejected):
            replace(self.payload(), candidate=b"x" * (h.MAX_BYTES + 1))

    def test_external_anchor_is_mandatory_exact_and_root_is_pinned(self):
        final = self.store.append(self.sign(self.payload()))
        with self.assertRaises(TypeError):
            h.History(self.path, self.root)
        with self.assertRaises(h.Rejected):
            h.History(self.path, self.root, None)
        for anchor in (self.genesis, replace(final, tip=b"other"),
                       replace(final, chain_digest=bytes(32)), replace(final, incumbent=b"other")):
            with self.assertRaises(h.Rejected):
                h.History(self.path, self.root, anchor)
        with self.assertRaises(h.Rejected):
            h.History(self.path, replace(self.root, policy=b"substitute"), final)

    def test_whole_store_rollback_detected_by_external_anchor(self):
        backup = self.path.with_suffix(".backup")
        shutil.copyfile(self.path, backup)
        final = self.store.append(self.sign(self.payload()))
        shutil.copyfile(backup, self.path)
        with self.assertRaises(h.Rejected):
            h.History(self.path, self.root, final)
        # A stale expected anchor accepts a stale store. The trust assumption matters.
        self.assertEqual(h.History(self.path, self.root, self.genesis).snapshot().anchor, self.genesis)

    def test_compact_anchor_detects_signed_history_substitution_same_tip_model(self):
        fork_path = self.path.with_name("fork.sqlite")
        fork = h.History.create(fork_path, self.root)
        first = self.store.append(self.sign(self.payload(certificate=b"certificate-A")))
        second = fork.append(self.sign(self.payload(anchor=self.genesis, certificate=b"certificate-B")))
        self.assertEqual((first.generation, first.incumbent, first.tip),
                         (second.generation, second.incumbent, second.tip))
        self.assertNotEqual(first.chain_digest, second.chain_digest)
        with self.assertRaises(h.Rejected):
            h.History(fork_path, self.root, first)

    def test_signed_successor_cannot_transplant_across_same_tip_model_forks(self):
        fork = h.History.create(self.path.with_name("fork.sqlite"), self.root)
        first = self.store.append(self.sign(self.payload(certificate=b"certificate-A")))
        fork.append(self.sign(self.payload(anchor=self.genesis, certificate=b"certificate-B")))
        successor = self.sign(self.payload(anchor=first, event_id=b"event-2"))
        with self.assertRaises(h.Rejected):
            fork.append(successor)
        self.assertEqual(self.store.append(successor).generation, 2)

    def test_tampered_head_root_event_and_missing_receipt_fail_closed(self):
        raw = self.sign(self.payload())
        final = self.store.append(raw)
        backup = self.path.with_suffix(".backup")
        shutil.copyfile(self.path, backup)
        mutations = [("UPDATE head SET incumbent=?", (b"forged",)),
                     ("UPDATE head SET generation=0", ()),
                     ("UPDATE config SET root=?", (b"forged",)),
                     ("UPDATE events SET envelope=?", (raw.replace(b"certificate", b"certificatx"),)),
                     ("UPDATE events SET generation=2", ()),
                     ("DELETE FROM events", ()),
                     ("INSERT INTO events VALUES (2, ?)", (raw,)),
                     ("DELETE FROM head", ())]
        for statement, parameters in mutations:
            with self.subTest(statement=statement):
                shutil.copyfile(backup, self.path)
                self.sql(statement, parameters)
                with self.assertRaises(h.Rejected):
                    h.History(self.path, self.root, final)

    def test_unknown_schema_trigger_and_missing_store_rejected(self):
        self.sql("CREATE TRIGGER evil AFTER UPDATE ON head BEGIN DELETE FROM events; END")
        with self.assertRaises(h.Rejected):
            self.store.snapshot()
        with self.assertRaises(h.Rejected):
            h.History(self.path.with_name("absent.sqlite"), self.root, self.genesis)
        self.assertFalse(self.path.with_name("absent.sqlite").exists())
        with self.assertRaises(FileExistsError):
            h.History.create(self.path, self.root)

    def test_independent_sqlite_processes_only_one_cas_wins(self):
        context = multiprocessing.get_context("spawn")
        barrier, results = context.Barrier(2), context.Queue()
        envelopes = [self.sign(self.payload(event_id=b"a", candidate=b"a")),
                     self.sign(self.payload(event_id=b"b", candidate=b"b"))]
        workers = [context.Process(target=_concurrent_worker,
                                  args=(self.path, self.root, self.genesis, raw, barrier, results))
                   for raw in envelopes]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=30)
            self.assertEqual(worker.exitcode, 0)
        output = [results.get(timeout=5), results.get(timeout=5)]
        self.assertEqual(sorted(row[0] for row in output), ["committed", "rejected"])
        final = next(row[1] for row in output if row[0] == "committed")
        self.assertEqual(len(h.History(self.path, self.root, final).snapshot().envelopes), 1)

    def test_actual_process_crashes_receipt_head_commit_and_recovery(self):
        context = multiprocessing.get_context("spawn")
        raw = self.sign(self.payload())
        for point, code in (("receipt-before-head", 71), ("before-commit", 72), ("after-commit", 73)):
            with self.subTest(point=point):
                worker = context.Process(target=_crash_worker,
                                         args=(self.path, self.root, self.genesis, raw, point))
                worker.start()
                worker.join(timeout=30)
                self.assertEqual(worker.exitcode, code)
                recovered = h.recover(self.path, self.root, previous=self.genesis, expected_envelope=raw)
                if point == "after-commit":
                    self.assertEqual(recovered.generation, 1)
                    with self.assertRaises(h.Rejected):
                        h.History(self.path, self.root, self.genesis)
                else:
                    self.assertEqual(recovered, self.genesis)
                self.assertEqual(h.History(self.path, self.root, recovered).snapshot().anchor, recovered)

    def test_recovery_rejects_ambiguous_intent_and_multiple_commits(self):
        raw = self.sign(self.payload())
        other = self.sign(self.payload(candidate=b"different"))
        self.store.append(raw)
        with self.assertRaises(h.Rejected):
            h.recover(self.path, self.root, previous=self.genesis, expected_envelope=other)
        self.store.append(self.sign(self.payload(event_id=b"event-2")))
        with self.assertRaises(h.Rejected):
            h.recover(self.path, self.root, previous=self.genesis, expected_envelope=raw)

    def test_recovery_never_commits_or_accepts_an_invalid_retained_intent(self):
        envelope = h.Envelope.decode(self.sign(self.payload()))
        invalid = replace(envelope, witness_signature=bytes(64)).encode()
        with self.assertRaises(h.Rejected):
            h.recover(self.path, self.root, previous=self.genesis, expected_envelope=invalid)
        self.assertEqual(self.store.snapshot().anchor, self.genesis)
        recovered = h.recover(self.path, self.root, previous=self.genesis, expected_envelope=envelope.encode())
        self.assertEqual(recovered, self.genesis)
        self.assertEqual(self.store.snapshot().envelopes, ())

    def test_root_store_and_external_anchor_substitution_is_undetectable(self):
        # Required negative result: no claim against control of every trust input.
        old_anchor = self.store.append(self.sign(self.payload()))
        authority, witness, attacker_root = _fixture()
        replacement = self.path.with_name("substitute.sqlite")
        attacker = h.History.create(replacement, attacker_root)
        payload = h.proposed_payload(attacker_root, attacker.expected_anchor, event_id=b"attacker-event",
                                     candidate=b"attacker-model", certificate=b"attacker-certificate")
        attacker_anchor = attacker.append(_sign(payload, authority, witness))
        shutil.copyfile(replacement, self.path)
        with self.assertRaises(h.Rejected):
            h.History(self.path, self.root, old_anchor)
        accepted = h.History(self.path, attacker_root, attacker_anchor).snapshot()
        self.assertEqual(accepted.anchor.incumbent, b"attacker-model")


if __name__ == "__main__":
    unittest.main(verbosity=2)
