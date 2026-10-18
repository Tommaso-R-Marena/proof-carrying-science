"""Semantics-preserving simplification (heuristic generator aid).

Simplifications preserve exact rational semantics and do not cancel
denominators without retaining domain obligations in Div nodes.
"""

from __future__ import annotations

from fractions import Fraction

from certnum.expr.ast import (
    Abs, Add, Const, Div, Expr, Max, Min, Mul, Neg, Pow, Sub, Var,
)


def simplify(e: Expr) -> Expr:
    if isinstance(e, Const) or isinstance(e, Var):
        return e
    if isinstance(e, Neg):
        a = simplify(e.arg)
        if isinstance(a, Const):
            return Const(-a.value)
        if isinstance(a, Neg):
            return a.arg
        return Neg(a)
    if isinstance(e, Abs):
        a = simplify(e.arg)
        if isinstance(a, Const):
            return Const(abs(a.value))
        if isinstance(a, Abs):
            return a
        return Abs(a)
    if isinstance(e, Add):
        l, r = simplify(e.left), simplify(e.right)
        if isinstance(l, Const) and isinstance(r, Const):
            return Const(l.value + r.value)
        if isinstance(l, Const) and l.value == 0:
            return r
        if isinstance(r, Const) and r.value == 0:
            return l
        return Add(l, r)
    if isinstance(e, Sub):
        l, r = simplify(e.left), simplify(e.right)
        if isinstance(l, Const) and isinstance(r, Const):
            return Const(l.value - r.value)
        if isinstance(r, Const) and r.value == 0:
            return l
        return Sub(l, r)
    if isinstance(e, Mul):
        l, r = simplify(e.left), simplify(e.right)
        if isinstance(l, Const) and isinstance(r, Const):
            return Const(l.value * r.value)
        if isinstance(l, Const) and l.value == 0:
            return Const(0)
        if isinstance(r, Const) and r.value == 0:
            return Const(0)
        if isinstance(l, Const) and l.value == 1:
            return r
        if isinstance(r, Const) and r.value == 1:
            return l
        return Mul(l, r)
    if isinstance(e, Div):
        l, r = simplify(e.left), simplify(e.right)
        # Do NOT cancel symbolic factors; only fold constants when denom ≠ 0
        if isinstance(l, Const) and isinstance(r, Const):
            if r.value == 0:
                return Div(l, r)  # preserve undefinedness
            return Const(l.value / r.value)
        if isinstance(r, Const) and r.value == 1:
            return l
        return Div(l, r)
    if isinstance(e, Pow):
        b = simplify(e.base)
        if isinstance(b, Const):
            if e.exp < 0 and b.value == 0:
                return Pow(b, e.exp)
            return Const(b.value ** e.exp)
        if e.exp == 0:
            return Const(1)
        if e.exp == 1:
            return b
        return Pow(b, e.exp)
    if isinstance(e, Min):
        l, r = simplify(e.left), simplify(e.right)
        if isinstance(l, Const) and isinstance(r, Const):
            return Const(min(l.value, r.value))
        return Min(l, r)
    if isinstance(e, Max):
        l, r = simplify(e.left), simplify(e.right)
        if isinstance(l, Const) and isinstance(r, Const):
            return Const(max(l.value, r.value))
        return Max(l, r)
    return e
