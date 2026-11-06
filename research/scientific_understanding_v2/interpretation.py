"""Bounded, source-bound scientific interpretation proposals, never authority.

Source code is parsed as data.  No submitted expression is evaluated, imported,
compiled, or passed to a symbolic parser.  The small arithmetic IR deliberately
preserves the distinction between a reported number and an established result.
"""
from __future__ import annotations

import ast
import csv
from copy import deepcopy
import hashlib
import io
import json
import math
from pathlib import PurePosixPath
import re
import unicodedata
import xml.etree.ElementTree as ET

from research.scientific_intake_v1.checks import bound_bytes

VERSION = "scientific-interpretation-v2.0"
MAX_TEXT = 1_000_000
MAX_NODES = 50_000
MAX_DEPTH = 48
MAX_EXPR = 8192
MAX_ITEMS = 1024
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_NUM = re.compile(NUMBER + r"\Z")
_CALLS = frozenset({"sin", "cos", "tan", "exp", "log", "ln", "sqrt", "abs", "sum"})
_MATH_NAMESPACES = frozenset({"math", "np", "numpy", "jnp", "xp"})
_KNOWN_UNITS = frozenset("1 s ms us ns min h day Hz kHz m cm mm um nm kg g mg ug mol mmol umol nmol M mM uM nM L mL uL K Pa kPa J W V A N rad percent % second minute hour litre liter mole metre meter item count dimensionless".split())
_BASE_UNITS = {"second": "s", "mole": "mol", "litre": "L", "liter": "L", "metre": "m", "meter": "m", "kilogram": "kg", "gram": "g", "kelvin": "K", "ampere": "A", "dimensionless": "1", "item": "item"}


class Unsupported(ValueError):
    """Expression is outside the explicitly supported, nonexecuting fragment."""


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _number(value):
    text = str(value)
    if len(text) > 128 or not _NUM.fullmatch(text):
        raise Unsupported("not a bounded finite decimal")
    if "e" in text.lower() and abs(int(text.lower().split("e")[1])) > 1000:
        raise Unsupported("numeric exponent bound")
    return {"op": "number", "value": text}


def _symbol(name):
    if not isinstance(name, str) or len(name) > 128 or not name.isidentifier() or unicodedata.normalize("NFKC", name) != name:
        raise Unsupported("ambiguous or unsupported symbol")
    return {"op": "symbol", "name": name}


def _tree_bound(tree):
    stack = [(tree, 0)]
    count = 0
    while stack:
        node, depth = stack.pop()
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise Unsupported("syntax tree resource bound")
        stack.extend((child, depth + 1) for child in ast.iter_child_nodes(node))


def _ast_ir(node, source):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        if isinstance(node.value, float) and not math.isfinite(node.value):
            raise Unsupported("non-finite number")
        literal = ast.get_source_segment(source, node)
        return _number(literal if literal is not None and _NUM.fullmatch(literal) else node.value)
    if isinstance(node, ast.Name):
        return _symbol(node.id)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _ast_ir(node.operand, source)
        return {"op": "neg", "arg": value} if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp):
        op = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "div", ast.Pow: "pow"}.get(type(node.op))
        if op is None:
            raise Unsupported("unsupported arithmetic operator")
        return {"op": op, "args": [_ast_ir(node.left, source), _ast_ir(node.right, source)]}
    if isinstance(node, ast.Subscript):
        if isinstance(node.slice, ast.Slice):
            index = {"op": "slice", **{key: _ast_ir(value, source) if value is not None else None for key, value in (("lower", node.slice.lower), ("upper", node.slice.upper), ("step", node.slice.step))}}
        else:
            index = _ast_ir(node.slice, source)
        return {"op": "subscript", "value": _ast_ir(node.value, source), "index": index}
    if isinstance(node, (ast.Tuple, ast.List)):
        if len(node.elts) > 64:
            raise Unsupported("vector arity bound")
        return {"op": "vector", "items": [_ast_ir(item, source) for item in node.elts]}
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id in _MATH_NAMESPACES:
            name = node.func.attr
        else:
            raise Unsupported("call is not a declared mathematical primitive")
        if name not in _CALLS or not 1 <= len(node.args) <= 4:
            raise Unsupported("call is not a declared mathematical primitive")
        # Axis is metadata about reduction, never silently dropped.
        if any(key.arg != "axis" or not isinstance(key.value, ast.Constant) or type(key.value.value) is not int or abs(key.value.value) > 16 for key in node.keywords):
            raise Unsupported("unsupported mathematical call keyword")
        result = {"op": "call", "function": "log" if name == "ln" else name, "args": [_ast_ir(arg, source) for arg in node.args]}
        if node.keywords:
            result["keywords"] = {key.arg: key.value.value for key in node.keywords}
        return result
    raise Unsupported("expression syntax outside arithmetic fragment")


def parse_expression(expression):
    """Parse bounded arithmetic into a JSON IR without running any expression."""
    if not isinstance(expression, str) or not expression.strip() or len(expression) > MAX_EXPR:
        raise Unsupported("expression length bound")
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        _tree_bound(tree)
        return _ast_ir(tree.body, expression.strip())
    except (SyntaxError, RecursionError, MemoryError) as exc:
        raise Unsupported("invalid or excessive expression syntax") from exc


