import copy
import hashlib
import time
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from replay import Kernel, expression, net, audit
from affine_certificates import certificate, model_data
from promotion_v2 import canonical, strict_json, IntegrityFailure
from universal_relu import Net, Term

TARGET = Net((Term(1, 2, 1),))
ZERO = Net(())
MIDDLE = Net((Term(1, 1, 1),))


class ReceiverSchemaTests(unittest.TestCase):
    def test_exact_model_roundtrip(self):
        self.assertEqual(net(model_data(TARGET)), TARGET)

    def test_noninteger_and_oversized_models_rejected(self):
        for value in (True, 1.5, "1", 2**513):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    net({"bias": value, "terms": []})

    def test_model_code_and_unknown_fields_rejected(self):
        for data in (
            {"bias": 0, "terms": [], "verifier": "ACCEPT"},
            {"bias": 0, "terms": [[1, "by sorry", 0]]},
            {"bias": 0, "terms": [[1, 2]]},
        ):
            with self.assertRaises(ValueError):
                net(data)

    def test_receiver_model_binding(self):
        c = certificate("equal", (ZERO, ZERO))
        with self.assertRaises(ValueError):
            expression(c, (ZERO, TARGET), "equal")

    def test_receiver_property_and_interval_binding(self):
        c = certificate("max_error", (ZERO, TARGET), (-20, 20))
        with self.assertRaises(ValueError):
            expression(c, (ZERO, TARGET), "equal")
        with self.assertRaises(ValueError):
            expression(c, (ZERO, TARGET), "max_error", (-20, 19))

    def test_claimed_kernel_flag_rejected(self):
        c = certificate("equal", (ZERO, ZERO))
        c["kernel_proved"] = True
        with self.assertRaises(ValueError):
            expression(c, (ZERO, ZERO), "equal")

    def test_canonical_json_attack_controls(self):
        for raw in (
            b'{"a":1,"a":2}',
            b'{"a":-0}',
            b'{"a":01}',
            b'{"a":0}\n',
            b'{"a":"\xff"}',
        ):
            with self.assertRaises(IntegrityFailure):
                strict_json(raw)

    def test_axiom_audit_requires_exact_inventory(self):
        for raw in (
            "",
            "'X' depends on axioms: [sorryAx]",
            "'X' depends on axioms: [Lean.ofReduceBool]",
            "'X' does not depend on any axioms\nextra",
        ):
            with self.assertRaises(ValueError):
                audit(raw, {"X"})
        self.assertEqual(audit("'X' does not depend on any axioms", {"X"}), {"X": []})

    def test_negative_certificate_requires_real_witness(self):
        c = certificate("equal", (ZERO, TARGET))
        c["result"]["counterexample"] = "by sorry"
        with self.assertRaises(ValueError):
            expression(c, (ZERO, TARGET), "equal")


class KernelReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="pgsi-kernel-tests-")
        cls.kernel = Kernel(Path(cls.temp.name) / "build")
        cls.counter = 0

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def replay(self, c, ns, prop, interval=None, witness=None):
        type(self).counter += 1
        return self.kernel.replay(
            [expression(c, ns, prop, interval, witness)], "Case" + str(self.counter)
        )

    def rejected(self, c, ns, prop, interval=None, witness=None):
        with self.assertRaisesRegex(RuntimeError, "Kernel check rejected"):
            self.replay(c, ns, prop, interval, witness)

    def test_all_37_theorems_audited(self):
        self.assertEqual(len(self.kernel.axioms), 37)
        self.assertTrue(
            all(
                set(a) <= {"propext", "Classical.choice", "Quot.sound"}
                for a in self.kernel.axioms.values()
            )
        )

    def test_positive_equal_permutation_cancellation_and_negative_weights(self):
        a = Net((Term(3, -2, 1), Term(-3, -2, 1), Term(2, 1, 0)))
        b = Net((Term(2, 1, 0),))
        r = self.replay(certificate("equal", (a, b)), (a, b), "equal")
        self.assertEqual(r["claims"], 1)

    def test_singleton_exact_zero_branch(self):
        a = Net((Term(1, 1, 0), Term(1, 1, -1)))
        self.replay(certificate("equal", (a, a)), (a, a), "equal")

    def test_positive_nonvacuous_preservation(self):
        self.replay(
            certificate("preserves", (ZERO, MIDDLE, TARGET)),
            (ZERO, MIDDLE, TARGET),
            "preserves",
            witness=-1,
        )

    def test_real_negative_equal_and_preservation(self):
        self.replay(certificate("equal", (ZERO, TARGET)), (ZERO, TARGET), "equal")
        self.replay(
            certificate("preserves", (TARGET, ZERO, TARGET)),
            (TARGET, ZERO, TARGET),
            "preserves",
        )

    def test_exact_maximum_large_integer_interval(self):
        bounds = (-(10**30), 10**30)
        self.replay(
            certificate("max_error", (ZERO, TARGET), bounds),
            (ZERO, TARGET),
            "max_error",
            bounds,
        )

    def test_fake_positive_rejected_by_kernel(self):
        c = certificate("equal", (ZERO, TARGET))
        c["result"] = {"passes": True, "counterexample": None}
        self.rejected(c, (ZERO, TARGET), "equal")

    def test_fake_negative_witness_rejected_by_kernel(self):
        c = certificate("equal", (ZERO, TARGET))
        c["result"]["counterexample"] = -1
        self.rejected(c, (ZERO, TARGET), "equal")

    def test_forgotten_input_fake_positive_rejected_by_kernel(self):
        c = certificate("preserves", (TARGET, ZERO, TARGET))
        c["result"] = {"passes": True, "counterexample": None}
        self.rejected(c, (TARGET, ZERO, TARGET), "preserves")

    def test_wrong_affine_coefficients_rejected_by_kernel(self):
        c = certificate("equal", (TARGET, TARGET))
        c["cells"][-1]["affine"][0][1] += 1
        self.rejected(c, (TARGET, TARGET), "equal")

    def test_missing_cell_rejected_by_kernel(self):
        c = certificate("equal", (TARGET, TARGET))
        c["cells"].pop(0)
        self.rejected(c, (TARGET, TARGET), "equal")

    def test_gap_overlap_and_premature_unbounded_cell_rejected(self):
        c = certificate("equal", (TARGET, TARGET))
        for field, value in (("low", 1), ("low", -1)):
            d = copy.deepcopy(c)
            d["cells"][-1][field] = value
            self.rejected(d, (TARGET, TARGET), "equal")
        d = copy.deepcopy(c)
        d["cells"][0]["high"] = None
        self.rejected(d, (TARGET, TARGET), "equal")

    def test_wrong_error_peak_and_reversed_window_rejected(self):
        c = certificate("max_error", (ZERO, TARGET), (-20, 20))
        for field, value in (
            ("max_error", 40),
            ("max_error", 42),
            ("argmax", -20),
            ("argmax", 21),
        ):
            d = copy.deepcopy(c)
            d["result"][field] = value
            self.rejected(d, (ZERO, TARGET), "max_error", (-20, 20))
        d = certificate("max_error", (ZERO, TARGET), (-20, 20))
        d["interval"] = [20, -20]
        self.rejected(d, (ZERO, TARGET), "max_error", (20, -20))

    def test_vacuous_preservation_cannot_claim_correct_witness(self):
        a = Net((Term(1, -1, 0), Term(-1, 1, 0)))
        b = Net((Term(1, -3, -3),))
        c = certificate("preserves", (a, b, TARGET))
        self.assertTrue(c["result"]["passes"])
        self.replay(c, (a, b, TARGET), "preserves")
        self.rejected(c, (a, b, TARGET), "preserves", witness=0)

    def test_receiver_cli_produces_kernel_checked_artifact(self):
        c = certificate("preserves", (ZERO, MIDDLE, TARGET))
        request = {
            "property": "preserves",
            "models": [model_data(n) for n in (ZERO, MIDDLE, TARGET)],
            "certificate": c,
            "interval": None,
            "witness": -1,
        }
        request_path = Path(self.temp.name) / "request.json"
        request_path.write_bytes(canonical(request))
        output = Path(self.temp.name) / "received"
        p = subprocess.run(
            [
                sys.executable,
                str(HERE / "replay.py"),
                "--request",
                str(request_path),
                "--output",
                str(output),
            ],
            text=True,
            capture_output=True,
            timeout=120,
        )
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        r = json.loads(p.stdout)
        self.assertTrue(r["kernel_checked_encoded_mathematical_claim"])
        self.assertFalse(r["pcs_promotion_authority"])
        self.assertFalse(r["native_execution_refinement_proved"])
        self.assertTrue((output / "Received.lean").is_file())
        self.assertEqual(len(r["sources"]), len(self.kernel.sources))

    def test_offline_guard_cli_and_optional_real_native_authorization(self):
        request = {
            "old": {"relu": True, "weight": 0, "bias": 0},
            "candidate": {"relu": True, "weight": 1, "bias": 1},
            "interval": [-20, 20],
        }
        request_path = Path(self.temp.name) / "guard-request.json"
        request_path.write_bytes(canonical(request))
        output = Path(self.temp.name) / "guard-received"
        args = [
            sys.executable,
            str(HERE / "guard.py"),
            "--request",
            str(request_path),
            "--output",
            str(output),
        ]
        bundle = os.environ.get("PCS_PGSI_AUTHORITY_BUNDLE")
        if os.environ.get("PCS_PGSI_REQUIRE_NATIVE") == "1" and not bundle:
            self.fail("Mandatory real native authority bundle missing")
        if bundle:
            args += ["--bundle", bundle]
        p = subprocess.run(args, text=True, capture_output=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        r = json.loads(p.stdout)
        self.assertTrue(r["kernel_checked_mathematical_guard"])
        self.assertFalse(r["promotion_performed"])
        self.assertFalse(r["production_authority"])
        self.assertEqual(r["old_exact_maximum"]["max_error"], 41)
        self.assertEqual(r["new_exact_maximum"]["max_error"], 20)
        if bundle:
            self.assertEqual(r["native_finite_authorization"]["verdict"], "ACCEPT")
        else:
            self.assertIsNone(r["native_finite_authorization"])

    def test_composed_guard_rejects_no_finite_improvement(self):
        from guard import guard_expression, replay_guards
        from proof_gate import Model

        n = Net((Term(1, 0, 0),))
        pc = certificate("preserves", (n, n, TARGET))
        mc = certificate("max_error", (n, TARGET), (-20, 20))
        e = guard_expression(
            Model(True, 0, 0), Model(True, 0, 0), pc, mc, mc, -20, 20, -1
        )
        with self.assertRaisesRegex(RuntimeError, "Kernel check rejected"):
            replay_guards(self.kernel, [e], "NoFiniteGain")

    def test_no_integer_correct_proof_includes_fractional_root(self):
        from replay import lean_net, rows
        from universal_relu import single_neuron

        a = single_neuron(False, 4, 0)
        shifted = Net(TARGET.terms, 1)
        c = certificate("preserves", (a, shifted, TARGET))
        self.assertTrue(c["result"]["passes"])
        self.kernel.replay(
            [f"(.noCorrect {lean_net(a)} {lean_net(TARGET)} {rows(c, 3)} : Claim)"],
            "NoIntegerRoot",
        )

    def test_compiled_checker_substitution_fails_before_execution(self):
        p = self.kernel.output / "IntegerAffine.olean"
        original = p.read_bytes()
        try:
            p.write_bytes(original + b"substituted")
            with self.assertRaisesRegex(RuntimeError, "Compiled checker changed"):
                self.kernel.run(HERE / "Audit.lean")
        finally:
            p.write_bytes(original)
        self.kernel.check_sources()

    def test_receipts_bind_original_request_despite_actual_path_replacement(self):
        cases = [
            (
                "replay.py",
                {
                    "property": "preserves",
                    "models": [model_data(n) for n in (ZERO, MIDDLE, TARGET)],
                    "certificate": certificate("preserves", (ZERO, MIDDLE, TARGET)),
                    "interval": None,
                    "witness": -1,
                },
            ),
            (
                "guard.py",
                {
                    "old": {"relu": True, "weight": 0, "bias": 0},
                    "candidate": {"relu": True, "weight": 1, "bias": 1},
                    "interval": [-20, 20],
                },
            ),
        ]
        for index, (script, request) in enumerate(cases):
            with self.subTest(script=script):
                raw = canonical(request)
                path = Path(self.temp.name) / (
                    "replace-request-" + str(index) + ".json"
                )
                path.write_bytes(raw)
                output = Path(self.temp.name) / ("replace-output-" + str(index))
                child = subprocess.Popen(
                    [
                        sys.executable,
                        str(HERE / script),
                        "--request",
                        str(path),
                        "--output",
                        str(output),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                try:
                    deadline = time.monotonic() + 30
                    while (
                        not output.exists()
                        and child.poll() is None
                        and time.monotonic() < deadline
                    ):
                        time.sleep(0.01)
                    self.assertTrue(
                        output.exists(), "Receiver did not reach post-parse proof setup"
                    )
                    path.write_bytes(canonical({"changed_after_parsing": True}))
                    out, err = child.communicate(timeout=120)
                    self.assertEqual(child.returncode, 0, out + err)
                    receipt = json.loads(out)
                    self.assertEqual(
                        receipt["request_sha256"], hashlib.sha256(raw).hexdigest()
                    )
                    self.assertNotEqual(
                        receipt["request_sha256"],
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.communicate()


if __name__ == "__main__":
    unittest.main()
