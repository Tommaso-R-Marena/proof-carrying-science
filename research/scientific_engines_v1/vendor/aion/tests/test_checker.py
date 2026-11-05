"""Adversarial and correctness tests for the independent checker.

Run:  PYTHONPATH=python python3 -m unittest discover -s tests -v
"""
import copy
import json
import os
import sys
import unittest
from fractions import Fraction as Q

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from aion import checker as ck, models, synth, reference  # noqa: E402
from aion.crn import CRN  # noqa: E402


def _cert_bd(N=12):
    c = models.birth_death(Q(1), Q(2))
    cert, err = synth.synth_sandwich(c, 0, N, [True], [N], (1,))
    assert cert is not None, err
    return cert


def _cert_2d(N=12, M=25):
    c = models.degradation_modulated_growth()
    cert, err = synth.synth_sandwich(c, 0, N, [True, False], [N, M], (1, 10))
    assert cert is not None, err
    return cert


class TestExactReference(unittest.TestCase):
    def test_birth_death_sandwich_contains_exact(self):
        for N in (5, 12, 20):
            cert = _cert_bd(N)
            rep = ck.check_certificate(cert)
            self.assertTrue(rep["ok"], rep)
            exact = reference.birth_death_exact(Q(1), Q(2), N, 1)
            self.assertLessEqual(Q(rep["lower_at_x0"]), exact)
            self.assertLessEqual(exact, Q(rep["upper_at_x0"]))

    def test_falling_factorial_cell_check_matches_pointwise(self):
        # the cell check certifies P <= 0 on the orthant; verify pointwise on a grid
        c = models.degradation_modulated_growth()
        rho = [Q(2), Q(11, 10)]
        corner = [1, 30]
        ok, _ = ck.cell_check(c, rho, corner)
        self.assertTrue(ok)
        for x in range(1, 40):
            for y in range(30, 70):
                self.assertLessEqual(ck.drift_val(c, rho, (x, y)), 0)

    def test_generator_factorisation(self):
        # L(C e)(x) = C e(x) P(x), checked exactly at many states
        c = models.gene_expression()
        rho = [Q(3, 2), Q(21, 20)]
        C = Q(7, 3)
        g = lambda y: C * ck.exp_bar(rho, y)
        for m in range(0, 6):
            for p in range(0, 8):
                x = (m, p)
                self.assertEqual(ck.gen(c, g, x), C * ck.exp_bar(rho, x) * ck.drift_val(c, rho, x))


class TestRejections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cert = _cert_2d()
        rep = ck.check_certificate(cls.cert)
        assert rep["ok"], rep

    def mutate(self, f):
        c = copy.deepcopy(self.cert)
        f(c)
        return ck.check_certificate(c)

    def test_corrupted_upper_table_entry(self):
        def f(c):
            k = "3,10"
            c["upper"]["table"][k] = str(Q(c["upper"]["table"][k]) / 2)
        self.assertFalse(self.mutate(f)["ok"])

    def test_corrupted_lower_table_entry(self):
        def f(c):
            k = "3,10"
            c["lower"]["F"][k] = str(Q(c["lower"]["F"][k]) * 2)
        self.assertFalse(self.mutate(f)["ok"])

    def test_overclaimed_upper(self):
        def f(c):
            c["claim"]["upper"] = str(Q(c["claim"]["upper"]) / 2)
        self.assertFalse(self.mutate(f)["ok"])

    def test_overclaimed_lower(self):
        def f(c):
            c["claim"]["lower"] = str(Q(c["claim"]["lower"]) * 2)
        self.assertFalse(self.mutate(f)["ok"])

    def test_negative_rate(self):
        def f(c):
            c["model"]["reactions"][1]["k"] = "-1"
        self.assertFalse(self.mutate(f)["ok"])

    def test_float_rejected(self):
        def f(c):
            c["upper"]["C"] = 0.5
        self.assertFalse(self.mutate(f)["ok"])

    def test_missing_entry(self):
        def f(c):
            del c["upper"]["table"]["0,0"]
        self.assertFalse(self.mutate(f)["ok"])

    def test_tail_too_steep(self):
        # an over-optimistic tail exponent violates the infinite-region cell check
        def f(c):
            c["upper"]["rho"][0] = "40"
            c["upper"]["C"] = str(Q(1, 40 ** c["target"]["level"]))
        r = self.mutate(f)
        self.assertFalse(r["ok"])

    def test_tail_decreasing_rejected(self):
        def f(c):
            c["upper"]["rho"][1] = "1/2"
        self.assertFalse(self.mutate(f)["ok"])

    def test_wrong_model_rejected(self):
        # certificate for one model must not certify a faster-growing one
        def f(c):
            c["model"]["reactions"][0]["k"] = "3/2"
        self.assertFalse(self.mutate(f)["ok"])

    def test_missing_escape_certificate(self):
        def f(c):
            for k in c["lower"]["V"]:
                c["lower"]["V"][k] = "0"
        self.assertFalse(self.mutate(f)["ok"])

    def test_target_changed(self):
        def f(c):
            c["target"]["level"] = c["target"]["level"] - 3
        self.assertFalse(self.mutate(f)["ok"])

    def test_json_roundtrip(self):
        c = json.loads(json.dumps(self.cert))
        self.assertTrue(ck.check_certificate(c)["ok"])


class TestNegativeResults(unittest.TestCase):
    def test_recurrent_chain_has_no_nontrivial_barrier(self):
        # immigration-death without taboo: P(reach N) = 1, so no certificate with
        # g(x0) < 1 can pass; the synthesiser must fail or return g(x0) >= 1.
        c = models.immigration_death()
        up, err = synth.synth_upper(c, 0, 6, [False], [6], x0=(0,))
        if up is not None:
            g = ck.check_upper(c, {"species": 0, "level": 6}, [False], up)["g"]
            self.assertGreaterEqual(g((0,)), 1 - Q(1, 10 ** 6))

    def test_explosive_network_bounds(self):
        # 2X -> 3X is explosive, but hitting probabilities are still certified
        c = models.schlogl_explosive()
        cert, err = synth.synth_sandwich(c, 0, 15, [True], [15], (3,))
        self.assertIsNotNone(cert, err)
        rep = ck.check_certificate(cert)
        self.assertTrue(rep["ok"], rep)


if __name__ == "__main__":
    unittest.main()