def render_expression(ir):
    """Render our own IR only; the returned text is never evaluated here."""
    op = ir["op"]
    if op == "number":
        return ir["value"]
    if op == "symbol":
        return ir["name"]
    if op in {"add", "sub", "mul", "div", "pow"}:
        token = {"add": "+", "sub": "-", "mul": "*", "div": "/", "pow": "**"}[op]
        return "(" + token.join(render_expression(arg) for arg in ir["args"]) + ")"
    if op == "neg":
        return "(-" + render_expression(ir["arg"]) + ")"
    if op == "call":
        args = [render_expression(arg) for arg in ir["args"]]
        args += [key + "=" + str(value) for key, value in sorted(ir.get("keywords", {}).items())]
        return ir["function"] + "(" + ",".join(args) + ")"
    if op == "subscript":
        index = ir["index"]
        if index["op"] == "slice":
            text = ":".join(render_expression(index[key]) if index[key] is not None else "" for key in ("lower", "upper", "step"))
            if index["step"] is None:
                text = text[:-1]
        else:
            text = render_expression(index)
        return render_expression(ir["value"]) + "[" + text + "]"
    if op == "vector":
        return "[" + ",".join(render_expression(item) for item in ir["items"]) + "]"
    raise Unsupported("IR cannot be rendered as bounded arithmetic")


def _unit(unit):
    if unit is None or not str(unit).strip():
        return None, "UNSPECIFIED"
    value = str(unit).strip().replace("μ", "u").replace("µ", "u").replace("−", "-")
    if len(value) > 256:
        return value[:256], "UNKNOWN"
    tokens = re.findall(r"[A-Za-z]+|%", value)
    known = value in _KNOWN_UNITS or bool(tokens) and all(token in _KNOWN_UNITS for token in tokens) and bool(re.fullmatch(r"[A-Za-z0-9%*/^()+.\s-]+", value))
    return value, "RECOGNIZED" if known else "UNKNOWN"


def _source(artifact, text, start=0, end=None, **locator):
    end = len(text) if end is None else end
    quote = text[start:end]
    location = {"line_start": text.count("\n", 0, start) + 1, "line_end": text.count("\n", 0, end) + 1,
                "char_start": start, "char_end": end, "text_encoding": "utf-8-sig",
                "source_sha256": artifact["sha256"], **locator}
    return {"artifact_id": artifact["id"], "sha256": artifact["sha256"], "path": artifact["path"], "locator": location, "quote": quote}


class _Builder:
    def __init__(self):
        self.result = {key: [] for key in ("claims", "equations", "quantities", "tables", "assumptions", "dependencies", "unresolved")}
        self.seen = set()

    def add(self, category, payload, source, *, kind=None, statement=None):
        if len(self.result[category]) >= MAX_ITEMS:
            return None
        value = {**deepcopy(payload), "source": deepcopy(source), "status": "CANDIDATE_INTERPRETATION",
                 "meaning_status": "MEANING_REVIEW_REQUIRED", "authority": False,
                 "transform": {"name": "source-grounded-scientific-interpretation", "version": VERSION}}
        value["id"] = category.rstrip("s") + "-" + _digest([category, value])[:24]
        if value["id"] in self.seen:
            return value
        self.seen.add(value["id"])
        self.result[category].append(value)
        if kind is not None and category != "claims":
            self.add("claims", {"kind": kind, "statement": statement or payload.get("statement", source["quote"]), "interpretation_id": value["id"], "interpretation": deepcopy(payload)}, source)
        return value

    def unresolved(self, source, reason, *, statement=None):
        return self.add("unresolved", {"reason": reason}, source, kind="unsupported", statement=statement)

    def equation(self, source, lhs, rhs, *, origin, **details):
        payload = {"lhs": lhs, "rhs": rhs, "relation": "eq", "origin": origin,
                   "expression": render_expression(rhs) if rhs is not None else None,
                   "parse_status": "SUPPORTED" if rhs is not None else "UNRESOLVED", "symbol_units": {}, **details}
        return self.add("equations", payload, source, kind="equation")

    def quantity(self, source, name, value, unit=None, **details):
        _number(value)
        canonical, status = _unit(unit)
        return self.add("quantities", {"name": name, "value": str(value), "unit": canonical, "unit_literal": unit,
                                      "unit_status": status, "value_semantics": "REPORTED", **details}, source, kind="quantity")


def _python(builder, artifact, text, *, source_override=None):
    try:
        tree = ast.parse(text, mode="exec")
        _tree_bound(tree)
    except (SyntaxError, Unsupported, RecursionError, MemoryError):
        builder.unresolved(source_override or _source(artifact, text, 0, min(len(text), 8192)), "Python syntax is invalid or exceeds the static parser bounds")
        return
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def source(node):
        return source_override or _source(artifact, text, offsets[node.lineno - 1], offsets[node.end_lineno], python_node=type(node).__name__)

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else ["." * node.level + (node.module or "")]
            for module in modules:
                builder.add("dependencies", {"kind": "python_import", "module": module, "resolution": "NOT_EXECUTED"}, source(node))
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        arguments = [arg.arg for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)]
        try:
            lhs = {"op": "function", "name": _symbol(node.name)["name"], "args": [_symbol(arg) for arg in arguments]}
        except Unsupported:
            continue
        stack = [(child, False) for child in reversed(node.body)]
        while stack:
            child, conditional = stack.pop()
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            if isinstance(child, ast.Return) and child.value is not None:
                expression = ast.get_source_segment(text, child.value) or ""
                if len(expression) > MAX_EXPR:
                    builder.unresolved(source(child), "Static return expression exceeds bound")
                    continue
                try:
                    rhs = _ast_ir(child.value, text)
                except Unsupported:
                    # Non-mathematical library/API returns are not scientific claims.
                    continue
                if rhs["op"] not in {"number", "symbol"}:
                    builder.equation(source(child), lhs, rhs, origin="python_static_return", function=node.name,
                                     arguments=arguments, conditional=conditional, execution="NEVER",
                                     semantics="Source return expression; control flow and implementation equivalence are not proved")
                continue
            stack.extend((item, conditional or isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.Match))) for item in reversed(list(ast.iter_child_nodes(child))))


