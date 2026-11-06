"""Independent, bounded numerical reproduction of explicitly supported examples.

Only trusted NumPy/SciPy kernels run. Submitted Python/doctests never run: their
AST is lowered to our small arithmetic IR and literal inputs. A numerical match
is evidence about this example and library version, not a mathematical proof.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import doctest
import hashlib
import math
import re

from .interpretation import NUMBER, Unsupported, parse_expression

MAX_BYTES = 2 * 1024 * 1024
MAX_EXAMPLES = 1024
MAX_VECTOR = 64
MAX_ITERATIONS = 2000
MAX_EVALUATIONS = 20000
_PRIMITIVES = frozenset({"sin", "cos", "tan", "exp", "log", "sqrt", "abs", "sum"})
_LIMITATIONS = [
    "Only literal-input Nelder-Mead minimization and solve_ivp examples in the declared arithmetic fragment are supported.",
    "Submitted code, imports, decorators and doctests are never executed.",
    "Results use trusted installed NumPy/SciPy numerical kernels; this is not formal verification or a Python implementation-equivalence proof.",
    "Iteration and evaluation counts depend on library versions, hardware and rounding; they are observations, not universal scientific claims.",
    "Displayed decimal precision defines comparison intervals; missing uncertainty and scientific applicability remain unresolved.",
]


def _finite(value, np):
    array = np.asarray(value)
    if array.dtype.kind not in "biuf" or array.size > 4096 or array.ndim > 2 or not np.all(np.isfinite(array)) or np.any(np.abs(array) > 1e200):
        raise Unsupported("nonfinite or excessive numerical intermediate")
    return value


def _evaluate(ir, environment, np, depth=0, budget=None):
    if budget is None:
        budget = [4096]
    budget[0] -= 1
    if budget[0] < 0:
        raise Unsupported("numerical operation budget exceeded")
    if depth > 48:
        raise Unsupported("numerical expression depth bound")
    op = ir["op"]
    if op == "number":
        return _finite(float(ir["value"]), np)
    if op == "symbol":
        if ir["name"] not in environment:
            raise Unsupported("unbound mathematical symbol: " + ir["name"])
        return _finite(environment[ir["name"]], np)
    if op == "neg":
        return _finite(-_evaluate(ir["arg"], environment, np, depth + 1, budget), np)
    if op in {"add", "sub", "mul", "div", "pow"}:
        values = [_evaluate(arg, environment, np, depth + 1, budget) for arg in ir["args"]]
        if len(values) != 2:
            raise Unsupported("binary arithmetic required")
        a, b = values
        if op == "pow" and (np.asarray(b).size != 1 or abs(float(b)) > 32):
            raise Unsupported("bounded scalar exponent required")
        with np.errstate(over="raise", divide="raise", invalid="raise", under="ignore"):
            if op == "add":
                result = a + b
            elif op == "sub":
                result = a - b
            elif op == "mul":
                result = a * b
            elif op == "div":
                result = a / b
            else:
                result = a ** b
        return _finite(result, np)
    if op == "vector":
        return _finite(np.asarray([_evaluate(item, environment, np, depth + 1, budget) for item in ir["items"]], dtype=float), np)
    if op == "subscript":
        value = _evaluate(ir["value"], environment, np, depth + 1, budget)

        def integer(part):
            result = _evaluate(part, environment, np, depth + 1, budget)
            if np.asarray(result).size != 1 or float(result) != int(float(result)) or abs(float(result)) > 4096:
                raise Unsupported("bounded integer index required")
            return int(float(result))

        index = ir["index"]
        if index["op"] == "slice":
            index = slice(*(integer(index[key]) if index[key] is not None else None for key in ("lower", "upper", "step")))
        else:
            index = integer(index)
        return _finite(value[index], np)
    if op == "call":
        args = [_evaluate(arg, environment, np, depth + 1, budget) for arg in ir["args"]]
        name = ir["function"]
        if name not in _PRIMITIVES:
            raise Unsupported("unapproved numerical primitive")
        with np.errstate(over="raise", divide="raise", invalid="raise", under="ignore"):
            if name == "sum" and ir.get("implementation") == "python_sum":
                if len(args) != 1 or ir.get("keywords"):
                    raise Unsupported("only the one-argument Python sum is supported")
                result = sum(args[0])
            else:
                function = {"sin": np.sin, "cos": np.cos, "tan": np.tan, "exp": np.exp, "log": np.log,
                            "sqrt": np.sqrt, "abs": np.abs, "sum": np.sum}[name]
                result = function(*args, **ir.get("keywords", {}))
        return _finite(result, np)
    if op == "model_call":
        args = [_evaluate(arg, environment, np, depth + 1, budget) for arg in ir["args"]]
        keywords = {key: _evaluate(arg, environment, np, depth + 1, budget) for key, arg in ir["keywords"].items()}
        return _model_value(ir["model"], args, keywords, np, depth + 1, budget)
    raise Unsupported("unsupported numerical IR operation")


def _model_value(model, args, keywords, np, depth=0, budget=None):
    if budget is None:
        budget = [4096]
    if depth > 16 or len(args) > len(model["positional"]):
        raise Unsupported("model call argument or recursion bound")
    environment = dict(model["globals"])
    bound = dict(model["defaults"])
    bound.update(zip(model["positional"], args))
    for name, value in keywords.items():
        if name not in model["parameters"] or name in model["positional"][:len(args)] or name in model["positional_only"]:
            raise Unsupported("ambiguous model call arguments")
        bound[name] = value
    if any(name not in bound for name in model["parameters"]):
        raise Unsupported("model call is missing a required parameter")
    environment.update(bound)
    for name, expression in model["assignments"]:
        environment[name] = _evaluate(expression, environment, np, depth + 1, budget)
    return _evaluate(model["rhs"], environment, np, depth + 1, budget)


def _literal(node, values, namespaces, np, depth=0):
    if depth > 12:
        raise Unsupported("literal nesting bound")
    if isinstance(node, ast.Constant) and type(node.value) in (int, float, str, bool, type(None)):
        value = node.value
        if isinstance(value, str) and len(value) > 256:
            raise Unsupported("literal string bound")
        if type(value) in (int, float) and (not math.isfinite(value) or abs(value) > 1e100):
            raise Unsupported("nonfinite or excessive literal")
        return value
    if isinstance(node, ast.Name) and node.id in values:
        return deepcopy(values[node.id])
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _literal(node.operand, values, namespaces, np, depth + 1)
        if type(value) not in (int, float):
            raise Unsupported("literal sign requires a number")
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, (ast.List, ast.Tuple)) and len(node.elts) <= MAX_VECTOR:
        values_ = [_literal(item, values, namespaces, np, depth + 1) for item in node.elts]
        return tuple(values_) if isinstance(node, ast.Tuple) else values_
    if isinstance(node, ast.Dict) and len(node.keys) <= 32:
        result = {}
        for key, value in zip(node.keys, node.values):
            if key is None:
                raise Unsupported("dictionary expansion is unsupported")
            key = _literal(key, values, namespaces, np, depth + 1)
            if not isinstance(key, str) or key in result:
                raise Unsupported("unique string option keys required")
            result[key] = _literal(value, values, namespaces, np, depth + 1)
        return result
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and namespaces.get(node.func.value.id) == "numpy":
        if node.func.attr in {"array", "asarray"} and len(node.args) == 1 and not node.keywords:
            value = _literal(node.args[0], values, namespaces, np, depth + 1)
            array = np.asarray(value, dtype=float)
            if array.ndim != 1 or not 1 <= array.size <= MAX_VECTOR:
                raise Unsupported("bounded one-dimensional literal vector required")
            return _finite(array, np)
        if node.func.attr == "linspace" and len(node.args) == 3 and not node.keywords:
            start, end, count = [_literal(arg, values, namespaces, np, depth + 1) for arg in node.args]
            if type(count) is not int or not 2 <= count <= 1000 or any(type(value) not in (int, float) for value in (start, end)):
                raise Unsupported("bounded literal linspace required")
            return _finite(np.linspace(start, end, count), np)
    raise Unsupported("input is not an approved literal construction")


def _lower(node, source, models, namespaces, primitives, allowed):
    """Use the frozen arithmetic parser, replacing only approved call nodes."""
    replacements = {}
    original_names = {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}

    class LowerCalls(ast.NodeTransformer):
        def visit_Call(self, call):
            if isinstance(call.func, ast.Name) and call.func.id in allowed or isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id in allowed:
                raise Unsupported("a local value shadows the mathematical callable")
            args = [_lower(arg, source, models, namespaces, primitives, allowed) for arg in call.args]
            if any(keyword.arg is None for keyword in call.keywords):
                raise Unsupported("call keyword expansion is unsupported")
            if isinstance(call.func, ast.Name) and call.func.id in models:
                keywords = {key.arg: _lower(key.value, source, models, namespaces, primitives, allowed) for key in call.keywords}
                if len(keywords) != len(call.keywords):
                    raise Unsupported("duplicate model-call keywords")
                ir = {"op": "model_call", "model": models[call.func.id], "args": args, "keywords": keywords}
            else:
                implementation = "numpy"
                if isinstance(call.func, ast.Name) and call.func.id in primitives:
                    declared = primitives[call.func.id]
                    name = declared.removeprefix("builtin:")
                    if declared == "builtin:sum":
                        implementation = "python_sum"
                elif isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and namespaces.get(call.func.value.id) in {"numpy", "math"}:
                    name = call.func.attr
                else:
                    raise Unsupported("function calls must resolve to approved mathematical primitives or parsed models")
                if name not in _PRIMITIVES or len(args) != 1:
                    raise Unsupported("unsupported mathematical primitive or arity")
                keywords = {}
                for key in call.keywords:
                    if key.arg != "axis" or not isinstance(key.value, ast.Constant) or type(key.value.value) is not int or abs(key.value.value) > 2:
                        raise Unsupported("only bounded constant reduction axes are supported")
                    keywords[key.arg] = key.value.value
                ir = {"op": "call", "function": name, "args": args, "keywords": keywords, "implementation": implementation}
            placeholder = "_scientific_call_" + str(len(replacements))
            while placeholder in original_names or placeholder in replacements:
                placeholder += "_"
            replacements[placeholder] = ir
            return ast.copy_location(ast.Name(id=placeholder, ctx=ast.Load()), call)

    transformed = LowerCalls().visit(deepcopy(node))
    ir = parse_expression(ast.unparse(transformed))

    def substitute(value):
        if isinstance(value, dict):
            if value.get("op") == "symbol":
                name = value["name"]
                if name in replacements:
                    return replacements[name]
                if name not in allowed:
                    raise Unsupported("mathematical expression has an unbound or shadowed symbol: " + name)
            return {key: substitute(item) for key, item in value.items()}
        if isinstance(value, list):
            return [substitute(item) for item in value]
        return value

    return substitute(ir)


def _function(node, source, values, models, namespaces, primitives, binding, np):
    if isinstance(node, ast.AsyncFunctionDef) or node.decorator_list or node.args.vararg or node.args.kwarg or len(node.args.args) + len(node.args.kwonlyargs) + len(node.args.posonlyargs) > 8:
        raise Unsupported("function decorators or variadic signatures are unsupported")
    positional = [arg.arg for arg in (*node.args.posonlyargs, *node.args.args)]
    parameters = positional + [arg.arg for arg in node.args.kwonlyargs]
    if len(set(parameters)) != len(parameters):
        raise Unsupported("duplicate model parameters")
    defaults = {}
    for name, default in zip(positional[len(positional) - len(node.args.defaults):], node.args.defaults):
        defaults[name] = _literal(default, values, namespaces, np)
    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        if default is not None:
            defaults[arg.arg] = _literal(default, values, namespaces, np)
    globals_ = {name: value for name, value in values.items() if type(value) in (int, float) or isinstance(value, np.ndarray)}
    allowed = set(parameters) | set(globals_)
    statements = list(node.body)
    if statements and isinstance(statements[0], ast.Expr) and isinstance(statements[0].value, ast.Constant) and isinstance(statements[0].value.value, str):
        statements.pop(0)
    assignments = []
    if not statements or not isinstance(statements[-1], ast.Return):
        raise Unsupported("model requires one final mathematical return")
    for statement in statements[:-1]:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            raise Unsupported("model control flow, mutations or side effects are unsupported")
        name = statement.targets[0].id
        assignments.append((name, _lower(statement.value, source, models, namespaces, primitives, allowed)))
        allowed.add(name)
    rhs = _lower(statements[-1].value, source, models, namespaces, primitives, allowed)
    dependencies = {item.id for item in ast.walk(node) if isinstance(item, ast.Name)} - set(parameters) - {name for name, _ in assignments}
    return {"name": node.name, "parameters": parameters, "positional": positional, "positional_only": [arg.arg for arg in node.args.posonlyargs], "defaults": defaults,
            "globals": globals_, "assignments": assignments, "rhs": rhs, "source": binding, "bindings": dependencies}


def _binding(text, raw_hash, name, example):
    lines = text.splitlines(keepends=True)
    start_line = example.lineno
    count = len(example.source.splitlines()) + len(example.want.splitlines())
    start = sum(len(line) for line in lines[:start_line])
    end = sum(len(line) for line in lines[:start_line + count])
    return {"name": name, "sha256": raw_hash, "locator": {"line_start": start_line + 1, "line_end": start_line + count,
            "char_start": start, "char_end": end, "text_encoding": "utf-8-sig"}, "quote": text[start:end]}


def _display_number(token):
    value = float(token)
    if not math.isfinite(value):
        raise Unsupported("reported number is nonfinite")
    mantissa, _, exponent = token.lower().partition("e")
    decimal_places = len(mantissa.partition(".")[2]) if "." in mantissa else 0
    tolerance = 0.5 * 10.0 ** ((int(exponent) if exponent else 0) - decimal_places)
    return value, tolerance


def _comparison(field, reported, observed, *, version_sensitive=False, solver_tolerance=0):
    value, tolerance = _display_number(reported)
    if version_sensitive:
        tolerance = 0
    difference = abs(float(observed) - value)
    matches = difference <= tolerance + 4 * math.ulp(value)
    solver_consistent = difference <= tolerance + solver_tolerance + 4 * math.ulp(value)
    return {"field": field, "reported": reported, "observed": float(observed), "absolute_difference": difference,
            "display_rounding_half_width": tolerance, "display_precision_status": "MATCH" if matches else "MISMATCH",
            "solver_tolerance_allowance": solver_tolerance,
            "status": "MATCH" if matches else ("WITHIN_DECLARED_SOLVER_TOLERANCE" if solver_consistent else "MISMATCH"),
            "version_sensitive": version_sensitive, "uncertainty": "Display precision only; no scientific uncertainty model supplied"}


def _reported_solver(want, observed):
    comparisons = []
    mapping = {"Current function value": "fun", "Iterations": "nit", "Function evaluations": "nfev"}
    for label, field in mapping.items():
        match = re.search(re.escape(label) + r"\s*:\s*(" + NUMBER + r")", want, re.I)
        if match:
            comparisons.append(_comparison(field, match[1], observed[field], version_sensitive=field != "fun"))
    if "Optimization terminated successfully." in want:
        comparisons.append({"field": "success", "reported": True, "observed": observed["success"],
                            "status": "MATCH" if observed["success"] else "MISMATCH", "version_sensitive": False})
    return comparisons


def _vector_report(want, observed, field, *, solver_tolerance=0):
    value = want.strip()
    if value.startswith("array(") and value.endswith(")"):
        value = value[6:-1].strip()
    if not value.startswith("[") or not value.endswith("]") or "..." in value:
        raise Unsupported("reported vector has unsupported formatting or omitted entries")
    content = value[1:-1]
    tokens = re.findall(NUMBER, content)
    remainder = re.sub(NUMBER, "", content)
    if re.sub(r"[\s,]", "", remainder) or len(tokens) != len(observed) or len(tokens) > MAX_VECTOR:
        raise Unsupported("reported and observed vector shape differ")
    return [_comparison(field + "[" + str(index) + "]", token, actual, solver_tolerance=solver_tolerance) for index, (token, actual) in enumerate(zip(tokens, observed))]


def _update_status(example):
    comparisons = example["comparisons"]
    decisive = [comparison for comparison in comparisons if not comparison["version_sensitive"]]
    example["status"] = "REFUTED" if any(item["status"] == "MISMATCH" for item in decisive) else ("REPRODUCED" if decisive else "INCONCLUSIVE")
    example["version_sensitive_count_differences"] = [item["field"] for item in comparisons if item["version_sensitive"] and item["status"] == "MISMATCH"]


def _public(value):
    if isinstance(value, dict):
        return {key: _public(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_public(item) for item in value]
    if isinstance(value, set):
        return sorted(value)
    if hasattr(value, "tolist"):
        return value.tolist()
    return value


def check_document(raw: bytes, name: str) -> dict:
    """Reproduce supported scientific documentation examples from exact bytes."""
    result = {"status": "UNSUPPORTED", "examples": [], "limitations": list(_LIMITATIONS), "authority": False,
              "source_sha256": hashlib.sha256(raw).hexdigest() if isinstance(raw, bytes) else None,
              "name": name, "execution": "TRUSTED_NUMERICAL_KERNELS_ONLY", "scientific_meaning": "MEANING_REVIEW_REQUIRED"}
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        result["reason"] = "document byte resource bound"
        return result
    try:
        text = raw.decode("utf-8-sig", errors="strict")
        if "\x00" in text:
            raise Unsupported("document contains NUL bytes")
        snippets = doctest.DocTestParser().get_examples(text)
        if len(snippets) > MAX_EXAMPLES:
            raise Unsupported("doctest example resource bound")
        import numpy as np
        import scipy
        from scipy.optimize import minimize
        from scipy.integrate import solve_ivp
        result["library_versions"] = {"numpy": np.__version__, "scipy": scipy.__version__}
    except (UnicodeError, ValueError, Unsupported, ImportError) as exc:
        result["reason"] = str(exc)[:256]
        return result
    values, models, namespaces, solver_names = {}, {}, {}, {}
    primitives = {"sum": "builtin:sum", "abs": "builtin:abs"}
    solutions = {}
    shadowed = set()

    def invalidate(identifier):
        dependent = [model_name for model_name, model in models.items() if identifier in model["bindings"]]
        for registry in (values, models, namespaces, solver_names, primitives, solutions):
            registry.pop(identifier, None)
        shadowed.add(identifier)
        for model_name in dependent:
            if model_name != identifier:
                invalidate(model_name)

    def invalidate_state():
        for registry in (values, models, namespaces, solver_names, primitives, solutions):
            registry.clear()
        result["unsupported_state_statement_count"] = result.get("unsupported_state_statement_count", 0) + 1
        limitation = "An unsupported state-changing statement invalidated the static environment; later examples require fresh declarations."
        if limitation not in result["limitations"]:
            result["limitations"].append(limitation)

    raw_hash = result["source_sha256"]
    for snippet in snippets:
        binding = _binding(text, raw_hash, name, snippet)
        if len(snippet.source) > 16384:
            continue
        try:
            tree = ast.parse(snippet.source, mode="exec")
            if len(list(ast.walk(tree))) > 2048 or len(tree.body) != 1:
                raise Unsupported("one bounded declaration or solver statement required")
            statement = tree.body[0]
            if isinstance(statement, ast.Import):
                for alias in statement.names:
                    local = alias.asname or alias.name
                    invalidate(local)
                    if alias.name in {"numpy", "math"}:
                        namespaces[local] = alias.name
                continue
            if isinstance(statement, ast.ImportFrom):
                for alias in statement.names:
                    local = alias.asname or alias.name
                    invalidate(local)
                    if statement.module == "scipy.optimize" and alias.name == "minimize":
                        solver_names[local] = "minimize"
                    elif statement.module == "scipy.integrate" and alias.name == "solve_ivp":
                        solver_names[local] = "solve_ivp"
                    elif statement.module in {"numpy", "math"} and alias.name in _PRIMITIVES:
                        primitives[local] = alias.name
                continue
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                invalidate(statement.name)
                model = _function(statement, snippet.source, values, models, namespaces, primitives, binding, np)
                models[statement.name] = model
                continue
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
                target, expression = statement.targets[0].id, statement.value
                invalidate(target)
                if not isinstance(expression, ast.Call) or not isinstance(expression.func, ast.Name) or expression.func.id not in solver_names:
                    values[target] = _literal(expression, values, namespaces, np)
                    continue
                solver = solver_names[expression.func.id]
                example = {"status": "UNSUPPORTED", "solver": solver, "source": binding, "source_bindings": [binding],
                           "reported": snippet.want, "observed": {}, "comparisons": [], "authority": False,
                           "limitations": [], "meaning_status": "MEANING_REVIEW_REQUIRED"}
                result["examples"].append(example)
                if any(key.arg is None for key in expression.keywords) or not expression.args or not isinstance(expression.args[0], ast.Name) or expression.args[0].id not in models:
                    raise Unsupported("solver requires a previously parsed mathematical model")
                model = models[expression.args[0].id]
                example["source_bindings"].append(model["source"])
                example["model"] = _public({"name": model["name"], "parameters": model["parameters"], "rhs": model["rhs"], "assignments": model["assignments"]})
                keywords = {key.arg: _literal(key.value, values, namespaces, np) for key in expression.keywords}
                if len(keywords) != len(expression.keywords):
                    raise Unsupported("duplicate solver keywords")
                if solver == "minimize":
                    if len(expression.args) != 2 or set(keywords) - {"method", "args", "options", "tol"}:
                        raise Unsupported("only explicit unconstrained Nelder-Mead options are supported")
                    if str(keywords.get("method", "")).lower() != "nelder-mead":
                        raise Unsupported("minimization method outside the supported Nelder-Mead fragment")
                    initial = np.asarray(_literal(expression.args[1], values, namespaces, np), dtype=float)
                    if initial.ndim != 1 or not 1 <= initial.size <= MAX_VECTOR:
                        raise Unsupported("bounded one-dimensional initial vector required")
                    _finite(initial, np)
                    arguments = keywords.get("args", ())
                    if not isinstance(arguments, (tuple, list)) or len(arguments) > 7:
                        raise Unsupported("literal tuple of model parameters required")
                    options = keywords.get("options", {})
                    if not isinstance(options, dict) or set(options) - {"xatol", "fatol", "maxiter", "maxfev", "disp", "adaptive"}:
                        raise Unsupported("unsupported Nelder-Mead option")
                    options = dict(options)
                    if any(key in options and type(options[key]) is not bool for key in ("disp", "adaptive")):
                        raise Unsupported("boolean solver flags required")
                    for key in ("xatol", "fatol"):
                        if key in options and (type(options[key]) not in (int, float) or not 0 < options[key] <= 1):
                            raise Unsupported("positive bounded convergence tolerance required")
                    for key, maximum in (("maxiter", MAX_ITERATIONS), ("maxfev", MAX_EVALUATIONS)):
                        if key in options and (type(options[key]) is not int or not 1 <= options[key] <= maximum):
                            raise Unsupported("solver work bound exceeded")
                    options.setdefault("maxiter", min(MAX_ITERATIONS, initial.size * 200))
                    options.setdefault("maxfev", min(MAX_EVALUATIONS, initial.size * 200))
                    options["disp"] = False
                    tol = keywords.get("tol")
                    if tol is not None and (type(tol) not in (int, float) or not 0 < tol <= 1):
                        raise Unsupported("positive bounded solver tolerance required")
                    objective = lambda x: float(_model_value(model, [x, *arguments], {}, np))
                    first = objective(initial)
                    _finite(first, np)
                    solved = minimize(objective, initial.copy(), method="Nelder-Mead", options=options, tol=tol)
                    try:
                        _finite(solved.x, np)
                        _finite(solved.fun, np)
                    except Unsupported as exc:
                        example.update(status="INCONCLUSIVE", reason="Numerical kernel returned a nonfinite or excessive result: " + str(exc))
                        continue
                    observed = {"x": solved.x.tolist(), "fun": float(solved.fun), "nit": int(solved.nit), "nfev": int(solved.nfev), "success": bool(solved.success)}
                    example["inputs"] = {"x0": initial.tolist(), "args": list(arguments), "options": options, "tol": tol}
                    example["observed"] = observed
                    example["comparisons"] = _reported_solver(snippet.want, observed)
                    example["limitations"].append("Bounded to at most 2000 iterations and 20000 evaluations; convergence and count equality depend on the installed numerical library.")
                    _update_status(example)
                    solutions[target] = example
                else:
                    if len(expression.args) != 3 or set(keywords) - {"method", "t_eval", "dense_output", "rtol", "atol", "args", "max_step", "first_step"}:
                        raise Unsupported("ODE solver call is outside the supported literal-input fragment")
                    span = _literal(expression.args[1], values, namespaces, np)
                    initial = np.asarray(_literal(expression.args[2], values, namespaces, np), dtype=float)
                    if not isinstance(span, (list, tuple)) or len(span) != 2 or any(type(t) not in (int, float) for t in span) or not span[0] < span[1] or span[1] - span[0] > 1e4 or initial.ndim != 1 or not 1 <= initial.size <= 16:
                        raise Unsupported("bounded increasing time interval and initial vector required")
                    if keywords.get("method", "RK45") not in {"RK45", "RK23", "DOP853"}:
                        raise Unsupported("only approved explicit ODE methods are supported")
                    for key in ("rtol", "atol", "max_step", "first_step"):
                        if key in keywords and (type(keywords[key]) not in (int, float) or not 0 < keywords[key] <= 1e4):
                            raise Unsupported("positive bounded ODE tolerance/step required")
                    arguments = keywords.pop("args", ())
                    if not isinstance(arguments, (list, tuple)) or len(arguments) > 6:
                        raise Unsupported("literal ODE parameters required")
                    evaluation_count = [0]

                    def derivative(t, y):
                        evaluation_count[0] += 1
                        if evaluation_count[0] > MAX_EVALUATIONS:
                            raise Unsupported("ODE work bound exceeded")
                        return _model_value(model, [t, y, *arguments], {}, np)

                    solved = solve_ivp(derivative, span, initial, **keywords)
                    try:
                        _finite(solved.t, np)
                        _finite(solved.y, np)
                    except Unsupported as exc:
                        example.update(status="INCONCLUSIVE", reason="Numerical kernel returned a nonfinite or excessive result: " + str(exc))
                        continue
                    example["observed"] = {"t": solved.t.tolist(), "y": solved.y.tolist(), "nfev": int(solved.nfev), "success": bool(solved.success)}
                    example["inputs"] = {"t_span": list(span), "y0": initial.tolist(), "args": list(arguments)}
                    _update_status(example)
                    solutions[target] = example
                continue
            if isinstance(statement, ast.Expr):
                expression = statement.value
                if isinstance(expression, ast.Call) and isinstance(expression.func, ast.Name) and expression.func.id == "print" and "print" not in shadowed and len(expression.args) == 1 and not expression.keywords:
                    expression = expression.args[0]
                if isinstance(expression, ast.Attribute) and isinstance(expression.value, ast.Name) and expression.value.id in solutions and expression.attr in {"x", "fun", "nit", "nfev", "t", "y"}:
                    example = solutions[expression.value.id]
                    field = expression.attr
                    if not snippet.want.strip():
                        continue
                    observed = example["observed"][field]
                    if field in {"x", "t"}:
                        solver_tolerance = example.get("inputs", {}).get("options", {}).get("xatol", 0) if field == "x" else 0
                        comparisons = _vector_report(snippet.want, observed, field, solver_tolerance=solver_tolerance)
                    elif field == "y":
                        raise Unsupported("two-dimensional ODE output display comparison requires explicit indexed observations")
                    else:
                        token = snippet.want.strip()
                        if not re.fullmatch(NUMBER, token):
                            raise Unsupported("scalar output display is not a finite decimal")
                        comparisons = [_comparison(field, token, observed, version_sensitive=field in {"nit", "nfev"})]
                    example["comparisons"].extend(comparisons)
                    example["source_bindings"].append(binding)
                    _update_status(example)
                    continue
            # Never keep stale literals after unsupported mutations, control
            # flow, deletes, or calls with potential side effects.
            invalidate_state()
        except (SyntaxError, Unsupported, ValueError, TypeError, KeyError, IndexError, OverflowError, ZeroDivisionError, FloatingPointError, RecursionError) as exc:
            if result["examples"] and result["examples"][-1]["source"] == binding:
                result["examples"][-1]["reason"] = str(exc)[:256]
                result["examples"][-1]["status"] = "UNSUPPORTED"
            elif not isinstance(locals().get("statement"), (ast.FunctionDef, ast.AsyncFunctionDef)):
                invalidate_state()
            continue
    supported = [example for example in result["examples"] if example["status"] != "UNSUPPORTED"]
    if any(example["status"] == "REFUTED" for example in supported):
        result["status"] = "REFUTED"
    elif supported and all(example["status"] == "REPRODUCED" for example in supported):
        result["status"] = "REPRODUCED" if len(supported) == len(result["examples"]) and not result.get("unsupported_state_statement_count") else "PARTIAL"
    elif supported:
        result["status"] = "PARTIAL"
    return _public(result)
