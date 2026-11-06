"""Frozen, conservative grading of candidates against internal manual probes.

Reference labels enter this module only after extraction/checking. Matching here
is an evaluation operation, never an oracle supplied to PCS or its ranker.
Importing this module opens no source or reference file.
"""
from __future__ import annotations

import ast
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import random
import re

try:
    from .retrieval import rank
except ImportError:
    from retrieval import rank

FROZEN_PROTOCOL = {
    "version": "scientific-manual-probe-grading-v1",
    "reference_role": "handcrafted independent internal reference; not external expert validation",
    "grounding": "exact source filename and SHA256; byte-validated candidate quote and overlapping reference quote",
    "semantic_matching": "typed entity/name plus finite value and explicit unit semantics, or finite canonical arithmetic AST; assertion atoms must occur in grounded quote",
    "missing_typed_slots": "abstain/miss; source discovery alone never establishes semantic recall",
    "assumption_policy": "assumption-sensitive inference abstains in this fragment; source overlap is not an assumption proof",
    "certification": "candidate relevance and a generic numerical/checker PASS do not certify scientific meaning",
    "precision_scope": "reference-supported candidate/probe pairs only; no overall precision for unannotated extractions",
    "counterclaims": "separate from supported recall; no observed proposal is abstention, not demonstrated refutation",
    "retrieval": "source relevance only; all reference statements including false questions; missing relevant candidates score zero",
    "retrieval_modes": ["bm25", "tfidf", "neural", "random"],
    "max_candidate_quote_chars": 4000,
    "retrieval_chunk_chars": 1000,
    "minimum_relevance_token_overlap": 0.6,
    "minimum_relevance_shared_tokens": 3,
    "tie_breaking": "stable candidate input order",
    "training_or_retuning": False,
}
_CATEGORIES = ("equations", "quantities", "tables", "assumptions", "unresolved", "claims")
_NAME_ALIASES = {
    "reportediterationcount": "iterations", "iterationcount": "iterations", "iteration": "iterations",
    "reportedfunctionevaluations": "functionevaluations", "functionevaluationcount": "functionevaluations",
    "reportedobjective": "objective", "objectivevalue": "objective",
    "reportedminimizer": "minimizer", "minimumobjective": "minimumobjective",
    "initialamount": "initialamount", "initialconcentration": "initialconcentration",
}
_UNIT_ALIASES = {"dimensionless": "1", "dimensionless_coordinate": "1", "dimensionless coordinate": "1",
                 "count": "item", "items": "item", "second": "s", "seconds": "s",
                 "minute": "min", "minutes": "min", "hour": "h", "hours": "h",
                 "micromolar": "uM", "millimolar": "mM", "molar": "M"}
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