def _xml_spans(text, root=None):
    """Match ElementTree preorder to exact lexical element spans, without expansion."""
    spans, stack = [], []
    cursor = 0
    while True:
        start = text.find("<", cursor)
        if start < 0:
            break
        if text.startswith("<!--", start):
            end = text.find("-->", start + 4)
            if end < 0:
                raise Unsupported("unterminated XML comment")
            cursor = end + 3
            continue
        if text.startswith("<![CDATA[", start):
            end = text.find("]]>", start + 9)
            if end < 0:
                raise Unsupported("unterminated CDATA")
            cursor = end + 3
            continue
        if text.startswith("<?", start):
            end = text.find("?>", start + 2)
            if end < 0:
                raise Unsupported("unterminated XML instruction")
            cursor = end + 2
            continue
        index, quote = start + 1, None
        while index < len(text):
            char = text[index]
            if quote:
                if char == quote:
                    quote = None
            elif char in "\"'":
                quote = char
            elif char == ">":
                break
            index += 1
        if index >= len(text):
            raise Unsupported("unterminated XML tag")
        end = index + 1
        token = text[start:end]
        if token.startswith("</"):
            if not stack:
                raise Unsupported("XML span mismatch")
            spans[stack.pop()][1] = end
        else:
            spans.append([start, end])
            if not token.rstrip().endswith("/>"):
                stack.append(len(spans) - 1)
            if len(spans) > MAX_NODES or len(stack) > MAX_DEPTH:
                raise Unsupported("XML resource bound")
        cursor = end
    if stack:
        raise Unsupported("XML lexical binding mismatch")
    if root is None:
        return spans
    elements = list(root.iter())
    if len(elements) != len(spans):
        raise Unsupported("XML lexical binding mismatch")
    return {id(element): tuple(span) for element, span in zip(elements, spans)}


def _local(element):
    return element.tag.rsplit("}", 1)[-1]


def _children(element, name):
    return [child for child in element if _local(child) == name]


def _mathml(element, depth=0):
    if depth > MAX_DEPTH:
        raise Unsupported("MathML depth bound")
    tag = _local(element)
    if tag == "math":
        if len(element) != 1:
            raise Unsupported("MathML must have exactly one expression")
        return _mathml(element[0], depth + 1)
    if tag == "ci":
        return _symbol((element.text or "").strip())
    if tag == "cn":
        if len(element):
            if len(element) == 1 and _local(element[0]) == "sep" and element.attrib.get("type") == "e-notation":
                return _number((element.text or "").strip() + "e" + (element[0].tail or "").strip())
            raise Unsupported("unsupported structured MathML number")
        return _number((element.text or "").strip())
    if tag == "csymbol" and element.attrib.get("definitionURL", "").endswith("/time"):
        return _symbol("time")
    if tag != "apply" or len(element) < 2:
        raise Unsupported("unsupported MathML construct: " + tag)
    operation = _local(element[0])
    args = [_mathml(child, depth + 1) for child in element[1:]]
    op = {"plus": "add", "times": "mul", "minus": "sub", "divide": "div", "power": "pow"}.get(operation)
    if op:
        if len(args) == 1 and op == "sub":
            return {"op": "neg", "arg": args[0]}
        if len(args) < 2 or op in {"div", "pow"} and len(args) != 2:
            raise Unsupported("invalid MathML operator arity")
        if op == "sub" and len(args) != 2:
            raise Unsupported("unsupported MathML subtraction arity")
        return {"op": op, "args": args}
    if operation in _CALLS and len(args) == 1:
        return {"op": "call", "function": "log" if operation == "ln" else operation, "args": args}
    raise Unsupported("unsupported MathML operator: " + operation)


def _mathml_parts(element):
    inner = element[0] if _local(element) == "math" and len(element) == 1 else element
    if _local(inner) == "apply" and len(inner) == 3 and _local(inner[0]) == "eq":
        return _mathml(inner[1]), _mathml(inner[2]), "eq"
    return None, _mathml(element), "expression"


