import ast
from fractions import Fraction
from pathlib import Path

import pytest

from research.scientific_semantics_v3.numerical import (
    Interval, evaluate, parse, rational, reproduce, rounding_interval,
)

ROOT = Path(__file__).parents[1]
DEV = ROOT / "fixtures/development/nist_hahn1/Hahn1.dat"


def test_real_nist_residual_reproduction_and_exact_enclosure():
    r = reproduce(DEV.read_bytes())
    assert r["status"] == "REPRODUCED_ROUNDED_COMPUTATION"
    assert r["observations"] == 236 and r["degrees_of_freedom"] == 229
    assert r["rss_relative_discrepancy"] < 1e-9
    assert r["exact_rational_rounding_enclosure"]["status"] == "COMPATIBLE"
    assert r["scientific_meaning"] == "OPEN" and r["authority"] is False


def test_altered_table_and_false_residual_are_rejected():
    raw = DEV.read_bytes()
    changed = raw.replace(b".591E0", b"99.591E0", 1)
    assert reproduce(changed)["status"] == "REFUTED"
    assert reproduce(raw.replace(b"1.5324382854E+00", b"0.0000000000E+00"))["status"] == "REFUTED"
    assert reproduce(raw.replace(b"229", b"228", 1))["status"] == "REFUTED"


@pytest.mark.parametrize("source", ["__import__('os').system('id')", "x.__class__", "[x for x in y]", "x**1000000", "x**x", "f(x)"])
def test_untrusted_formula_cannot_execute(source):
    with pytest.raises(ValueError): evaluate(ast.parse(source, mode="eval").body, {"x": 2.0}, "float")


def test_exact_interval_contains_enumerated_corner_values():
    a = Interval(Fraction(-3, 2), Fraction(5, 3))
    b = Interval(Fraction(2, 7), Fraction(7, 2))
    for result, op in [(a+b, lambda x,y:x+y), (a*b, lambda x,y:x*y),
                       (a/b, lambda x,y:x/y), (a-b, lambda x,y:x-y)]:
        for x in [a.lo, Fraction(0), a.hi]:
            for y in [b.lo, Fraction(1), b.hi]:
                assert result.lo <= op(x,y) <= result.hi
    assert a.square().lo == 0 and a.square().hi == Fraction(25,9)
    with pytest.raises(ValueError): a/Interval(Fraction(-1), Fraction(1))


def test_print_rounding_not_statistical_uncertainty():
    bound = rounding_interval("1.20E-2")
    assert bound.lo == Fraction("0.01195") and bound.hi == Fraction("0.01205")
    assert rational("-1.20E-2") == Fraction(-3,250)
    with pytest.raises(ValueError): rational("1e1000000")


def test_transcendental_has_no_fabricated_interval_certificate():
    tree=ast.parse("b1*(1-exp(-b2*x))",mode="eval").body
    assert evaluate(tree,{"b1":2.0,"b2":1.0,"x":1.0},"float") > 1
    with pytest.raises(ValueError,match="transcendental"):
        evaluate(tree,{k:Interval(Fraction(1),Fraction(1)) for k in ["b1","b2","x"]},"interval")


def test_ambiguous_duplicate_parameter_and_source_size_fail_closed():
    raw=DEV.read_bytes()
    assert reproduce(raw+b"\n b1 = 1 1 1 1\n")["status"] == "UNKNOWN"
    assert reproduce(b"NIST/ITL StRD"+b"X"*1024**2)["status"] == "UNKNOWN"
