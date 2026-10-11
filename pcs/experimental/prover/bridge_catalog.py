"""Build a playable finite forest from actual Lean transitions and final proofs.

The public browser replays this artifact. It does not run Lean. An exact human
path can also be freshly checked by the protected public workflow/local backend.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from .environment import LeanEnvironment, search, _symbolic_priority,reference_expression
from .induction_environment import InductionEnvironment
from .induction_ir import digest,expression
from .discovery import decode,type_of
from .induction_language import formalize
from .induction_corpus import tasks

VERSION = "pcs-bridge-builder-v1"


def compact(state):
    return {"goals": [{"target": g["target"], "locals": [{"name": l["name"], "type": l["type"]} for l in g["locals"]]} for g in state["goals"]]}


def build(output):
    output = Path(output); output.mkdir(exist_ok=True, parents=True)
    env = InductionEnvironment(timeout=30)
    authored = [
        ("tutorial", "First bridge", "Carry a fact through two rules.", "For all propositions A, B and C, if ((A implies B) and (B implies C)) then (A implies C)."),
        ("cargo", "Cargo exchange", "Unpack two facts and deliver them in the opposite order.", "For all propositions A and B, if (A and B) then (B and A)."),
        ("length", "Endless railway", "Prove a rule for every finite train using a shorter train.", tasks()[0]["original_statement"]),
        ("association", "Junction engineer", "Show that changing the junctions keeps the same carriages.", tasks()[1]["original_statement"]),
    ]
    catalog = {"format": "pcs-bridge-catalog-v1", "version": VERSION,
        "core_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "adapter_sha256": env.source_sha, "lean": env.version, "missions": [],
        "boundary": "Archived real Lean transitions and proofs. Browser/Worker graph replay is not a fresh kernel invocation. Fresh checks use the exact path in protected CI.",
        "pcs_authority": False}
    try:
        for identity, title, description, statement in authored:
            goal = formalize(statement)["candidates"][0]["ir"]
            result = search(env, goal, budget=192, beam=4)
            if result["status"] != "verified": raise RuntimeError("cannot build checked game "+identity)
            primary = result["receipt"]["actions"]
            paths = [primary]
            for i in range(len(primary)):
                state = env.observe(goal, primary[:i])["states"][-1]
                options = sorted(env.candidates(state), key=lambda a: -_symbolic_priority(state,a))
                for alternative in options[:5]:
                    if alternative == primary[i]: continue
                    path = primary[:i]+[alternative]+primary[i+1:]
                    try:
                        observation = env.observe(goal,path)
                        if observation["status"] == "closed":
                            env.verify(goal,path); paths.append(path); break
                    except RuntimeError: continue
            nodes, receipts = {}, []
            def add_path(path):
                for i in range(len(path)+1):
                    prefix = path[:i]; key = digest(prefix)[:24]
                    observed = env.observe(goal,prefix)
                    if key not in nodes:
                        nodes[key] = {"id": key, "path": prefix, "state": compact(observed["states"][-1]),
                                      "state_sha256": digest(observed["states"][-1]), "edges": []}
                    if i < len(path):
                        edge = {"action": path[i], "status": "closed" if i+1 == len(path) else "open", "next": digest(path[:i+1])[:24], "error": ""}
                        if edge not in nodes[key]["edges"]: nodes[key]["edges"].append(edge)
                receipt = env.verify(goal,path); receipts.append(receipt)
                nodes[digest(path)[:24]]["receipt_index"] = len(receipts)-1
            for path in paths: add_path(path)
            # Real rejected attempts create meaningful negative examples. Valid
            # unexplored actions are not mislabeled invalid or shown as failures.
            for node in list(nodes.values()):
                if not node["state"]["goals"]: continue
                state = env.observe(goal,node["path"])["states"][-1]
                for action in env.candidates(state)[:8]:
                    if any(e["action"] == action for e in node["edges"]): continue
                    try: observed = env.observe(goal,node["path"]+[action])
                    except RuntimeError: continue
                    if observed["status"] == "invalid":
                        node["edges"].append({"action": action, "status": "invalid", "next": None, "error": observed["error"][:1000]}); break
            # Projection cards display their actual selected kernel premise.
            for node in nodes.values():
                state=env.observe(goal,node["path"])["states"][-1]
                if not state["goals"]:continue
                mapping={l["id"]:l["name"] for l in state["goals"][0]["locals"]}
                variables={}
                for local in state["goals"][0]["locals"]:
                    try:variables[local["name"]]=type_of(local["expression"])
                    except ValueError:pass
                for edge in node["edges"]:
                    argument=edge["action"]["argument"]
                    if type(argument) is str:
                        premise=reference_expression(state,argument)
                        if premise:
                            try:edge["premise"]=expression(decode(premise,mapping),variables)[1]
                            except (ValueError,KeyError):pass
            initial_actions = []
            for action in primary[:len(goal["binders"])]:
                if action["kind"] != "intro": break
                initial_actions.append(action)
            start = digest(initial_actions)[:24]
            mission = {"id": identity, "title": title, "description": description, "statement": statement,
                "goal": goal, "goal_sha256": digest(goal), "start": start,
                "automatic_setup_actions": initial_actions, "nodes": nodes, "receipts": receipts,
                "license": "Apache-2.0", "training_split": "public_train"}
            catalog["missions"].append(mission)
            print(identity,len(nodes),len(receipts),flush=True)
        catalog["content_sha256"] = digest(catalog)
        raw = json.dumps(catalog,ensure_ascii=False,sort_keys=True,separators=(",", ":"))
        (output/"bridge-builder-catalog.json").write_text(raw+"\n")
        (output/"bridge-builder-catalog.mjs").write_text("// Generated from actual Lean 4.28. Do not hand-edit; run bridge_catalog.\nexport default "+raw+";\n")
        return catalog
    finally: env.close()


def verify(catalog):
    expected = {k:v for k,v in catalog.items() if k != "content_sha256"}
    if digest(expected) != catalog["content_sha256"]: raise ValueError("catalog identity changed")
    env = LeanEnvironment(timeout=30)
    checks = 0
    try:
        for mission in catalog["missions"]:
            if digest(mission["goal"]) != mission["goal_sha256"]: raise ValueError("goal changed")
            for node in mission["nodes"].values():
                state = env.observe(mission["goal"],node["path"])["states"][-1]
                if digest(state) != node["state_sha256"] or compact(state) != node["state"]:
                    raise ValueError("state differs from actual Lean")
                for edge in node["edges"]:
                    observed = env.observe(mission["goal"],node["path"]+[edge["action"]])
                    if observed["status"] != edge["status"]: raise ValueError("forged transition")
                    if edge["next"] is not None and mission["nodes"][edge["next"]]["path"] != node["path"]+[edge["action"]]:
                        raise ValueError("edge changed proof path")
                    checks += 1
            for receipt in mission["receipts"]:
                fresh = env.verify(mission["goal"],receipt["actions"])
                if fresh != receipt: raise ValueError("forged final proof")
        return {"verified_transitions":checks,"kernel_proofs":sum(len(m["receipts"]) for m in catalog["missions"]),"lean":env.version}
    finally: env.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output");p.add_argument("--verify");a=p.parse_args()
    if a.verify: print(json.dumps(verify(json.loads(Path(a.verify).read_text()))))
    elif a.output: build(a.output)
    else: p.error("--output or --verify required")


if __name__ == "__main__": main()
