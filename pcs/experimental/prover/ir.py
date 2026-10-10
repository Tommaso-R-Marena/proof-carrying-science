"""Closed typed mathematical fragment. Receiver-owned rendering, no raw Lean."""
from __future__ import annotations

import hashlib
import json
import re

TYPES = {"Prop": "Prop", "Nat": "Nat", "Int": "Int", "NatFn": "Nat → Nat"}
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,23}\Z")
OPS = {"and": ("Prop", "Prop", "∧"), "or": ("Prop", "Prop", "∨"),
       "implies": ("Prop", "Prop", "→"), "iff": ("Prop", "Prop", "↔"),
       "add": (None, None, "+"), "mul": (None, None, "*"),
       "eq": (None, "Prop", "="), "le": (None, "Prop", "≤")}


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def expression(e, variables, depth=0):
    if depth > 12 or type(e) is not dict:
        raise ValueError("invalid or overdeep typed expression")
    op = e.get("op")
    if op == "var" and set(e) == {"op", "name"} and e["name"] in variables:
        return variables[e["name"]], e["name"]
    if op == "number" and set(e) == {"op", "value", "type"}:
        n, t = e["value"], e["type"]
        if type(n) is int and 0 <= n <= 1000 and t in {"Nat", "Int"}:
            return t, f"({n} : {t})"
    if op in {"true", "false"} and set(e) == {"op"}:
        return "Prop", op.title()
    if op == "not" and set(e) == {"op", "arg"}:
        t, a = expression(e["arg"], variables, depth + 1)
        if t == "Prop":
            return "Prop", f"(¬ {a})"
    if op == "apply" and set(e) == {"op", "fn", "arg"}:
        ft, f = expression(e["fn"], variables, depth + 1)
        at, a = expression(e["arg"], variables, depth + 1)
        if ft == "NatFn" and at == "Nat":
            return "Nat", f"({f} {a})"
    if op in {"forall", "exists"} and set(e) == {"op", "name", "type", "body"}:
        n, t = e["name"], e["type"]
        if type(n) is not str or not NAME.fullmatch(n) or n in variables or t not in TYPES:
            raise ValueError("invalid binder or name shadowing")
        bt, b = expression(e["body"], {**variables, n: t}, depth + 1)
        if bt == "Prop":
            return "Prop", f"({'∀' if op == 'forall' else '∃'} ({n} : {TYPES[t]}), {b})"
    if op in OPS and set(e) == {"op", "left", "right"}:
        lt, l = expression(e["left"], variables, depth + 1)
        rt, r = expression(e["right"], variables, depth + 1)
        expected, result, symbol = OPS[op]
        allowed = lt == rt and (lt == expected if expected else lt in {"Nat", "Int"})
        if allowed:
            return result or lt, f"({l} {symbol} {r})"
    raise ValueError("unsupported or ill-typed expression")


def theorem(obj):
    if type(obj) is not dict or set(obj) != {"format", "binders", "body"} or obj["format"] != "pcs-math-ir-v1":
        raise ValueError("invalid mathematical declaration")
    if len(json.dumps(obj)) > 16000 or type(obj["binders"]) is not list or len(obj["binders"]) > 12:
        raise ValueError("declaration exceeds bounds")
    variables, prefix = {}, []
    for b in obj["binders"]:
        if type(b) is not dict or set(b) != {"name", "type"}:
            raise ValueError("invalid binder")
        n, t = b["name"], b["type"]
        if type(n) is not str or not NAME.fullmatch(n) or n in variables or t not in TYPES:
            raise ValueError("unknown type or duplicate binder")
        variables[n] = t
        prefix.append(f"({n} : {TYPES[t]})")
    t, body = expression(obj["body"], variables)
    if t != "Prop":
        raise ValueError("theorem must be a proposition")
    return f"∀ {' '.join(prefix)}, {body}" if prefix else body


def var(name):
    return {"op": "var", "name": name}


def binary(op, a, b):
    return {"op": op, "left": a, "right": b}


def declaration(names, body, domain="Prop"):
    obj = {"format": "pcs-math-ir-v1", "binders": [{"name": n, "type": domain} for n in names], "body": body}
    theorem(obj)
    return obj