def protocol_sha256():
    return hashlib.sha256(json.dumps(FROZEN_PROTOCOL, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _fraction(value):
    if type(value) not in (int, float, str) or isinstance(value, float) and not math.isfinite(value):
        raise ValueError("not a finite number")
    text = str(value)
    if len(text) > 128 or not _NUMBER.fullmatch(text):
        raise ValueError("not a bounded finite decimal")
    if "e" in text.lower() and abs(int(text.lower().split("e")[1])) > 1000:
        raise ValueError("numeric exponent bound")
    return Fraction(text)


def _numeric_equal(actual, expected, tolerance=0):
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _numeric_equal(a, b, tolerance) for a, b in zip(actual, expected))
    if isinstance(expected, bool):
        return type(actual) is bool and actual == expected
    try:
        tol = _fraction(tolerance)
        return tol >= 0 and abs(_fraction(actual)-_fraction(expected)) <= tol
    except (ValueError, TypeError, OverflowError):
        return False


def _name(value):
    if not isinstance(value, str):
        return None
    # Case carries scientific meaning in identifiers such as M, m, pM, and PM.
    if value.isidentifier() and len(value) <= 4:
        return value
    normalized = re.sub(r"[^a-z0-9]", "", value.lower().removeprefix("sbml_"))
    return _NAME_ALIASES.get(normalized, normalized)


def _unit(value):
    if value is None or not isinstance(value, str) or not value.strip():
        return None
    value = value.strip().replace("μ", "u").replace("µ", "u").replace("−", "-")
    return _UNIT_ALIASES.get(value, value)


def canonical_expression(value, depth=0):
    """Compare bounded arithmetic syntax; no eval, CAS, or numerical sampling."""
    if depth > 40:
        raise ValueError("expression depth bound")
    if type(value) in (int, float):
        return ("number", str(_fraction(value)))
    if isinstance(value, str):
        if not value or len(value) > 4096:
            raise ValueError("expression length bound")
        tree = ast.parse(value.replace("^", "**"), mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 2048:
            raise ValueError("expression node bound")
        return canonical_expression(tree.body, depth+1)
    if isinstance(value, dict):
        op = value.get("op")
        fields = {"number": {"op", "value"}, "symbol": {"op", "name"},
                  "add": {"op", "args"}, "mul": {"op", "args"}, "sub": {"op", "args"},
                  "div": {"op", "args"}, "pow": {"op", "args"}, "neg": {"op", "arg"},
                  "reaction_rate": {"op", "reaction"}, "derivative": {"op", "state", "variable"},
                  "subscript": {"op", "value", "index"}, "slice": {"op", "lower", "upper", "step"},
                  "vector": {"op", "items"}, "call": {"op", "function", "args", "keywords"}}
        if op not in fields or set(value)-fields[op]:
            raise ValueError("unsupported typed AST fields")
        if op == "number":
            return ("number", str(_fraction(value.get("value"))))
        if op == "symbol":
            name = value.get("name")
            if not isinstance(name, str) or not name.isidentifier():
                raise ValueError("bad symbol")
            return ("symbol", name)
        if op in ("add", "mul", "sub", "div", "pow"):
            args = value.get("args")
            if not isinstance(args, list) or not 2 <= len(args) <= 64:
                raise ValueError("bad operation arity")
            return _operation(op, [canonical_expression(x, depth+1) for x in args])
        if op == "neg":
            return ("neg", canonical_expression(value["arg"], depth+1))
        if op == "reaction_rate":
            if not isinstance(value.get("reaction"), str) or not value["reaction"].isidentifier():
                raise ValueError("bad reaction identifier")
            return ("reaction_rate", value["reaction"])
        if op == "derivative":
            if not all(isinstance(value.get(k), str) and value[k].isidentifier() for k in ("state", "variable")):
                raise ValueError("bad derivative identifier")
            return ("derivative", value["state"], value["variable"])
        if op == "subscript":
            return ("subscript", canonical_expression(value["value"], depth+1), canonical_expression(value["index"], depth+1))
        if op == "slice":
            return ("slice", *(canonical_expression(value[k], depth+1) if value.get(k) is not None else None for k in ("lower", "upper", "step")))
        if op == "vector":
            if not isinstance(value.get("items"), list) or len(value["items"]) > 64:
                raise ValueError("vector arity bound")
            return ("vector", tuple(canonical_expression(x, depth+1) for x in value["items"]))
        if op == "call":
            name = value.get("function")
            if name not in {"sin", "cos", "tan", "exp", "log", "ln", "sqrt", "abs", "sum"}:
                raise ValueError("unsupported call")
            args = value.get("args", [])
            if not isinstance(args, list) or not 1 <= len(args) <= 4:
                raise ValueError("call arity bound")
            keywords = value.get("keywords", {})
            if not isinstance(keywords, dict) or any(k != "axis" or type(v) is not int for k, v in keywords.items()):
                raise ValueError("unsupported call keyword")
            return ("call", "log" if name == "ln" else name, tuple(canonical_expression(x, depth+1) for x in args), tuple(sorted(keywords.items())))
        raise ValueError("unsupported typed AST")
    if isinstance(value, ast.Constant) and type(value.value) in (int, float):
        return ("number", str(_fraction(value.value)))
    if isinstance(value, ast.Name):
        return ("symbol", value.id)
    if isinstance(value, ast.UnaryOp) and isinstance(value.op, (ast.USub, ast.UAdd)):
        child = canonical_expression(value.operand, depth+1)
        return ("neg", child) if isinstance(value.op, ast.USub) else child
    if isinstance(value, ast.BinOp):
        op = {ast.Add: "add", ast.Mult: "mul", ast.Sub: "sub", ast.Div: "div", ast.Pow: "pow"}.get(type(value.op))
        if op:
            return _operation(op, [canonical_expression(value.left, depth+1), canonical_expression(value.right, depth+1)])
    if isinstance(value, ast.Subscript):
        return ("subscript", canonical_expression(value.value, depth+1), canonical_expression(value.slice, depth+1))
    if isinstance(value, ast.Slice):
        return ("slice", *(canonical_expression(x, depth+1) if x is not None else None for x in (value.lower, value.upper, value.step)))
    if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) <= 64:
        return ("vector", tuple(canonical_expression(x, depth+1) for x in value.elts))
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
        if any(k.arg != "axis" or not isinstance(k.value, ast.Constant) or type(k.value.value) is not int for k in value.keywords):
            raise ValueError("unsupported call keyword")
        if len({k.arg for k in value.keywords}) != len(value.keywords):
            raise ValueError("duplicate call keyword")
        return canonical_expression({"op": "call", "function": value.func.id, "args": value.args,
                                     "keywords": {k.arg: k.value.value for k in value.keywords}} , depth+1)
    raise ValueError("unsupported expression")


def _operation(op, args):
    if op in ("add", "mul"):
        flat = []
        for arg in args:
            flat.extend(arg[1] if arg[0] == op else [arg])
        return (op, tuple(sorted(flat, key=repr)))
    if len(args) != 2:
        raise ValueError("nonbinary arithmetic")
    return (op, *args)


def _expr_equal(actual, expected):
    try:
        return canonical_expression(actual) == canonical_expression(expected)
    except (ValueError, TypeError, KeyError, SyntaxError, RecursionError):
        return False


class _Sources:
    def __init__(self, inventory):
        self.artifacts = inventory.get("artifacts", []) if isinstance(inventory, dict) else inventory
        self.cache = {}

    def text(self, source):
        if not isinstance(source, dict):
            return None
        path, digest = source.get("path"), source.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str):
            return None
        key = (path, digest, source.get("artifact_id"))
        if key in self.cache:
            return self.cache[key]
        matches = [a for a in self.artifacts if a.get("path") == path and a.get("sha256") == digest
                   and (source.get("artifact_id") is None or a.get("id") == source["artifact_id"])]
        text = None
        if len(matches) == 1:
            try:
                raw = Path(matches[0]["snapshot_path"]).read_bytes()
                if len(raw) <= 10*1024*1024 and hashlib.sha256(raw).hexdigest() == digest:
                    text = raw.decode("utf-8-sig")
            except (OSError, KeyError, UnicodeError):
                pass
        self.cache[key] = text
        return text

    def valid(self, source, limit=True):
        text = self.text(source)
        if text is None:
            return False
        quote = source.get("quote")
        if not isinstance(quote, str) or not quote or limit and len(quote) > FROZEN_PROTOCOL["max_candidate_quote_chars"]:
            return False
        locator = source.get("locator")
        if not isinstance(locator, dict):
            return False
        start, end = locator.get("char_start"), locator.get("char_end")
        return type(start) is int and type(end) is int and 0 <= start < end <= len(text) and text[start:end] == quote


