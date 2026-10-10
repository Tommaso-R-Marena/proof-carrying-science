"""Bidirectional controlled mathematical English / typed Lean fragment.

The parser generates arbitrary compositions in its grammar, not a theorem/proof
lookup table. English intent outside the grammar is unresolved, never certified.
"""
from __future__ import annotations

import re

from .ir import TYPES, OPS, binary, var, declaration, theorem, expression, digest

TOKEN = re.compile(r"∀|∃|→|↔|∧|∨|¬|≤|[A-Za-z][A-Za-z0-9_]*|[0-9]+|[(),:+*=]")
SYMBOLS = {v[2]: k for k, v in OPS.items()}
PRECEDENCE = {"↔": 1, "→": 2, "∨": 3, "∧": 4, "=": 5, "≤": 5, "+": 6, "*": 7}


class Parser:
    def __init__(self, source, variables=None, precedence=None):
        if type(source) is not str or len(source) > 3000:
            raise ValueError("statement exceeds language bound")
        self.tokens = TOKEN.findall(source)
        if "".join(self.tokens) != re.sub(r"\s", "", source):
            raise ValueError("unsupported mathematical syntax")
        self.i, self.variables = 0, dict(variables or {})
        self.precedence = precedence or PRECEDENCE

    def take(self, expected=None):
        if self.i >= len(self.tokens):
            raise ValueError("incomplete statement")
        value = self.tokens[self.i]
        if expected is not None and value != expected:
            raise ValueError("expected " + expected)
        self.i += 1
        return value

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else ""

    def parse(self, minimum=0):
        tok = self.take()
        if tok == "(":
            left = self.parse()
            self.take(")")
        elif tok in {"∀", "∃"}:
            binders = []
            while self.peek() == "(":
                self.take("("); name = self.take(); self.take(":"); domain = self.take()
                if domain == "Nat" and self.peek() == "→":
                    self.take("→"); self.take("Nat"); domain = "NatFn"
                self.take(")")
                if name in self.variables or domain not in TYPES:
                    raise ValueError("invalid type or shadowed name")
                self.variables[name] = domain
                binders.append((name, domain))
            if not binders:
                raise ValueError("typed binders required")
            self.take(",")
            left = self.parse()
            for name, domain in reversed(binders):
                del self.variables[name]
                left = {"op": "forall" if tok == "∀" else "exists", "name": name, "type": domain, "body": left}
        elif tok == "¬":
            left = {"op": "not", "arg": self.parse(8)}
        elif tok in {"True", "False"}:
            left = {"op": tok.lower()}
        elif tok.isdigit():
            domain = next((v for v in self.variables.values() if v in {"Nat", "Int"}), "Nat")
            if self.peek() == ":":
                self.take(":"); domain = self.take()
            left = {"op": "number", "value": int(tok), "type": domain}
        elif tok in self.variables:
            left = var(tok)
            if self.variables[tok] == "NatFn" and self.peek() and (self.peek() == "(" or self.peek() in self.variables):
                left = {"op": "apply", "fn": left, "arg": self.parse(8)}
        else:
            raise ValueError("unknown or unresolved symbol: " + tok)
        while self.peek() in self.precedence and self.precedence[self.peek()] >= minimum:
            symbol = self.take()
            p = self.precedence[symbol]
            right = self.parse(p if symbol == "→" else p + 1)
            left = binary(SYMBOLS[symbol], left, right)
        return left

    def complete(self):
        value = self.parse()
        if self.i != len(self.tokens):
            raise ValueError("trailing mathematical syntax")
        expression(value, self.variables)
        return value


def parse_lean(source):
    """Eligible theorem TYPE only. Submitted proof/code is never executed."""
    header = re.fullmatch(r"\s*theorem\s+[A-Za-z][A-Za-z0-9_]*\s*:\s*(.+)", source, re.S)
    if header:
        source = header.group(1)
    body = Parser(source).complete()
    binders = []
    while body["op"] == "forall":
        binders.append({"name": body["name"], "type": body["type"]})
        body = body["body"]
    result = {"format": "pcs-math-ir-v1", "binders": binders, "body": body}
    theorem(result)
    return result


DOMAINS = {"propositions": "Prop", "natural numbers": "Nat", "integers": "Int",
           "functions from natural numbers to natural numbers": "NatFn"}


