"""Bounded inspectable obligation scheduler and checked research memory.

Plans are explicit proposals. Dependencies gate execution; every mathematical
result is independently proved. No autonomous novelty or literature claim.
"""
from __future__ import annotations

from copy import deepcopy
from .environment import search
from .ir import digest, theorem


def investigate(env, plan, rank=None, budget=96, *, reuse=False, source_revision=None, source_license=None):
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
    from .library import LICENSES
    if type(reuse) is not bool or (reuse and (type(source_revision) is not str or not source_revision or source_license not in LICENSES)):
        raise ValueError("explicit checked-reuse mode and source provenance required")
    memory = {}
    library = {"format": "pcs-checked-lemma-library-v1", "entries": []}
    library_ids, construction_calls, construction_seconds = [], 0, 0.0
    for name in order:
        node = by_id[name]
        if any(memory[d]["status"] != "verified" for d in node["depends_on"]):
            memory[name] = {"status": "blocked_dependency", "receipt": None}
            continue
        if not reuse or not library["entries"]:
            memory[name] = search(env, node["goal"], rank, budget=budget, beam=4)
        else:
            from .library import LibraryEnvironment
            reusable = LibraryEnvironment(library, cache=env.cache, timeout=env.timeout, max_steps=env.max_steps)
            try:
                from .library import reuse_priority
                memory[name] = search(reusable, node["goal"], rank or reuse_priority, budget=budget, beam=4)
                memory[name]["available_verified_nodes"] = list(library_ids)
                construction_calls += reusable.construction_invocations
                construction_seconds += reusable.construction_seconds
            finally:
                reusable.close()
        if reuse and memory[name]["status"] == "verified":
            from .data import structural_fingerprint
            if structural_fingerprint(node["goal"]) not in {structural_fingerprint(e["goal"]) for e in library["entries"]}:
                library["entries"].append({"goal": deepcopy(node["goal"]),
                    "actions": deepcopy(memory[name]["receipt"]["actions"]),
                    "license": source_license, "source_revision": source_revision})
                library_ids.append(name)
    return {"format": "pcs-research-memory-v1", "plan_sha256": digest(plan), "execution_order": order,
            "results": memory, "verified_results": sum(r["status"] == "verified" for r in memory.values()),
            "pcs_authority": False, "checked_reuse": reuse,
            "library": library if reuse else None,
            "library_construction_invocations": construction_calls,
            "library_construction_seconds": construction_seconds,
            "limitations": "Explicit dependency scheduling and optional kernel-checked preceding-lemma reuse; no learned planning, automatic conjectures or literature search."}