def _normalize_quote(text):
    return " ".join(str(text).split())


_STOP = frozenset("the a an of for to is in at and or with as this that value apply math ci cn times plus divide power xmlns http www org mathml metaid parameter reaction kineticlaw listofparameters type integer real".split())


def _tokens(text):
    return {t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z_0-9]*|\d+(?:\.\d+)?", text) if t.lower() not in _STOP}


def _quote_overlap(left, right):
    a, b = _normalize_quote(left), _normalize_quote(right)
    if not a or not b:
        return False
    if a == b:
        return True
    if (a in b or b in a) and len(min((a, b), key=len)) >= 20:
        return True
    ta, tb = _tokens(a), _tokens(b)
    overlap = ta & tb
    return len(overlap) >= FROZEN_PROTOCOL["minimum_relevance_shared_tokens"] and len(overlap)/max(1, min(len(ta), len(tb))) >= FROZEN_PROTOCOL["minimum_relevance_token_overlap"]


def _grounded(candidate_source, reference_source, sources, relevance=False):
    if (not sources.valid(candidate_source) or not isinstance(reference_source, dict)
            or Path(candidate_source["path"]).name != Path(reference_source.get("path", "")).name
            or candidate_source["sha256"] != reference_source.get("sha256")):
        return False
    quote = reference_source.get("quote", "")
    if not isinstance(quote, str) or not quote.strip() or len(quote) > 100_000:
        return False
    text = sources.text(candidate_source)
    # Whitespace normalization accommodates documentation indentation; actual
    # source character intervals, rather than shared words, ground grading.
    pattern = r"\s+".join(re.escape(part) for part in quote.split())
    occurrences = list(re.finditer(pattern, text))
    if not occurrences:
        return False
    if relevance:
        return _quote_overlap(candidate_source["quote"], quote)
    start, end = (candidate_source["locator"][key] for key in ("char_start", "char_end"))
    return any(start < m.end() and end > m.start() for m in occurrences)


