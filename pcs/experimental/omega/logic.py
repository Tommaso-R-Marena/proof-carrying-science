"""Independent exhaustive Boolean checker and constrained repair language.

The wire AST is the zero-arity fragment of PCS semantic_translation_v1.
Nothing here executes submitted code, validates scientific intent, or registers
a new PCS authoritative verifier. All inputs and search transitions are bounded.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import itertools
import re

from pcs.canonical_json import canonicalize_jcs_bytes

CHECKER = "pcs-omega-exhaustive-bool/1"
OPS = ("atom", "true", "false", "not", "and", "or", "implies")
MAX_NODES, MAX_DEPTH, MAX_ACTIONS = 63, 8, 128


def digest(value):
    return hashlib.sha256(canonicalize_jcs_bytes(value)).hexdigest()


def exact(value, fields, label="object"):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(f"Unexpected {label} fields")
    return value


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be an integer in [{low},{high}]")
    return value


def variables(value):
    if (type(value) is not list or not 1 <= len(value) <= 4 or
            any(type(v) is not str or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,15}", v) for v in value) or
            len(set(value)) != len(value) or value != sorted(value)):
        raise ValueError("Declare 1–4 distinct sorted Boolean symbols")
    return value


def validate_formula(formula, names):
    variables(names)
    count = 0

    def visit(node, depth):
        nonlocal count
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise ValueError("Formula complexity bound exceeded")
        if type(node) is not dict or node.get("op") not in OPS:
            raise ValueError("Unsupported Boolean construct")
        op = node["op"]
        fields = {"op"}
        if op == "atom":
            fields |= {"symbol", "args"}
        elif op == "not":
            fields |= {"body"}
        elif op in {"and", "or", "implies"}:
            fields |= {"left", "right"}
        exact(node, fields, "formula")
        if op == "atom" and (node["symbol"] not in names or node["args"] != []):
            raise ValueError("Unresolved symbol, arity, or non-Boolean unit")
        if op == "not":
            visit(node["body"], depth + 1)
        elif op in {"and", "or", "implies"}:
            visit(node["left"], depth + 1)
            visit(node["right"], depth + 1)

    visit(formula, 0)
    return count


def task(value):
    exact(value, {"variables", "source", "candidate"}, "reasoning task")
    variables(value["variables"])
    for name in ("source", "candidate"):
        validate_formula(value[name], value["variables"])
    return value


def evaluate(formula, assignment):
    op = formula["op"]
    if op == "atom":
        return assignment[formula["symbol"]]
    if op in {"true", "false"}:
        return op == "true"
    if op == "not":
        return not evaluate(formula["body"], assignment)
    a = evaluate(formula["left"], assignment)
    b = evaluate(formula["right"], assignment)
    return a and b if op == "and" else a or b if op == "or" else not a or b


def check(value):
    task(value)
    rows, witness = [], None
    for bits in itertools.product((False, True), repeat=len(value["variables"])):
        assignment = dict(zip(value["variables"], bits))
        a, b = evaluate(value["source"], assignment), evaluate(value["candidate"], assignment)
        rows.append([a, b])
        if a != b and witness is None:
            witness = {"assignment": assignment, "source_true": a, "candidate_true": b}
    return {"format": "pcs-omega-check-v1", "checker": CHECKER, "task_sha256": digest(value),
            "source_sha256": digest(value["source"]), "candidate_sha256": digest(value["candidate"]),
            "assignments_checked": len(rows), "truth_pairs": rows,
            "equivalent": witness is None, "counterexample": witness,
            "scope": "All valuations of the explicitly declared Boolean symbols",
            "pcs_authority": False, "lean_kernel_checked": False}


def verify_receipt(value, receipt):
    if digest(receipt) != digest(check(value)):
        raise ValueError("Forged, stale, or wrong-task checker receipt")
    return True


def walk(formula, path=()):
    yield path, formula
    if formula["op"] == "not":
        yield from walk(formula["body"], path + ("body",))
    elif formula["op"] in {"and", "or", "implies"}:
        yield from walk(formula["left"], path + ("left",))
        yield from walk(formula["right"], path + ("right",))


def action_id(action):
    return action["operation"] + "@" + "/".join(action["path"])


def apply_action(formula, action, names):
    validate_formula(formula, names)
    exact(action, {"kind", "path", "operation"}, "repair action")
    if (action["kind"] != "REPAIR_CANDIDATE" or type(action["path"]) is not list or
            len(action["path"]) > MAX_DEPTH or any(type(p) is not str or p not in {"body", "left", "right"} for p in action["path"])):
        raise ValueError("Invalid repair path or action")
    result = deepcopy(formula)
    node = result
    parent, field = None, None
    for field in action["path"]:
        parent = node
        if field not in node:
            raise ValueError("Repair path does not exist")
        node = node[field]
    operation = action["operation"]
    if type(operation) is not str:
        raise ValueError("Repair operation must be a string")
    if operation == "insert_not":
        replacement = {"op": "not", "body": deepcopy(node)}
    elif operation == "remove_not" and node["op"] == "not":
        replacement = deepcopy(node["body"])
    elif operation == "swap" and node["op"] in {"and", "or", "implies"}:
        replacement = {"op": node["op"], "left": deepcopy(node["right"]), "right": deepcopy(node["left"])}
    elif operation in {"replace_and", "replace_or", "replace_implies"} and node["op"] in {"and", "or", "implies"}:
        replacement = {**deepcopy(node), "op": operation.removeprefix("replace_")}
    else:
        raise ValueError("Unsupported or inapplicable repair")
    if parent is None:
        result = replacement
    else:
        parent[field] = replacement
    validate_formula(result, names)
    return result


def actions(formula, names):
    validate_formula(formula, names)
    out, seen = [], {digest(formula)}
    for path, node in walk(formula):
        operations = ["insert_not"]
        if node["op"] == "not":
            operations.append("remove_not")
        if node["op"] in {"and", "or", "implies"}:
            operations += ["swap", "replace_and", "replace_or", "replace_implies"]
        for operation in operations:
            action = {"kind": "REPAIR_CANDIDATE", "path": list(path), "operation": operation}
            try:
                candidate = apply_action(formula, action, names)
            except ValueError:
                continue
            key = digest(candidate)
            if key in seen:
                continue
            seen.add(key)
            out.append(action)
            if len(out) == MAX_ACTIONS:
                return out
    return out


def lean_source(value):
    """Emit only a fixed proof template over validated data, never submitted Lean."""
    task(value)
    names = {name: "p" + str(i) for i, name in enumerate(value["variables"])}

    def term(node):
        op = node["op"]
        if op == "atom":
            return names[node["symbol"]]
        if op in {"true", "false"}:
            return op
        if op == "not":
            return f"(!{term(node['body'])})"
        a, b = term(node["left"]), term(node["right"])
        return f"({a} && {b})" if op == "and" else f"({a} || {b})" if op == "or" else f"(!{a} || {b})"

    params = " ".join(names.values())
    proof = " <;> ".join("cases " + n for n in names.values()) + " <;> decide"
    return (f"-- Experimental Boolean interpretation; scientific intent remains unproved.\n"
            f"-- task_sha256={digest(value)}\n"
            f"theorem omega_equivalence ({params} : Bool) :\n"
            f"    {term(value['source'])} = {term(value['candidate'])} := by\n  {proof}\n"
            "#print axioms omega_equivalence\n")
