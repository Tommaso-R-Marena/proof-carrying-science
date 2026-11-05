from fractions import Fraction

import pytest
from hypothesis import given, strategies as st

from certnum.interval.interval import Interval


rats = st.fractions(min_value=-50, max_value=50, max_denominator=30)


def test_empty_membership():
    assert 0 not in Interval.empty()


def test_add_sound_on_samples():
    I = Interval.mk(-2, 3)
    J = Interval.mk(Fraction(1, 2), 4)
    K = I.add(J)
    for x in [I.lo, I.hi, I.midpoint()]:
        for y in [J.lo, J.hi, J.midpoint()]:
            assert x + y in K


def test_mul_cross_zero():
    I = Interval.mk(-2, 3)
    J = Interval.mk(-1, 4)
    K = I.mul(J)
    assert (-2) * 4 in K
    assert 3 * (-1) in K
    assert 0 in K


def test_div_undefined_at_zero():
    I = Interval.mk(1, 2)
    J = Interval.mk(-1, 1)
    r = I.div(J)
    assert not r.is_ok


def test_recip_positive():
    I = Interval.mk(2, 4)
    r = I.recip()
    assert r.is_ok
    assert Fraction(1, 4) in r.interval
    assert Fraction(1, 2) in r.interval


def test_square_tighter_than_mul():
    I = Interval.mk(-2, 3)
    assert I.square().width() <= I.mul(I).width()


@given(rats, rats, rats, rats)
def test_add_property(a, b, c, d):
    I = Interval.of_bounds(a, b)
    J = Interval.of_bounds(c, d)
    if I.is_empty or J.is_empty:
        return
    x = (I.lo + I.hi) / 2
    y = (J.lo + J.hi) / 2
    assert x + y in I.add(J)


@given(rats, rats, rats, rats)
def test_mul_property(a, b, c, d):
    I = Interval.of_bounds(a, b)
    J = Interval.of_bounds(c, d)
    if I.is_empty or J.is_empty:
        return
    x = I.lo
    y = J.hi
    assert x * y in I.mul(J)
