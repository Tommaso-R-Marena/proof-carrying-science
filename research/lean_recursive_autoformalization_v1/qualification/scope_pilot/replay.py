"""Score recorded candidates on every nonempty set of unary predicate profiles."""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

from reference import denotations

HERE = Path(__file__).resolve().parent
ARITY = {"all": 1, "some": 1, "not": 1, "imp": 2, "iff": 2, "and": 2, "or": 2}


def formula(tree, bound=False, depth=0):
    if depth > 32:
        raise ValueError("depth budget")
    if isinstance(tree, str) and tree in {"T", "I"} and bound:
        return tree
    if not isinstance(tree, list) or not tree or not isinstance(tree[0], str):
        raise ValueError("closed formula required")
    op, *children = tree
    if ARITY.get(op) != len(children):
        raise ValueError("unknown constructor or arity")
    return (op, *(formula(child, bound or op in {"all", "some"}, depth+1) for child in children))


def evaluate(expr, world, assignment=None):
    if expr == "T":
        return assignment[0]
    if expr == "I":
        return assignment[1]
    op, *args = expr
    if op in {"all", "some"}:
        reduce = all if op == "all" else any
        return reduce(evaluate(args[0], world, x) for x in world)
    left = evaluate(args[0], world, assignment)
    if op == "not":
        return not left
    right = evaluate(args[1], world, assignment)
    return {"imp": not left or right, "iff": left == right, "or": left or right, "and": left and right}[op]


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate property")
        result[key] = value
    return result


def score(items, candidates):
    profiles = tuple(itertools.product((False, True), repeat=2))
    worlds = [frozenset(subset) for n in range(1, 5) for subset in itertools.combinations(profiles, n)]
    outcomes = {}
    for item, _ in items:
        if item not in candidates:
            outcomes[item] = {"status": "missing"}
            continue
        try:
            expr = formula(candidates[item])
        except ValueError:
            outcomes[item] = {"status": "invalid_formula"}
            continue
        for world in worlds:
            tagged = {p for p in world if p[0]}
            inspected = {p for p in world if p[1]}
            expected = denotations(tagged, inspected, world)[item]
            if evaluate(expr, world) != expected:
                outcomes[item] = {"status": "refuted", "world": sorted(world), "reference": expected}
                break
        else:
            outcomes[item] = {"status": "equivalent_to_reference"}
    extra = sorted(set(candidates) - set(outcomes))
    return {"protocol_valid": not extra and all(v["status"] == "equivalent_to_reference" for v in outcomes.values()),
            "extra_ids": extra, "outcomes": outcomes, "nonempty_profile_sets": len(worlds)}


def replay():
    for line in (HERE / "protocol.sha256").read_text().splitlines():
        digest, name = line.split()
        if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"changed protocol file {name}")
    receipt = json.loads((HERE / "attempt.json").read_text())
    from request import payload, MODEL
    if receipt["payload_sha256"] != hashlib.sha256(payload).hexdigest() or receipt["model"] != MODEL:
        raise ValueError("request binding differs")
    if receipt.get("status") != 200 or len(receipt["candidates"]) != 1:
        raise ValueError("no completed single candidate")
    reply = receipt["candidates"][0]
    if reply["finishReason"] != "STOP":
        raise ValueError("incomplete generation")
    body = json.loads("".join(p["text"] for p in reply["content"]["parts"]), object_pairs_hook=unique)
    return score(json.loads((HERE / "prompts.json").read_text()), body)


if __name__ == "__main__":
    print(json.dumps(replay(), sort_keys=True, indent=2))
