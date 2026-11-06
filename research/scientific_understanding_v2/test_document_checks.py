"""Authored numerical reproduction and adversarial static-document tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from .document_checks import check_document


IMPORTS = ">>> import numpy as np\n>>> from scipy.optimize import minimize\n"
MODEL = ">>> def objective(x):\n...     return sum((x - 2)**2)\n"
RUN = ">>> x0 = np.array([0., 0.])\n>>> result = minimize(objective, x0, method='nelder-mead', options={'xatol': 1e-8, 'disp': True})\nOptimization terminated successfully.\nCurrent function value: 0.000000\n>>> print(result.x)\n[2.000000 2.000000]\n"


class DocumentChecksTests(unittest.TestCase):
    def run_document(self, text):
        result = check_document(text.encode(), "authored.rst")
        self.assertFalse(result["authority"])
        self.assertEqual(result["source_sha256"], hashlib.sha256(text.encode()).hexdigest())
        json.dumps(result, allow_nan=False)
        for example in result["examples"]:
            self.assertFalse(example["authority"])
            for source in example["source_bindings"]:
                locator = source["locator"]
                self.assertEqual(source["quote"], text[locator["char_start"]:locator["char_end"]])
                self.assertEqual(source["sha256"], result["source_sha256"])
        return result

    def test_reconstructs_literal_objective_without_source_execution(self):
        result = self.run_document(IMPORTS + MODEL + RUN)
        self.assertEqual(result["status"], "REPRODUCED")
        example = result["examples"][0]
        self.assertEqual(example["status"], "REPRODUCED")
        self.assertLess(example["observed"]["fun"], 1e-12)
        self.assertEqual(example["model"]["rhs"]["function"], "sum")

    def test_altered_reported_number_is_refuted(self):
        result = self.run_document(IMPORTS + MODEL + RUN.replace("Current function value: 0.000000", "Current function value: 9.000000"))
        self.assertEqual(result["status"], "REFUTED")
        self.assertTrue(any(comparison["field"] == "fun" and comparison["status"] == "MISMATCH" for comparison in result["examples"][0]["comparisons"]))

    def test_version_sensitive_counts_are_observations(self):
        text = IMPORTS + MODEL + RUN.replace("Current function value: 0.000000", "Current function value: 0.000000\nIterations: 1\nFunction evaluations: 1")
        result = self.run_document(text)
        example = result["examples"][0]
        self.assertEqual(example["status"], "REPRODUCED")
        self.assertEqual(example["version_sensitive_count_differences"], ["nit", "nfev"])
        self.assertTrue(all(item["version_sensitive"] for item in example["comparisons"] if item["field"] in {"nit", "nfev"}))

    def test_parameters_and_safe_wrapper_are_reconstructed(self):
        text = IMPORTS + ">>> def f(x, a, *, b):\n...     return sum(a*(x-1)**2) + b\n>>> def objective(x):\n...     return f(x, 0.5, b=3.)\n" + RUN.replace("0.000000", "3.000000").replace("[2.000000 2.000000]", "[1.000000 1.000000]")
        result = self.run_document(text)
        self.assertEqual(result["status"], "REPRODUCED")
        self.assertEqual(result["examples"][0]["model"]["rhs"]["op"], "model_call")

    def test_uploaded_calls_and_mutation_are_never_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = str(Path(directory) / "must-not-exist")
            text = IMPORTS + ">>> def objective(x):\n...     __import__('pathlib').Path(" + repr(marker) + ").write_text('executed')\n...     return sum(x**2)\n" + RUN
            result = self.run_document(text)
            self.assertNotEqual(result["status"], "REPRODUCED")
            self.assertFalse(Path(marker).exists())
        for mutation in ("x0[0] = -10", "del x0", "x0.append(3)"):
            text = IMPORTS + MODEL + RUN.replace(">>> result =", ">>> " + mutation + "\n>>> result =")
            result = self.run_document(text)
            self.assertFalse(any(example["status"] == "REPRODUCED" for example in result["examples"]))

    def test_shadowing_async_and_changed_global_abstain(self):
        texts = [
            IMPORTS + MODEL + RUN.replace(">>> result =", ">>> minimize = None\n>>> result ="),
            IMPORTS + MODEL.replace("def objective", "async def objective") + RUN,
            IMPORTS + ">>> k = 1\n>>> def objective(x):\n...     return sum((x-k)**2)\n>>> k = 2\n" + RUN,
            IMPORTS + ">>> def objective(x, sum=3):\n...     return sum(x**2)\n" + RUN,
            IMPORTS + ">>> def objective(x, np=3):\n...     return np.sum(x**2)\n" + RUN,
        ]
        for text in texts:
            with self.subTest(text=text):
                result = self.run_document(text)
                self.assertFalse(any(example["status"] == "REPRODUCED" for example in result["examples"]))

    def test_bound_and_unsupported_solver(self):
        self.assertEqual(check_document(b"x" * (2 * 1024 * 1024 + 1), "large.rst")["status"], "UNSUPPORTED")
        result = self.run_document(IMPORTS + MODEL + RUN.replace("nelder-mead", "BFGS"))
        self.assertEqual(result["status"], "UNSUPPORTED")
        self.assertIn("Nelder-Mead", result["examples"][0]["reason"])
        result = self.run_document(IMPORTS + MODEL + RUN.replace("'disp': True", "'maxiter': 999999"))
        self.assertEqual(result["examples"][0]["status"], "UNSUPPORTED")

    def test_generic_ode_parses_without_faking_output_comparison(self):
        text = ">>> import numpy as np\n>>> from scipy.integrate import solve_ivp\n>>> def rhs(t, y):\n...     return [-y[0]]\n>>> solution = solve_ivp(rhs, (0., 1.), [1.], t_eval=np.linspace(0., 1., 3), rtol=1e-8, atol=1e-10)\n"
        result = self.run_document(text)
        example = result["examples"][0]
        self.assertEqual(example["status"], "INCONCLUSIVE")
        self.assertTrue(example["observed"]["success"])
        self.assertAlmostEqual(example["observed"]["y"][0][-1], 0.367879441, places=7)
        self.assertFalse(example["comparisons"])

    def test_actual_development_document_first_example(self):
        # This is the development source, not oracle/reference/heldout labels.
        path = Path(__file__).parent / "fixtures" / "upstream" / "scipy_optimize.rst"
        if not path.exists():
            self.skipTest("development source fixture unavailable")
        result = check_document(path.read_bytes(), path.name)
        first = result["examples"][0]
        self.assertEqual(first["status"], "REPRODUCED")
        self.assertEqual(first["model"]["name"], "rosen")
        self.assertLess(first["observed"]["fun"], 1e-12)
        self.assertEqual(first["inputs"]["x0"], [1.3, 0.7, 0.8, 1.9, 1.2])
        self.assertTrue(any(item["field"] == "nit" and item["version_sensitive"] for item in first["comparisons"]))


if __name__ == "__main__":
    unittest.main()