def _records(interpretation):
    if "interpretations" in interpretation:
        interpretation = interpretation["interpretations"]
    records, seen = [], set()
    for category in _CATEGORIES:
        for index, item in enumerate(interpretation.get(category, [])):
            if not isinstance(item, dict):
                continue
            ident = item.get("interpretation_id", item.get("id", f"{category}-{index}"))
            if ident in seen:
                continue
            seen.add(ident)
            payload = item.get("interpretation") if category == "claims" else item
            record = {**(payload if isinstance(payload, dict) else {}), **item, "_category": category, "_id": ident}
            records.append(record)
    return records


def _expectation(annotation):
    expected = dict(annotation.get("typed_expectation", {}))
    if annotation.get("expected_status") != "supported":
        if isinstance(expected.get("counterclaim"), dict):
            expected = dict(expected["counterclaim"])
        if "counterclaim_value" in expected:
            expected["value"] = expected.pop("counterclaim_value")
        if "claimed_value" in expected:
            expected["value"] = expected.pop("claimed_value")
            expected["unit"] = expected.pop("claimed_unit", expected.get("unit"))
            expected.pop("reported_value", None)
        if "proposed_universal_value" in expected:
            expected["value"] = expected.pop("proposed_universal_value")
            expected["universal"] = True
            expected["relation"] = "equals"
        if expected.get("relation") == "not_reported":
            expected["any_reported_value"] = True
            expected["unit"] = expected.pop("proposed_unit", None)
            expected["relation"] = "equals"
        if expected.get("relation") == "requires" and type(expected.get("value")) is bool:
            expected["value"] = not expected["value"]
    return expected


def _subtrees(tree):
    yield tree
    if isinstance(tree, tuple):
        for item in tree:
            if isinstance(item, tuple):
                yield from _subtrees(item)


def _linear_terms(tree):
    op = tree[0]
    if op == "symbol":
        return {tree[1]: Fraction(1)}
    if op == "number":
        return {"__constant__": Fraction(tree[1])} if Fraction(tree[1]) else {}
    if op == "neg":
        result = _linear_terms(tree[1])
        return {k: -v for k, v in result.items()} if result is not None else None
    if op in {"add", "sub"}:
        children = tree[1] if op == "add" else (tree[1], ("neg", tree[2]))
        result = Counter()
        for child in children:
            terms = _linear_terms(child)
            if terms is None:
                return None
            for key, value in terms.items():
                result[key] += value
        return {k: v for k, v in result.items() if v}
    if op == "mul":
        coefficient, residual = Fraction(1), []
        for factor in tree[1]:
            if factor[0] == "number":
                coefficient *= Fraction(factor[1])
            else:
                residual.append(factor)
        if len(residual) != 1:
            return None
        result = _linear_terms(residual[0])
        return {k: coefficient*v for k, v in result.items()} if result is not None else None
    return None


