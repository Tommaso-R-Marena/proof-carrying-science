"""Typed expression AST for certified numerical computation.

Semantics are exact on rationals where defined. Interval evaluation produces
sound enclosures; floating-point host math is never authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import FrozenSet, Tuple, Union


@dataclass(frozen=True)
class Const:
    value: Fraction

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", Fraction(self.value))

    def vars(self) -> FrozenSet[str]:
        return frozenset()


@dataclass(frozen=True)
class Var:
    name: str

    def vars(self) -> FrozenSet[str]:
        return frozenset({self.name})


@dataclass(frozen=True)
class Neg:
    arg: "Expr"

    def vars(self) -> FrozenSet[str]:
        return self.arg.vars()


@dataclass(frozen=True)
class Abs:
    arg: "Expr"

    def vars(self) -> FrozenSet[str]:
        return self.arg.vars()


@dataclass(frozen=True)
class Add:
    left: "Expr"
    right: "Expr"

    def vars(self) -> FrozenSet[str]:
        return self.left.vars() | self.right.vars()


@dataclass(frozen=True)
class Sub:
    left: "Expr"
    right: "Expr"

    def vars(self) -> FrozenSet[str]:
        return self.left.vars() | self.right.vars()


@dataclass(frozen=True)
class Mul:
    left: "Expr"
    right: "Expr"

    def vars(self) -> FrozenSet[str]:
        return self.left.vars() | self.right.vars()


@dataclass(frozen=True)
class Div:
    left: "Expr"
    right: "Expr"

    def vars(self) -> FrozenSet[str]:
        return self.left.vars() | self.right.vars()


@dataclass(frozen=True)
class Pow:
    base: "Expr"
    exp: int  # integer exponent only in v1

    def vars(self) -> FrozenSet[str]:
        return self.base.vars()


@dataclass(frozen=True)
class Min:
    left: "Expr"
    right: "Expr"

    def vars(self) -> FrozenSet[str]:
        return self.left.vars() | self.right.vars()


@dataclass(frozen=True)
class Max:
    left: "Expr"
    right: "Expr"

    def vars(self) -> FrozenSet[str]:
        return self.left.vars() | self.right.vars()


Expr = Union[Const, Var, Neg, Abs, Add, Sub, Mul, Div, Pow, Min, Max]


def expr_to_json(e: Expr) -> dict:
    if isinstance(e, Const):
        return {"op": "const", "value": str(e.value)}
    if isinstance(e, Var):
        return {"op": "var", "name": e.name}
    if isinstance(e, Neg):
        return {"op": "neg", "arg": expr_to_json(e.arg)}
    if isinstance(e, Abs):
        return {"op": "abs", "arg": expr_to_json(e.arg)}
    if isinstance(e, Add):
        return {"op": "add", "left": expr_to_json(e.left), "right": expr_to_json(e.right)}
    if isinstance(e, Sub):
        return {"op": "sub", "left": expr_to_json(e.left), "right": expr_to_json(e.right)}
    if isinstance(e, Mul):
        return {"op": "mul", "left": expr_to_json(e.left), "right": expr_to_json(e.right)}
    if isinstance(e, Div):
        return {"op": "div", "left": expr_to_json(e.left), "right": expr_to_json(e.right)}
    if isinstance(e, Pow):
        return {"op": "pow", "base": expr_to_json(e.base), "exp": e.exp}
    if isinstance(e, Min):
        return {"op": "min", "left": expr_to_json(e.left), "right": expr_to_json(e.right)}
    if isinstance(e, Max):
        return {"op": "max", "left": expr_to_json(e.left), "right": expr_to_json(e.right)}
    raise TypeError(f"unsupported expr {type(e)}")


def expr_from_json(obj: dict) -> Expr:
    op = obj["op"]
    if op == "const":
        return Const(Fraction(obj["value"]))
    if op == "var":
        return Var(obj["name"])
    if op == "neg":
        return Neg(expr_from_json(obj["arg"]))
    if op == "abs":
        return Abs(expr_from_json(obj["arg"]))
    if op == "add":
        return Add(expr_from_json(obj["left"]), expr_from_json(obj["right"]))
    if op == "sub":
        return Sub(expr_from_json(obj["left"]), expr_from_json(obj["right"]))
    if op == "mul":
        return Mul(expr_from_json(obj["left"]), expr_from_json(obj["right"]))
    if op == "div":
        return Div(expr_from_json(obj["left"]), expr_from_json(obj["right"]))
    if op == "pow":
        return Pow(expr_from_json(obj["base"]), int(obj["exp"]))
    if op == "min":
        return Min(expr_from_json(obj["left"]), expr_from_json(obj["right"]))
    if op == "max":
        return Max(expr_from_json(obj["left"]), expr_from_json(obj["right"]))
    raise ValueError(f"unsupported op {op}")
