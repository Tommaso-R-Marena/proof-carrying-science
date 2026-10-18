from fractions import Fraction

from certnum.ad.forward import differentiate, gradient_interval
from certnum.certificate.checker import check_certificate
from certnum.certificate.schema import make_certificate
from certnum.expr.ast import expr_to_json
from certnum.expr.eval import eval_exact, eval_interval, mean_value_enclosure
from certnum.expr.parse import parse_expr
from certnum.expr.simplify import simplify
from certnum.interval.interval import Interval
from certnum.opt.branch_bound import optimize
from certnum.root.isolation import RootStatus, isolate_roots


def test_parse_and_eval():
    e = parse_expr("x^2 - 2*x + 1")
    assert eval_exact(e, {"x": Fraction(3)}) == Fraction(4)
    enc = eval_interval(e, {"x": Interval.mk(0, 2)})
    assert enc.is_ok
    assert Fraction(0) in enc.interval or enc.interval.lo <= 0 <= enc.interval.hi


def test_simplify_const_fold():
    e = simplify(parse_expr("2 + 3*4"))
    from certnum.expr.ast import Const
    assert isinstance(e, Const) and e.value == 14


def test_ad_polynomial():
    e = parse_expr("x^3 + 2*x")
    d = differentiate(e, "x")
    # 3x^2 + 2 at x=1 is 5
    assert eval_exact(d, {"x": 1}) == 5


def test_root_unique_quadratic():
    e = parse_expr("x^2 - 2")
    roots = isolate_roots(e, "x", Interval.mk(1, 2), max_width=Fraction(1, 100))
    assert any(r.status in (RootStatus.UNIQUE, RootStatus.EXISTS) for r in roots)


def test_optimize_quadratic():
    e = parse_expr("(x-1)^2")
    cert = optimize(e, {"x": Interval.mk(0, 3)}, tol=Fraction(1, 50))
    assert cert.lower_bound <= 0
    assert cert.upper_bound >= 0
    assert cert.gap >= 0


def test_mean_value_can_be_tighter():
    e = parse_expr("x*(1-x)")
    box = {"x": Interval.mk(0, 1)}
    nat = eval_interval(e, box).interval
    mv = mean_value_enclosure(e, box).interval
    # Dependency problem: natural is [-0?,1] style wide; MV often tighter
    assert mv.width() <= nat.width() + Fraction(1, 1000000)


def test_interval_certificate_roundtrip():
    e = parse_expr("x + y")
    box = {"x": Interval.mk(1, 2), "y": Interval.mk(3, 4)}
    enc = eval_interval(e, box)
    cert = make_certificate(
        "interval_enclosure",
        claim={
            "expr": expr_to_json(e),
            "box": {k: v.to_json() for k, v in box.items()},
            "enclosure": enc.interval.to_json(),
        },
        witness={"sample_points": [{"x": "1", "y": "3"}]},
    )
    assert check_certificate(cert).accepted


def test_adversarial_bad_enclosure_rejected():
    e = parse_expr("x + y")
    box = {"x": Interval.mk(1, 2), "y": Interval.mk(3, 4)}
    # Claim too tight / wrong
    cert = make_certificate(
        "interval_enclosure",
        claim={
            "expr": expr_to_json(e),
            "box": {k: v.to_json() for k, v in box.items()},
            "enclosure": Interval.mk(0, 1).to_json(),
        },
        witness={},
    )
    assert not check_certificate(cert).accepted