def _xml(builder, artifact, text):
    source = _source(artifact, text, 0, min(len(text), 8192))
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
        builder.unresolved(source, "XML document types and entity declarations are forbidden")
        return
    try:
        # Count lexical nodes/depth before constructing an ElementTree, so even
        # well-formed but enormous trees are rejected before allocation.
        lexical_spans = _xml_spans(text)
        root = ET.fromstring(text)
        elements = list(root.iter())
        if len(elements) != len(lexical_spans):
            raise Unsupported("XML lexical binding mismatch")
        spans = {id(element): tuple(span) for element, span in zip(elements, lexical_spans)}
    except (ET.ParseError, Unsupported, RecursionError, MemoryError) as exc:
        builder.unresolved(source, "XML parse rejected: " + str(exc)[:160])
        return

    def src(element):
        start, end = spans[id(element)]
        return _source(artifact, text, start, end, xml_element=_local(element), **({"xml_id": element.attrib["id"]} if "id" in element.attrib else {}))

    if _local(root) != "sbml":
        for element in root.iter():
            if _local(element) == "math":
                try:
                    lhs, ir, relation = _mathml_parts(element)
                    builder.add("equations", {"lhs": lhs, "rhs": ir, "expression": render_expression(ir), "origin": "mathml_expression", "parse_status": "SUPPORTED", "symbol_units": {}, "relation": relation}, src(element), kind="equation")
                except Unsupported as exc:
                    builder.unresolved(src(element), str(exc))
        return
    models = _children(root, "model")
    if len(models) != 1:
        builder.unresolved(src(root), "SBML must have one model")
        return
    model = models[0]
    units, symbol_units, species = {}, {}, {}
    builder.add("assumptions", {"kind": "model_metadata", "model_id": model.attrib.get("id"), "name": model.attrib.get("name"),
                                "sbml_level": root.attrib.get("level"), "sbml_version": root.attrib.get("version"),
                                "statement": "SBML encodes model assumptions and mathematical definitions; biological validity requires review"}, src(model), kind="model_assumption")
    for element in model.iter():
        if _local(element) != "unitDefinition":
            continue
        terms = []
        for unit in element.iter():
            if _local(unit) == "unit":
                terms.append({key: unit.attrib.get(key, default) for key, default in (("kind", ""), ("exponent", "1"), ("scale", "0"), ("multiplier", "1"))})
        name = element.attrib.get("id")
        if name:
            rendered = []
            for term in terms:
                base = _BASE_UNITS.get(term["kind"], term["kind"])
                prefix = "" if term["scale"] == "0" and term["multiplier"] == "1" else "(" + term["multiplier"] + "*10**" + term["scale"] + ")*"
                scaled = prefix + base
                rendered.append(("(" + scaled + ")" if prefix else base) + ("**" + term["exponent"] if term["exponent"] != "1" else ""))
            units[name] = "*".join(rendered) or None
            builder.add("assumptions", {"kind": "unit_definition", "name": name, "terms": terms, "unit_expression": units[name]}, src(element), kind="model_assumption")

    def declared_unit(name):
        return units.get(name, _BASE_UNITS.get(name, name)) if name else None

    time_unit = declared_unit(model.attrib.get("timeUnits"))
    if time_unit:
        symbol_units["time"] = time_unit
    # Only explicit declarations enter symbol_units. SBML default units are not
    # invented when the source omits the declaration.
    global_identifiers = [element.attrib["id"] for collection in model if _local(collection) in {"listOfCompartments", "listOfSpecies", "listOfParameters"} for element in collection if "id" in element.attrib]
    if len(set(global_identifiers)) != len(global_identifiers):
        builder.unresolved(src(model), "Duplicate global SBML identifiers create ambiguous symbol scope")
        return
    for collection in model:
        if _local(collection) not in {"listOfCompartments", "listOfSpecies", "listOfParameters"}:
            continue
        for element in collection:
            tag, identifier = _local(element), element.attrib.get("id")
            if not identifier:
                continue
            try:
                _symbol(identifier)
            except Unsupported as exc:
                builder.unresolved(src(element), str(exc))
                continue
            raw_unit = element.attrib.get("units") if tag != "species" else element.attrib.get("substanceUnits", model.attrib.get("substanceUnits"))
            unit = declared_unit(raw_unit)
            if tag == "species":
                species[identifier] = element
                # Species identifiers denote concentration unless explicitly
                # amount-only; a volume unit must also be explicitly available.
                if element.attrib.get("hasOnlySubstanceUnits") != "true":
                    compartments = [e for c in _children(model, "listOfCompartments") for e in c if e.attrib.get("id") == element.attrib.get("compartment")]
                    volume = declared_unit(compartments[0].attrib.get("units")) if len(compartments) == 1 else None
                    unit = "(" + unit + ")/(" + volume + ")" if unit and volume else None
            if unit:
                symbol_units[identifier] = unit
            for attribute in ("value", "size", "initialAmount", "initialConcentration"):
                if attribute in element.attrib:
                    value_unit = declared_unit(raw_unit) if attribute == "initialAmount" else unit
                    try:
                        builder.quantity(src(element), identifier, element.attrib[attribute], value_unit,
                                         role="sbml_" + attribute, symbol=identifier, declared_unit=raw_unit,
                                         model_id=model.attrib.get("id"), units_declared=bool(raw_unit))
                    except Unsupported as exc:
                        builder.unresolved(src(element), str(exc))
            flags = {key: element.attrib[key] for key in ("constant", "boundaryCondition", "hasOnlySubstanceUnits", "compartment") if key in element.attrib}
            if flags:
                builder.add("assumptions", {"kind": "sbml_declaration", "symbol": identifier, "declarations": flags}, src(element), kind="model_assumption")
    for collection in model:
        if _local(collection) == "listOfInitialAssignments":
            for assignment in collection:
                maths = _children(assignment, "math")
                try:
                    if len(maths) != 1:
                        raise Unsupported("Initial assignment has no unique MathML expression")
                    lhs = _symbol(assignment.attrib.get("symbol"))
                    builder.equation(src(assignment), lhs, _mathml(maths[0]), origin="sbml_initial_assignment", symbol_units=symbol_units,
                                     model_id=model.attrib.get("id"), applicability="initial_time")
                except Unsupported as exc:
                    builder.unresolved(src(assignment), str(exc))
        if _local(collection) == "listOfRules":
            for rule in collection:
                tag, variable = _local(rule), rule.attrib.get("variable")
                maths = _children(rule, "math")
                if tag not in {"assignmentRule", "rateRule", "algebraicRule"} or len(maths) != 1:
                    builder.unresolved(src(rule), "Unsupported or missing SBML rule mathematics")
                    continue
                try:
                    lhs = _symbol(variable) if tag == "assignmentRule" else ({"op": "derivative", "state": _symbol(variable)["name"], "variable": "time"} if tag == "rateRule" else _number("0"))
                    builder.equation(src(rule), lhs, _mathml(maths[0]), origin="sbml_" + tag, symbol_units=symbol_units,
                                     model_id=model.attrib.get("id"), time_unit=time_unit)
                except Unsupported as exc:
                    builder.unresolved(src(rule), str(exc))
        if _local(collection) != "listOfReactions":
            continue
        for reaction in collection:
            reaction_id = reaction.attrib.get("id", "unnamed")
            laws = _children(reaction, "kineticLaw")
            row_values = []
            for side, sign in (("listOfReactants", "-1"), ("listOfProducts", "1")):
                for group in _children(reaction, side):
                    for reference in group:
                        if _local(reference) != "speciesReference":
                            continue
                        stoich = reference.attrib.get("stoichiometry", "1")
                        try:
                            _number(stoich)
                        except Unsupported:
                            builder.unresolved(src(reference), "Nonconstant or unsupported stoichiometry")
                            continue
                        row_values.append({"species": reference.attrib.get("species"), "coefficient": stoich, "sign": sign,
                                           "coefficient_origin": "explicit" if "stoichiometry" in reference.attrib else "SBML_default_one", "source": src(reference)})
            if row_values:
                builder.add("tables", {"kind": "sbml_stoichiometry", "reaction": reaction_id, "rows": row_values,
                                       "columns": ["species", "coefficient", "sign"], "row_count": len(row_values)}, src(reaction), kind="numerical_result")
            if len(laws) != 1:
                builder.unresolved(src(reaction), "Reaction has no unique kinetic law")
                continue
            law = laws[0]
            local_units = dict(symbol_units)
            for parameters in law:
                if _local(parameters) not in {"listOfParameters", "listOfLocalParameters"}:
                    continue
                for parameter in parameters:
                    identifier = parameter.attrib.get("id")
                    unit = declared_unit(parameter.attrib.get("units"))
                    if identifier and unit:
                        local_units[identifier] = unit
                    if identifier and "value" in parameter.attrib:
                        try:
                            builder.quantity(src(parameter), identifier, parameter.attrib["value"], unit, role="sbml_local_parameter", scope=reaction_id)
                        except Unsupported as exc:
                            builder.unresolved(src(parameter), str(exc))
            maths = _children(law, "math")
            try:
                if len(maths) != 1:
                    raise Unsupported("Kinetic law has no unique MathML expression")
                lhs = {"op": "reaction_rate", "reaction": reaction_id}
                builder.equation(src(law), lhs, _mathml(maths[0]), origin="sbml_kinetic_law", symbol_units=local_units,
                                 scope=reaction_id, model_id=model.attrib.get("id"), time_unit=time_unit,
                                 stoichiometry=row_values)
            except Unsupported as exc:
                builder.unresolved(src(law), str(exc))


