"""Independent authored counterexamples and exact-scalar numerical oracles.

These cases were written without consulting held-out sources or predictions.
"""
import ast
from fractions import Fraction
import random
import pytest
from research.scientific_semantics_v3 import numerical as numeric


def document(formula, rows="1 2\n0.5 3", rss="0", std="0"):
    return ("NIST/ITL StRD\nModel: authored\n y = " + formula + " + e\nStarting values\n"
            " b1 = 1 1 1.0000000000 0.1\nResidual Sum of Squares: " + rss + "\n"
            "Residual Standard Deviation: " + std + "\nDegrees of Freedom: 1\n"
            "Number of Observations: 2\nData: y x\n" + rows + "\n").encode()


def test_long_decimal_constant_retains_exact_source_spelling():
    literal = "0.12345678901234567890123456789"
    tree = numeric.parse(document(literal + "+b1*x"))["tree"]
    point = numeric.evaluate(tree, {"b1": numeric.Interval(Fraction(0), Fraction(0)),
                                    "x": numeric.Interval(Fraction(0), Fraction(0))}, "interval")
    assert point.lo == point.hi == Fraction(literal)
    # This was the independently found pre-repair counterexample: converting
    # through ast.Constant's float loses the exact source decimal.
    assert Fraction(str(ast.parse(literal, mode="eval").body.value)) != Fraction(literal)


def test_unbound_float_ast_cannot_claim_exact_decimal_meaning():
    with pytest.raises(ValueError, match="source span required"):
        numeric.evaluate(ast.parse("0.12345678901234567890123456789", mode="eval").body, {}, "interval")


def test_parser_never_invents_x_equals_one_as_required_domain():
    result = numeric.reproduce(document("b1/(x-1)"))
    assert result["status"] == "REPRODUCED_ROUNDED_COMPUTATION"
    assert result["rss_float"] == 0
    assert result["authority"] is False
    assert result["scientific_meaning"] == "OPEN"


def test_interval_contains_independent_exact_scalar_samples():
    rng = random.Random(271828)
    tree = ast.parse("(b1+b2*x)/(1+b3*x)", mode="eval").body
    eps = Fraction(1, 100)
    for _ in range(240):
        a, b, c = (Fraction(rng.randint(-50, 50), 10), Fraction(rng.randint(-30, 30), 10),
                   Fraction(rng.randint(-3, 3), 10))
        bound = numeric.evaluate(tree, {
            "b1": numeric.Interval(a-eps, a+eps), "b2": numeric.Interval(b-eps, b+eps),
            "b3": numeric.Interval(c-eps, c+eps), "x": numeric.Interval(Fraction(-1), Fraction(1))}, "interval")
        for j in range(41):
            x = Fraction(j-20, 20)
            for da, db, dc in [(-eps, -eps, -eps), (-eps, eps, -eps), (eps, -eps, eps), (eps, eps, eps), (Fraction(0),)*3]:
                exact = ((a+da)+(b+db)*x)/(1+(c+dc)*x)
                assert bound.lo <= exact <= bound.hi


def test_transcendental_interval_result_remains_unsupported():
    with pytest.raises(ValueError, match="not implemented"):
        numeric.evaluate(ast.parse("exp(-b1*x)", mode="eval").body,
                         {"b1": numeric.Interval(Fraction(1, 100), Fraction(1, 100)),
                          "x": numeric.Interval(Fraction(5), Fraction(5))}, "interval")


def test_uploaded_formula_calls_never_execute(tmp_path):
    marker = tmp_path / "executed"
    formula = "__import__('pathlib').Path(" + repr(str(marker)) + ").touch()"
    result = numeric.reproduce(document(formula))
    assert result["status"] == "UNKNOWN"
    assert not marker.exists()
