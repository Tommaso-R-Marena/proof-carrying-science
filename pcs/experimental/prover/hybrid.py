"""A bounded, attributed portfolio; proposals never confer proof authority.

Std gets its three fixed whole-goal attempts first. Remaining action expansions
are split between structural retrieval and the frozen learned model. The two
action stages share only receiver-observed states in one fixed memory generation.
Every winning receipt is replayed in a new independent Lean environment.
"""
from copy import deepcopy
import time

from .environment import search
from .induction_ir import digest, theorem
from .memory_environment import structural_rank, replay_memory_receipt
from .memory_cost import MeasuredMemoryEnvironment, MeasuredInductionEnvironment

ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
STD_TACTICS = ("simp_all", "omega", "grind")


def std_search(env, goal):
    """Receiver-owned commands only; an exact independent final theorem audit."""
    statement = theorem(goal)
    start = time.monotonic()
    before = env.actual_calls
    attempts = []
    receipt = None
    for tactic in STD_TACTICS:
        proof = "  repeat intro\n  " + tactic
        try:
            kernel = env._source(f"theorem pcs_hybrid_result : {statement} := by\n{proof}\n#pcs_audit pcs_hybrid_result\n", "PCS_KERNEL:")
            if not set(kernel["axioms"]) <= ALLOWED_AXIOMS:
                raise RuntimeError("unapproved proof axioms")
            receipt = {"format": "pcs-std-baseline-proof-v1", "goal_sha256": digest(goal),
                       "statement": statement, "proof": proof, "kernel": kernel,
                       "lean": env.version, "pcs_scientific_authority": False}
            attempts.append({"tactic": tactic, "status": "verified"})
            break
        except RuntimeError as error:
            attempts.append({"tactic": tactic, "status": "failed", "error": str(error)[-1200:]})
    return {"status": "verified" if receipt else "unknown", "receipt": receipt,
            "attempts": attempts, "expansions": len(attempts),
            "cost": {"all_lean_calls": env.actual_calls - before,
                     "wall_seconds": time.monotonic() - start}}


def replay_std_receipt(goal, receipt, *, cache=None):
    if receipt.get("goal_sha256") != digest(goal) or receipt.get("statement") != theorem(goal):
        raise ValueError("changed immutable theorem")
    # Proof text is not arbitrary submitted code: regenerate from a fixed tactic.
    proof = receipt.get("proof")
    if proof not in {"  repeat intro\n  " + tactic for tactic in STD_TACTICS}:
        raise ValueError("unapproved Std proof")
    env = MeasuredInductionEnvironment(cache=cache, timeout=30)
    try:
        kernel = env._source(f"theorem pcs_hybrid_replay : {theorem(goal)} := by\n{proof}\n#pcs_audit pcs_hybrid_replay\n", "PCS_KERNEL:")
        if not set(kernel["axioms"]) <= ALLOWED_AXIOMS:
            raise ValueError("unapproved replay axioms")
        return {"status": "verified", "kernel": kernel, "all_lean_calls": env.actual_calls,
                "goal_sha256": digest(goal), "pcs_scientific_authority": False}
    finally:
        env.close()


def solve(goal, library, model, *, budget=48, cache=None, timeout=30):
    """Budget counts 3 whole-goal attempts plus actual action expansions.

    Whole-goal tactics can perform more internal work than a single proof action;
    physical Lean calls, cold construction and replay are reported separately.
    Cache is bounded and cleared after each immutable goal. No state is imported
    from a producer, a different theorem or a different library generation.
    """
    if type(budget) is not int or not 6 <= budget <= 96:
        raise ValueError("hybrid budget must be an integer in [6,96]")
    goal = deepcopy(goal)
    identity = digest(goal)
    start = time.monotonic()
    stages = []
    total_calls = 0
    std = MeasuredInductionEnvironment(cache=cache, timeout=timeout)
    try:
        result = std_search(std, goal)
        stages.append({"component": "ordinary_Std", "status": result["status"],
                       "expansions": result["expansions"], "cost": result["cost"]})
        total_calls += std.actual_calls
    finally:
        std.close()
    if result["status"] == "verified":
        independent = replay_std_receipt(goal, result["receipt"], cache=cache)
        total_calls += independent["all_lean_calls"]
        winner = "ordinary_Std"
        cache_records = 0
    else:
        remaining = budget - result["expansions"]
        env = MeasuredMemoryEnvironment(library, cache=cache, timeout=timeout)
        try:
            allocations = (("memory_structural", structural_rank, remaining // 2),
                           ("frozen_neural", model.rank, remaining - remaining // 2))
            for name, rank, allocation in allocations:
                before = env.actual_calls
                result = search(env, goal, rank, budget=allocation, depth=18, beam=4)
                stages.append({"component": name, "status": result["status"],
                               "expansions": result["expansions"],
                               "cost": {"all_lean_calls": env.actual_calls - before,
                                        "wall_seconds": result["wall_seconds"]}})
                if len(env.observations) > budget + 2:
                    raise RuntimeError("receiver cache exceeds bound")
                if result["status"] == "verified":
                    break
            cache_records = len(env.observations)
            total_calls += env.actual_calls
            winner = stages[-1]["component"] if result["status"] == "verified" else None
            independent = None
            if winner:
                replay_start = time.monotonic()
                fresh = replay_memory_receipt(goal, result["receipt"], cache=cache)
                independent = {"status": "verified", "kernel": fresh["kernel"],
                               "goal_sha256": identity,
                               "wall_seconds": time.monotonic() - replay_start,
                               "physical_calls": "not instrumented by legacy replay helper"}
            env.observations.clear()
        finally:
            env.close()
    if digest(goal) != identity:
        raise RuntimeError("goal mutation")
    expansions = sum(stage["expansions"] for stage in stages)
    if expansions > budget:
        raise RuntimeError("portfolio exceeded expansion budget")
    if result["receipt"] and result["receipt"]["goal_sha256"] != identity:
        raise RuntimeError("proof bound to wrong goal")
    return {"format": "pcs-attributed-hybrid-v1", "status": result["status"],
            "goal_sha256": identity, "receipt": result["receipt"], "independent_replay": independent,
            "winning_component": winner, "stages": stages, "expansions": expansions,
            "receiver_cache_records": cache_records, "budget": budget,
            "cost": {"measured_lean_calls_excluding_legacy_memory_replay": total_calls,
                     "cold_wall_seconds": time.monotonic() - start},
            "pcs_scientific_authority": False}
