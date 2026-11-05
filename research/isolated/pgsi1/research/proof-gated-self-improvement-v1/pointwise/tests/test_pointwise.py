from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from dominance import absolute, certificate, nonnegative, refined_rows, violation
from receive import Kernel, canonical, expression, net, strict_json
from promotion_v2 import IntegrityFailure
from affine_certificates import model_data
from universal_relu import Cell, Net, Term, single_neuron

TARGET = Net((Term(1, 2, 1),))
ZERO = Net(())
MID = Net((Term(1, 1, 1),))


class ProducerTests(unittest.TestCase):
    def test_exhaustive_affine_signs(self):
        for a, b, l, h in itertools.product(
            range(-4, 5), range(-4, 5), range(-3, 4), range(-3, 4)
        ):
            if l > h:
                continue
            c = Cell(l, h)
            expected = all(a * x + b >= 0 for x in range(l, h + 1))
            self.assertEqual(nonnegative(c, (a, b)), expected)
            if not expected:
                x = violation(c, (a, b))
                self.assertTrue(c.contains(x))
                self.assertLess(a * x + b, 0)

    def test_unbounded_violation_extreme_roots(self):
        for c in (Cell(None, None), Cell(None, -10), Cell(10, None)):
            for f in (
                (1, 10**100),
                (-1, 10**100),
                (0, -1),
                (1, -(10**100)),
                (-1, -(10**100)),
            ):
                if not nonnegative(c, f):
                    x = violation(c, f)
                    self.assertTrue(c.contains(x))
                    self.assertLess(f[0] * x + f[1], 0)

    def test_zero_boundary_negative_slope(self):
        with self.assertRaises(ValueError):
            absolute(Cell(0, None), (1, -1))
        self.assertEqual(absolute(Cell(0, None), (-1, 0)), (1, 0))
        self.assertEqual(absolute(Cell(None, 0), (1, 0)), (-1, 0))

    def test_activation_partition_needs_error_refinement(self):
        old = Net((), 2)
        new = single_neuron(False, 1, 0)
        rows = refined_rows(old, new, ZERO)
        self.assertGreater(len(rows), 1)
        c = certificate(old, new, ZERO)
        self.assertFalse(c["result"]["passes"])
        x = c["result"]["counterexample"]
        self.assertGreater(abs(new.predict(x)), 2)

    def test_all_small_single_neurons_bounded_oracle(self):
        ns = [
            single_neuron(r, w, b)
            for r, w, b in itertools.product((False, True), range(-2, 3), range(-2, 3))
        ]
        for a, b in itertools.product(ns, repeat=2):
            c = certificate(a, b, TARGET)
            brute = all(
                abs(b.predict(x) - TARGET.predict(x))
                <= abs(a.predict(x) - TARGET.predict(x))
                for x in range(-64, 65)
            )
            self.assertEqual(c["result"]["passes"], brute)

    def test_seeded_multiunit_oracle(self):
        rng = random.Random(202610170201)
        for _ in range(100):
            ns = tuple(
                Net(
                    tuple(
                        Term(*(rng.randint(-5, 5) for _ in range(3)))
                        for _ in range(rng.randint(0, 8))
                    ),
                    rng.randint(-5, 5),
                )
                for _ in range(3)
            )
            c = certificate(*ns)
            for cell, forms in refined_rows(*ns):
                for x in range(-32, 33):
                    if cell.contains(x):
                        self.assertEqual(
                            [a * x + b for a, b in forms], [n.predict(x) for n in ns]
                        )
            if c["result"]["passes"]:
                self.assertTrue(
                    all(
                        abs(ns[1].predict(x) - ns[2].predict(x))
                        <= abs(ns[0].predict(x) - ns[2].predict(x))
                        for x in range(-256, 257)
                    )
                )
            else:
                x = c["result"]["counterexample"]
                self.assertGreater(
                    abs(ns[1].predict(x) - ns[2].predict(x)),
                    abs(ns[0].predict(x) - ns[2].predict(x)),
                )

    def test_all_supported_tail_cases_rejected(self):
        for k in range(18, 32):
            c = certificate(
                single_neuron(True, k, 4), single_neuron(True, k + 1, 2 - k), TARGET
            )
            self.assertFalse(c["result"]["passes"])
            self.assertGreaterEqual(c["result"]["counterexample"], k + 3)

    def test_deterministic_and_permutation(self):
        a = Net((Term(3, -2, 1), Term(-4, 5, -1), Term(4, 5, -1)))
        b = Net(tuple(reversed(a.terms)))
        self.assertEqual(
            canonical(certificate(a, b, TARGET)), canonical(certificate(a, b, TARGET))
        )
        self.assertTrue(certificate(a, b, TARGET)["result"]["passes"])


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.ns = (ZERO, MID, TARGET)
        self.c = certificate(*self.ns)

    def test_receiver_model_binding(self):
        with self.assertRaises(ValueError):
            expression(self.c, (MID, ZERO, TARGET))

    def test_exact_fields_and_decision_types(self):
        changes = [
            ("kernel_proved", True),
            ("format", "unknown"),
            ("extra", 1),
            ("result", {"passes": 1, "counterexample": None}),
        ]
        for key, value in changes:
            c = copy.deepcopy(self.c)
            c[key] = value
            with self.assertRaises(ValueError):
                expression(c, self.ns)

    def test_integer_injection_and_resource_bounds(self):
        for value in (True, 1.0, "0); axiom fake : False", 1 << 513):
            c = copy.deepcopy(self.c)
            c["cells"][0]["affine"][0][0] = value
            with self.assertRaises(ValueError):
                expression(c, self.ns)
        with self.assertRaises(ValueError):
            expression(self.c, (Net((Term(1, 1, 1),) * 129), MID, TARGET))

    def test_strict_json_and_model_parser(self):
        for raw in (
            b'{"x":1,"x":2}',
            b'{ "x":1}',
            b'{"x":-0}',
            b'{"x":1}\n',
            b'{"x":NaN}',
        ):
            with self.assertRaises(IntegrityFailure):
                strict_json(raw)
        for data in (
            {"bias": True, "terms": []},
            {"bias": 0, "terms": [[1, 1, 1]], "unknown": 0},
        ):
            with self.assertRaises(ValueError):
                net(data)

    def test_negative_witness_type(self):
        c = certificate(MID, ZERO, TARGET)
        c["result"]["counterexample"] = False
        with self.assertRaises(ValueError):
            expression(c, (MID, ZERO, TARGET))


class RealKernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.k = Kernel(Path(cls.temp.name) / "kernel")
        cls.serial = 0

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def replay(self, cert, ns):
        type(self).serial += 1
        return self.k.replay([expression(cert, ns)], "Test" + str(self.serial))

    def test_useful_two_stage_improvement(self):
        for ns in ((ZERO, MID, TARGET), (MID, TARGET, TARGET)):
            self.assertTrue(certificate(*ns)["result"]["passes"])
            self.replay(certificate(*ns), ns)

    def test_supported_tail_negative_real_kernel(self):
        ns = (single_neuron(True, 31, 4), single_neuron(True, 32, -29), TARGET)
        self.replay(certificate(*ns), ns)

    def test_false_positive_rejected_by_kernel(self):
        ns = (MID, ZERO, TARGET)
        c = certificate(*ns)
        c["result"] = {"passes": True, "counterexample": None}
        with self.assertRaises(RuntimeError):
            self.replay(c, ns)

    def test_false_negative_witness_rejected_by_kernel(self):
        ns = (ZERO, MID, TARGET)
        c = certificate(*ns)
        c["result"] = {"passes": False, "counterexample": 10**60}
        with self.assertRaises(RuntimeError):
            self.replay(c, ns)

    def test_forged_affines_rejected_by_kernel(self):
        ns = (ZERO, MID, TARGET)
        c = certificate(*ns)
        c["cells"][0]["affine"][0][1] += 1
        with self.assertRaises(RuntimeError):
            self.replay(c, ns)

    def test_gap_and_overlap_rejected_by_kernel(self):
        ns = (ZERO, MID, TARGET)
        for shift in (-1, 1):
            c = certificate(*ns)
            c["cells"][1]["low"] += shift
            with self.assertRaises(RuntimeError):
                self.replay(c, ns)

    def test_both_unbounded_tails_required(self):
        ns = (ZERO, MID, TARGET)
        for side in (0, -1):
            c = certificate(*ns)
            c["cells"].pop(side)
            with self.assertRaises(RuntimeError):
                self.replay(c, ns)

    def test_cancellation_zero_and_huge_integers(self):
        n = Net(
            (Term(10**60, -(10**60), 10**60), Term(-(10**60), -(10**60), 10**60)),
            -(10**60),
        )
        ns = (n, Net((), -(10**60)), ZERO)
        self.replay(certificate(*ns), ns)

    def test_compiled_checker_drift_fails_closed(self):
        path = self.k.output / "Pointwise.olean"
        raw = path.read_bytes()
        try:
            path.write_bytes(raw + b"changed")
            with self.assertRaises(RuntimeError):
                self.k.check_sources()
        finally:
            path.write_bytes(raw)
        self.k.check_sources()

    def test_mathematical_guard_actual_kernel(self):
        from replay import rows

        ns = (ZERO, MID, TARGET)
        c = certificate(*ns)
        # Real concrete finite gate plus whole-domain checker, no injected verdict.
        source = (
            "import Pointwise\nopen PCS.Research.Pointwise\nexample : guard ⟨true,0,0⟩ ⟨true,1,1⟩ "
            + rows(c, 3)
            + " = true := by decide\n"
        )
        path = self.k.output / "RealGuard.lean"
        path.write_text(source)
        self.k.run(path)

    def test_request_path_replacement_receipt_binds_original_bytes(self):
        request = {
            "models": [model_data(n) for n in (ZERO, MID, TARGET)],
            "certificate": certificate(ZERO, MID, TARGET),
        }
        raw = canonical(request)
        root = Path(self.temp.name)
        path = root / "request.json"
        path.write_bytes(raw)
        output = root / "cli"
        with (root / "cli.log").open("w") as log:
            p = subprocess.Popen(
                [
                    sys.executable,
                    str(HERE / "receive.py"),
                    "--request",
                    str(path),
                    "--output",
                    str(output),
                ],
                stdout=log,
                stderr=log,
            )
            try:
                deadline = time.monotonic() + 120
                while (
                    not (output / "Received.lean").exists()
                    and p.poll() is None
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.01)
                self.assertTrue((output / "Received.lean").exists())
                path.write_bytes(b'{"changed":true}')
                self.assertEqual(p.wait(timeout=120), 0, (root / "cli.log").read_text())
            finally:
                if p.poll() is None:
                    p.kill()
                    p.wait()
        receipt = json.loads((output / "RECEIPT.json").read_text())
        self.assertEqual(receipt["request_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertFalse(receipt["promotion_performed"])
        self.assertFalse(receipt["native_execution_refinement_proved"])
        self.assertEqual(receipt["verified_verdict"], "HOLDS")
        self.assertIsNone(receipt["counterexample"])

    def test_real_negative_cli_receipt_is_explicit_refutation(self):
        ns = (MID, ZERO, TARGET)
        cert = certificate(*ns)
        root = Path(self.temp.name)
        path = root / "negative-request.json"
        path.write_bytes(
            canonical({"models": [model_data(n) for n in ns], "certificate": cert})
        )
        output = root / "negative-cli"
        p = subprocess.run(
            [
                sys.executable,
                str(HERE / "receive.py"),
                "--request",
                str(path),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        receipt = json.loads((output / "RECEIPT.json").read_text())
        self.assertEqual(receipt["verified_verdict"], "REFUTED")
        self.assertEqual(receipt["counterexample"], cert["result"]["counterexample"])
        self.assertFalse(receipt["promotion_performed"])


if __name__ == "__main__":
    unittest.main()
