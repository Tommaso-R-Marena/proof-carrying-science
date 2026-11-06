"""Fresh Lean compilation, full empty-axiom audit, and binding tamper checks."""
import copy
from pathlib import Path
import tempfile
import unittest

try:
    from .verify_formal import (DEFAULT_LEAN, REQUIRED_THEOREMS, ROOT, inspect_source,
                                parse_axiom_audit, replay_formal_receipt, verify_formal)
except ImportError:
    from verify_formal import (DEFAULT_LEAN, REQUIRED_THEOREMS, ROOT, inspect_source,
                               parse_axiom_audit, replay_formal_receipt, verify_formal)


class FormalSourceTests(unittest.TestCase):
    def test_import_and_no_admitted_declarations(self):
        source = inspect_source(ROOT / "formal" / "Dimensions.lean")
        self.assertEqual(source["forbidden_tokens"], [])
        self.assertEqual(source["unexpected_imports"], [])
        self.assertTrue(source["required_theorems_present"])

    def test_audit_parser_does_not_accept_nonempty_dependencies(self):
        output = "'X.a' does not depend on any axioms\n'X.b' depends on axioms: [propext, Classical.choice]\n"
        parsed = parse_axiom_audit(output)
        self.assertTrue(parsed["a"]["empty"])
        self.assertFalse(parsed["b"]["empty"])
        self.assertEqual(parsed["b"]["axioms"], ["propext", "Classical.choice"])

    def test_source_policy_detects_new_axiom_and_unexpected_import(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Bad.lean"
            source.write_text('import Mathlib\n-- axiom ignored in comment\naxiom bad : False\n')
            checked = inspect_source(source)
        self.assertEqual(checked["forbidden_tokens"], ["axiom"])
        self.assertEqual(checked["unexpected_imports"], ["Mathlib"])

    def test_absent_compiler_is_unknown(self):
        result = verify_formal("/path/which/does/not/exist/lean")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertFalse(result["authority"])


@unittest.skipUnless(DEFAULT_LEAN.is_file(), "Lean 4.28 is unavailable; formal obligation remains OPEN")
class LeanCompilationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = verify_formal(DEFAULT_LEAN)

    def test_source_compiles_with_complete_empty_audit(self):
        result = self.receipt
        self.assertEqual(result["status"], "VERIFIED", result)
        self.assertEqual(result["returncode"], 0)
        self.assertTrue(result["all_declared_theorems_audited"])
        self.assertTrue(result["required_audit_empty"])
        self.assertEqual(set(REQUIRED_THEOREMS) - result["axiom_audit"].keys(), set())
        self.assertTrue(result["source_stable_during_compile"])
        self.assertFalse(result["authority"])
        self.assertEqual(result["python_lean_refinement"], "OPEN")
        self.assertIn("-M1024", result["command"])
        self.assertIn("-j1", result["command"])

    def test_compiler_and_source_are_bound_to_receipt(self):
        result = self.receipt
        for key in ("source_sha256", "compiler_sha256", "stdout_sha256"):
            self.assertRegex(result[key], r"^[0-9a-f]{64}$")
        self.assertIn("4.28.0", result["compiler_version"])

    def test_forged_receipt_binding_fails_replay(self):
        forged = copy.deepcopy(self.receipt)
        forged["source_sha256"] = "0" * 64
        replayed = replay_formal_receipt(forged)
        self.assertEqual(replayed["status"], "REFUTED")
        self.assertFalse(replayed["replay_bindings_match"])
        self.assertFalse(replayed["authority"])


@unittest.skipUnless(DEFAULT_LEAN.is_file(), "Lean 4.28 is unavailable; conservation obligation remains OPEN")
class ConservationCompilationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = verify_formal(DEFAULT_LEAN, profile="conservation")

    def test_finite_integer_conservation_compiles_with_explicit_axiom_audit(self):
        result = self.receipt
        self.assertEqual(result["status"], "VERIFIED", result)
        self.assertEqual(result["allowed_lean_axioms"], ["propext"])
        self.assertTrue(result["all_declared_theorems_audited"])
        self.assertTrue(result["all_declared_axiom_audits_permitted"])
        self.assertFalse(result["all_declared_axiom_audits_empty"])
        self.assertEqual(len(result["axiom_audit"]), 9)
        for audit in result["axiom_audit"].values():
            self.assertEqual(audit["axioms"], ["propext"])
        self.assertEqual(result["python_lean_refinement"], "OPEN")
        self.assertFalse(result["authority"])
        self.assertIn("finite exact integer", result["scope"])


@unittest.skipUnless(DEFAULT_LEAN.is_file(), "Lean 4.28 is unavailable; sampling counterexample remains OPEN")
class SamplingCompilationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = verify_formal(DEFAULT_LEAN, profile="sampling")

    def test_fixed_sample_counterexample_compiles_with_empty_audit(self):
        result = self.receipt
        self.assertEqual(result["status"], "VERIFIED", result)
        self.assertEqual(result["allowed_lean_axioms"], [])
        self.assertTrue(result["all_declared_theorems_audited"])
        self.assertTrue(result["all_declared_axiom_audits_empty"])
        self.assertEqual(len(result["axiom_audit"]), 3)
        self.assertEqual(result["python_lean_refinement"], "OPEN")
        self.assertFalse(result["authority"])
        self.assertIn("twelve fixed samples", result["scope"])
        self.assertRegex(result["source_sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("-M1024", result["command"])
        self.assertIn("-j1", result["command"])


if __name__ == "__main__":
    unittest.main()