def _latex_arithmetic(value):
    value = value.strip().rstrip(".;")
    value = value.replace("−", "-").replace("×", "*").replace("·", "*")
    for command in (r"\left", r"\right", r"\,", r"\!", r"\;", r"\quad"):
        value = value.replace(command, "")
    value = value.replace(r"\cdot", "*").replace(r"\times", "*")
    value = re.sub(r"\\(?:mathbf|mathrm|mathit|operatorname)\{([A-Za-z][A-Za-z0-9]*)\}", r"\1", value)
    # Repeated innermost fractions, with a strict finite rewrite budget.
    for _ in range(16):
        changed = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", value)
        if changed == value:
            break
        value = changed
    value = re.sub(r"([A-Za-z][A-Za-z0-9]*)_\{([^{}]+)\}", r"\1[\2]", value)
    value = re.sub(r"([A-Za-z][A-Za-z0-9]*)_([A-Za-z0-9])\b", r"\1[\2]", value)
    for name in ("sin", "cos", "tan", "exp", "log", "ln", "sqrt"):
        value = value.replace("\\" + name, name)
    value = value.replace("^", "**").replace("{", "(").replace("}", ")")
    value = re.sub(r"(?<=\d)\s*(?=[A-Za-z(])", "*", value)
    value = re.sub(r"(?<=[)\]])\s*(?=[A-Za-z0-9(])", "*", value)
    if "\\" in value or "=" in value:
        raise Unsupported("unsupported LaTeX construct")
    return value


def _equation_text(builder, source, expression):
    original = expression.strip()
    if not original or len(original) > MAX_EXPR or "=" not in original:
        return
    # Comparison chains, approximate equality and unconstrained quantifiers do
    # not lower into exact equations.
    if re.search(r"≈|\\approx|<=|>=|==|!=|\\(?:leq|geq|sim)\b", original):
        builder.unresolved(source, "Approximate or comparative statement is not an exact equation")
        return
    left, right = original.split("=", 1)
    try:
        derivative = re.fullmatch(r"\s*d([A-Za-z][A-Za-z0-9_]*)/d([A-Za-z][A-Za-z0-9_]*)\s*", left)
        latex_derivative = re.fullmatch(r"\s*\\frac\{d\s*([A-Za-z][A-Za-z0-9_]*)\}\{d\s*([A-Za-z][A-Za-z0-9_]*)\}\s*", left)
        derivative = derivative or latex_derivative
        if derivative:
            lhs = {"op": "derivative", "state": derivative[1], "variable": derivative[2]}
        else:
            normal_left = _latex_arithmetic(left)
            function = re.fullmatch(r"([A-Za-z][A-Za-z0-9_]*)\(([^()]*)\)", normal_left)
            if function:
                args = [arg.strip() for arg in function[2].split(",") if arg.strip()]
                lhs = {"op": "function", "name": function[1], "args": [_symbol(arg) for arg in args]}
            else:
                lhs = parse_expression(normal_left)
        if r"\sum" in right:
            raise Unsupported("Summation notation requires explicit, reviewed summand scope; source is retained")
        rhs = parse_expression(_latex_arithmetic(right))
        builder.equation(source, lhs, rhs, origin="document_equation", source_expression=original)
    except Unsupported as exc:
        builder.equation(source, None, None, origin="document_equation", source_expression=original, unresolved_reason=str(exc))
        builder.unresolved(source, str(exc))


