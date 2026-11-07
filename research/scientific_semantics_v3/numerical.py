"""Independent, nonexecuting reconstruction of the bounded NIST StRD format.

This checks published rounded coefficients/data, not statistical assumptions or
global optimality. The model's additive error term is excluded only when forming
its fitted conditional mean. No source code, eval, or generated program runs.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
import math
import re
import time

NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
SCALAR = re.compile(NUMBER + r"\Z")


def rational(text):
    if not isinstance(text, str) or len(text) > 80 or not SCALAR.fullmatch(text):
        raise ValueError("bounded decimal expected")
    if "e" in text.lower() and abs(int(text.lower().split("e")[1])) > 100:
        raise ValueError("decimal exponent bound")
    return Fraction(text)


@dataclass(frozen=True)
class Interval:
    lo: Fraction
    hi: Fraction

    def __post_init__(self):
        if self.lo > self.hi or max(self.lo.numerator.bit_length(), self.hi.numerator.bit_length(),
                                    self.lo.denominator.bit_length(), self.hi.denominator.bit_length()) > 65536:
            raise ValueError("interval bounds")

    def __add__(self, other):
        return Interval(self.lo + other.lo, self.hi + other.hi)

    def __neg__(self):
        return Interval(-self.hi, -self.lo)

    def __sub__(self, other):
        return self + -other

    def __mul__(self, other):
        vals = [a*b for a in (self.lo, self.hi) for b in (other.lo, other.hi)]
        return Interval(min(vals), max(vals))

    def __truediv__(self, other):
        if other.lo <= 0 <= other.hi:
            raise ValueError("denominator interval contains zero")
        return self * Interval(1/other.hi, 1/other.lo)

    def square(self):
        if self.lo <= 0 <= self.hi:
            return Interval(Fraction(0), max(self.lo*self.lo, self.hi*self.hi))
        return Interval(min(self.lo*self.lo, self.hi*self.hi), max(self.lo*self.lo, self.hi*self.hi))

    def public(self):
        def exact(q):
            if max(q.numerator.bit_length(), q.denominator.bit_length()) <= 8192:
                return str(q)
            return {"numerator_hex": hex(q.numerator), "denominator_hex": hex(q.denominator)}
        return {"lower": exact(self.lo), "upper": exact(self.hi),
                "lower_float": float(self.lo), "upper_float": float(self.hi)}


def rounding_interval(text):
    """An explicit assumption: the last printed decimal was rounded to nearest."""
    value = rational(text)
    mantissa, _, exponent = text.lower().partition("e")
    places = len(mantissa.partition(".")[2])
    quantum = Fraction(10) ** (int(exponent or 0) - places)
    return Interval(value - quantum/2, value + quantum/2)


def parse(raw):
    if len(raw) > 1024*1024:
        raise ValueError("NIST document size bound")
    text = raw.decode("ascii")
    if not text.startswith("NIST/ITL StRD"):
        raise ValueError("not supported StRD document")
    if len(re.findall(r"^Model:", text, re.M)) != 1:
        raise ValueError("ambiguous model declaration")
    model = text.split("Model:", 1)[1].split("Starting values", 1)[0]
    match = re.search(r"\by\s*=\s*(.+)", model, re.S)
    if not match:
        raise ValueError("no supported scalar model")
    formula = re.sub(r"\s+", "", match.group(1))
    if not formula.endswith("+e"):
        raise ValueError("explicit additive error model required")
    formula = formula[:-2]
    tree = ast.parse(formula, mode="eval").body
    if len(list(ast.walk(tree))) > 256:
        raise ValueError("model expression bound")
    params = {}
    std = {}
    for match in re.finditer(r"^\s*(b[1-9][0-9]?)\s*=\s*(.+)$", text, re.M):
        tokens = match[2].split()
        if len(tokens) != 4 or any(not SCALAR.fullmatch(x) for x in tokens) or match[1] in params:
            raise ValueError("ambiguous parameter table")
        params[match[1]] = tokens[2]
        std[match[1]] = tokens[3]
    if not 1 <= len(params) <= 16:
        raise ValueError("parameter count bound")
    if set(params) != {f"b{i}" for i in range(1, len(params)+1)}:
        raise ValueError("parameter identifiers must be consecutive")
    allowed_nodes = (ast.Constant, ast.Name, ast.UnaryOp, ast.BinOp, ast.Call, ast.Load,
                     ast.USub, ast.UAdd, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            raise ValueError("unsupported model syntax")
        if isinstance(node, ast.Name) and node.id not in {*params, "x", "exp", "log"}:
            raise ValueError("undeclared model dependency")
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float):
                raise ValueError("non-numerical model literal")
            node.source_literal = ast.get_source_segment(formula, node)
            rational(node.source_literal)
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in {"exp", "log"}
                                          or len(node.args) != 1 or node.keywords):
            raise ValueError("unsupported model function")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow) and (not isinstance(node.right, ast.Constant)
                or type(node.right.value) is not int or not 0 <= node.right.value <= 8):
            raise ValueError("model power bound")
    stats = {}
    names = {"rss": "Residual Sum of Squares", "residual_std": "Residual Standard Deviation",
             "df": "Degrees of Freedom", "n": "Number of Observations"}
    for key, name in names.items():
        matches = re.findall(r"^"+name+r":\s*("+NUMBER+r")\s*$", text, re.M)
        if len(matches) != 1:
            raise ValueError("missing/duplicate certified statistic")
        stats[key] = matches[0]
    data = re.split(r"^Data:\s+y\s+x\s*$", text, flags=re.M)
    if len(data) != 2:
        raise ValueError("ambiguous observation table")
    rows = []
    for line in data[1].splitlines():
        if not line.strip():
            continue
        tokens = line.split()
        if len(tokens) != 2 or any(not SCALAR.fullmatch(x) for x in tokens):
            raise ValueError("malformed numerical observation")
        rows.append(tuple(tokens))
        if len(rows) > 4096:
            raise ValueError("observation bound")
    return {"formula": formula, "tree": tree, "parameters": params,
            "parameter_std": std, "statistics": stats, "rows": rows,
            "error_term": "additive e; distribution and independence not established"}


def evaluate(node, env, mode, depth=0):
    if depth > 32:
        raise ValueError("model expression depth")
    def constant(value):
        if mode == "interval":
            v = rational(str(value)); return Interval(v, v)
        if mode == "decimal":
            return Decimal(str(value))
        return float(value)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        if type(node.value) is float and mode != "float" and not hasattr(node, "source_literal"):
            raise ValueError("exact decimal literal source span required")
        result = constant(getattr(node, "source_literal", node.value))
    elif isinstance(node, ast.Name) and node.id in env:
        result = env[node.id]
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = evaluate(node.operand, env, mode, depth+1)
        result = -value if isinstance(node.op, ast.USub) else value
    elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
        a = evaluate(node.left, env, mode, depth+1)
        if isinstance(node.op, ast.Pow):
            if not isinstance(node.right, ast.Constant) or type(node.right.value) is not int or not 0 <= node.right.value <= 8:
                raise ValueError("bounded nonnegative literal power required")
            result = constant(1)
            for _ in range(node.right.value): result = result*a
        else:
            b = evaluate(node.right, env, mode, depth+1)
            if isinstance(node.op, ast.Add): result = a+b
            elif isinstance(node.op, ast.Sub): result = a-b
            elif isinstance(node.op, ast.Mult): result = a*b
            else: result = a/b
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"exp", "log"} and len(node.args) == 1 and not node.keywords:
        value = evaluate(node.args[0], env, mode, depth+1)
        if mode == "interval":
            raise ValueError("transcendental interval bound not implemented")
        if mode == "decimal": result = value.exp() if node.func.id == "exp" else value.ln()
        else: result = math.exp(value) if node.func.id == "exp" else math.log(value)
    else:
        raise ValueError("outside nonexecuting arithmetic model fragment")
    if mode == "float" and not math.isfinite(result):
        raise ValueError("nonfinite model result")
    return result


def reproduce(raw):
    started = time.monotonic()
    result = {"checker": "nist-rounded-model-v3", "status": "UNKNOWN", "authority": False,
              "scientific_meaning": "OPEN", "scope": "Tabulated observations, printed fitted coefficients and residual statistics; no global optimum or empirical validity proof"}
    try:
        parsed = parse(raw)
        rows, params, stats = parsed["rows"], parsed["parameters"], parsed["statistics"]
        n, df = int(rational(stats["n"])), int(rational(stats["df"]))
        if Fraction(n) != rational(stats["n"]) or Fraction(df) != rational(stats["df"]):
            raise ValueError("noninteger counts")
        if n != len(rows) or df != n-len(params) or df <= 0:
            result.update(status="REFUTED", reason="data/count/parameter degrees-of-freedom inconsistency")
            return result
        values = {k: float(v) for k, v in params.items()}
        residuals = [float(y)-evaluate(parsed["tree"], {**values, "x": float(x)}, "float") for y, x in rows]
        rss = math.fsum(r*r for r in residuals)
        with localcontext() as ctx:
            ctx.prec = 80
            dp = {k: Decimal(v) for k, v in params.items()}
            drss = sum((Decimal(y)-evaluate(parsed["tree"], {**dp, "x": Decimal(x)}, "decimal"))**2 for y, x in rows)
        reported_rss = float(stats["rss"])
        relative = abs(rss-reported_rss)/max(abs(reported_rss), 1e-300)
        result.update(formula=parsed["formula"], observations=n, fitted_parameters=len(params),
                      degrees_of_freedom=df, rss_float=rss, rss_decimal80=str(drss),
                      rss_reported=stats["rss"], rss_relative_discrepancy=relative,
                      float_decimal_absolute_difference=abs(rss-float(drss)),
                      residual_std_recomputed=math.sqrt(rss/df), residual_std_reported=stats["residual_std"],
                      assumptions=["Source data values interpreted as their exact tabulated decimals.",
                                   "Printed coefficients approximate a fit; parameter standard deviations are not rounding bounds.",
                                   "Fitted conditional mean excludes the additive error term e; no distribution is inferred."],
                      statistical_assumptions_status="NOT_VERIFIED")
        relative_std = abs(math.sqrt(rss/df)-float(stats["residual_std"]))/max(abs(float(stats["residual_std"])), 1e-300)
        result["status"] = "REPRODUCED_ROUNDED_COMPUTATION" if relative <= 1e-7 and relative_std <= 1e-7 else "REFUTED"
        result["comparison_tolerance"] = {"relative": 1e-7, "justification": "Predeclared finite reproduction tolerance, not a rigorous error bound"}
        try:
            ip = {k: rounding_interval(v) for k, v in params.items()}
            bound = Interval(Fraction(0), Fraction(0))
            for y, x in rows:
                yf, xf = rational(y), rational(x)
                predicted = evaluate(parsed["tree"], {**ip, "x": Interval(xf, xf)}, "interval")
                bound = bound + (Interval(yf, yf)-predicted).square()
            report = rounding_interval(stats["rss"])
            overlap = max(bound.lo, report.lo) <= min(bound.hi, report.hi)
            result["exact_rational_rounding_enclosure"] = {"status": "COMPATIBLE" if overlap else "INCOMPATIBLE",
                "rss_interval": bound.public(), "reported_rounding_interval": report.public(),
                "assumption": "Each coefficient and reported RSS rounded to nearest at last printed digit; tabulated observations exact",
                "scope": "Conservative rational interval arithmetic enclosure over these finite inputs, not formal Python refinement or optimum certification"}
        except ValueError as exc:
            result["exact_rational_rounding_enclosure"] = {"status": "UNSUPPORTED", "reason": str(exc)}
    except (ValueError, UnicodeError, SyntaxError, ZeroDivisionError, OverflowError, ArithmeticError) as exc:
        result.update(status="UNKNOWN", reason=type(exc).__name__+": "+str(exc)[:180])
    finally:
        result["seconds"] = time.monotonic()-started
    return result
