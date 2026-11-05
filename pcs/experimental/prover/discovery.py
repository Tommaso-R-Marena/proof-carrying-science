"""Bounded abstraction proposals from actual structured Lean proof states.

The decoder is untrusted: every lifted claim is re-elaborated and independently
proved before admission. No proof state, score or producer flag is a certificate.
"""
from __future__ import annotations

from copy import deepcopy

from .induction_ir import TYPES, UNARY, binary, var, theorem, expression, digest
from .data import structural_fingerprint
from .environment import search
from .library import FORMAT, validate_library


def spine(e):
    args = []
    while e["kind"] == "application":
        args.insert(0, e["children"][1]); e = e["children"][0]
    return e, args


def type_of(e):
    head, args = spine(e)
    if e["kind"] == "sort" and e["value"] == "0": return "Prop"
    name = head["value"].split(":")[0] if head["kind"] == "constant" else ""
    if name in {"Nat", "Int"} and not args: return name
    if name == "List" and len(args) == 1 and type_of(args[0]) == "Nat": return "NatList"
    if e["kind"] == "forall" and type_of(e["children"][0]) == "Nat":
        result = type_of(e["children"][1])
        if result in {"Nat", "Prop"}: return "NatFn" if result == "Nat" else "NatPred"
    raise ValueError("unsupported kernel type")


def decode(e, locals_, bound=(), depth=0):
    if depth > 12: raise ValueError("kernel expression exceeds fragment depth")
    kind = e["kind"]
    if kind == "local" and e["value"] in locals_: return var(locals_[e["value"]])
    if kind == "bound" and int(e["value"]) < len(bound): return var(bound[-1-int(e["value"])])
    if kind == "natural": return {"op": "number", "value": int(e["value"]), "type": "Nat"}
    if kind == "forall":
        domain, body = e["children"]
        try: t = type_of(domain)
        except ValueError:
            # An implication binder is a proof, not a mathematical variable.
            return binary("implies", decode(domain, locals_, bound, depth+1),
                          decode(body, locals_, (*bound, "unsupportedProofBinder"), depth+1))
        n = "q" + str(depth)
        return {"op": "forall", "name": n, "type": t,
                "body": decode(body, locals_, (*bound, n), depth+1)}
    head, args = spine(e)
    name = head["value"].split(":")[0] if head["kind"] == "constant" else ""
    dec = lambda x: decode(x, locals_, bound, depth+1)
    if kind == "constant" and name in {"True", "False"}: return {"op": name.lower()}
    if name in {"And", "Or", "Iff"} and len(args) == 2:
        return binary({"And": "and", "Or": "or", "Iff": "iff"}[name], dec(args[0]), dec(args[1]))
    if name == "Not" and len(args) == 1: return {"op": "not", "arg": dec(args[0])}
    if name == "Eq" and len(args) == 3: return binary("eq", dec(args[1]), dec(args[2]))
    if name == "Ne" and len(args) == 3: return {"op":"not","arg":binary("eq",dec(args[1]),dec(args[2]))}
    if name in {"HAdd.hAdd", "HMul.hMul", "HAppend.hAppend", "LE.le"} and len(args) >= 3:
        return binary({"HAdd.hAdd": "add", "HMul.hMul": "mul", "HAppend.hAppend": "append", "LE.le": "le"}[name], dec(args[-2]), dec(args[-1]))
    if name in {"Nat.add", "Nat.mul", "Nat.le", "List.append"} and len(args) >= 2:
        return binary({"Nat.add": "add", "Nat.mul": "mul", "Nat.le": "le", "List.append": "append"}[name], dec(args[-2]), dec(args[-1]))
    if name == "OfNat.ofNat" and len(args) == 3 and args[1]["kind"] == "natural":
        return {"op": "number", "value": int(args[1]["value"]), "type": type_of(args[0])}
    for op, (_, _, constant) in UNARY.items():
        if name == constant and args: return {"op": op, "arg": dec(args[-1])}
    if name == "List.nil": return {"op": "nil"}
    if name == "List.cons" and len(args) == 3: return {"op": "cons", "head": dec(args[-2]), "tail": dec(args[-1])}
    if head["kind"] in {"local", "bound"} and len(args) == 1:
        return {"op": "apply", "fn": dec(head), "arg": dec(args[0])}
    raise ValueError("unsupported kernel expression")


