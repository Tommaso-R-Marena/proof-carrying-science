"""Lossless bounded sharing of actual Lean expression trees and binding edges.

This graph is a representation, never a proof-state authority. Constants retain
universe-bearing identities, locals retain Lean IDs, and de Bruijn references
remain unchanged. Binder edges are resolved per occurrence, rather than treating
shared bound-variable nodes as globally scoped mathematical variables.
"""
from copy import deepcopy
from .induction_ir import digest


def encode_state(state, *, max_nodes=8192, max_occurrences=65536):
    if type(state) is not dict or type(state.get("goals")) is not list:
        raise ValueError("structured Lean state required")
    nodes, interned, roots, bindings = [], {}, [], []
    occurrences = 0

    def visit(expression, scope=(), path=(), depth=0):
        nonlocal occurrences
        occurrences += 1
        if occurrences > max_occurrences or depth > 128:
            raise ValueError("proof expression occurrence/depth bound")
        if type(expression) is not dict or set(expression) != {"kind", "value", "children"}:
            raise ValueError("noncanonical Lean expression node")
        if type(expression["kind"]) is not str or type(expression["value"]) is not str or type(expression["children"]) is not list:
            raise ValueError("malformed Lean expression node")
        identity = digest(expression)
        child_indices = []
        for index, child in enumerate(expression["children"]):
            child_scope = (*scope, path) if expression["kind"] in {"forall", "lambda", "let"} and index == len(expression["children"]) - 1 else scope
            child_indices.append(visit(child, child_scope, (*path, index), depth + 1))
        if identity not in interned:
            if len(nodes) >= max_nodes:
                raise ValueError("proof expression sharing bound")
            interned[identity] = len(nodes)
            nodes.append({"kind": expression["kind"], "value": expression["value"], "children": child_indices})
        if expression["kind"] == "bound":
            try:
                index = int(expression["value"])
            except ValueError:
                raise ValueError("invalid de Bruijn index") from None
            if index < 0 or index >= len(scope):
                raise ValueError("unbound de Bruijn reference")
            bindings.append({"occurrence_path": list(path), "binder_path": list(scope[-1-index]), "index": index})
        return interned[identity]

    metadata = deepcopy(state)
    for goal_index, goal in enumerate(state["goals"]):
        roots.append({"goal": goal_index, "role": "target", "node": visit(goal["expression"], path=(goal_index, -1))})
        metadata["goals"][goal_index].pop("expression")
        for local_index, local in enumerate(goal["locals"]):
            roots.append({"goal": goal_index, "role": "local", "local": local_index,
                          "node": visit(local["expression"], path=(goal_index, local_index))})
            metadata["goals"][goal_index]["locals"][local_index].pop("expression")
    # Available premises retain their exact original expression trees; this
    # representation compresses the goal/context without changing catalog APIs.
    return {"format": "pcs-lean-expression-dag-v1", "nodes": nodes, "roots": roots,
            "bindings": bindings, "metadata": metadata, "state_sha256": digest(state),
            "occurrences": occurrences, "unique_nodes": len(nodes)}


def decode_state(graph):
    if graph.get("format") != "pcs-lean-expression-dag-v1" or len(graph.get("nodes", [])) > 8192:
        raise ValueError("invalid expression DAG")
    nodes = graph["nodes"]
    expanded = []
    expanded_sizes = []
    allocation_nodes = 0
    for index, node in enumerate(nodes):
        if type(node) is not dict or set(node) != {"kind", "value", "children"} or len(node["children"]) > 4:
            raise ValueError("invalid shared expression node")
        if any(type(child) is not int or not 0 <= child < index for child in node["children"]):
            raise ValueError("cyclic, forward or invalid DAG edge")
        size = 1 + sum(expanded_sizes[child] for child in node["children"])
        allocation_nodes += size
        if size > 65536 or allocation_nodes > 2_000_000:
            raise ValueError("DAG expansion exceeds receiver allocation bound")
        expanded_sizes.append(size)
        expanded.append({"kind": node["kind"], "value": node["value"],
                         "children": [deepcopy(expanded[child]) for child in node["children"]]})
    state = deepcopy(graph["metadata"])
    for root in graph["roots"]:
        expression = deepcopy(expanded[root["node"]])
        goal = state["goals"][root["goal"]]
        if root["role"] == "target":
            goal["expression"] = expression
        elif root["role"] == "local":
            goal["locals"][root["local"]]["expression"] = expression
        else:
            raise ValueError("unknown expression root")
    if digest(state) != graph["state_sha256"]:
        raise ValueError("DAG does not reconstruct bound proof state")
    if encode_state(state)["bindings"] != graph["bindings"]:
        raise ValueError("forged binder correspondence")
    return state