def _tables(builder, artifact, text, *, delimiter=None):
    if delimiter:
        try:
            reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
            rows = []
            previous = 0
            for values in reader:
                rows.append((values, previous, reader.line_num))
                previous = reader.line_num
                if len(rows) > 10001 or len(values) > 256:
                    raise Unsupported("table resource bound")
        except (csv.Error, Unsupported) as exc:
            builder.unresolved(_source(artifact, text, 0, min(len(text), 8192)), "Table parse rejected: " + str(exc))
            return
        if not rows:
            return
        headers = rows[0][0]
        if not headers or any(not value.strip() for value in headers) or len(set(headers)) != len(headers) or any(len(row[0]) != len(headers) for row in rows):
            builder.unresolved(_source(artifact, text, 0, min(len(text), 8192)), "Table has ambiguous headers or inconsistent columns")
            return
        line_offsets = [0]
        for line in text.splitlines(keepends=True):
            line_offsets.append(line_offsets[-1] + len(line))
        records = [(values, _source(artifact, text, line_offsets[start], line_offsets[end], row=index + 1)) for index, (values, start, end) in enumerate(rows[1:], 1)]
        _emit_table(builder, _source(artifact, text), headers, records, "delimited_observation")
        return
    # Markdown tables are observations, not inferred experimental evidence.
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    index = 0
    while index + 1 < len(lines):
        header = lines[index].strip().strip("|")
        separator = lines[index + 1].strip().strip("|")
        if "|" not in header or not re.fullmatch(r"[\s:|\-]+", separator) or "-" not in separator:
            index += 1
            continue
        headers = [value.strip() for value in header.split("|")]
        start, index, records = index, index + 2, []
        while index < len(lines) and "|" in lines[index] and lines[index].strip():
            values = [value.strip() for value in lines[index].strip().strip("|").split("|")]
            if len(values) != len(headers):
                break
            records.append((values, _source(artifact, text, offsets[index], offsets[index + 1], row=len(records) + 2)))
            index += 1
        if headers and len(set(headers)) == len(headers) and all(headers):
            _emit_table(builder, _source(artifact, text, offsets[start], offsets[index]), headers, records, "markdown_observation")


def _emit_table(builder, source, headers, records, kind):
    columns = []
    for header in headers:
        match = re.fullmatch(r"(.+?)\s*[\[(]([^\]()]+)[\])]", header)
        name, unit = (match[1].strip(), match[2].strip()) if match else (header, None)
        canonical, status = _unit(unit)
        columns.append({"name": name, "header": header, "unit": canonical, "unit_status": status})
    rows = []
    for row_number, (values, row_source) in enumerate(records, 1):
        rows.append({"row": row_number, "values": dict(zip(headers, values)), "source": row_source})
        for column, value in zip(columns, values):
            if len(value) <= 128 and _NUM.fullmatch(value):
                try:
                    builder.quantity(row_source, column["name"], value, column["unit"], role="table_cell", column=column["header"], row=row_number)
                except Unsupported as exc:
                    builder.unresolved(row_source, str(exc))
    builder.add("tables", {"kind": kind, "columns": columns, "rows": rows[:10000], "row_count": len(rows),
                           "semantics": "Source observations; no population, causal, or uncertainty model inferred"}, source, kind="numerical_result")


def _document_solver_context(artifact, text, lines, offsets, index, imports):
    """Recover a unique local solver spelling and literal method, never run it."""
    prompt = re.match(r"\s*>>> ?(.*)", lines[index].rstrip("\n"))
    if not prompt:
        return None
    code, end = [prompt[1]], index + 1
    while end < len(lines):
        continuation = re.match(r"\s*\.\.\. ?(.*)", lines[end].rstrip("\n"))
        if not continuation:
            break
        code.append(continuation[1])
        end += 1
    source_code = "\n".join(code)
    if len(source_code) > MAX_EXPR:
        return None
    try:
        tree = ast.parse(source_code)
        _tree_bound(tree)
    except (SyntaxError, Unsupported, RecursionError):
        return None
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom) and statement.level == 0:
            for alias in statement.names:
                local = alias.asname or alias.name
                imports.pop(local, None)
                if statement.module in {"scipy.optimize", "scipy.integrate"}:
                    imports[local] = statement.module + "." + alias.name
        elif isinstance(statement, ast.Import):
            for alias in statement.names:
                imports[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]
        elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            imports.pop(statement.name, None)
        elif isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    imports.pop(target.id, None)

    def qualified(node):
        if isinstance(node, ast.Name):
            return imports.get(node.id)
        if isinstance(node, ast.Attribute):
            parent = qualified(node.value)
            return parent + "." + node.attr if parent else None
        return None

    roots = [statement.value for statement in tree.body if isinstance(statement, (ast.Assign, ast.Expr)) and isinstance(statement.value, ast.Call)]
    calls = [(node, qualified(node.func)) for root in roots for node in ast.walk(root) if isinstance(node, ast.Call)]
    calls = [(node, solver) for node, solver in calls if solver in {"scipy.optimize.minimize", "scipy.integrate.solve_ivp", "scipy.integrate.odeint"}]
    if len(calls) != 1:
        return None
    call, solver = calls[0]
    method_nodes = [keyword.value for keyword in call.keywords if keyword.arg == "method"]
    method = method_nodes[0].value if len(method_nodes) == 1 and isinstance(method_nodes[0], ast.Constant) and isinstance(method_nodes[0].value, str) else None
    return {"solver": solver, "method": method, "method_status": "EXPLICIT_LITERAL" if method is not None else "UNSPECIFIED_OR_NONLITERAL",
            "objective_or_rhs": call.args[0].id if call.args and isinstance(call.args[0], ast.Name) else None,
            "argument_expressions": [ast.unparse(argument) for argument in call.args],
            "keyword_expressions": [{"name": keyword.arg, "expression": ast.unparse(keyword.value)} for keyword in call.keywords],
            "source": _source(artifact, text, offsets[index], offsets[end], fragment="solver_call"),
            "semantics": "Source call context only; imported callable identity, execution and scientific meaning are unverified"}


