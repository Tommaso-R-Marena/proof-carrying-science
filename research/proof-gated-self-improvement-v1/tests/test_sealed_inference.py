"""Exact-byte inference tests. Mock positive verifier is used ONLY for store tests.

The separate CI workflow also performs a real Lean-authorized two-generation
promotion before loading both artifacts through this same sealed loader.
"""
from __future__ import annotations

import itertools
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from proof_gate import Model, POLICY_HASH, wire_bytes
from promotion_v2 import ResearchPromotionStore, IntegrityFailure, StaleHead, blob_hash
from sealed_inference import decode_sealed_model, load_sealed, load_path_sealed

START = Model(True, 0, 0)
NEXT = Model(True, 1, 1)
OPTIMUM = Model(True, 2, 1)

class SealedInferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="pgsi-seal-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = ResearchPromotionStore.initialize(
            self.root / "store", Path("/no-lean"), START)

    @staticmethod
    def fake_yes(*_):
        # Not a semantic oracle; used to test loader and transaction behavior.
        return True

    def test_genesis_sealed_inference(self):
        snapshot = load_sealed(self.store)
        self.assertEqual(snapshot.head.generation, 0)
        self.assertEqual(snapshot.artifact, wire_bytes(START))
        self.assertEqual(snapshot.active_digest, snapshot.head.active_sha256)
        self.assertEqual(snapshot.head.policy_sha256, POLICY_HASH)
        self.assertEqual(snapshot.model, START)
        self.assertEqual(snapshot.batch(tuple(range(-3, 4))),
                         tuple(START.predict(x) for x in range(-3, 4)))

    def test_promotion_changes_head_but_not_sealed_memory(self):
        previous = load_sealed(self.store)
        head = self.store._promote_with_oracle(wire_bytes(NEXT), previous.head, self.fake_yes)
        now = load_sealed(self.store, expected=head)
        self.assertEqual(now.model, NEXT)
        self.assertEqual(previous.model, START)
        self.assertEqual(previous.predict(4), START.predict(4))
        self.assertEqual(now.predict(4), NEXT.predict(4))
        with self.assertRaises(StaleHead):
            load_sealed(self.store, expected=previous.head)

    def test_mutated_underlying_file_does_not_change_previous_snapshot(self):
        previous = load_sealed(self.store)
        path = self.store._blob_path(previous.head.active_sha256)
        path.write_bytes(wire_bytes(NEXT))
        self.assertEqual(previous.predict(10), 0)
        self.assertEqual(previous.active_digest, previous.head.active_sha256)
        with self.assertRaises(IntegrityFailure):
            load_sealed(self.store)

    def test_ledger_tamper_blocks_sealed_loader(self):
        initial = self.store.snapshot()
        head = self.store._promote_with_oracle(wire_bytes(NEXT), initial, self.fake_yes)
        self.assertEqual(load_sealed(self.store).head, head)
        (self.root / "store" / "receipts" / "00000001.json").write_bytes(b"{}")
        with self.assertRaises(IntegrityFailure):
            load_sealed(self.store)

    def test_rolled_back_head_blocks_sealed_loader(self):
        old_head = (self.root / "store" / "HEAD.json").read_bytes()
        self.store._promote_with_oracle(wire_bytes(NEXT), self.store.snapshot(), self.fake_yes)
        (self.root / "store" / "HEAD.json").write_bytes(old_head)
        with self.assertRaises(IntegrityFailure):
            load_sealed(self.store)

    def test_orphan_receipt_blocks_sealed_loader(self):
        expected = self.store.snapshot()
        orphan = self.root / "store" / "receipts" / "00000001.json"
        orphan.write_bytes(b"{}")
        with self.assertRaises(IntegrityFailure):
            load_sealed(self.store, expected=expected)

    def test_path_only_loading_is_always_denied(self):
        snapshot = load_sealed(self.store)
        with self.assertRaises(IntegrityFailure):
            load_path_sealed(self.store._blob_path(snapshot.head.active_sha256),
                             snapshot.head.active_sha256)

    def test_sealed_inference_rejects_untyped_inputs(self):
        s = load_sealed(self.store)
        for x in (True, 3.0, "3", None):
            with self.subTest(x=x):
                with self.assertRaises(TypeError):
                    s.predict(x)
        with self.assertRaises(TypeError):
            s.batch([1, 2, 3])

    def test_reject_noncanonical_inference_bytes(self):
        bad = (
            b"", b"PGSI1|R|0|0\n", b"PGSI1|R|01|0", b"PGSI1|R|-0|0",
            b"PGSI1|R|+1|0", b"PGSI1|R|1|0 ", b"PGSI1|R|1|0|garbage",
            b"PGSI1|A|0|0", b"PGSI2|R|0|0", b"PGSI1|R|33|0",
            b"PGSI1|R|-33|0", b"PGSI1|R|0|33", b"PGSI1|R|0|-33",
            b"PGSI1|R|0|0\x00suffix", b"\xff\xfe",
        )
        for raw in bad:
            with self.subTest(raw=raw):
                with self.assertRaises(IntegrityFailure):
                    decode_sealed_model(raw)
        for value in ("PGSI1|R|0|0", bytearray(b"PGSI1|R|0|0"), None):
            with self.assertRaises(IntegrityFailure):
                decode_sealed_model(value)

    def test_complete_bounded_model_roundtrip_and_independent_predictions(self):
        inputs = tuple(range(-20, 21))
        cases = 0
        for activation, w, b in itertools.product(
            (False, True), range(-32, 33), range(-32, 33)
        ):
            model = Model(activation, w, b)
            raw = wire_bytes(model)
            parsed = decode_sealed_model(raw)
            self.assertEqual(parsed, model)
            self.assertEqual(wire_bytes(parsed), raw)
            for x in inputs:
                expected = w * x + b
                if activation:
                    expected = max(0, expected)
                self.assertEqual(parsed.predict(x), expected)
                cases += 1
        self.assertEqual(cases, 8450 * len(inputs))

if __name__ == "__main__":
    unittest.main()