def _assertion_atoms_in_quote(record, expected):
    """A tiny valid source span cannot license invented typed assertion atoms."""
    quote = record["source"]["quote"]
    identifiers = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", quote))
    numbers = []
    for literal in re.findall(r"(?<![A-Za-z_0-9.])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?![A-Za-z_0-9.])", quote):
        try:
            numbers.append(_fraction(literal))
        except ValueError:
            pass
    if "value" in expected and type(expected["value"]) is not bool:
        def flatten(item, depth=0):
            if depth > 16:
                raise ValueError("numeric value nesting bound")
            if isinstance(item, list):
                for child in item:
                    yield from flatten(child, depth+1)
            else:
                yield item
        vals = list(flatten(expected["value"]))
        if any(not any(abs(numerator-_fraction(wanted)) <= _fraction(expected.get("absolute_tolerance", 0))
                       for numerator in numbers) for wanted in vals):
            return False
        anchors = [expected.get(k) for k in ("entity", "quantity", "parameter") if isinstance(expected.get(k), str)]
        if anchors and not any(_name(a) in {_name(t) for t in identifiers} for a in anchors):
            return False
    expression = expected.get("rhs", expected.get("expression"))
    if expression is not None:
        try:
            for node in _subtrees(canonical_expression(expression)):
                if not node or not isinstance(node[0], str):
                    continue
                if node[0] == "symbol" and node[1] not in identifiers:
                    return False
                if node[0] == "number" and Fraction(node[1]) not in numbers:
                    return False
        except (ValueError, TypeError, SyntaxError, IndexError):
            return False
    return True


