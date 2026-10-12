"""Ten fixed owner diagnostics, separate from rate-limited public submissions.

Every diagnostic really invokes Lean. These authored controls are operational
qualification, not a held-out capability benchmark or a self-improvement claim.
No submitted code, paid runner, production credential or automatic training.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import time

CASES = ("hybrid-natural", "hybrid-logic", "learned-chain", "human-actions",
         "counterexample", "ambiguous", "unsupported", "forged-proof",
         "goal-tampering", "budget-exhaustion")
ROOT = Path(__file__).resolve().parents[3]
NATURAL = "For all natural numbers n, (n + 0) equals n."
LOGIC = "For all propositions U and V, if (U and V) then (V and U)."
CHAIN = "For all propositions U and V, if (U and V) then (U and (U and V))."
FALSE = "For all natural numbers n, (n + 1) equals n."


def run(case):
    if case not in CASES:
        raise ValueError("fixed owner diagnostic required")
    from .hybrid_cli import run as hybrid_run
    from .hybrid import replay_std_receipt, std_search
    from .induction_language import formalize
    from .induction_ir import digest
    from .memory_cli import run as memory_run
    from .memory_environment import replay_memory_receipt, structural_rank
    from .memory_cost import MeasuredInductionEnvironment, MeasuredMemoryEnvironment
    from .memory_falsify import falsify, check_witness
    from .environment import search

    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.monotonic()
    preflight = MeasuredInductionEnvironment(timeout=30)
    try:
        kernel = preflight._source("theorem pcs_qualification_preflight : True := by\n  trivial\n#pcs_audit pcs_qualification_preflight\n", "PCS_KERNEL:")
        assert not kernel["axioms"]
        lean_version = preflight.version
        if case in {"forged-proof", "goal-tampering"}:
            goal = formalize(NATURAL)["candidates"][0]["ir"]
            result = std_search(preflight, goal)
            assert result["status"] == "verified"
            receipt = deepcopy(result["receipt"])
            if case == "forged-proof":
                receipt["proof"] = "sorry"
            else:
                goal = formalize(FALSE)["candidates"][0]["ir"]
            try:
                replay_std_receipt(goal, receipt)
            except ValueError:
                outcome = {"status": "rejected", "reason": "untrusted proof or immutable goal mismatch", "proof_accepted": False}
            else:
                raise AssertionError("adversarial receipt accepted")
        elif case in {"counterexample", "budget-exhaustion"}:
            env = MeasuredMemoryEnvironment(None, timeout=30)
            try:
                goal = formalize(FALSE if case == "counterexample" else LOGIC)["candidates"][0]["ir"]
                if case == "counterexample":
                    outcome = falsify(env, goal, limit=32)
                    assert outcome["status"] == "verified_counterexample"
                    fresh = MeasuredMemoryEnvironment(None, timeout=30)
                    try:
                        replay = check_witness(fresh, goal, outcome["receipt"]["witness"])
                        assert replay["original_goal_sha256"] == digest(goal)
                        outcome["independent_replay"] = replay
                    finally:
                        fresh.close()
                else:
                    outcome = search(env, goal, structural_rank, budget=1, depth=18, beam=4)
                    assert outcome["status"] == "unknown" and outcome["expansions"] <= 1 and outcome["receipt"] is None
                    outcome["boundary"] = "One expansion exhausted; no proof, timeout or universal impossibility claim."
            finally:
                env.close()
        elif case in {"learned-chain", "human-actions"}:
            actions = None
            if case == "human-actions":
                actions = [{"kind": "intro", "argument": "h0"}, {"kind": "intro", "argument": "h1"},
                           {"kind": "intro", "argument": "h2"}, {"kind": "constructor", "argument": None},
                           {"kind": "exact", "argument": "h2.2"}, {"kind": "exact", "argument": "h2.1"}]
            outcome = memory_run(CHAIN if actions is None else LOGIC, ROOT / "research/verified-memory-v1",
                                 budget=48, policy="learned" if actions is None else "exact_actions", actions=actions,
                                 feedback=False)
            assert outcome["status"] == "verified"
            goal = outcome["formalization"]["candidates"][0]["ir"]
            replay = replay_memory_receipt(goal, outcome["search"]["receipt"])
            outcome["independent_replay"] = {"status": "verified", "kernel": replay["kernel"], "goal_sha256": digest(goal)}
        else:
            statement = {"hybrid-natural": NATURAL, "hybrid-logic": LOGIC,
                         "ambiguous": "For all propositions P, Q and R, P and Q or R.",
                         "unsupported": "Prove the Riemann hypothesis."}[case]
            outcome = hybrid_run(statement, ROOT / "research/verified-memory-v1", budget=48)
            expected = {"ambiguous": "ambiguous_interpretation", "unsupported": "unsupported_formalization"}.get(case, "verified")
            assert outcome["status"] == expected
    finally:
        preflight.close()
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    source = hashlib.sha256()
    for raw in sorted(p for p in tracked if p):
        path = ROOT / raw.decode()
        source.update(raw + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return {"format": "pcs-hosted-owner-qualification-v1", "case": case,
            "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "tracked_source_sha256": source.hexdigest(), "lean_version": lean_version,
            "preflight_kernel": kernel, "outcome": outcome,
            "resources": {"wall_seconds": time.monotonic() - start,
                          "child_user_cpu_seconds": after.ru_utime - before.ru_utime,
                          "child_system_cpu_seconds": after.ru_stime - before.ru_stime,
                          "cumulative_largest_child_rss_kib": after.ru_maxrss},
            "public_worker_admissions_exercised": 0, "financial_spend": 0,
            "capability_benchmark": False, "automatic_training": False, "pcs_authority": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=CASES)
    args = parser.parse_args()
    print("PCS_OWNER_QUALIFICATION_V1:" + json.dumps(run(args.case), separators=(",", ":")))
