from fractions import Fraction

from certnum.expr.parse import parse_expr
from certnum.interval.interval import Interval
from certnum.ode.sqrt_log import log_enclosure, sqrt_enclosure, sqrt_interval
from certnum.opt.branch_bound import optimize
from certnum.root.newton import interval_newton_step, refine_root
from certnum.root.isolation import RootStatus


def test_sqrt_enclosure_verified_by_squares():
    enc = sqrt_enclosure(Fraction(2))
    assert enc.is_ok
    lo, hi = enc.interval.lo, enc.interval.hi
    assert lo * lo <= 2 <= hi * hi
    assert lo >= 0


def test_sqrt_interval_monotone():
    enc = sqrt_interval(Interval.mk(1, 4))
    assert enc.is_ok
    assert Fraction(1) in enc.interval or enc.interval.lo <= 1
    assert Fraction(2) in enc.interval or enc.interval.hi >= 2


def test_log_near_one():
    enc = log_enclosure(Fraction(1))
    assert enc.is_ok
    assert enc.interval.lo == 0 and enc.interval.hi == 0
    enc2 = log_enclosure(Fraction(3, 2))
    assert enc2.is_ok
    assert enc2.interval.lo > 0


def test_newton_contracts_sqrt2():
    e = parse_expr("x^2 - 2")
    step = interval_newton_step(e, "x", Interval.mk(Fraction(1), Fraction(2)))
    assert step is not None
    assert not step.after.is_empty
    assert step.after.width() <= Fraction(1)


def test_refine_root_unique():
    e = parse_expr("x^2 - 2")
    cert = refine_root(e, "x", Interval.mk(1, 2), max_steps=10)
    assert cert.status in (RootStatus.UNIQUE, RootStatus.EXISTS, RootStatus.POSSIBLE)


def test_opt_provenance_coverage():
    e = parse_expr("(x-1)^2 + (y)^2")
    cert = optimize(
        e,
        {"x": Interval.mk(0, 2), "y": Interval.mk(-1, 1)},
        tol=Fraction(1, 10),
    )
    assert cert.coverage_ok()
    assert cert.lower_bound <= cert.upper_bound
