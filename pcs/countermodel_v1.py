"""Independent, bounded checker for PCS Arena's concrete first-order witnesses.

This evaluates pinned formulas, never submitted code or proof certificates. It
does not elevate a game outcome to PCS or Lean authority.
"""
from __future__ import annotations

import hashlib
from copy import deepcopy
import itertools
import json
from importlib.resources import files
from pathlib import Path

VERSION = "pcs-countermodel-lab-v1"
RULESET_SHA256 = "d3b02eb4eb39976fd3179a44ef1b6bffd17a8f4a271b1bd7cddb97eb71276df2"


def _missions():
    rows = json.loads(files("pcs.schemas").joinpath("countermodel_missions_v1.json").read_text())
    encoded = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
    if hashlib.sha256(encoded).hexdigest() != RULESET_SHA256:
        raise ValueError("Countermodel ruleset pin mismatch")
    return {row["id"]: row for row in rows}


def _world(value):
    if not isinstance(value, dict) or set(value) != {"n", "P", "Q", "R"}:
        raise ValueError("Unexpected world fields")
    n = value["n"]
    if type(n) is not int or not 1 <= n <= 3:
        raise ValueError("Domain must contain 1–3 entities")
    for p in ("P", "Q"):
        if not isinstance(value[p], list) or len(value[p]) != n or any(type(v) is not bool for v in value[p]):
            raise ValueError("Predicates must be explicit Boolean arrays")
    if not isinstance(value["R"], list) or len(value["R"]) != n:
        raise ValueError("Invalid relation dimensions")
    for row in value["R"]:
        if not isinstance(row, list) or len(row) != n or any(type(v) is not bool for v in row):
            raise ValueError("Invalid Boolean relation")
    return value


def _eval(node, world, bindings):
    op = node["op"]
    if op == "pred":
        return world[node["p"]][bindings[node["x"]]]
    if op == "rel":
        return world["R"][bindings[node["x"]]][bindings[node["y"]]]
    if op == "not":
        return not _eval(node["f"], world, bindings)
    if op in {"and", "or", "imp"}:
        a, b = _eval(node["a"], world, bindings), _eval(node["b"], world, bindings)
        return (a and b) if op == "and" else (a or b) if op == "or" else (not a or b)
    values = (_eval(node["f"], world, {**bindings, node["x"]: i}) for i in range(world["n"]))
    if op == "forall":
        return all(values)
    if op == "exists":
        return any(values)
    raise ValueError("Unsupported pinned formula")


def _verdict(mission, world):
    return _eval(mission["a"], world, {}), _eval(mission["b"], world, {})


def _minimum(mission):
    for n in range(1, 4):
        bits = 2 * n + (n * n if mission["kind"] == "relation" else 0)
        for assignment in itertools.product((False, True), repeat=bits):
            world = {"n": n, "P": list(assignment[:n]), "Q": list(assignment[n:2*n]),
                     "R": [list(assignment[2*n+i*n:2*n+(i+1)*n]) for i in range(n)]
                     if mission["kind"] == "relation" else [[False]*n for _ in range(n)]}
            left, right = _verdict(mission, world)
            if left != right:
                return n
    return None


def check_countermodel_witness(document):
    if not isinstance(document, dict) or set(document) != {"format", "version", "mission_id", "world"}:
        raise ValueError("Use only the documented witness fields; submitted verdicts are forbidden")
    if document["format"] != "pcs-countermodel-witness-v1" or document["version"] != VERSION:
        raise ValueError("Unsupported witness version")
    mission_id = document["mission_id"]
    if not isinstance(mission_id, str) or mission_id not in _missions():
        raise ValueError("Unregistered countermodel mission")
    mission = _missions()[mission_id]
    world = _world(document["world"])
    left, right = _verdict(mission, world)
    return {"format": "pcs-countermodel-python-assessment-v1", "mission_id": mission_id,
            "ruleset_sha256": RULESET_SHA256, "source_true": left, "proposal_true": right,
            "counterexample": left != right, "domain_size": world["n"],
            "minimum_domain_size": _minimum(mission), "checker": "INDEPENDENT_PYTHON_FINITE_FOL",
            "lean_kernel_checked": False, "pcs_authoritative": False,
            "scope": "Pinned formulas over explicit nonempty Boolean worlds with 1–3 entities"}


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("Duplicate JSON field")
        out[key] = value
    return out


def check_countermodel_file(path):
    with Path(path).open("rb") as handle:
        raw = handle.read(16385)
    if len(raw) > 16384:
        raise ValueError("Witness exceeds 16 KiB")
    document = json.loads(raw, object_pairs_hook=_unique)
    return check_countermodel_witness(document)


