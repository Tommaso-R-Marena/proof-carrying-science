"""Recursive-descent parser for a small expression language.

Grammar (informal):
  expr := term (('+'|'-') term)*
  term := power (('*'|'/') power)*
  power := unary ('^' INTEGER)?
  unary := ('-'|'abs') unary | primary
  primary := NUMBER | IDENT | '(' expr ')' | 'min'|'max' '(' expr ',' expr ')'
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import List, Optional

from certnum.expr.ast import (
    Abs, Add, Const, Div, Expr, Max, Min, Mul, Neg, Pow, Sub, Var,
)


_TOKEN = re.compile(
    r"""
    \s*
    (
        \d+/\d+           # rational literal
      | \d+\.\d+          # decimal (converted exactly via Fraction)
      | \d+               # integer
      | [A-Za-z_][A-Za-z0-9_]*
      | \^|\+|\-|\*|/|\(|\)|,
    )
    """,
    re.VERBOSE,
)


class ParseError(ValueError):
    pass


def _tokenize(s: str) -> List[str]:
    pos = 0
    out: List[str] = []
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m:
            raise ParseError(f"unexpected input at {pos}: {s[pos:pos+20]!r}")
        tok = m.group(1)
        out.append(tok)
        pos = m.end()
    return out


class _Parser:
    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.i = 0

    def peek(self) -> Optional[str]:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def eat(self, expected: Optional[str] = None) -> str:
        tok = self.peek()
        if tok is None:
            raise ParseError("unexpected end of input")
        if expected is not None and tok != expected:
            raise ParseError(f"expected {expected!r}, got {tok!r}")
        self.i += 1
        return tok

    def parse(self) -> Expr:
        e = self.expr()
        if self.peek() is not None:
            raise ParseError(f"trailing input {self.peek()!r}")
        return e

    def expr(self) -> Expr:
        left = self.term()
        while self.peek() in ("+", "-"):
            op = self.eat()
            right = self.term()
            left = Add(left, right) if op == "+" else Sub(left, right)
        return left

    def term(self) -> Expr:
        left = self.power()
        while self.peek() in ("*", "/"):
            op = self.eat()
            right = self.power()
            left = Mul(left, right) if op == "*" else Div(left, right)
        return left

    def power(self) -> Expr:
        base = self.unary()
        if self.peek() == "^":
            self.eat("^")
            exp_tok = self.eat()
            if not re.fullmatch(r"-?\d+", exp_tok):
                # allow leading minus already consumed as unary; require integer
                raise ParseError(f"integer exponent required, got {exp_tok!r}")
            return Pow(base, int(exp_tok))
        return base

    def unary(self) -> Expr:
        if self.peek() == "-":
            self.eat("-")
            return Neg(self.unary())
        if self.peek() == "abs":
            self.eat("abs")
            self.eat("(")
            arg = self.expr()
            self.eat(")")
            return Abs(arg)
        return self.primary()

    def primary(self) -> Expr:
        tok = self.peek()
        if tok is None:
            raise ParseError("unexpected end")
        if tok in ("min", "max"):
            op = self.eat()
            self.eat("(")
            a = self.expr()
            self.eat(",")
            b = self.expr()
            self.eat(")")
            return Min(a, b) if op == "min" else Max(a, b)
        if tok == "(":
            self.eat("(")
            e = self.expr()
            self.eat(")")
            return e
        if re.fullmatch(r"\d+/\d+", tok) or re.fullmatch(r"\d+(\.\d+)?", tok):
            self.eat()
            return Const(Fraction(tok))
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tok):
            self.eat()
            return Var(tok)
        raise ParseError(f"unexpected token {tok!r}")


def parse_expr(s: str) -> Expr:
    return _Parser(_tokenize(s)).parse()