def _reported_finding(reported, line, solver_context):
    raw_name = reported["name"]
    label = re.sub(r"\s+", " ", raw_name.strip()).lower()
    count_names = {"iterations": "iterations", "function evaluations": "function_evaluations", "gradient evaluations": "gradient_evaluations"}
    is_count = label in count_names
    if is_count:
        name, quantity_type = count_names[label], "count"
    elif "function value" in label:
        name, quantity_type = "reported_objective", "objective_value"
    elif label.startswith("minimum value"):
        objective = bool(re.search(r"\b(function|objective)\b", label)) or bool(solver_context and solver_context["solver"] == "scipy.optimize.minimize")
        name, quantity_type = ("minimum_objective", "objective_value") if objective else ("reported_minimum", "reported_statistic")
    else:
        name, quantity_type = label.replace(" ", "_"), "reported_statistic"
    tail = line[reported.end():]
    unit = "count" if is_count else None
    # A function value has no inferred physical dimension. Only a unit actually
    # printed beside the reported value can supply one.
    explicit_unit = re.match(r"\s*([A-Za-zμµ%][A-Za-z0-9μµ%]*(?:(?:\^|\*\*)[-+]?\d+)?)\b", tail)
    if not is_count and explicit_unit and _unit(explicit_unit[1])[1] == "RECOGNIZED":
        unit = explicit_unit[1]
    uncertainty = None
    plus_minus = re.match(r"\s*±\s*(" + NUMBER + r")", tail)
    if plus_minus:
        uncertainty = {"kind": "plus_minus", "value": plus_minus[1], "unit": unit}
    interval = re.search(r"(?:(?P<level>" + NUMBER + r")\s*%\s*)?(?:confidence interval|CI)\s*[:=]?\s*\[\s*(?P<lower>" + NUMBER + r")\s*,\s*(?P<upper>" + NUMBER + r")\s*\]", tail, re.I)
    if interval:
        uncertainty = {"kind": "reported_confidence_interval", "lower": interval["lower"], "upper": interval["upper"],
                       "confidence_level_percent": interval["level"], "unit": unit, "coverage_model": "UNSPECIFIED"}
    variability = re.search(r"\bmay\s+(?:vary|differ)\b", line, re.I)
    conditions = ["Author-reported source value; source conditions and scientific meaning require review."]
    if solver_context:
        conditions.append("This finding is local to the adjacent source solver call and its supplied argument/option expressions.")
    if variability:
        conditions.append(variability[0])
    return name, unit, {"raw_name": raw_name, "quantity_type": quantity_type, "role": "document_numerical_result",
                       "approximate": bool(reported["approx"]), "uncertainty": uncertainty,
                       "relation": "approximate" if reported["approx"] else ("uncertainty_interval" if uncertainty else "reported_value"),
                       "version_sensitive": is_count, "reported_variability": {"may_vary": bool(variability), "literal": variability[0] if variability else None},
                       "solver_context": deepcopy(solver_context), "conditions": conditions}