def _semantic(record, expected, peers, annotation, sources):
    """Return (match, target_identified, reason), never mine meaning from quotes."""
    if record["_category"] == "unresolved" or record.get("parse_status") == "UNRESOLVED":
        return False, False, "unresolved candidate"
    typed = record.get("typed_expectation", record.get("typed", {}))
    value = {**record, **(typed if isinstance(typed, dict) else {})}
    target = False
    for key in ("entity", "parameter", "reaction_id"):
        if key in expected:
            options = (value.get(key), value.get("name"), value.get("symbol"), value.get("scope"))
            if key == "reaction_id" and isinstance(value.get("lhs"), dict):
                options += (value["lhs"].get("reaction"),)
            if _name(expected[key]) not in {_name(x) for x in options if x is not None}:
                return False, False, "entity or reaction differs/missing"
            target = True
    if "quantity" in expected:
        options = (value.get("quantity"), value.get("name"), value.get("role"), value.get("symbol"))
        if _name(expected["quantity"]) not in {_name(x) for x in options if x is not None}:
            return False, target, "quantity name differs/missing"
        target = True
    if "lhs" in expected:
        if not _expr_equal(value.get("lhs"), expected["lhs"]):
            return False, target, "equation lhs differs/missing"
        target = True
    if not target and "expression" in expected:
        # Standalone expression probes can identify their exact expression.
        target = _expr_equal(value.get("rhs", value.get("expression")), expected["expression"])
    if not target:
        return False, False, "no explicit typed entity/name/lhs match"
    if expected.get("universal") and value.get("universal") is not True:
        return False, True, "universal claim not proposed"
    if expected.get("not_a_universal_bound") and value.get("universal") is True:
        return False, True, "illustrative result promoted to universal bound"
    if expected.get("not_a_universal_bound") and value.get("universal") is not False and value.get("value_semantics") != "REPORTED":
        return False, True, "reported versus universal scope is unspecified"
    if value.get("relation") in {"neq", "ne", "not_equals", "not_equal", "less_than", "greater_than"}:
        return False, True, "relation or polarity differs"
    relations = {"eq": "equals", "=": "equals", "equals_vector": "equals", "equivalent_expression": "equals"}
    wanted_relation = relations.get(expected.get("relation"), expected.get("relation"))
    if wanted_relation is None and any(k in expected for k in ("value", "rhs", "expression")):
        wanted_relation = "equals"
    actual_relation = relations.get(value.get("relation"), value.get("relation"))
    if wanted_relation == "equals" and actual_relation not in (None, "equals"):
        return False, True, "typed equality relation differs"
    if wanted_relation and wanted_relation != "equals" and actual_relation != wanted_relation:
        return False, True, "typed relation differs/missing"
    if "value" in expected and not _numeric_equal(value.get("value"), expected["value"], expected.get("absolute_tolerance", 0)):
        return False, True, "numeric or boolean value differs/missing"
    if "unit" in expected and _unit(value.get("unit")) != _unit(expected["unit"]):
        return False, True, "unit semantics differs/missing"
    if expected.get("any_reported_value"):
        try:
            _fraction(value.get("value"))
        except (ValueError, TypeError):
            return False, True, "no reported finite value proposed"
    for key in ("rhs", "expression"):
        if key in expected and not _expr_equal(value.get("rhs", value.get("expression")), expected[key]):
            return False, True, "equation rhs differs/missing"
    for key in ("condition", "depends_on_Y", "derivative", "initial_value", "dimension", "declarations", "stoichiometric_weights"):
        if key in expected and value.get(key) != expected[key]:
            return False, True, f"typed slot {key} differs/missing"
    if "variables" in expected:
        actual = value.get("variables")
        if actual is not None and actual != expected["variables"]:
            return False, True, "typed variables differ"
        if actual is None:
            try:
                nodes = list(_subtrees(canonical_expression(value.get("rhs", value.get("expression")))))
                if not all(canonical_expression(v) in nodes for v in expected["variables"]):
                    return False, True, "typed variables differ/missing"
            except (ValueError, TypeError, SyntaxError):
                return False, True, "typed variables differ/missing"
    if "terms" in expected:
        try:
            actual = _linear_terms(canonical_expression(value.get("rhs", value.get("expression"))))
            wanted = {k: _fraction(v) for k, v in expected["terms"].items() if _fraction(v)}
            if actual != wanted or ("terms" in value and value["terms"] != expected["terms"]):
                return False, True, "typed linear terms differ/missing"
        except (ValueError, TypeError, SyntaxError, AttributeError):
            return False, True, "typed linear terms differ/missing"
    if "dimension_name" in expected and not (expected["dimension_name"] == "dimensionless" and value.get("dimension") == {}):
        if value.get("dimension_name") != expected["dimension_name"]:
            return False, True, "dimension name differs/missing"
    if "parameters" in expected:
        parameters = value.get("parameters", {})
        if not isinstance(parameters, dict) or not isinstance(expected["parameters"], dict):
            return False, True, "parameter map malformed"
        for name, wanted in expected["parameters"].items():
            if isinstance(wanted, dict):
                if parameters.get(name) != wanted:
                    return False, True, "parameter dimension differs/missing"
                continue
            found = parameters.get(name)
            if found is None:
                matches = [p.get("value") for p in peers if _name(p.get("name")) == _name(name)
                           and p.get("scope") == value.get("scope") and _grounded(p.get("source"), annotation.get("source"), sources)]
                if len(matches) == 1:
                    found = matches[0]
            if not _numeric_equal(found, wanted, expected.get("absolute_tolerance", 0)):
                return False, True, "parameter value differs/missing"
    inferred = (annotation.get("units", {}).get("scope") == "reviewer_inferred_constraint"
                or annotation.get("label_provenance", {}).get("claim_origin") == "reviewer_derived_consequence"
                or value.get("inferred") is True)
    if inferred:
        return False, True, "assumption-sensitive inference is outside this grading fragment; abstain"
    if annotation.get("expected_status") == "supported":
        try:
            if not _assertion_atoms_in_quote(record, expected):
                return False, True, "grounded quote lacks assertion atoms"
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return False, True, "unsupported source assertion atoms"
    # Unknown expectation fields cannot be silently treated as a full match.
    supported = {"entity", "parameter", "reaction_id", "quantity", "lhs", "rhs", "expression", "value", "unit",
                 "relation", "absolute_tolerance", "variables", "terms", "parameters", "dimension_name", "dimension",
                 "condition", "depends_on_Y", "derivative", "initial_value", "stoichiometric_weights", "universal",
                 "not_a_universal_bound", "declarations", "any_reported_value"}
    if set(expected)-supported:
        return False, True, "unhandled typed expectation slots"
    if "value" not in expected and not expected.get("any_reported_value") and not any(k in expected for k in ("rhs", "expression", "dimension", "parameters", "condition", "declarations", "derivative", "initial_value")):
        return False, True, "no supported assertion slot"
    return True, True, "typed and source-grounded match"


