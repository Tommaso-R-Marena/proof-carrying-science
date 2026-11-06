"""Conservative dimensional checks for research expressions; never execution authority.

Dimensions use exact integer SI7 exponents in (length, mass, time, current,
thermodynamic_temperature, amount, luminous_intensity) order. A VERIFIED result
means only dimensional consistency under the *supplied* unit declarations. It
says nothing about empirical validity, numerical domains, or Python/Lean refinement.
Numbers, including zero, are dimensionless. Missing SBML declarations remain unknown.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

DIMENSION_ORDER = ("length", "mass", "time", "current", "temperature", "amount", "luminous_intensity")
ZERO = (0, 0, 0, 0, 0, 0, 0)
LENGTH = (1, 0, 0, 0, 0, 0, 0)
TIME = (0, 0, 1, 0, 0, 0, 0)
AMOUNT = (0, 0, 0, 0, 0, 1, 0)
VOLUME = (3, 0, 0, 0, 0, 0, 0)
CONCENTRATION = (-3, 0, 0, 0, 0, 1, 0)
VOLTAGE = (2, 1, -3, -1, 0, 0, 0)
SCHEMA = "scientific-dimensions/v2"
MAX_NODES = 512
MAX_POWER = 32


def _fraction(value: Any, path: str) -> Fraction:
    text = str(value)
    if len(text) > 256:
        _issue("numeric_limit", path, "Exact rational literal exceeds the research resource bound")
    for exponent in re.findall(r"[eE]([+-]?[0-9]+)", text):
        if len(exponent.lstrip("+-")) > 3 or abs(int(exponent)) > 64:
            _issue("numeric_limit", path, "Decimal exponent exceeds the research resource bound")
    try:
        result = Fraction(text)
    except (ValueError, TypeError, ZeroDivisionError, OverflowError):
        _issue("invalid_number", path, "Only finite exact rational literals are supported")
    if result.numerator.bit_length() > 4096 or result.denominator.bit_length() > 4096:
        _issue("numeric_limit", path, "Exact rational exceeds the research resource bound")
    return result


def _bounded_unit(dimension: tuple[int, ...], factor: Fraction) -> Unit:
    if any(abs(x) > 1024 for x in dimension) or factor.numerator.bit_length() > 4096 or factor.denominator.bit_length() > 4096:
        _issue("unit_resource_limit", "$unit", "Unit expression exceeds bounded exact arithmetic limits")
    return Unit(dimension, factor)


def _rat(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _plus(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(x + y for x, y in zip(a, b))


def _times(a: tuple[int, ...], n: int) -> tuple[int, ...]:
    return tuple(x * n for x in a)


@dataclass(frozen=True)
class Unit:
    dimension: tuple[int, ...]
    factor: Fraction = Fraction(1)


# L is a volume and M is amount/volume; these are not independent SI bases.
UNITS: dict[str, Unit] = {
    "1": Unit(ZERO), "dimensionless": Unit(ZERO), "unitless": Unit(ZERO),
    "m": Unit(LENGTH), "s": Unit(TIME), "second": Unit(TIME),
    "min": Unit(TIME, Fraction(60)), "minute": Unit(TIME, Fraction(60)),
    "mol": Unit(AMOUNT), "mmol": Unit(AMOUNT, Fraction(1, 1000)),
    "L": Unit(VOLUME, Fraction(1, 1000)), "litre": Unit(VOLUME, Fraction(1, 1000)),
    "liter": Unit(VOLUME, Fraction(1, 1000)),
    "M": Unit(CONCENTRATION, Fraction(1000)), "mM": Unit(CONCENTRATION),
    "V": Unit(VOLTAGE), "mV": Unit(VOLTAGE, Fraction(1, 1000)),
    "kg": Unit((0, 1, 0, 0, 0, 0, 0)), "A": Unit((0, 0, 0, 1, 0, 0, 0)),
    "K": Unit((0, 0, 0, 0, 1, 0, 0)),
}
AFFINE_UNITS = frozenset(("C", "°C", "degC", "Celsius", "celsius", "degree_Celsius"))


class DimensionIssue(Exception):
    def __init__(self, status: str, code: str, path: str, detail: str):
        self.status, self.code, self.path, self.detail = status, code, path, detail
        super().__init__(detail)


def _issue(code: str, path: str, detail: str, *, refuted: bool = False) -> None:
    raise DimensionIssue("REFUTED" if refuted else "UNKNOWN", code, path, detail)


def _parse_python(expression: str) -> dict[str, Any]:
    if len(expression) > 8192:
        _issue("expression_too_large", "$", "Expression exceeds the bounded research parser limit")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError, RecursionError) as exc:
        _issue("invalid_syntax", "$", str(exc))
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        _issue("expression_too_large", "$", "Expression exceeds the bounded research parser limit")

    def visit(node: ast.AST, path: str) -> dict[str, Any]:
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            literal = ast.get_source_segment(expression, node) or str(node.value)
            value = _fraction(literal.replace("_", ""), path)
            return {"op": "number", "value": str(value)}
        if isinstance(node, ast.Name):
            return {"op": "symbol", "name": node.id}
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = visit(node.operand, path + ".arg")
            return {"op": "neg", "arg": value} if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp):
            names = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "div", ast.Pow: "pow"}
            op = names.get(type(node.op))
            if op:
                return {"op": op, "args": [visit(node.left, path + ".args[0]"), visit(node.right, path + ".args[1]")]}
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            return {"op": "call", "function": node.func.id, "args": [visit(x, f"{path}.args[{i}]") for i, x in enumerate(node.args)]}
        _issue("unsupported_syntax", path, f"Unsupported safe arithmetic node: {type(node).__name__}")

    return visit(tree.body, "$")


def parse_unit(declaration: str | None) -> Unit:
    """Parse multiplicative units only. Unknown/affine units raise UNKNOWN issues."""
    if not isinstance(declaration, str) or not declaration.strip():
        _issue("missing_unit", "$unit", "No explicit unit declaration is available")
    declaration = declaration.strip()
    if declaration in AFFINE_UNITS:
        _issue("affine_unit_unsupported", "$unit", "Celsius requires an affine offset and is not a multiplicative unit")
    if declaration in UNITS:
        return UNITS[declaration]
    ir = _parse_python(declaration.replace("^", "**"))

    def visit(node: dict[str, Any]) -> Unit:
        op = node.get("op")
        if op == "symbol":
            name = node["name"]
            if name in AFFINE_UNITS:
                _issue("affine_unit_unsupported", "$unit", "Affine Celsius units require explicit offset semantics")
            if name not in UNITS:
                _issue("unknown_unit", "$unit", f"Unknown unit {name!r}")
            return UNITS[name]
        if op == "number" and node["value"] == "1":
            return Unit(ZERO)
        if op in ("mul", "div"):
            left, right = (visit(x) for x in node["args"])
            sign = 1 if op == "mul" else -1
            return _bounded_unit(_plus(left.dimension, _times(right.dimension, sign)), left.factor * (right.factor ** sign))
        if op == "pow":
            base = visit(node["args"][0])
            exponent = _integer_literal(node["args"][1], "$unit.exponent")
            return _bounded_unit(_times(base.dimension, exponent), base.factor ** exponent)
        _issue("unsupported_unit_expression", "$unit", "Unit declarations must use known units, multiplication, division, and integer powers")

    return visit(ir)


def _integer_literal(node: Any, path: str) -> int:
    sign = 1
    if isinstance(node, dict) and node.get("op") == "neg":
        sign, node = -1, node.get("arg")
    if not isinstance(node, dict) or node.get("op") != "number":
        _issue("noninteger_power", path, "A dimension exponent must be an explicit bounded integer")
    value = _fraction(node.get("value"), path) * sign
    if value.denominator != 1 or abs(value) > MAX_POWER:
        _issue("noninteger_power", path, f"Only explicit integer powers between {-MAX_POWER} and {MAX_POWER} are supported")
    return value.numerator


@dataclass
class _Typed:
    dimension: tuple[int, ...]
    canonical: dict[str, Any]
    factor: Fraction | None


def _infer(ir: dict[str, Any], symbol_units: Mapping[str, str], conversions: list[dict], path: str = "$", budget: list[int] | None = None) -> _Typed:
    if budget is None:
        budget = [MAX_NODES]
    budget[0] -= 1
    if budget[0] < 0:
        _issue("expression_too_large", path, "Expression exceeds the bounded research checker limit")
    if not isinstance(ir, dict):
        _issue("malformed_ir", path, "Expression nodes must be objects")
    op = ir.get("op")
    if op == "number":
        value = _fraction(ir.get("value"), path)
        return _Typed(ZERO, {"op": "number", "value": str(value)}, Fraction(1))
    if op == "symbol":
        name = ir.get("name")
        if not isinstance(name, str) or name not in symbol_units:
            _issue("unknown_symbol", path, f"No explicit unit declaration for symbol {name!r}")
        try:
            unit = parse_unit(symbol_units[name])
        except DimensionIssue as exc:
            raise DimensionIssue(exc.status, exc.code, path, f"Symbol {name!r}: {exc.detail}") from exc
        factor = _rat(unit.factor)
        conversions.append({"path": path, "symbol": name, "declared_unit": symbol_units[name], "factor_to_SI": factor})
        return _Typed(unit.dimension, {"op": "scale", "factor": factor, "arg": {"op": "symbol", "name": name}}, unit.factor)
    if op == "neg":
        item = _infer(ir.get("arg"), symbol_units, conversions, path + ".arg", budget)
        return _Typed(item.dimension, {"op": "neg", "arg": item.canonical}, item.factor)
    if op in ("add", "sub", "mul", "div", "pow"):
        args = ir.get("args")
        if not isinstance(args, list) or len(args) != 2:
            _issue("malformed_ir", path, f"{op} requires two arguments")
        left = _infer(args[0], symbol_units, conversions, path + ".args[0]", budget)
        if op == "pow":
            exponent = _integer_literal(args[1], path + ".args[1]")
            dimension = _times(left.dimension, exponent)
            factor = left.factor ** exponent if left.factor is not None else None
            _bounded_unit(dimension, factor if factor is not None else Fraction(1))
            return _Typed(dimension, {"op": "pow", "args": [left.canonical, {"op": "number", "value": str(exponent)}]}, factor)
        right = _infer(args[1], symbol_units, conversions, path + ".args[1]", budget)
        if op in ("add", "sub"):
            if left.dimension != right.dimension:
                _issue("dimension_mismatch", path, f"{op} requires equal dimensions: {left.dimension} versus {right.dimension}", refuted=True)
            factor = left.factor if left.factor == right.factor else None
            dimension = left.dimension
        else:
            sign = 1 if op == "mul" else -1
            dimension = _plus(left.dimension, _times(right.dimension, sign))
            factor = left.factor * right.factor ** sign if left.factor is not None and right.factor is not None else None
        _bounded_unit(dimension, factor if factor is not None else Fraction(1))
        return _Typed(dimension, {"op": op, "args": [left.canonical, right.canonical]}, factor)
    if op == "call":
        function, args = ir.get("function"), ir.get("args")
        if not isinstance(args, list):
            _issue("malformed_ir", path, "Call arguments must be a list")
        if function == "sum" and args:
            values = [_infer(x, symbol_units, conversions, f"{path}.args[{i}]", budget) for i, x in enumerate(args)]
            if any(x.dimension != values[0].dimension for x in values[1:]):
                _issue("dimension_mismatch", path, "sum requires equal dimensions", refuted=True)
            factor = values[0].factor if all(x.factor == values[0].factor for x in values) else None
            return _Typed(values[0].dimension, {"op": "call", "function": "sum", "args": [x.canonical for x in values]}, factor)
        if function not in ("exp", "log", "sin", "cos") or len(args) != 1:
            _issue("unsupported_function", path, f"Function {function!r} is outside the declared dimension rules")
        arg = _infer(args[0], symbol_units, conversions, path + ".args[0]", budget)
        if arg.dimension != ZERO:
            _issue("transcendental_requires_dimensionless", path, f"{function} requires a dimensionless argument; found {arg.dimension}", refuted=True)
        return _Typed(ZERO, {"op": "call", "function": function, "args": [arg.canonical]}, Fraction(1))
    if op == "derivative":
        state, variable = ir.get("state"), ir.get("variable")
        left = _infer({"op": "symbol", "name": state}, symbol_units, conversions, path + ".state", budget)
        right = _infer({"op": "symbol", "name": variable}, symbol_units, conversions, path + ".variable", budget)
        return _Typed(_plus(left.dimension, _times(right.dimension, -1)), {"op": "derivative", "state": left.canonical, "variable": right.canonical}, left.factor / right.factor if left.factor is not None and right.factor is not None else None)
    _issue("unsupported_ir", path, f"Unsupported expression operation {op!r}")


def _request(expression: Any, symbol_units: Mapping[str, str], assumptions: Sequence[str], expected_unit: str | None = None, rhs: Any = None) -> dict:
    return {"expression": expression, "rhs": rhs, "symbol_units": dict(symbol_units), "assumptions": list(assumptions), "expected_unit": expected_unit}


def _result(request: dict, operation: str) -> dict:
    # The replay input is deliberately retained, allowing a fresh independent check.
    return {"schema": SCHEMA, "operation": operation, "status": "UNKNOWN", "authority": False,
            "scope": "dimensional consistency under explicit declarations only", "dimension_order": list(DIMENSION_ORDER),
            "assumptions": list(request["assumptions"]), "symbol_unit_declarations": dict(request["symbol_units"]),
            "diagnostics": [], "conversion_factors": [], "replay": {"operation": operation, "input": request},
            "request_sha256": hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "python_lean_refinement": "OPEN"}


def _as_ir(expression: str | dict) -> dict:
    return _parse_python(expression) if isinstance(expression, str) else expression


def _failure(result: dict, exc: DimensionIssue) -> dict:
    result.update(status=exc.status, diagnostics=[{"code": exc.code, "path": exc.path, "detail": exc.detail}])
    return result


def check_expression(expression: str | dict, symbol_units: Mapping[str, str], *, expected_unit: str | None = None, assumptions: Sequence[str] = ()) -> dict:
    """Check safe arithmetic, preserving exact scale conversion evidence and replay."""
    request = _request(expression, symbol_units, assumptions, expected_unit)
    result = _result(request, "expression")
    try:
        typed = _infer(_as_ir(expression), symbol_units, result["conversion_factors"])
        result.update(dimension=list(typed.dimension), canonical_expression=typed.canonical,
                      homogeneous_factor_to_SI=_rat(typed.factor) if typed.factor is not None else None)
        if expected_unit is not None:
            expected = parse_unit(expected_unit)
            result["expected_dimension"] = list(expected.dimension)
            if typed.dimension != expected.dimension:
                _issue("expected_dimension_mismatch", "$", f"Expected {expected.dimension}, found {typed.dimension}", refuted=True)
            result["homogeneous_factor_to_expected"] = _rat(typed.factor / expected.factor) if typed.factor is not None else None
        result["status"] = "VERIFIED"
    except (DimensionIssue, RecursionError) as exc:
        if isinstance(exc, RecursionError):
            exc = DimensionIssue("UNKNOWN", "expression_too_deep", "$", "Expression nesting exceeds the checker limit")
        _failure(result, exc)
    return result


def check_equation(lhs: str | dict, rhs: str | dict, symbol_units: Mapping[str, str], *, assumptions: Sequence[str] = ()) -> dict:
    request = _request(lhs, symbol_units, assumptions, rhs=rhs)
    result = _result(request, "equation")
    try:
        left = _infer(_as_ir(lhs), symbol_units, result["conversion_factors"], "$.lhs")
        right = _infer(_as_ir(rhs), symbol_units, result["conversion_factors"], "$.rhs")
        result.update(lhs_dimension=list(left.dimension), rhs_dimension=list(right.dimension),
                      canonical_lhs=left.canonical, canonical_rhs=right.canonical)
        if left.dimension != right.dimension:
            _issue("equation_dimension_mismatch", "$", f"Left dimension {left.dimension} differs from right {right.dimension}", refuted=True)
        result["rhs_to_lhs_unit_factor"] = _rat(right.factor / left.factor) if left.factor is not None and right.factor is not None else None
        result["status"] = "VERIFIED"
    except (DimensionIssue, RecursionError) as exc:
        if isinstance(exc, RecursionError):
            exc = DimensionIssue("UNKNOWN", "expression_too_deep", "$", "Expression nesting exceeds the checker limit")
        _failure(result, exc)
    return result


def check_derivative(rhs: str | dict, state: str, symbol_units: Mapping[str, str], *, time_symbol: str = "time", time_unit: str | None = None, assumptions: Sequence[str] = ()) -> dict:
    """Check d(state)/d(time). A time declaration must be supplied explicitly."""
    request = _request(rhs, symbol_units, assumptions)
    request.update(state=state, time_symbol=time_symbol, time_unit=time_unit)
    result = _result(request, "derivative")
    declared = dict(symbol_units)
    try:
        if time_unit is not None:
            if time_symbol in declared and declared[time_symbol] != time_unit:
                _issue("conflicting_time_declaration", "$.lhs.variable", "Explicit time_unit conflicts with the symbol unit declaration")
            declared[time_symbol] = time_unit
        if time_symbol in declared:
            try:
                time = parse_unit(declared[time_symbol])
            except DimensionIssue as exc:
                raise DimensionIssue(exc.status, exc.code, "$.lhs.variable", exc.detail) from exc
            if time.dimension != TIME:
                _issue("time_dimension_mismatch", "$.lhs.variable", "The time variable must have the SI time dimension", refuted=True)
        checked = check_equation({"op": "derivative", "state": state, "variable": time_symbol}, rhs, declared, assumptions=assumptions)
        for key, value in checked.items():
            if key not in ("replay", "request_sha256", "operation", "symbol_unit_declarations"):
                result[key] = value
        result["effective_symbol_unit_declarations"] = declared
    except DimensionIssue as exc:
        _failure(result, exc)
    return result


def replay(result: Mapping[str, Any]) -> dict:
    """Re-run retained inputs; verification does not trust the claimed status."""
    item = result["replay"]
    request = item["input"]
    if item["operation"] == "expression":
        return check_expression(request["expression"], request["symbol_units"], expected_unit=request["expected_unit"], assumptions=request["assumptions"])
    if item["operation"] == "equation":
        return check_equation(request["expression"], request["rhs"], request["symbol_units"], assumptions=request["assumptions"])
    if item["operation"] == "derivative":
        return check_derivative(request["expression"], request["state"], request["symbol_units"], time_symbol=request["time_symbol"], time_unit=request["time_unit"], assumptions=request["assumptions"])
    raise ValueError("Unsupported replay operation")
