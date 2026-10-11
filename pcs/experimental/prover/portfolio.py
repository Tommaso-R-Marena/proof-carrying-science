"""Bounded learned reuse with a reserved symbolic-search fallback.

The allocation is fixed before new prospective evaluation: one quarter for
learned shortcuts, the remaining actual expansion budget for basic actions.
Both stages keep the same immutable theorem and independently verify success.
The fallback cannot use retrieved lemma actions. All work remains accounted.
"""
from copy import deepcopy

from .environment import candidates, search
from .ir import digest


class _BasicActionView:
    def __init__(self, env): self.env = env
    def __getattr__(self, name): return getattr(self.env, name)
    def candidates(self, state): return candidates(state)


def search_portfolio(env, goal, rank, *, budget=64, depth=18, beam=4):
    if type(budget) is not int or not 1 <= budget <= 4096:
        raise ValueError("invalid portfolio expansion budget")
    goal = deepcopy(goal)
    original = digest(goal)
    fast = search(env, goal, rank, budget=max(1, budget // 4), depth=depth, beam=beam)
    stages = [{"stage": "learned_reuse", "status": fast["status"], "expansions": fast["expansions"],
               "lean_invocations": fast["lean_invocations"], "wall_seconds": fast["wall_seconds"]}]
    result = fast
    attempts = [{**a, "stage": "learned_reuse"} for a in fast["attempts"]]
    remaining = budget - fast["expansions"]
    if fast["status"] != "verified" and remaining > 0:
        if digest(goal) != original: raise RuntimeError("immutable portfolio theorem changed")
        slow = search(_BasicActionView(env), goal, budget=remaining, depth=depth, beam=beam)
        stages.append({"stage": "symbolic_fallback", "status": slow["status"], "expansions": slow["expansions"],
                       "lean_invocations": slow["lean_invocations"], "wall_seconds": slow["wall_seconds"]})
        attempts += [{**a, "stage": "symbolic_fallback"} for a in slow["attempts"]]
        result = slow
    result["attempts"] = attempts
    result["expansions"] = sum(s["expansions"] for s in stages)
    result["lean_invocations"] = sum(s["lean_invocations"] for s in stages)
    result["wall_seconds"] = sum(s["wall_seconds"] for s in stages)
    result["portfolio"] = {"format": "pcs-reuse-portfolio-v1", "allocation": "one-quarter learned; remaining actual budget basic actions",
                           "budget": budget, "stages": stages, "selected_stage": stages[-1]["stage"]}
    if result["expansions"] > budget or digest(goal) != original:
        raise RuntimeError("portfolio budget or goal integrity violation")
    if result["receipt"] and result["receipt"]["goal_sha256"] != original:
        raise RuntimeError("portfolio receipt changed the theorem")
    return result