def lift_state(state, *, assumptions=True):
    """Close the first goal over its context, using kernel nodes, not pretty text."""
    if not state.get("goals"): raise ValueError("no open goal")
    g = state["goals"][0]
    mapping, binders, premises = {}, [], []
    for local in g["locals"]:
        try: t = type_of(local["expression"])
        except ValueError:
            if assumptions: premises.append(decode(local["expression"], mapping))
            continue
        n = "v" + str(len(binders)); mapping[local["id"]] = n
        binders.append({"name": n, "type": t})
    body = decode(g["expression"], mapping)
    for premise in reversed(premises): body = binary("implies", premise, body)
    used = set()
    def names(e):
        if e.get("op") == "var": used.add(e["name"])
        for v in e.values():
            if isinstance(v, dict): names(v)
    names(body)
    while body["op"] == "forall":
        binders.append({"name": body["name"], "type": body["type"]}); body = body["body"]
    result = {"format": "pcs-math-ir-v1", "binders": [b for b in binders if b["name"] in used], "body": body}
    theorem(result)
    return result


def _propose(trajectories, *, maximum=24):
    """Harvest actual open states, plus cuts of their conjunction/implication IR.

    Removing assumptions proposes stronger claims; their truth is NOT assumed.
    A candidate may fail. This is bounded lemma mining, not novel mathematics.
    """
    if not 1 <= maximum <= 64: raise ValueError("invalid discovery bound")
    result, seen = [], set()
    training_goals = {structural_fingerprint(t["goal"]) for t in trajectories}
    for record in trajectories:
        if record.get("split") != "train" or record.get("license") != "Apache-2.0":
            raise ValueError("discovery accepts licensed training trajectories only")
        states = record["result"].get("states", [])
        if not states:
            states = [a["state"] for a in record["result"].get("attempts", []) if "state" in a]
        for index, state in enumerate(states):
            for assumptions in [False, True]:
                try: candidate = lift_state(state, assumptions=assumptions)
                except (ValueError, KeyError, IndexError): continue
                cuts = [candidate]
                def visit(body):
                    if body["op"] in {"and", "implies"}:
                        for side in ["left", "right"]:
                            cuts.append({**deepcopy(candidate), "body": deepcopy(body[side])})
                            visit(body[side])
                visit(candidate["body"])
                for goal in cuts:
                    try: identity = structural_fingerprint(goal)
                    except ValueError: continue
                    if identity in seen: continue
                    seen.add(identity)
                    result.append({"goal": goal, "source_task": record["id"], "source_family": record["family"],
                                   "source_state_index": index, "source_state_sha256": digest(state),
                                   "assumptions_retained": assumptions, "candidate_sha256": identity})
                    result[-1]["whole_training_goal"] = identity in training_goals
                    if len(result) >= maximum: return result
    return result


def propose(trajectories, *, maximum=24):
    """Round-robin tasks, so one long proof cannot consume the mining budget."""
    if not 1 <= maximum <= 64: raise ValueError("invalid discovery bound")
    pools = [_propose([t], maximum=maximum) for t in trajectories]
    result, seen = [], set()
    for index in range(maximum):
        for pool in pools:
            if index >= len(pool): continue
            candidate = pool[index]
            if candidate["candidate_sha256"] in seen: continue
            seen.add(candidate["candidate_sha256"]); result.append(candidate)
            if len(result) >= maximum: return result
    return result


def discover(env, training, *, heldout=(), candidate_limit=24, budget=96, source_revision):
    forbidden = {structural_fingerprint(t["goal"]) for t in heldout}
    families = {t["family"] for t in heldout}
    if any(t["family"] in families or structural_fingerprint(t["goal"]) in forbidden for t in training):
        raise ValueError("training/evaluation firewall violation")
    candidates = propose(training, maximum=candidate_limit)
    library, audit, successful = {"format": FORMAT, "entries": []}, [], []
    for candidate in candidates:
        if candidate["candidate_sha256"] in forbidden:
            audit.append({**candidate, "status": "excluded_holdout", "expansions": 0}); continue
        start_calls, start_seconds = env.invocations, env.seconds
        result = search(env, candidate["goal"], budget=budget, beam=4)
        audit.append({**candidate, "status": result["status"], "expansions": result["expansions"],
                      "lean_invocations": env.invocations-start_calls, "lean_seconds": env.seconds-start_seconds,
                      "receipt": result["receipt"]})
        if result["status"] == "verified" and len(library["entries"]) < 8:
            # A fresh compiler audit is mandatory even after search's own check.
            receipt = env.verify(candidate["goal"], result["receipt"]["actions"])
            library["entries"].append({"goal": candidate["goal"], "actions": receipt["actions"],
                                       "license": "Apache-2.0", "source_revision": source_revision})
            successful.append({"id": candidate["candidate_sha256"], "family": candidate["source_family"],
                               "split": "train", "goal": candidate["goal"], "result": result})
    return validate_library(library, heldout), audit, successful