def _document(builder, artifact, text):
    _tables(builder, artifact, text)
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    index = 0
    solver_context, imports = None, {}
    while index < len(lines):
        line = lines[index]
        source = _source(artifact, text, offsets[index], offsets[index + 1])
        if re.match(r"\s*>>>", line):
            solver_context = _document_solver_context(artifact, text, lines, offsets, index, imports)
        elif line.strip() and not line.startswith((" ", "\t")):
            # Do not carry a prior algorithm into unrelated prose or examples.
            solver_context = None
        if re.match(r"\s*\.\.\s+math::", line):
            start, block = index, []
            index += 1
            while index < len(lines) and (not lines[index].strip() or lines[index].startswith((" ", "\t"))):
                if lines[index].strip():
                    block.append(lines[index].strip())
                index += 1
            _equation_text(builder, _source(artifact, text, offsets[start], offsets[index]), " ".join(block))
            continue
        prompt = re.match(r"\s*>>> (def\s+.*)", line)
        if prompt:
            start, code = index, [prompt[1]]
            index += 1
            while index < len(lines):
                continuation = re.match(r"\s*\.\.\. ?(.*)", lines[index].rstrip("\n"))
                if not continuation:
                    break
                code.append(continuation[1])
                index += 1
            _python(builder, artifact, "\n".join(code) + "\n", source_override=_source(artifact, text, offsets[start], offsets[index], fragment="doctest_function"))
            continue
        if re.search(r"\b(caus(?:e|es|ed|ing)|proves?|statistically significant)\b", line, re.I):
            builder.unresolved(source, "Causal or significance language is unsupported without an explicit identification or statistical model")
        # Explicit numerical findings and measurements retain approximation and
        # uncertainty, rather than silently asserting exact equality.
        measurement = re.compile(r"(?P<approx>approximately\s+|about\s+|~\s*|≈\s*)?(?P<value>" + NUMBER + r")\s*(?:±\s*(?P<uncertainty>" + NUMBER + r")\s*)?(?P<unit>[%A-Za-zμµ][A-Za-z0-9μµ%]*(?:(?:\^|\*\*)[-+]?\d+)?(?:\s*/\s*[A-Za-z]+(?:(?:\^|\*\*)[-+]?\d+)?)?)(?![\w])")
        for match in measurement.finditer(line):
            unit, unit_status = _unit(match["unit"])
            if unit_status != "RECOGNIZED" and not re.search(r"\b(measured|reported|concentration|rate|mass|length|temperature|value)\b", line, re.I):
                continue
            # Words following unlabelled counts are not invented units.
            if match["unit"].lower() in {"which", "when", "at", "and", "or", "is", "of", "the", "to", "with", "variables", "iterations"}:
                continue
            name = line[:match.start()].strip(" :*=\t")[-160:] or "reported measurement"
            uncertainty = {"kind": "plus_minus", "value": match["uncertainty"], "unit": unit} if match["uncertainty"] else None
            interval = re.search(r"(?:(?P<level>" + NUMBER + r")\s*%\s*)?(?:confidence interval|CI)\s*[:=]?\s*\[\s*(?P<lower>" + NUMBER + r")\s*,\s*(?P<upper>" + NUMBER + r")\s*\]", line[match.end():], re.I)
            if interval:
                uncertainty = {"kind": "reported_confidence_interval", "lower": interval["lower"], "upper": interval["upper"],
                               "confidence_level_percent": interval["level"], "unit": unit, "coverage_model": "UNSPECIFIED"}
            try:
                builder.quantity(source, name, match["value"], match["unit"], approximate=bool(match["approx"]), uncertainty=uncertainty,
                                 relation="approximate" if match["approx"] else ("uncertainty_interval" if uncertainty else "reported_value"), role="document_measurement")
            except Unsupported as exc:
                builder.unresolved(source, str(exc))
        reported = re.search(r"(?P<name>(?:Current\s+)?function value|Iterations|Function evaluations|Gradient evaluations|minimum value(?: of [^\n]{0,80}?)?|mean|standard deviation|accuracy|loss)\s*(?::|=|\bis\b)\s*(?P<approx>approximately\s+|about\s+|~\s*|≈\s*)?(?P<value>" + NUMBER + r")", line, re.I)
        if reported:
            name, unit, finding = _reported_finding(reported, line, solver_context)
            builder.quantity(source, name, reported["value"], unit, **finding)
            builder.add("claims", {"kind": "numerical_result", "statement": line.strip(), "name": name, "value": reported["value"],
                                   "unit": _unit(unit)[0], "reported_status": "UNVERIFIED", **finding}, source)
        # Only explicitly delimited equations or a standalone ODE are accepted.
        for match in re.finditer(r":math:`([^`]+)`|\$([^$\n]+)\$|\\\((.*?)\\\)|\\\[(.*?)\\\]", line):
            expression = next(group for group in match.groups() if group is not None)
            _equation_text(builder, source, expression)
        plain = re.fullmatch(r"\s*(?:\$\$)?\s*(d[A-Za-z][A-Za-z0-9_]*/d[A-Za-z][A-Za-z0-9_]*\s*=.+?)(?:\$\$)?\s*", line)
        if plain:
            _equation_text(builder, source, plain[1])
        index += 1
    # Multi-line display math in Markdown/LaTeX.
    for match in re.finditer(r"\$\$(.{0,8192}?)\$\$|\\\[(.{0,8192}?)\\\]|\\begin\{(?:equation\*?|align\*?)\}(.{0,8192}?)\\end\{(?:equation\*?|align\*?)\}", text, re.S):
        expression = next(group for group in match.groups() if group is not None)
        if len(expression) <= MAX_EXPR:
            _equation_text(builder, _source(artifact, text, match.start(), match.end()), expression.replace("\n", " "))
    for match in re.finditer(r"<math\b[^>]{0,1024}>.{0,8192}?</math\s*>", text, re.S | re.I):
        fragment = match[0]
        source = _source(artifact, text, match.start(), match.end(), fragment="html_mathml")
        try:
            _xml_spans(fragment)
            math_element = ET.fromstring(fragment)
            lhs, rhs, relation = _mathml_parts(math_element)
            builder.add("equations", {"lhs": lhs, "rhs": rhs, "expression": render_expression(rhs), "relation": relation,
                                      "origin": "html_mathml", "parse_status": "SUPPORTED", "symbol_units": {}}, source, kind="equation")
        except (ET.ParseError, Unsupported, RecursionError) as exc:
            builder.unresolved(source, "HTML MathML rejected: " + str(exc)[:160])


def interpret(inventory):
    """Interpret exact PR201 inventory bytes into nonauthoritative candidates.

    Adapter observations alone cannot establish source content: raw sources are
    hash/size checked using PR201's bound_bytes before any extraction.  Errors
    remain explicit and do not cause unsupported data to acquire authority.
    """
    builder = _Builder()
    artifacts = inventory.get("artifacts", []) if isinstance(inventory, dict) else inventory
    if isinstance(artifacts, dict):
        artifacts = list(artifacts.values())
    if not isinstance(artifacts, list) or len(artifacts) > 256:
        raise ValueError("inventory artifact bound")
    for artifact in sorted(artifacts, key=lambda value: (value.get("path", ""), value.get("id", ""))):
        try:
            raw = bound_bytes(artifact)
            text = raw.decode("utf-8-sig", errors="strict")
            if len(text) > MAX_TEXT or "\x00" in text:
                raise Unsupported("text size or NUL bound")
        except (OSError, KeyError, ValueError, UnicodeError) as exc:
            source = {"artifact_id": artifact.get("id"), "sha256": artifact.get("sha256"), "path": artifact.get("path"), "locator": {}, "quote": ""}
            builder.unresolved(source, "Source unavailable, changed, or outside textual bounds: " + type(exc).__name__)
            continue
        suffix = PurePosixPath(artifact["path"]).suffix.lower()
        if suffix == ".py":
            _python(builder, artifact, text)
        elif suffix in {".sbml", ".xml", ".mathml"}:
            _xml(builder, artifact, text)
        elif suffix in {".csv", ".tsv"}:
            _tables(builder, artifact, text, delimiter="\t" if suffix == ".tsv" else ",")
        elif suffix in {".md", ".markdown", ".rst", ".txt", ".tex", ".html", ".htm", ".log"}:
            _document(builder, artifact, text)
        else:
            builder.unresolved(_source(artifact, text, 0, min(len(text), 8192)), "No automatic scientific interpretation for this format")
    return builder.result
