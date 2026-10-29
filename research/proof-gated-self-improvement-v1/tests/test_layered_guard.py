import unittest
from pathlib import Path
from proof_gate import Model, check
from layered_guard import evaluate_layered, authorize_layered

class LayeredGuardTests(unittest.TestCase):
    def test_two_original_improvements_survive_stronger_policy(self):
        start, middle, optimum = (Model(True, 0, 0),
                                  Model(True, 1, 1),
                                  Model(True, 2, 1))
        first = evaluate_layered(start, middle)
        second = evaluate_layered(middle, optimum)
        self.assertTrue(first.accepted_reference)
        self.assertTrue(second.accepted_reference)
        self.assertEqual((first.old_window_max_error,
                          first.proposed_window_max_error), (41, 20))
        self.assertEqual((second.old_window_max_error,
                          second.proposed_window_max_error), (20, 0))
        self.assertTrue(second.exact_target_all_integers)

    def test_finite_gate_regression_is_detected_on_all_integers(self):
        old, new = Model(True, 3, -3), Model(True, 3, -1)
        self.assertTrue(check(old, new).accepted)
        verdict = evaluate_layered(old, new)
        self.assertFalse(verdict.accepted_reference)
        self.assertTrue(verdict.benchmark_pass)
        self.assertFalse(verdict.universal_no_forgetting)
        self.assertEqual(verdict.universal_counterexample, 4)
        self.assertEqual(verdict.reason, "REJECT:lost_previously_correct_integer_input")

    def test_identity_and_unbounded_weights_remain_disallowed(self):
        a = Model(True, 1, 1)
        self.assertFalse(evaluate_layered(a, a).accepted_reference)

    def test_windows_are_exact_and_validated(self):
        a, b = Model(True, 0, 0), Model(True, 1, 1)
        # Dynamic interval scores, no enumeration of all integers.
        narrow = evaluate_layered(a, b, low=-1, high=1)
        self.assertTrue(narrow.accepted_reference)
        with self.assertRaises(ValueError):
            evaluate_layered(a, b, low=1, high=-1)

    def test_missing_lean_cannot_be_replaced_by_python_checks(self):
        start, middle = Model(True, 0, 0), Model(True, 1, 1)
        self.assertTrue(evaluate_layered(start, middle).accepted_reference)
        decision = authorize_layered(start, middle, Path("/missing-pgsi-lean"))
        self.assertFalse(decision.accepted_reference)
        self.assertEqual(decision.reason, "REJECT:lean_unavailable_or_negative")

if __name__ == "__main__":
    unittest.main()