def command(args):
    try:
        result = check_countermodel_file(args.input)
    except (ValueError, OSError, UnicodeError) as error:
        print(json.dumps({"error": str(error), "pcs_authoritative": False}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["counterexample"] else 1


def replay_countermodel_session(document):
    """Recompute a player's choices independently of the browser/Worker code.

    No submitted state, outcome, score, reward or assistance flag is accepted.
    A valid unsuccessful search is a valid replay, never a countermodel proof.
    """
    if not isinstance(document, dict) or set(document) != {"version", "mission_id", "actions"}:
        raise ValueError("Use only version, mission_id and actions; submitted labels are forbidden")
    mission_id = document["mission_id"]
    missions = _missions()
    if document["version"] != VERSION or not isinstance(mission_id, str) or mission_id not in missions:
        raise ValueError("Unregistered mission or version")
    actions = document["actions"]
    if not isinstance(actions, list) or not 1 <= len(actions) <= 120:
        raise ValueError("Use 1–120 typed actions")
    mission = missions[mission_id]
    world = {"n": 1, "P": [False], "Q": [False], "R": [[False]]}
    steps = []
    checks = hints = edits = 0
    feedback = False
    first_success = None
    for index, action in enumerate(actions):
        if not isinstance(action, dict) or not isinstance(action.get("type"), str):
            raise ValueError("Invalid typed action")
        before, feedback_before, hints_before = deepcopy(world), feedback, hints
        kind, reward = action["type"], 0
        if kind in {"add", "remove", "hint", "check"}:
            if set(action) != {"type"}:
                raise ValueError("Unexpected action fields")
            if kind == "add":
                if world["n"] == 3:
                    raise ValueError("Maximum domain size reached")
                world["n"] += 1
                for p in ("P", "Q"):
                    world[p].append(False)
                world["R"] = [row + [False] for row in world["R"]] + [[False] * world["n"]]
                edits += 1
            elif kind == "remove":
                if world["n"] == 1:
                    raise ValueError("Empty domains are forbidden")
                world["n"] -= 1
                for p in ("P", "Q"):
                    world[p].pop()
                world["R"] = [row[:-1] for row in world["R"][:-1]]
                edits += 1
            elif kind == "hint":
                if hints == 3:
                    raise ValueError("Hint budget exceeded")
                hints += 1
                feedback = True
            else:
                checks += 1
                left, right = _verdict(mission, world)
                if left != right:
                    reward = 10 if first_success is None else -2
                    if first_success is None:
                        first_success = index
                else:
                    reward = -1
                feedback = True
        elif kind == "toggle":
            if (mission["kind"] != "unary" or set(action) != {"type", "p", "i"}
                    or action["p"] not in ("P", "Q") or type(action["i"]) is not int
                    or not 0 <= action["i"] < world["n"]):
                raise ValueError("Invalid unary toggle")
            world[action["p"]][action["i"]] = not world[action["p"]][action["i"]]
            edits += 1
        elif kind == "toggle_relation":
            if (mission["kind"] != "relation" or set(action) != {"type", "i", "j"}
                    or any(type(action[k]) is not int or not 0 <= action[k] < world["n"] for k in ("i", "j"))):
                raise ValueError("Invalid relation toggle")
            i, j = action["i"], action["j"]
            world["R"][i][j] = not world["R"][i][j]
            edits += 1
        else:
            raise ValueError("Unknown action")
        left, right = _verdict(mission, world)
        steps.append({"index": index, "action": deepcopy(action), "state_before": before,
                      "world": deepcopy(world), "domain_size": world["n"],
                      "source_true": left, "proposal_true": right, "counterexample": left != right,
                      "checker_feedback_before_action": feedback_before, "checker_feedback_exposed": feedback,
                      "received_checker_response": kind == "check", "assisted_before_action": hints_before > 0,
                      "assisted": hints > 0, "reward": reward})
    if checks == 0:
        raise ValueError("At least one checker request is required")
    minimum = _minimum(mission)
    left, right = _verdict(mission, world)
    verified = actions[-1]["type"] == "check" and left != right
    score = max(1, 120 - 20 * (world["n"] - minimum) - 2 * hints - max(0, checks - 1) * 2 - edits // 5) if verified else 0
    return {"format": "pcs-countermodel-independent-replay-v1", "version": VERSION, "mission_id": mission_id,
            "ruleset_sha256": RULESET_SHA256, "checker": "INDEPENDENT_PYTHON_FINITE_FOL",
            "lean_kernel_checked": False, "pcs_authoritative": False, "final_world": deepcopy(world),
            "final_verdict": {"left": left, "right": right, "counterexample": left != right},
            "minimum_domain_size": minimum, "steps": steps, "checks": checks, "hints": hints,
            "edits": edits, "solved": first_success is not None, "final_verified": verified, "score": score}


def check_countermodel_session_file(path):
    with Path(path).open("rb") as handle:
        raw = handle.read(32769)
    if len(raw) > 32768:
        raise ValueError("Search notebook exceeds 32 KiB")
    def reject_constant(_value):
        raise ValueError("Non-finite JSON constant")

    try:
        document = json.loads(raw, object_pairs_hook=_unique, parse_constant=reject_constant)
    except RecursionError as error:
        raise ValueError("JSON nesting exceeds parser limit") from error
    if isinstance(document, dict) and document.get("format") == "pcs-countermodel-local-trace-v1":
        if (set(document) != {"format", "scope", "version", "mission_id", "actions"}
                or document["scope"] != "unverified player-recorded action trace; replay on PCS Worker required"):
            raise ValueError("Unexpected local search notebook fields")
        document = {key: document[key] for key in ("version", "mission_id", "actions")}
    return replay_countermodel_session(document)


def replay_command(args):
    try:
        result = check_countermodel_session_file(args.input)
    except (ValueError, OSError, UnicodeError) as error:
        print(json.dumps({"error": str(error), "pcs_authoritative": False}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["final_verified"] else 1