def _promoted(record, checks):
    if record.get("authority") is True or record.get("certified") is True or record.get("meaning_status") == "CERTIFIED":
        return True
    return any(c.get("interpretation_id", c.get("claim_id")) == record["_id"]
               and c.get("certifies_meaning") is True and c.get("status") in {"PASS", "CHECKED", "VERIFIED"}
               for c in checks if isinstance(c, dict))


def _has_assertion(record, expected, annotation, checks):
    if _promoted(record, checks):
        return True
    if record["_category"] == "unresolved" or record.get("parse_status") == "UNRESOLVED":
        return False
    if (annotation.get("units", {}).get("scope") == "reviewer_inferred_constraint"
            or annotation.get("label_provenance", {}).get("claim_origin") == "reviewer_derived_consequence"
            or record.get("inferred") is True):
        return False
    if "value" in expected or expected.get("any_reported_value"):
        if record.get("value") is None or "unit" in expected and expected["unit"] is not None and _unit(record.get("unit")) is None:
            return False
        if type(record["value"]) is bool:
            return type(expected.get("value")) is bool
        try:
            if isinstance(record["value"], list):
                return bool(record["value"]) and all(_fraction(x) is not None for x in record["value"])
            return _fraction(record["value"]) is not None
        except (ValueError, TypeError):
            return False
    return any(record.get(k) is not None for k in ("rhs", "expression", "dimension", "parameters", "condition", "declarations"))


def grade_reference(annotations, interpretation, inventory, checks=None):
    """Grade frozen output, retaining every reference miss and counterclaim probe."""
    annotations = annotations.get("annotations", []) if isinstance(annotations, dict) else annotations
    checks = checks if checks is not None else interpretation.get("checks", [])
    records, sources = _records(interpretation), _Sources(inventory)
    outcomes, correct_pairs, proposal_pairs, unsupported = [], set(), set(), set()
    for annotation in annotations:
        positive = annotation.get("expected_status") == "supported"
        expected = _expectation(annotation)
        covered, matched, targets, mismatches, promoted, unresolved, assertions = [], [], [], [], [], [], []
        for record in records:
            if not _grounded(record.get("source"), annotation.get("source"), sources):
                continue
            ident = record["_id"]
            covered.append(ident)
            match, target, reason = _semantic(record, expected, records, annotation, sources)
            if record["_category"] == "unresolved":
                unresolved.append(ident)
            if target:
                targets.append(ident)
                if _has_assertion(record, expected, annotation, checks):
                    assertions.append(ident)
            if match:
                matched.append(ident)
                if positive:
                    correct_pairs.add((annotation["id"], ident))
                if _promoted(record, checks):
                    promoted.append(ident)
            elif target:
                mismatches.append({"candidate_id": ident, "reason": reason})
            if (positive and target and record["_category"] != "unresolved") or (not positive and match):
                proposal_pairs.add((annotation["id"], ident))
            if _promoted(record, checks) and ((positive and target and not match) or (not positive and match)):
                unsupported.add((annotation["id"], ident))
        outcome = ("supported_candidate_discovered" if matched else "missed_supported_claim") if positive else (
            "counterclaim_proposed" if matched else "counterclaim_not_proposed_or_abstained")
        outcomes.append({"annotation_id": annotation["id"], "expected_status": annotation.get("expected_status"),
                         "reference_class": "supported" if positive else "counterclaim_or_insufficient_evidence",
                         "outcome": outcome, "source_covered": bool(covered), "source_candidate_ids": covered,
                         "semantic_match_ids": matched, "targeted_candidate_ids": targets,
                         "semantic_mismatches": mismatches, "promoted_candidate_ids": promoted,
                         "unresolved_candidate_ids": unresolved, "explicit_typed_proposal_ids": assertions,
                         "abstained": not matched and not assertions})
    positives = [o for o in outcomes if o["reference_class"] == "supported"]
    recalled = sum(bool(o["semantic_match_ids"]) for o in positives)
    counters = [o for o in outcomes if o["reference_class"] != "supported"]
    return {"protocol": FROZEN_PROTOCOL, "protocol_sha256": protocol_sha256(), "outcomes": outcomes,
            "metrics": {"supported_manual_claim_count": len(positives), "supported_manual_claims_discovered": recalled,
                        "supported_manual_claim_recall": recalled/len(positives) if positives else None,
                        "candidate_covered_probe_count": sum(o["source_covered"] for o in outcomes),
                        "reference_supported_probe_precision": len(correct_pairs)/len(proposal_pairs) if proposal_pairs else None,
                        "reference_supported_candidate_probe_pairs": len(correct_pairs), "candidate_proposal_probe_pairs": len(proposal_pairs),
                        "precision_denominator": "typed-targeted proposals on supported probes plus exact false/counterclaim proposals; unannotated candidates excluded",
                        "semantic_mismatch_count": sum(len(o["semantic_mismatches"]) for o in positives),
                        "unsupported_promotion_count": len(unsupported), "unsupported_promotions": [list(p) for p in sorted(unsupported)],
                        "counterclaim_probe_count": len(counters), "counterclaims_proposed": sum(bool(o["semantic_match_ids"]) for o in counters),
                        "abstention_count": sum(o["abstained"] for o in outcomes),
                        "unmatched_probe_count": sum(not o["semantic_match_ids"] for o in outcomes),
                        "certification_note": "Candidate discovery is not certified scientific understanding; generic checker PASS does not upgrade meaning.",
                        "overall_extraction_precision": None}}


