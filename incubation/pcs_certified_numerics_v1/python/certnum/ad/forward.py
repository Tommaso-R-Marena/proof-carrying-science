"""Forward-mode symbolic automatic differentiation for the expression AST.

Derivatives are exact symbolic expressions. Interval evaluation of derivatives
yields verified derivative bounds (subject to domain conditions).
"""

from __future__ import annotations

from typing import Dict, Mapping, Optional

from certnum.expr.ast import (
    Abs, Add, Const, Div, Expr, Max, Min, Mul, Neg, Pow, Sub, Var,
)
from certnum.expr.eval import eval_interval
from certnum.expr.simplify import simplify
from certnum.interval.interval import Enclosure, Interval


def differentiate(e: Expr, var: str) -> Expr:
    """Symbolic ∂e/∂var for supported operators."""
    if isinstance(e, Const):
        return Const(0)
    if isinstance(e, Var):
        return Const(1 if e.name == var else 0)
    if isinstance(e, Neg):
        return Neg(differentiate(e.arg, var))
    if isinstance(e, Abs):
        # d/dx |u| = u/|u| * u' when u ≠ 0; at 0 subgradient [-1,1].
        # We encode sign(u)*u' via u/|u| * u' and leave 0-crossing as
        # interval obligation for the evaluator (Abs' enclosure uses hull).
        u = e.arg
        return Div(Mul(u, differentiate(u, var)), Abs(u))
    if isinstance(e, Add):
        return Add(differentiate(e.left, var), differentiate(e.right, var))
    if isinstance(e, Sub):
        return Sub(differentiate(e.left, var), differentiate(e.right, var))
    if isinstance(e, Mul):
        # product rule
        return Add(
            Mul(differentiate(e.left, var), e.right),
            Mul(e.left, differentiate(e.right, var)),
        )
    if isinstance(e, Div):
        # (n' d - n d') / d^2
        n, d = e.left, e.right
        num = Sub(Mul(differentiate(n, var), d), Mul(n, differentiate(d, var)))
        return Div(num, Pow(d, 2))
    if isinstance(e, Pow):
        # d/dx u^k = k * u^(k-1) * u' for integer k
        k = e.exp
        if k == 0:
            return Const(0)
        return Mul(Mul(Const(k), Pow(e.base, k - 1)), differentiate(e.base, var))
    if isinstance(e, Min) or isinstance(e, Max):
        # Not classically differentiable on ties; reject as unsupported symbolic form.
        # Callers should use interval subgradients separately.
        raise ValueError("symbolic derivative of min/max is unsupported in v1")
    raise ValueError(f"unsupported differentiation for {type(e)}")


def gradient_expr(e: Expr) -> Dict[str, Expr]:
    return {v: simplify(differentiate(e, v)) for v in sorted(e.vars())}


def gradient_interval(e: Expr, box: Mapping[str, Interval]) -> Optional[Dict[str, Interval]]:
    """Interval enclosure of the gradient over `box`, or None if unsupported."""
    try:
        g = gradient_expr(e)
    except ValueError:
        return None
    out: Dict[str, Interval] = {}
    for v, de in g.items():
        enc = eval_interval(de, box)
        if not enc.is_ok:
            return None
        out[v] = enc.interval
    return out


def jacobian_interval(
    exprs: Mapping[str, Expr], box: Mapping[str, Interval]
) -> Optional[Dict[str, Dict[str, Interval]]]:
    """Jacobian enclosures for a map of named expressions."""
    J: Dict[str, Dict[str, Interval]] = {}
    for name, e in exprs.items():
        g = gradient_interval(e, box)
        if g is None:
            return None
        J[name] = g
    return J
