from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from research.authorization_history_v1 import history
from research.scientific_history_v1.receiver import POLICY, checker_identity
from research.scientific_history_v1.test_receiver import real_config, FIXTURES
from research.scientific_history_v2 import audit
from research.scientific_history_v2.cli import load_anchor, load_root, bounded_file
from research.scientific_receiver_v1 import host


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = real_config()  # Requires real Lean; failure is not a skip.
        path = Path(audit.__file__).resolve()
        pin = host.Pin("source", str(path), hashlib.sha256(path.read_bytes()).hexdigest())
        cls.config = replace(config, pins=tuple(sorted((*config.pins, pin), key=lambda x: x.path)))
        cls.genesis = (FIXTURES / "zero-step.wire").read_bytes()
        cls.valid = (FIXTURES / "one-step.wire").read_bytes()
        cls.bad = (FIXTURES / "wrong-environment.wire").read_bytes()

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "history.sqlite"
        self.authority, self.witness = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
        self.root = history.Root(self.authority.public_key().public_bytes_raw(),
                                 self.witness.public_key().public_bytes_raw(), POLICY,
                                 checker_identity(self.config), b"audit-genesis", self.genesis)
        self.store = history.History.create(self.path, self.root)
        self.initial = history.initial(self.root)

    def signed(self, raw=None, *, anchor=None, event_id=b"first", **changes):
        payload = history.proposed_payload(self.root, anchor or self.initial, event_id=event_id,
                                           candidate=self.valid if raw is None else raw, certificate=b"")
        payload = replace(payload, **changes)
        return history.Envelope(payload, self.authority.sign(payload.signing_bytes()),
                                self.witness.sign(payload.signing_bytes())).encode()

    def assert_preflight_rejects(self, wires, anchor=None, *, root=None, budget=None):
        # Use the checkpoint that these exact bytes would produce if the
        # challenged auth/scope check were incorrectly omitted. A mismatched
        # dummy final anchor must not make every negative vacuously pass.
        if anchor is None and type(wires) is tuple and len(wires) == 1:
            try:
                payload = history.Envelope.decode(wires[0]).payload
                anchor = history.Anchor(payload.next_generation, payload.candidate, payload.event_id,
                                        hashlib.sha256(history.LINK_DOMAIN + self.initial.chain_digest
                                                       + wires[0]).digest())
            except history.Rejected:
                anchor = self.initial
        with patch.object(host, "ReceiverService", side_effect=AssertionError("must not launch verifier")):
            with self.assertRaises((audit.AuditRejected, history.Rejected)):
                audit.audit_material(root or self.root, anchor or self.initial, wires, self.config,
                                      budget=budget or audit.AuditBudget())

    def test_budget_types_and_hard_bounds(self):
        for kwargs in ({"max_events": True}, {"max_events": 33}, {"max_artifact_bytes": 8193},
                       {"max_total_envelope_bytes": 1048577}, {"max_wall_seconds": float("inf")},
                       {"max_wall_seconds": 0}, {"max_wall_seconds": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(audit.AuditRejected):
                audit.AuditBudget(**kwargs)

    def test_empty_history_still_actually_checks_genesis(self):
        report = audit.audit_history(self.path, self.root, self.initial, self.config)
        self.assertEqual(len(report.artifacts), 1)
        self.assertEqual(report.artifacts[0].raw, self.genesis)
        self.assertEqual(report.retrospective_mathematical_validity, "EXECUTED_PASS")
        self.assertTrue(report.historical_math_valid)
        self.assertEqual(report.historically_authenticated_verification, "UNVERIFIED")
        self.assertFalse(report.scientific_acceptance or report.production_authority)
        self.assertEqual(report.as_dict()["resume_policy"].split(";")[0], "restart_from_checked_genesis")

    def test_full_valid_history_checks_every_exact_candidate(self):
        first = self.signed()
        anchor1 = self.store.append(first)
        second = self.signed(self.genesis, anchor=anchor1, event_id=b"second")
        final = self.store.append(second)
        before = self.path.read_bytes()
        report = audit.audit_history(self.path, self.root, final, self.config)
        self.assertEqual(tuple(x.raw for x in report.artifacts), (self.genesis, self.valid, self.genesis))
        self.assertEqual(report.artifacts[1].result.final_a, Fraction(7, 2))
        self.assertEqual(report.envelope_sha256, tuple(map(audit.digest, (first, second))))
        self.assertEqual(report.anchor, final)
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaises(FrozenInstanceError):
            report.artifacts[1].result.final_a = Fraction(0)

    def test_portable_material_and_streamed_prefix_are_distinct(self):
        wire = self.signed()
        final = self.store.append(wire)
        stream = audit.audit_material_events(self.root, final, (wire,), self.config)
        genesis = next(stream)
        self.assertIs(type(genesis), audit.AuditProgress)
        self.assertFalse(genesis.complete_history)
        self.assertEqual(genesis.index, 0)
        candidate = next(stream)
        self.assertEqual(candidate.artifact.raw, self.valid)
        report = next(stream)
        self.assertIs(type(report), audit.AuditReport)
        self.assertEqual(report.anchor, final)
        with self.assertRaises(StopIteration):
            next(stream)

    def test_invalid_old_science_followed_by_valid_current_is_rejected(self):
        bad = self.signed(self.bad)
        anchor = self.store.append(bad)  # Real signatures authenticate intent, not science.
        final = self.store.append(self.signed(self.valid, anchor=anchor, event_id=b"valid-current"))
        before = self.path.read_bytes()
        with self.assertRaises(audit.AuditRejected):
            audit.audit_history(self.path, self.root, final, self.config)
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_genesis_is_not_validated_by_empty_history(self):
        root = replace(self.root, genesis_incumbent=self.bad)
        path = self.path.with_name("bad-genesis.sqlite")
        history.History.create(path, root)
        with self.assertRaises(audit.AuditRejected):
            audit.audit_history(path, root, history.initial(root), self.config)

    def test_missing_reordered_duplicated_and_wrong_anchor_material_rejects_before_science(self):
        first = self.signed()
        a1 = self.store.append(first)
        second = self.signed(anchor=a1, event_id=b"second")
        a2 = self.store.append(second)
        for wires, target in (((first,), a2), ((second, first), a2), ((first, first), a2),
                              ((second,), a2), ((first, second), a1)):
            with self.subTest(wires=wires):
                self.assert_preflight_rejects(wires, target)

    def test_wrong_scope_reserved_certificate_and_generation_rejects_before_science(self):
        for changes in ({"policy": b"unsupported"}, {"checker": bytes(32)},
                        {"authority": bytes(32)}, {"certificate": b"fake-positive-proof"},
                        {"next_generation": 9}, {"expected_generation": 1}):
            with self.subTest(changes=changes):
                self.assert_preflight_rejects((self.signed(**changes),))

    def test_wrong_signatures_root_and_same_metadata_different_bytes_reject_before_science(self):
        decoded = history.Envelope.decode(self.signed())
        changed = replace(decoded, payload=replace(decoded.payload, candidate=self.genesis)).encode()
        badsig = replace(decoded, witness_signature=bytes(64)).encode()
        wrongroot = replace(self.root, authority=Ed25519PrivateKey.generate().public_key().public_bytes_raw())
        for wire, root in ((changed, self.root), (badsig, self.root), (self.signed(), wrongroot)):
            self.assert_preflight_rejects((wire,), root=root)

    def test_noncanonical_truncated_and_unknown_encodings_reject_before_science(self):
        wire = self.signed()
        for raw in (wire + b"\n", wire[:-1], b"{}", b'[' * 1000, b'\xff', b'null'):
            with self.subTest(raw=raw[:20]):
                self.assert_preflight_rejects((raw,))

    def test_new_resource_budgets_reject_before_science(self):
        wire = self.signed()
        for budget in (audit.AuditBudget(max_events=0), audit.AuditBudget(max_total_envelope_bytes=1),
                       audit.AuditBudget(max_total_artifact_bytes=len(self.genesis)),
                       audit.AuditBudget(max_artifact_bytes=1)):
            self.assert_preflight_rejects((wire,), budget=budget)
        self.assert_preflight_rejects((), budget=audit.AuditBudget(max_total_artifact_bytes=0))
        self.assert_preflight_rejects([wire])  # Mutable inputs are not captured implicitly.

    def test_untrusted_positive_cache_cannot_bypass_replay(self):
        with self.assertRaises(TypeError):
            audit.audit_material(self.root, self.initial, (), self.config, cache={"accepted": True})
        with self.assertRaises(TypeError):
            audit.audit_history(self.path, self.root, self.initial, self.config, verifier=lambda _: True)

    def test_missing_actual_verifier_fails_not_skips(self):
        config = replace(self.config, command=("/nonexistent/pcs-required-lean",))
        root = replace(self.root, checker=checker_identity(config))
        with self.assertRaises(audit.AuditRejected):
            audit.audit_material(root, history.initial(root), (), config)

    def test_changed_pinned_scientific_source_fails_closed(self):
        wrong = replace(self.config.pins[0], sha256="0" * 64)
        config = replace(self.config, pins=(wrong, *self.config.pins[1:]))
        root = replace(self.root, checker=checker_identity(config))
        with self.assertRaises(audit.AuditRejected):
            audit.audit_material(root, history.initial(root), (), config)

    def test_tampered_store_or_missing_store_rejects_before_science(self):
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE head SET generation=7")
        with patch.object(host, "ReceiverService", side_effect=AssertionError("must not launch verifier")):
            for path in (self.path, self.path.with_name("missing.sqlite")):
                with self.subTest(path=path), self.assertRaises(history.Rejected):
                    audit.audit_history(path, self.root, self.initial, self.config)
        self.assertFalse(self.path.with_name("missing.sqlite").exists())

    def test_change_during_actual_replay_cannot_return_a_complete_audit(self):
        final = self.store.append(self.signed())
        actual = audit._check_artifact
        calls = 0

        def verify_then_corrupt(raw, root, config, service):
            nonlocal calls
            checked = actual(raw, root, config, service)  # Actual Lean, unchanged verdict.
            calls += 1
            if calls == 2:
                with sqlite3.connect(self.path) as connection:
                    connection.execute("UPDATE head SET generation=99")
            return checked

        with patch.object(audit, "_check_artifact", side_effect=verify_then_corrupt):
            with self.assertRaises(history.Rejected):
                audit.audit_history(self.path, self.root, final, self.config)
        self.assertEqual(calls, 2)  # Both checks really completed before the negative store fault.

    def test_cli_bootstrap_is_strict_and_files_are_bounded_regular(self):
        self.assertEqual(load_root(self.root.encode()), self.root)
        anchor_raw = audit.canonical({"generation": self.initial.generation,
                                      "incumbent_hex": self.initial.incumbent.hex(),
                                      "tip_hex": self.initial.tip.hex(),
                                      "chain_digest_hex": self.initial.chain_digest.hex()})
        self.assertEqual(load_anchor(anchor_raw), self.initial)
        for raw in (self.root.encode() + b"\n", b"{}", b'[' * 1000):
            with self.assertRaises(audit.AuditRejected):
                load_root(raw)
        root_path = self.path.with_name("root.json")
        root_path.write_bytes(self.root.encode())
        self.assertEqual(bounded_file(root_path, 32768), self.root.encode())
        with self.assertRaises(audit.AuditRejected):
            bounded_file(root_path, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
