"""Exact and interval evaluation of expression ASTs."""

from __future__ import annotations

from fractions import Fraction
from typing import Dict, Mapping, Optional, Tuple

from certnum.expr.ast import (
    Abs, Add, Const, Div, Expr, Max, Min, Mul, Neg, Pow, Sub, Var,
)
from certnum.interval.interval import Enclosure, EnclStatus, Interval

Env = Mapping[str, Fraction]
Box = Mapping[str, Interval]


class EvalError(Exception):
    def __init__(self, status: EnclStatus, message: str):
        super().__init__(message)
        self.status = status


def eval_exact(e: Expr, env: Env) -> Fraction:
    """Exact rational evaluation; raises EvalError on undefined operations."""
    if isinstance(e, Const):
        return e.value
    if isinstance(e, Var):
        if e.name not in env:
            raise EvalError(EnclStatus.UNDEFINED, f"unbound variable {e.name}")
        return env[e.name]
    if isinstance(e, Neg):
        return -eval_exact(e.arg, env)
    if isinstance(e, Abs):
        return abs(eval_exact(e.arg, env))
    if isinstance(e, Add):
        return eval_exact(e.left, env) + eval_exact(e.right, env)
    if isinstance(e, Sub):
        return eval_exact(e.left, env) - eval_exact(e.right, env)
    if isinstance(e, Mul):
        return eval_exact(e.left, env) * eval_exact(e.right, env)
    if isinstance(e, Div):
        den = eval_exact(e.right, env)
        if den == 0:
            raise EvalError(EnclStatus.UNDEFINED, "division by zero")
        return eval_exact(e.left, env) / den
    if isinstance(e, Pow):
        base = eval_exact(e.base, env)
        if e.exp < 0 and base == 0:
            raise EvalError(EnclStatus.UNDEFINED, "0 to negative power")
        return base ** e.exp
    if isinstance(e, Min):
        return min(eval_exact(e.left, env), eval_exact(e.right, env))
    if isinstance(e, Max):
        return max(eval_exact(e.left, env), eval_exact(e.right, env))
    raise EvalError(EnclStatus.UNSUPPORTED, f"unsupported node {type(e)}")


def eval_interval(e: Expr, box: Box) -> Enclosure:
    """Natural interval extension (sound enclosure under domain conditions)."""
    if isinstance(e, Const):
        return Enclosure.ok(Interval.singleton(e.value))
    if isinstance(e, Var):
        if e.name not in box:
            return Enclosure.fail(EnclStatus.UNDEFINED)
        return Enclosure.ok(box[e.name])
    if isinstance(e, Neg):
        r = eval_interval(e.arg, box)
        return Enclosure.ok(r.interval.neg()) if r.is_ok else r
    if isinstance(e, Abs):
        r = eval_interval(e.arg, box)
        return Enclosure.ok(r.interval.abs()) if r.is_ok else r
    if isinstance(e, Add):
        a, b = eval_interval(e.left, box), eval_interval(e.right, box)
        if not a.is_ok:
            return a
        if not b.is_ok:
            return b
        return Enclosure.ok(a.interval.add(b.interval))
    if isinstance(e, Sub):
        a, b = eval_interval(e.left, box), eval_interval(e.right, box)
        if not a.is_ok:
            return a
        if not b.is_ok:
            return b
        return Enclosure.ok(a.interval.sub(b.interval))
    if isinstance(e, Mul):
        a, b = eval_interval(e.left, box), eval_interval(e.right, box)
        if not a.is_ok:
            return a
        if not b.is_ok:
            return b
        return Enclosure.ok(a.interval.mul(b.interval))
    if isinstance(e, Div):
        a, b = eval_interval(e.left, box), eval_interval(e.right, box)
        if not a.is_ok:
            return a
        if not b.is_ok:
            return b
        return a.interval.div(b.interval)
    if isinstance(e, Pow):
        a = eval_interval(e.base, box)
        if not a.is_ok:
            return a
        return a.interval.pow_int(e.exp)
    if isinstance(e, Min):
        a, b = eval_interval(e.left, box), eval_interval(e.right, box)
        if not a.is_ok:
            return a
        if not b.is_ok:
            return b
        # min range ⊆ hull of intervals, with lo = min(lo's), hi = min(hi's) is NOT sound
        # Sound enclosure: [min(lo_a, lo_b), min(hi_a, hi_b)] can be too tight.
        # Correct: range of min is inside [min(lo_a,lo_b), max(hi_a,hi_b)] intersected
        # with both? Standard: mk(min(a.lo,b.lo), min(a.hi,b.hi)) is sound for min.
        Ia, Ib = a.interval, b.interval
        if Ia.is_empty or Ib.is_empty:
            return Enclosure.ok(Interval.empty())
        return Enclosure.ok(Interval.mk(min(Ia.lo, Ib.lo), min(Ia.hi, Ib.hi)))  # type: ignore[arg-type]
    if isinstance(e, Max):
        a, b = eval_interval(e.left, box), eval_interval(e.right, box)
        if not a.is_ok:
            return a
        if not b.is_ok:
            return b
        Ia, Ib = a.interval, b.interval
        if Ia.is_empty or Ib.is_empty:
            return Enclosure.ok(Interval.empty())
        return Enclosure.ok(Interval.mk(max(Ia.lo, Ib.lo), max(Ia.hi, Ib.hi)))  # type: ignore[arg-type]
    return Enclosure.fail(EnclStatus.UNSUPPORTED)


def mean_value_enclosure(
    e: Expr,
    box: Box,
    center: Optional[Mapping[str, Fraction]] = None,
    deriv_box: Optional[Box] = None,
) -> Enclosure:
    """Mean-value form enclosure using interval derivative bounds.

    Requires univariate or provides componentwise Lipschitz via gradient box.
    For multivariate: f(x) ∈ f(c) + Σ G_i * (X_i - c_i) with G_i ⊇ ∂f/∂x_i(X).
    """
    from certnum.ad.forward import gradient_interval

    vars_ = sorted({v for I in [e] for v in e.vars()})
    if not vars_:
        return eval_interval(e, box)

    # Center
    c: Dict[str, Fraction] = {}
    for v in vars_:
        if center and v in center:
            c[v] = Fraction(center[v])
        else:
            I = box[v]
            if I.is_empty or I.midpoint() is None:
                return Enclosure.fail(EnclStatus.EMPTY_DOMAIN)
            c[v] = I.midpoint()  # type: ignore[assignment]

    try:
        fc = eval_exact(e, c)
    except EvalError as err:
        return Enclosure.fail(err.status)

    grads = deriv_box
    if grads is None:
        g_enc = gradient_interval(e, box)
        if g_enc is None:
            return Enclosure.fail(EnclStatus.UNSUPPORTED)
        grads = g_enc

    acc = Interval.singleton(fc)
    for v in vars_:
        dv = grads[v]
        dx = box[v].sub(Interval.singleton(c[v]))
        acc = acc.add(dv.mul(dx))
    return Enclosure.ok(acc)
