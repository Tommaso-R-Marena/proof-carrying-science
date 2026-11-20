"""Closed set-algebra translation and proof search over arbitrary carriers."""
from __future__ import annotations

import hashlib
import itertools
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
MODULE = HERE / "lean" / "PCS" / "V2" / "SetAlgebra.lean"
BINARY = {"union", "inter", "diff", "inf", "sup"}
WORDS = {"union": "union", "intersection": "inter", "difference": "diff",
         "infimum": "inf", "supremum": "sup"}
SYMBOLS = {"|": "union", "∪": "union", "&": "inter", "∩": "inter",
           "\\": "diff", "∖": "diff"}
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,15}\Z")
TOKEN = re.compile(r"\s+|[A-Za-z][A-Za-z0-9_]*|[,()=⊆|&~\\∖∪∩∅]")
ALLOWED_AXIOMS = {"propext", "Quot.sound", "Classical.choice"}


def validate(contract: dict) -> None:
    """Reject uncertain binding, unknown constructors and excessive recursion/work."""
    if type(contract) is not dict or set(contract) != {"variables", "premises", "conclusion"}:
        raise ValueError("invalid contract fields")
    variables = contract["variables"]
    if (type(variables) is not list or len(variables) > 8 or
        any(type(v) is not str or not NAME.fullmatch(v) for v in variables) or
        len(set(variables)) != len(variables)):
        raise ValueError("invalid or duplicate set binders")
    premises = contract["premises"]
    if type(premises) is not list or len(premises) > 8:
        raise ValueError("invalid premises")
    visited = 0

    def expression(e, depth):
        nonlocal visited
        visited += 1
        if visited > 128 or depth > 24 or type(e) is not dict or len(e) != 1:
            raise ValueError("invalid or oversized expression")
        k, val = next(iter(e.items()))
        if k == "var" and type(val) is str and val in variables:
            return
        if k in ("empty", "univ") and val is True:
            return
        if k == "compl":
            expression(val, depth + 1)
            return
        if k in BINARY and type(val) is list and len(val) == 2:
            for child in val:
                expression(child, depth + 1)
            return
        raise ValueError("unbound variable or invalid set constructor")

    for pred in [*premises, contract["conclusion"]]:
        if type(pred) is not dict or len(pred) != 1:
            raise ValueError("invalid relation")
        k, pair = next(iter(pred.items()))
        if k not in ("equal", "subset") or type(pair) is not list or len(pair) != 2:
            raise ValueError("invalid binary relation")
        for e in pair:
            expression(e, 1)


class _Parser:
    def __init__(self, tokens, names, anonymous=False):
        self.tokens = tokens
        self.pos = 0
        self.names = list(names)
        self.anonymous = anonymous

    def take(self, *words):
        end = self.pos + len(words)
        if [s.lower() for s in self.tokens[self.pos:end]] == list(words):
            self.pos = end
            return True
        return False

    def need(self, *words):
        if not self.take(*words):
            raise ValueError("unexpected token")

    def name_pair(self):
        if len(self.names) != 2:
            raise ValueError("anaphor requires two bound sets")
        return [{"var": n} for n in self.names]

    def primary(self):
        if self.take("("):
            value = self.expression()
            self.need(")")
            return value
        if self.take("~"):
            return {"compl": self.primary()}
        self.take("the")
        if self.take("empty", "set") or self.take("∅"):
            return {"empty": True}
        if self.take("universal", "set"):
            return {"univ": True}
        if self.take("complement", "of"):
            return {"compl": self.primary()}
        if self.take("result", "of", "taking") or self.take("taking"):
            # These are optional wrappers specifically around a paired operation.
            self.need("their")
            return self.paired_operation()
        if self.take("their"):
            return self.paired_operation()
        if self.pos == len(self.tokens):
            raise ValueError("missing expression")
        token = self.tokens[self.pos]
        self.pos += 1
        key = WORDS.get(token.lower())
        if key:
            if key == "inf":
                self.take("(", "greatest", "lower", "bound", ")")
            if key == "sup":
                self.take("(", "least", "upper", "bound", ")")
            self.need("of")
            if self.take("two", "sets"):
                if self.names or key == "diff":
                    raise ValueError("ambiguous anonymous binders")
                self.names = ["A", "B"]
                self.anonymous = True
                return {key: self.name_pair()}
            left = self.primary()
            self.need("and")
            return {key: [left, self.primary()]}
        if self.anonymous or token not in self.names:
            raise ValueError("free variable")
        return {"var": token}

    def paired_operation(self):
        if self.pos == len(self.tokens):
            raise ValueError("missing paired operation")
        op = WORDS.get(self.tokens[self.pos].lower())
        if op not in {"inf", "sup", "inter", "union"}:
            raise ValueError("ambiguous paired operation")
        self.pos += 1
        return {op: self.name_pair()}

    def expression(self):
        left = self.primary()
        # A group may chain one associative operator. Group mixed operators and
        # nested differences explicitly to remove precedence ambiguities.
        previous = None
        while self.pos < len(self.tokens) and self.tokens[self.pos] in SYMBOLS:
            op = SYMBOLS[self.tokens[self.pos]]
            if previous is not None and (previous != op or op == "diff"):
                raise ValueError("mixed ungrouped set operators")
            self.pos += 1
            left = {op: [left, self.primary()]}
            previous = op
        return left

    def atom(self):
        lhs = self.expression()
        if self.take("is", "a", "subset", "of") or self.take("⊆"):
            op = "subset"
        elif (self.take("is", "the", "same", "as") or self.take("is", "equal", "to") or
              self.take("equals") or self.take("=") or self.take("is")):
            op = "equal"
        else:
            raise ValueError("missing relation")
        return {op: [lhs, self.expression()]}

    def contract(self):
        premises = []
        if self.take("if"):
            premises.append(self.atom())
            while self.take("and"):
                premises.append(self.atom())
            self.take(",")
            self.need("then")
        conclusion = self.atom()
        if self.pos != len(self.tokens):
            raise ValueError("trailing source")
        result = {"variables": self.names, "premises": premises, "conclusion": conclusion}
        validate(result)
        return result