def retrieval_candidates(interpretation, inventory):
    """Only byte-bound equation/quantity/table/unresolved spans, never whole files."""
    sources, candidates, seen = _Sources(inventory), [], set()
    for record in _records(interpretation):
        if record["_category"] not in {"equations", "quantities", "tables", "unresolved"}:
            continue
        source = record.get("source")
        if not sources.valid(source):
            continue
        quote = source["quote"]
        size = FROZEN_PROTOCOL["retrieval_chunk_chars"]
        for offset in range(0, len(quote), size):
            text = quote[offset:offset+size]
            start = source["locator"]["char_start"]+offset
            key = (source["path"], source["sha256"], start, start+len(text))
            if key in seen:
                continue
            seen.add(key)
            bound = {**source, "quote": text, "locator": {**source["locator"], "char_start": start, "char_end": start+len(text)}}
            candidates.append({"id": record["_id"]+f":{offset}", "text": text, "kind": record["_category"], "source": bound})
    return candidates


def evaluate_retrieval(annotations, interpretation, inventory, checkpoint=None, seed=1729):
    """Evaluate relevance only; absent source candidates are explicit zero scores."""
    annotations = annotations.get("annotations", []) if isinstance(annotations, dict) else annotations
    candidates, sources = retrieval_candidates(interpretation, inventory), _Sources(inventory)
    result = {"protocol_sha256": protocol_sha256(), "scope": "source relevance only, including false-question source discovery",
              "candidate_count": len(candidates), "candidate_ids": [c["id"] for c in candidates], "modes": {}}
    for mode in FROZEN_PROTOCOL["retrieval_modes"]:
        outcomes = []
        for annotation in annotations:
            relevant = {i for i, c in enumerate(candidates) if _grounded(c["source"], annotation.get("source"), sources, relevance=True)}
            if mode == "random":
                rng = random.Random(f"{seed}:{annotation['id']}")
                scores = [rng.random() for _ in candidates]
            else:
                scores = rank(annotation["statement"], candidates, mode, checkpoint)
            order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
            position = next((i+1 for i, candidate in enumerate(order) if candidate in relevant), None)
            outcomes.append({"annotation_id": annotation["id"], "reference_status": annotation.get("expected_status"),
                             "relevant_candidate_count": len(relevant), "rank": position,
                             "top_candidate_id": candidates[order[0]]["id"] if order else None,
                             "reciprocal_rank": 1/position if position else 0.0})
        n = len(outcomes)
        result["modes"][mode] = {"n": n, "top1": sum(o["rank"] == 1 for o in outcomes)/n if n else None,
                                  "mrr": sum(o["reciprocal_rank"] for o in outcomes)/n if n else None,
                                  "reference_candidate_coverage": sum(o["relevant_candidate_count"] > 0 for o in outcomes)/n if n else None,
                                  "outcomes": outcomes}
    return result
