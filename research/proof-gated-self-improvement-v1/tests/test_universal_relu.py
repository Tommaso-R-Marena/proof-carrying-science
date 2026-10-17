import itertools
import random
import unittest

from proof_gate import Model, check, target
from universal_relu import (
    Term, Net, integer_cells, all_integer_equal,
    universal_correctness_preserved, exact_interval_max_error, single_neuron
)

TARGET = Net((Term(1, 2, 1),))
TWO_TARGET = Net((Term(1, 2, 1), Term(1, -1, 1)))

def random_net(rng, length=4):
    return Net(tuple(Term(rng.randrange(-3, 4), rng.randrange(-4, 5),
                          rng.randrange(-8, 9)) for _ in range(length)),
               rng.randrange(-10, 11))

class UniversalExactReLUTests(unittest.TestCase):
    def test_affine_branches_cover_all_integer_cells(self):
        rng = random.Random(901)
        for _ in range(150):
            n = random_net(rng)
            _, cells = integer_cells(n)
            for cell in cells:
                a, b = n.affine(cell.point())
                # brute-check each integer near all cuts; includes both tails
                for x in range(-40, 41):
                    if cell.contains(x):
                        self.assertEqual(n.predict(x), a*x+b, (n, cell, x))

    def test_negative_weight_cut_correct_at_integer_root(self):
        for w, b in itertools.product(range(-7, 8), repeat=2):
            t = Term(1, w, b)
            cut = t.cut()
            if cut is None:
                self.assertEqual(w, 0)
                continue
            for x in range(cut-6, cut+8):
                expected_active = (w*x+b > 0)
                self.assertEqual(expected_active, w*cut+b > 0 if x <= cut
                                 else w*(cut+1)+b > 0, (w, b, cut, x))

    def test_two_hidden_complete_model_matches_target_all_integers(self):
        complete = Net((Term(1, 2, 1), Term(1, -1, 1)))
        self.assertTrue(all_integer_equal(complete, TWO_TARGET).passes)
        swapped = Net(tuple(reversed(complete.terms)))
        self.assertTrue(all_integer_equal(complete, swapped).passes)

    def test_cancelled_and_zero_coefficient_networks(self):
        original = Net((Term(3, 2, -1), Term(-3, 2, -1),
                        Term(0, 10, 8)), 9)
        self.assertTrue(all_integer_equal(original, Net((), 9)).passes)

    def test_linear_embedding_over_all_integers(self):
        for w, b in itertools.product(range(-4, 5), repeat=2):
            net = single_neuron(False, w, b)
            for x in range(-24, 25):
                self.assertEqual(net.predict(x), w*x+b)
            self.assertTrue(all_integer_equal(
                net, Net((Term(1, w, b), Term(-1, -w, -b)))).passes)

    def test_equivalence_rejection_constructs_valid_witness(self):
        a = single_neuron(True, 3, -3)
        b = single_neuron(True, 3, -1)
        d = all_integer_equal(a, b)
        self.assertFalse(d.passes)
        self.assertIsInstance(d.counterexample, int)
        self.assertNotEqual(a.predict(d.counterexample), b.predict(d.counterexample))

    def test_randomized_equivalence_against_bounded_brute_force(self):
        rng = random.Random(927)
        for _ in range(550):
            a, b = random_net(rng), random_net(rng)
            d = all_integer_equal(a, b)
            if d.passes:
                for x in range(-160, 161):
                    self.assertEqual(a.predict(x), b.predict(x))
            else:
                self.assertNotEqual(a.predict(d.counterexample), b.predict(d.counterexample))

    def test_randomized_no_forgetting_against_bounded_brute_force(self):
        rng = random.Random(928)
        for _ in range(550):
            old, new = random_net(rng, 3), random_net(rng, 3)
            d = universal_correctness_preserved(old, new, TARGET)
            if d.passes:
                for x in range(-120, 121):
                    if old.predict(x) == TARGET.predict(x):
                        self.assertEqual(new.predict(x), TARGET.predict(x))
            else:
                x = d.counterexample
                self.assertEqual(old.predict(x), TARGET.predict(x))
                self.assertNotEqual(new.predict(x), TARGET.predict(x))

    def test_correctness_at_very_distant_exact_integer_root(self):
        # Unbounded quantification catches a correctness point at 1,000,000
        # that ordinary train/test partitions can easily miss.
        old = single_neuron(False, 1, -1000000)
        zero = Net(())
        wrong = Net((), 1)
        self.assertEqual(old.predict(1000000), zero.predict(1000000))
        result = universal_correctness_preserved(old, wrong, zero)
        self.assertFalse(result.passes)
        self.assertEqual(result.counterexample, 1000000)

    def test_no_forgetting_stronger_than_finite_corpus(self):
        # Old predicts constant 0, correct on all x<=-1 under relu(2x+1).
        # Candidate that creates a negative-tail output violates universal
        # correctness despite potentially matching finitely many examples.
        old = Net(())
        new = Net((Term(1, -1, -100),))
        result = universal_correctness_preserved(old, new, TARGET)
        self.assertFalse(result.passes)
        self.assertLess(result.counterexample, -100)

    def test_original_two_generation_sequence_preserves_all_correct_cases(self):
        a = single_neuron(True, 0, 0)
        b = single_neuron(True, 1, 1)
        c = single_neuron(True, 2, 1)
        self.assertTrue(universal_correctness_preserved(a, b, TARGET).passes)
        self.assertTrue(universal_correctness_preserved(b, c, TARGET).passes)
        self.assertTrue(all_integer_equal(c, TARGET).passes)

    def test_certified_finite_ood_witness_can_still_worsen_error(self):
        old, new = Model(True, 3, -3), Model(True, 3, -1)
        self.assertTrue(check(old, new).accepted)
        a = single_neuron(old.relu, old.weight, old.bias)
        b = single_neuron(new.relu, new.weight, new.bias)
        self.assertTrue(universal_correctness_preserved(a, b, TARGET).passes)
        self.assertGreater(abs(b.predict(20)-target(20)),
                           abs(a.predict(20)-target(20)))

    def test_interval_maximum_exact_against_all_integers(self):
        rng = random.Random(398)
        for _ in range(230):
            a, b = random_net(rng), random_net(rng, 2)
            low, high = sorted((rng.randrange(-100, 101),
                                rng.randrange(-100, 101)))
            score, witness = exact_interval_max_error(a, b, low, high)
            self.assertTrue(low <= witness <= high)
            self.assertEqual(score, abs(a.predict(witness)-b.predict(witness)))
            self.assertEqual(score, max(abs(a.predict(x)-b.predict(x))
                                        for x in range(low, high+1)))

    def test_invalid_interval_and_input_type(self):
        with self.assertRaises(ValueError):
            exact_interval_max_error(TARGET, TARGET, 2, 1)
        with self.assertRaises(TypeError):
            Net((Term(1.1, 1, 0),))
        with self.assertRaises(TypeError):
            TARGET.predict(1.0)

if __name__ == "__main__":
    unittest.main()