def formalize(source, ranker=None):
    if type(source) is not str or not source.strip() or len(source) > 3000:
        raise ValueError("invalid English source")
    text = source.strip().rstrip(".")
    names, domain = [], None
    body = text
    for words, t in DOMAINS.items():
        alternatives = words + "|" + {"natural numbers": "natural number", "integers": "integer", "propositions": "proposition"}.get(words, words)
        match = re.fullmatch(r"(?:For all|For every|For any) (?:" + alternatives + r") ([A-Za-z0-9_, ]+), (.+)", text, re.I)
        if match:
            names = re.findall(r"[A-Za-z][A-Za-z0-9_]*", re.sub(r"\band\b", "", match[1]))
            domain, body = t, match[2]
            break
    existence = re.fullmatch(r"There exists (?:a|an) (natural number|integer|proposition) ([A-Za-z][A-Za-z0-9_]*) such that (.+)", text, re.I)
    if existence:
        domain = {"natural number": "Nat", "integer": "Int", "proposition": "Prop"}[existence[1].lower()]
        body = f"∃ ({existence[2]} : {domain}), {existence[3]}"
    if domain is None:
        return {"status": "unsupported", "source": source, "source_sha256": digest(source),
                "candidates": [], "reason": "Use explicit typed quantifiers in the supported grammar."}
    def nested_exists(match):
        t = {"natural number": "Nat", "integer": "Int", "proposition": "Prop"}[match[1].lower()]
        return f"∃ ({match[2]} : {t}), "
    body = re.sub(r"there exists (?:a|an) (natural number|integer|proposition) ([A-Za-z][A-Za-z0-9_]*) such that ", nested_exists, body, flags=re.I)
    if re.match(r"if ", body, re.I):
        pieces = re.split(r"\bthen\b", body[3:], maxsplit=1, flags=re.I)
        if len(pieces) != 2:
            return {"status": "unsupported", "candidates": [], "reason": "If requires an explicit then clause.", "source": source}
        body = "(" + pieces[0].strip() + ") → (" + pieces[1].strip() + ")"
    for english, symbol in [("if and only if", "↔"), ("is less than or equal to", "≤"),
                            ("equals", "="), ("implies", "→"), ("and", "∧"), ("or", "∨"), ("not", "¬")]:
        body = re.sub(r"\b" + english + r"\b", symbol, body, flags=re.I)
    # Unparenthesized mixing of conjunction/disjunction requires clarification.
    groups, current = [], [set()]
    for character in body:
        if character == "(": current.append(set())
        elif character == ")": groups.append(current.pop() if len(current) > 1 else current[0])
        elif character in {"∧", "∨"}: current[-1].add(character)
    ambiguous = any({"∧", "∨"} <= g for g in groups + current)
    candidates = []
    for precedence in ([PRECEDENCE, {**PRECEDENCE, "∧": 3, "∨": 4}] if ambiguous else [PRECEDENCE]):
        try:
            ir = declaration(names, Parser(body, {n: domain for n in names}, precedence).complete(), domain)
            formal = theorem(ir)
            if not any(c["lean"] == formal for c in candidates):
                candidates.append({"ir": ir, "lean": formal, "interpretation_sha256": digest(ir),
                                   "score": ranker(source, ir) if ranker else None})
        except ValueError as ex:
            return {"status": "unsupported", "source": source, "candidates": [], "reason": str(ex)}
    if ranker:
        candidates.sort(key=lambda c: -c["score"])
    return {"status": "ambiguous" if len(candidates) > 1 else "supported",
            "source": source, "source_sha256": digest(source), "candidates": candidates,
            "semantic_authorization": False,
            "fidelity_boundary": "Controlled grammar interpretation; user intent and unrestricted English equivalence unproved."}


def explain(ir):
    theorem(ir)
    words = {"and": "and", "or": "or", "implies": "implies", "iff": "if and only if",
             "eq": "equals", "le": "is less than or equal to", "add": "plus", "mul": "times"}
    domains = {v: k for k, v in DOMAINS.items()}
    def render(e):
        op = e["op"]
        if op == "var": return e["name"]
        if op == "number": return str(e["value"])
        if op in {"true", "false"}: return op
        if op == "not": return "not (" + render(e["arg"]) + ")"
        if op == "apply": return render(e["fn"]) + " applied to " + render(e["arg"])
        if op in {"forall", "exists"}:
            return ("for every " if op == "forall" else "there exists ") + e["name"] + " of type " + e["type"] + ", " + render(e["body"])
        return "(" + render(e["left"]) + " " + words[op] + " " + render(e["right"]) + ")"
    binders = ir["binders"]
    statement = "; ".join("For all " + domains[b["type"]] + " " + b["name"] for b in binders)
    statement += (", " if statement else "") + render(ir["body"])
    assumptions, conclusion = [], ir["body"]
    while conclusion["op"] == "implies":
        assumptions.append(render(conclusion["left"]))
        conclusion = conclusion["right"]
    return {"statement": statement + ".", "variables": binders,
            "assumptions": assumptions, "conclusion": render(conclusion),
            "source_correspondence": {"ir_sha256": digest(ir), "lean": theorem(ir)},
            "limits": "Statement explanation only. Proof explanation is not kernel-certified English; no empirical or external grounding."}
