"""Bounded inspectable obligation scheduler and checked research memory.

Plans are explicit proposals. Dependencies gate execution; every mathematical
result is independently proved. No autonomous novelty or literature claim.
"""
from __future__ import annotations

from copy import deepcopy
from .environment import search
from .ir import digest, theorem


def investigate(env, plan, rank=None, budget=96):
    if type(plan) is not dict or set(plan) != {"format", "nodes"} or plan["format"] != "pcs-research-plan-v1":
        raise ValueError("invalid research plan")
    nodes = deepcopy(plan["nodes"])
    if type(nodes) is not list or not 1 <= len(nodes) <= 16:
        raise ValueError("bounded plan required")
    by_id = {}
    for node in nodes:
        if set(node) != {"id", "goal", "depends_on"} or type(node["id"]) is not str or node["id"] in by_id:
            raise ValueError("invalid or duplicate plan node")
        theorem(node["goal"])
        if type(node["depends_on"]) is not list or any(type(d) is not str for d in node["depends_on"]):
            raise ValueError("invalid dependencies")
        by_id[node["id"]] = node
    order, visiting = [], set()
    def visit(name):
        if name not in by_id or name in visiting: raise ValueError("dangling or cyclic research dependency")
        if name in order: return
        visiting.add(name)
        for parent in by_id[name]["depends_on"]: visit(parent)
        visiting.remove(name); order.append(name)
    for name in by_id: visit(name)
    memory = {}
    for name in order:
        node = by_id[name]
        if any(memory[d]["status"] != "verified" for d in node["depends_on"]):
            memory[name] = {"status": "blocked_dependency", "receipt": None}
            continue
        memory[name] = search(env, node["goal"], rank, budget=budget, beam=4)
    return {"format": "pcs-research-memory-v1", "plan_sha256": digest(plan), "execution_order": order,
            "results": memory, "verified_results": sum(r["status"] == "verified" for r in memory.values()),
            "pcs_authority": False, "limitations": "Explicit dependency scheduling; no learned planning, automatic conjectures, literature search or certified reuse of preceding lemmas."}
