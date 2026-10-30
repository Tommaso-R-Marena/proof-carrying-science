"""Independent brute force, branch scans and corrupt-certificate controls."""

import copy
import itertools
import random
import unittest
from unittest.mock import patch
from universal_relu import (
    Net,
    Term,
    piecewise_cells,
    all_integer_equal,
    universal_correctness_preserved,
    exact_interval_max_error,
)
from affine_certificates import certificate, verify
from proof_gate import Model, wire_bytes, POLICY_HASH
from promotion_v2 import Head, blob_hash, ZERO_HASH, IntegrityFailure
from sealed_inference import SealedInference

TARGET = Net((Term(1, 2, 1),))


def evaluate(n, x):
    return n.bias + sum(t.coefficient * max(0, t.weight * x + t.bias) for t in n.terms)


def net(rng, width):
    return Net(
        tuple(
            Term(rng.randint(-4, 4), rng.randint(-4, 4), rng.randint(-12, 12))
            for _ in range(width)
        ),
        rng.randint(-6, 6),
    )


class SweepTests(unittest.TestCase):
    def test_exhaustive_signed_zero_breakpoint_coefficients(self):
        for c, w, b in itertools.product(range(-2, 3), repeat=3):
            n = Net((Term(c, w, b),))
            _, rows = piecewise_cells(n)
            for cell, (pair,) in rows:
                for x in range(-30, 31):
                    if cell.contains(x):
                        self.assertEqual(pair[0] * x + pair[1], evaluate(n, x))

    def test_sweep_matches_retained_branch_scan(self):
        rng = random.Random(91722)
        for _ in range(200):
            nets = tuple(net(rng, rng.randrange(0, 12)) for _ in range(3))
            _, rows = piecewise_cells(*nets)
            for cell, pairs in rows:
                for n, pair in zip(nets, pairs):
                    self.assertEqual(pair, n.affine(cell.point()))

    def test_all_two_unit_networks_small_lattice_against_enumeration(self):
        # All 3^6 ordered two-unit parameter configurations, not random examples.
        zero = Net(())
        for values in itertools.product((-1, 0, 1), repeat=6):
            a = Net((Term(*values[:3]), Term(*values[3:])))
            equal = all(evaluate(a, x) == 0 for x in range(-16, 17))
            self.assertEqual(all_integer_equal(a, zero).passes, equal)
            self.assertEqual(
                exact_interval_max_error(a, zero, -16, 16),
                max((abs(evaluate(a, x)), x) for x in range(-16, 17)),
            )

    def test_random_differential_bounded_and_constructive_witnesses(self):
        rng = random.Random(77013)
        for _ in range(300):
            a, b, t = net(rng, 4), net(rng, 5), net(rng, 3)
            max_error, x = exact_interval_max_error(a, t, -60, 60)
            self.assertEqual(
                (max_error, x),
                max((abs(evaluate(a, z) - evaluate(t, z)), z) for z in range(-60, 61)),
            )
            decision = universal_correctness_preserved(a, b, t)
            if decision.passes:
                self.assertTrue(
                    all(
                        evaluate(a, z) != evaluate(t, z)
                        or evaluate(b, z) == evaluate(t, z)
                        for z in range(-80, 81)
                    )
                )
            else:
                z = decision.counterexample
                self.assertEqual(evaluate(a, z), evaluate(t, z))
                self.assertNotEqual(evaluate(b, z), evaluate(t, z))

    def test_large_magnitudes_cancellation_permutation(self):
        big = 10**120
        n = Net(tuple(Term((-1) ** i, big + i, -big * i) for i in range(256)), big)
        permutation = Net(tuple(reversed(n.terms)), big)
        self.assertTrue(all_integer_equal(n, permutation).passes)
        cancelled = Net(
            n.terms + tuple(Term(-t.coefficient, t.weight, t.bias) for t in n.terms)
        )
        self.assertTrue(all_integer_equal(cancelled, Net(())).passes)
        score, x = exact_interval_max_error(n, permutation, -(10**160), 10**160)
        self.assertEqual(score, 0)


