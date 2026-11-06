"""Adversarial dimensional checks, including exact biological concentration scales."""
from fractions import Fraction
import unittest

try:
    from .dimensions import (AMOUNT, CONCENTRATION, TIME, VOLTAGE, ZERO,
                             check_derivative, check_equation, check_expression,
                             parse_unit, replay)
except ImportError:
    from dimensions import (AMOUNT, CONCENTRATION, TIME, VOLTAGE, ZERO,
                            check_derivative, check_equation, check_expression,
                            parse_unit, replay)


class DimensionsTests(unittest.TestCase):
    def test_known_units_and_biological_concentration(self):
        self.assertEqual(parse_unit("mmol/L").dimension, CONCENTRATION)
        self.assertEqual(parse_unit("mmol/L").factor, Fraction(1))
        self.assertEqual(parse_unit("M").factor, Fraction(1000))
        self.assertEqual(parse_unit("mM").factor, Fraction(1))
        self.assertEqual(parse_unit("mV").dimension, VOLTAGE)
        self.assertEqual(parse_unit("mol").dimension, AMOUNT)

    def test_derivative_dimension_and_minute_scale(self):
        result = check_derivative("-k*S", "S", {"S": "mM", "k": "min^-1", "time": "s"}, assumptions=["S is explicitly a concentration"])
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["rhs_to_lhs_unit_factor"], {"numerator": 1, "denominator": 60})
        self.assertEqual(result["assumptions"], ["S is explicitly a concentration"])
        self.assertFalse(result["authority"])
        self.assertEqual(replay(result), result)

    def test_false_rate_units_refuted(self):
        result = check_derivative("k*S", "S", {"S": "mM", "k": "s", "time": "s"})
        self.assertEqual(result["status"], "REFUTED")
        self.assertEqual(result["diagnostics"][0]["code"], "equation_dimension_mismatch")

    def test_unitless_literal_zero_has_no_implicit_dimension(self):
        for expression in ("S+0", "0-S", "S+1", "S+0.0"):
            with self.subTest(expression=expression):
                result = check_expression(expression, {"S": "mM"})
                self.assertEqual(result["status"], "REFUTED")
        result = check_expression("0*S", {"S": "mM"})
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["dimension"], list(CONCENTRATION))

    def test_addition_incompatible_dimensions(self):
        result = check_expression("S+t", {"S": "mM", "t": "s"})
        self.assertEqual(result["status"], "REFUTED")
        self.assertEqual(result["diagnostics"][0]["path"], "$")

    def test_exact_normalization_evidence_for_mixed_scales(self):
        result = check_expression("a+b", {"a": "M", "b": "mM"})
        self.assertEqual(result["status"], "VERIFIED")
        self.assertIsNone(result["homogeneous_factor_to_SI"])
        self.assertEqual(result["canonical_expression"]["args"][0]["factor"], {"numerator": 1000, "denominator": 1})
        self.assertEqual(result["canonical_expression"]["args"][1]["factor"], {"numerator": 1, "denominator": 1})

    def test_missing_species_unit_not_inferred(self):
        result = check_derivative("k*S", "S", {"k": "s^-1", "time": "s"})
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["diagnostics"][0]["code"], "unknown_symbol")
        self.assertIn("lhs.state", result["diagnostics"][0]["path"])

    def test_missing_time_unit_not_defaulted(self):
        result = check_derivative("k*S", "S", {"S": "mM", "k": "s^-1"})
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("lhs.variable", result["diagnostics"][0]["path"])

    def test_unknown_and_affine_units(self):
        for unit, code in (("furlongs", "unknown_unit"), ("degC", "affine_unit_unsupported"), ("Celsius", "affine_unit_unsupported"), (None, "missing_unit")):
            with self.subTest(unit=unit):
                result = check_expression("T", {"T": unit})
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertEqual(result["diagnostics"][0]["code"], code)
                self.assertFalse(result["authority"])

    def test_transcendentals_require_dimensionless(self):
        for call in ("exp", "log", "sin", "cos"):
            self.assertEqual(check_expression(f"{call}(x)", {"x": "s"})["status"], "REFUTED")
            self.assertEqual(check_expression(f"{call}(x)", {"x": "dimensionless"})["status"], "VERIFIED")
        # Numerical domains (for example log(-1)) are deliberately a separate obligation.
        self.assertEqual(check_expression("log(-1)", {})["status"], "VERIFIED")

    def test_integer_power_and_quotient(self):
        result = check_expression("x**-2 / t", {"x": "m", "t": "s"})
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["dimension"], [-2, 0, -1, 0, 0, 0, 0])
        for expression in ("x**0.5", "x**n", "x**100"):
            self.assertEqual(check_expression(expression, {"x": "m", "n": "dimensionless"})["status"], "UNKNOWN")

    def test_numeric_constant_is_dimensionless(self):
        self.assertEqual(check_expression("0.1", {})["dimension"], list(ZERO))
        self.assertEqual(check_expression("1", {}, expected_unit="s")["status"], "REFUTED")
        self.assertEqual(check_expression("t", {"t": "min"}, expected_unit="s")["homogeneous_factor_to_expected"], {"numerator": 60, "denominator": 1})

    def test_safe_subset_never_executes(self):
        for expression in ("__import__('os').system('false')", "x.real", "[x for x in xs]", "x[0]", "lambda: 1", "x//2", "1j"):
            self.assertEqual(check_expression(expression, {})["status"], "UNKNOWN")

    def test_interpreter_ir_and_equation(self):
        ir = {"op": "mul", "args": [{"op": "symbol", "name": "k"}, {"op": "symbol", "name": "S"}]}
        lhs = {"op": "derivative", "state": "S", "variable": "time"}
        result = check_equation(lhs, ir, {"S": "mM", "k": "s^-1", "time": "s"})
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(replay(result), result)

    def test_replay_does_not_trust_claimed_status(self):
        result = check_expression("S+t", {"S": "mM", "t": "s"})
        result["status"] = "VERIFIED"
        self.assertEqual(replay(result)["status"], "REFUTED")

    def test_bounded_and_malformed_ir(self):
        for ir in ({"op": "add", "args": []}, {"op": "call", "function": "exp", "args": "x"}, {"op": "number", "value": "nan"}, {"op": "unknown"}, None):
            self.assertEqual(check_expression(ir, {})["status"], "UNKNOWN")
        nested = {"op": "number", "value": "1"}
        for _ in range(520):
            nested = {"op": "neg", "arg": nested}
        self.assertEqual(check_expression(nested, {})["status"], "UNKNOWN")

    def test_sum_and_unknown_function(self):
        self.assertEqual(check_expression("sum(a,b)", {"a": "mM", "b": "M"})["status"], "VERIFIED")
        self.assertEqual(check_expression("sum(a,b)", {"a": "mM", "b": "s"})["status"], "REFUTED")
        self.assertEqual(check_expression("sqrt(a)", {"a": "m"})["status"], "UNKNOWN")

    def test_time_declaration_and_conflicts_replay(self):
        wrong = check_derivative("k*S", "S", {"S": "mM", "k": "m^-1", "time": "m"})
        self.assertEqual(wrong["status"], "REFUTED")
        self.assertEqual(replay(wrong), wrong)
        conflict = check_derivative("k*S", "S", {"S": "mM", "k": "s^-1", "time": "s"}, time_unit="min")
        self.assertEqual(conflict["status"], "UNKNOWN")
        self.assertEqual(replay(conflict), conflict)
        explicit = check_derivative("k*S", "S", {"S": "mM", "k": "s^-1"}, time_unit="s")
        self.assertEqual(explicit["status"], "VERIFIED")
        self.assertEqual(replay(explicit), explicit)

    def test_resource_bounds_return_unknown(self):
        for expression in ("1e1000000000", {"op": "number", "value": "1" * 257}, "((((min**32)**32)**32)**32)"):
            result = check_expression("x", {"x": expression}) if isinstance(expression, str) and "min" in expression else check_expression(expression, {})
            self.assertEqual(result["status"], "UNKNOWN")

    def test_amount_is_not_concentration(self):
        result = check_equation("n", "c", {"n": "mmol", "c": "mM"})
        self.assertEqual(result["status"], "REFUTED")
        self.assertEqual(check_equation("n", "c*volume", {"n": "mmol", "c": "mM", "volume": "L"})["status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