def _binders(tokens):
    values = []
    for i, t in enumerate(tokens):
        if not NAME.fullmatch(t) or t.lower() in {"if", "then", "for", "and", "sets", "set", "the"}:
            continue
        if i == 0 or tokens[i-1].lower() in {",", "and"}:
            values.append(t)
    # Reconstruct the complete list grammar; reject missing separators, trailing
    # commas, stray words, and a second 'and'.
    joined = " ".join(tokens)
    word = r"[A-Za-z][A-Za-z0-9_]{0,15}"
    if not re.fullmatch(rf"{word}(?: , {word})*(?: (?:, )?and {word})?", joined):
        raise ValueError("invalid binder list")
    if len(values) != sum(t != "," and t.lower() != "and" for t in tokens):
        raise ValueError("reserved binder")
    return values


def parse_english(source: str) -> dict | None:
    """Fully consume controlled English. An unsupported sentence abstains."""
    if type(source) is not str or len(source) > 2048:
        return None
    source = source.strip().removesuffix(".")
    tokens = []
    i = 0
    while i < len(source):
        m = TOKEN.match(source, i)
        if m is None:
            return None
        i = m.end()
        if not m[0].isspace():
            tokens.append(m[0])
    if not tokens or len(tokens) > 192:
        return None
    if [t.lower() for t in tokens[:2]] in (["prove", "that"], ["show", "that"]):
        tokens = tokens[2:]
    lower = [t.lower() for t in tokens]
    if lower[:2] not in (["for", "all"], ["for", "any"], ["for", "every"]):
        try:
            return _Parser(tokens, []).contract()
        except ValueError:
            return None
    start = 2
    count = None
    if lower[start:start+1] in (["two"], ["three"], ["four"]):
        count = {"two": 2, "three": 3, "four": 4}[lower[start]]
        start += 1
    if lower[start:start+1] not in (["sets"], ["set"]):
        return None
    singular = lower[start] == "set"
    start += 1
    answers = []
    for cut in range(start, min(start + 25, len(tokens))):
        if tokens[cut] != ",":
            continue
        try:
            if start == cut and count == 2:
                names = ["A", "B"]
                # An anonymous pair can only be referenced by "their ...".
                if any(t in names for t in tokens[cut+1:]):
                    continue
            else:
                names = _binders(tokens[start:cut])
            if (singular and len(names) != 1) or (count is not None and count != len(names)):
                continue
            answers.append(_Parser(tokens[cut+1:], names, anonymous=(start == cut)).contract())
        except ValueError:
            continue
    return answers[0] if len(answers) == 1 else None


def check_pair(reference, candidate):
    from .set_algebra_kernel import check_pair as checked
    return checked(reference, candidate)