class CertificateTests(unittest.TestCase):
    def test_roundtrip_all_three_properties_with_separate_checker(self):
        for mode, nets, interval in [
            ("equal", (TARGET, TARGET), None),
            ("preserves", (Net(()), TARGET, TARGET), None),
            ("max_error", (Net(()), TARGET), (-(10**30), 10**30)),
        ]:
            c = certificate(mode, nets, interval)
            with (
                patch(
                    "universal_relu.piecewise_cells",
                    side_effect=AssertionError("must not run producer"),
                ),
                patch(
                    "universal_relu.Net.affine",
                    side_effect=AssertionError("must not run producer"),
                ),
            ):
                self.assertTrue(verify(c, nets, mode, interval)["checked"])

    def test_negative_certificates_have_replayable_actual_witnesses(self):
        old = Net((Term(1, 3, -3),))
        new = Net((Term(1, 3, -1),))
        c = certificate("preserves", (old, new, TARGET))
        self.assertFalse(c["result"]["passes"])
        self.assertEqual(c["result"]["counterexample"], 4)
        self.assertTrue(verify(c, (old, new, TARGET), "preserves")["checked"])
        c = certificate("equal", (old, new))
        self.assertFalse(c["result"]["passes"])
        verify(c, (old, new), "equal")

    def test_false_affine_coefficients_rejected(self):
        c = certificate("equal", (TARGET, TARGET))
        c["cells"][0]["affine"][0][1] += 1
        with self.assertRaises(ValueError):
            verify(c, (TARGET, TARGET), "equal")

    def test_missing_overlapping_reversed_and_crossing_cells_rejected(self):
        nets = (TARGET, TARGET)
        original = certificate("equal", nets)
        mutants = []
        c = copy.deepcopy(original)
        c["cells"].pop()
        mutants.append(c)
        c = copy.deepcopy(original)
        c["cells"][1]["low"] -= 1
        mutants.append(c)
        c = copy.deepcopy(original)
        c["cells"][0]["high"] += 1
        c["cells"][1]["low"] += 1
        mutants.append(c)
        c = copy.deepcopy(original)
        c["cells"].reverse()
        mutants.append(c)
        for c in mutants:
            with self.subTest(c=c):
                with self.assertRaises(ValueError):
                    verify(c, nets, "equal")

    def test_result_model_property_scope_and_bool_integer_forgery_rejected(self):
        nets = (Net(()), TARGET)
        original = certificate("max_error", nets, (-20, 20))
        for field, value in [("max_error", 0), ("argmax", -20), ("argmax", True)]:
            c = copy.deepcopy(original)
            c["result"][field] = value
            with self.assertRaises(ValueError):
                verify(c, nets, "max_error", (-20, 20))
        with self.assertRaises(ValueError):
            verify(original, (TARGET, TARGET), "max_error", (-20, 20))
        with self.assertRaises(ValueError):
            verify(original, nets, "max_error", (-21, 20))
        with self.assertRaises(ValueError):
            verify(original, nets, "equal")
        c = certificate("equal", (TARGET, TARGET))
        c["result"]["passes"] = 1
        with self.assertRaises(ValueError):
            verify(c, (TARGET, TARGET), "equal")

    def test_random_certificates_independently_replay(self):
        rng = random.Random(109991)
        for _ in range(70):
            a, b, t = net(rng, 4), net(rng, 4), net(rng, 2)
            for mode, nets, interval in [
                ("equal", (a, b), None),
                ("preserves", (a, b, t), None),
                ("max_error", (a, t), (-77, 92)),
            ]:
                verify(certificate(mode, nets, interval), nets, mode, interval)


class SnapshotConsistencyTests(unittest.TestCase):
    def test_inconsistent_public_constructor_cannot_execute_another_model(self):
        model = Model(True, 0, 0)
        raw = wire_bytes(model)
        head = Head(0, blob_hash(raw), POLICY_HASH, ZERO_HASH)
        self.assertEqual(SealedInference(head, raw, model).predict(7), 0)
        with self.assertRaises(IntegrityFailure):
            SealedInference(head, raw, Model(True, 2, 1))
        with self.assertRaises(IntegrityFailure):
            SealedInference(head, wire_bytes(Model(True, 2, 1)), model)

    def test_model_predict_refuses_noninteger_implementation_semantics(self):
        for value in [True, 2.5, "2", None]:
            with self.assertRaises(TypeError):
                Model(True, 2, 1).predict(value)


if __name__ == "__main__":
    unittest.main()


class NewNegativeControls(unittest.TestCase):
    def test_maximum_improvement_and_vacuous_no_forgetting_do_not_imply_l1_improvement(
        self,
    ):
        from layered_guard import evaluate_layered

        a, b = Model(False, -1, 0), Model(True, -3, -3)
        verdict = evaluate_layered(a, b)
        self.assertTrue(verdict.accepted_reference)
        self.assertEqual(
            (verdict.old_window_max_error, verdict.proposed_window_max_error), (61, 57)
        )
        xs = list(range(-20, -3)) + list(range(4, 21))
        self.assertEqual(sum(abs(a.predict(x) - max(0, 2 * x + 1)) for x in xs), 833)
        self.assertEqual(sum(abs(b.predict(x) - max(0, 2 * x + 1)) for x in xs), 986)
        from universal_relu import single_neuron

        nets = (
            single_neuron(a.relu, a.weight, a.bias),
            single_neuron(b.relu, b.weight, b.bias),
            TARGET,
        )
        checked = verify(certificate("preserves", nets), nets, "preserves")
        self.assertIsNone(checked["previously_correct_witness"])

    def test_nonvacuous_preservation_and_perfect_window_can_hide_far_domain_failure(
        self,
    ):
        old = Net(())
        new = Net(TARGET.terms + (Term(10, 1, -21),))
        checked = verify(
            certificate("preserves", (old, new, TARGET)),
            (old, new, TARGET),
            "preserves",
        )
        self.assertIsNotNone(checked["previously_correct_witness"])
        self.assertEqual(exact_interval_max_error(new, TARGET, -20, 20)[0], 0)
        self.assertEqual(
            (
                abs(old.predict(32) - TARGET.predict(32)),
                abs(new.predict(32) - TARGET.predict(32)),
            ),
            (65, 110),
        )
