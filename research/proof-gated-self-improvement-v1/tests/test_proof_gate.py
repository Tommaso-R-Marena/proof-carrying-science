import dataclasses
import itertools
import random
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from proof_gate import (DOMAIN, POLICY, POLICY_HASH, Model, check, check_request,
                        check_with_lean, demonstration, digest, loss, parse_model,
                        request, solved)

class ProofGatedTests(unittest.TestCase):
    def setUp(self):
        self.a = Model(True, 0, 0)
        self.b = Model(True, 1, 1)
        self.c = Model(True, 2, 1)

    def test_two_accepted_generations(self):
        self.assertTrue(check(self.a, self.b).accepted)
        self.assertTrue(check(self.b, self.c).accepted)
        self.assertTrue(solved(self.a) < solved(self.b) < solved(self.c))
        self.assertLess(loss(self.c), loss(self.b))
        self.assertEqual(loss(self.c), 0)

    def test_exhaustive_small_transition_oracle(self):
        models = [Model(k, w, b) for k, w, b in
                  itertools.product((False, True), range(-2, 4), range(-2, 4))]
        self.assertEqual(len(models), 72)
        for old in models:
            for candidate in models:
                observed = check(old, candidate).accepted
                expected = solved(old) < solved(candidate) and loss(candidate) < loss(old)
                self.assertEqual(observed, expected, (old, candidate))

    def test_randomized_boundaries(self):
        rng = random.Random(20261016)
        for _ in range(3000):
            old = Model(bool(rng.getrandbits(1)), rng.randrange(-32, 33),
                        rng.randrange(-32, 33))
            candidate = Model(bool(rng.getrandbits(1)), rng.randrange(-32, 33),
                              rng.randrange(-32, 33))
            d = check(old, candidate)
            if d.accepted:
                self.assertTrue(solved(old) < solved(candidate))
                self.assertLess(loss(candidate), loss(old))

    def test_never_modify_correct_old_predictions(self):
        for k, w, b in itertools.product((False, True), range(-3, 4), range(-3, 4)):
            candidate = Model(k, w, b)
            if check(self.a, candidate).accepted:
                self.assertTrue(solved(self.a) < solved(candidate))

    def test_perfect_model_terminal(self):
        for w, b in itertools.product(range(-4, 5), repeat=2):
            self.assertFalse(check(self.c, Model(True, w, b)).accepted)

    def test_architecture_modifications_are_guarded(self):
        self.assertFalse(check(self.a, Model(False, 1, 1)).accepted)
        self.assertTrue(check(Model(False, 0, 0), self.b).accepted)

    def test_identity_and_rollback_rejected(self):
        self.assertFalse(check(self.b, self.b).accepted)
        self.assertFalse(check(self.b, self.a).accepted)

    def test_stale_incumbent_fails(self):
        with self.assertRaisesRegex(ValueError, "stale"):
            check_request(request(self.a, self.b), self.b)

    def test_policy_substitution_fails(self):
        req = request(self.a, self.b)
        req["policy_hash"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "policy"):
            check_request(req, self.a)
        req = request(self.a, self.b)
        req["candidate"]["domain"] = [0]
        with self.assertRaises(ValueError):
            check_request(req, self.a)

    def test_unrecognized_fields_rejected(self):
        for x in ({"relu": True, "weight": 1, "bias": 1, "bypass": True},
                  {"relu": True, "weight": 1}):
            with self.assertRaises(ValueError):
                parse_model(x)
        req = request(self.a, self.b)
        req["override"] = True
        with self.assertRaises(ValueError):
            check_request(req, self.a)

    def test_type_and_bound_integrity(self):
        for bad in (True, 1.0, "1", None, 9999999):
            with self.assertRaises((ValueError, TypeError)):
                Model(True, bad, 0)
        with self.assertRaises(TypeError):
            Model(1, 1, 1)

    def test_hash_policy_commitment(self):
        self.assertEqual(digest(dict(reversed(list(POLICY.items())))), POLICY_HASH)
        self.assertNotEqual(digest({**POLICY, "domain": [0]}), POLICY_HASH)

    def test_trace(self):
        out = demonstration()
        self.assertEqual([e["verdict"]["accepted"] for e in out["events"]],
                         [False, False, True, True])
        self.assertEqual(out["final"], dataclasses.asdict(self.c))

    def test_missing_lean_fails_closed(self):
        self.assertFalse(check_with_lean(self.a, self.b, Path("/absent-pgsi-gate")))

    def test_deterministic_automatic_search(self):
        from proof_gate import automatic_search
        out = automatic_search()
        self.assertEqual(out["generation_count"], 2)
        self.assertEqual(out["final"], dataclasses.asdict(self.c))
        self.assertEqual([e["verdict"]["new_loss"] for e in out["trace"]], [6, 0])

    def test_single_coordinate_dead_end(self):
        near = [Model(True, -1, 0), Model(True, 1, 0),
                Model(True, 0, -1), Model(True, 0, 1), Model(False, 0, 0)]
        self.assertTrue(all(not check(self.a, m).accepted for m in near))
        self.assertTrue(check(self.a, self.b).accepted)

    def test_automatic_search_fails_closed_without_lean(self):
        from proof_gate import automatic_search
        with self.assertRaisesRegex(RuntimeError, "FAIL CLOSED"):
            automatic_search(formal_dir=Path("/absent-pgsi-gate"))


    def test_canonical_wire_uniqueness_and_roundtrip(self):
        from proof_gate import wire_bytes
        models = [Model(a, w, b) for a in (False, True)
                  for w in range(-32, 33) for b in range(-32, 33)]
        serialized = [wire_bytes(m) for m in models]
        self.assertEqual(len(models), 8450)
        self.assertEqual(len(set(serialized)), len(models))
        self.assertEqual(wire_bytes(self.a), b"PGSI1|R|0|0")
        self.assertEqual(wire_bytes(self.b), b"PGSI1|R|1|1")
        self.assertEqual(wire_bytes(Model(False, -32, 32)), b"PGSI1|L|-32|32")
        self.assertTrue(all(b"\\n" not in s and b"\\r" not in s for s in serialized))

    def test_unavailable_artifact_authority_fails_closed(self):
        from proof_gate import artifact_gate, wire_bytes
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as d:
            a, b = Path(d) / "active", Path(d) / "candidate"
            a.write_bytes(wire_bytes(self.a))
            b.write_bytes(wire_bytes(self.b))
            self.assertFalse(artifact_gate(a, b, Path("/missing-pgsi-lean")))

    def test_frozen_benchmark_can_hide_generalization_regression(self):
        # Accepted benchmark steps do NOT imply out-of-domain improvement.
        hidden = (-20, -10, 10, 20)
        def hidden_loss(m):
            return sum(abs(m.predict(x)) for x in hidden)
        self.assertTrue(check(self.a, self.b).accepted)
        self.assertGreater(hidden_loss(self.b), hidden_loss(self.a))


if __name__ == "__main__":
    unittest.main()
