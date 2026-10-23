"""PRISM benchmark suite.

Workloads (all deterministic / seeded):
  random   — random instances, several sizes and seeds (held-out seeds 1000+ are
             only used for the final table, never for tuning)
  lesion   — pathway-lesion family with nuisance switches (designed to favour the
             core-guided sandwich)
  or       — regulator-activity (OR) family: negative control (large adversarial
             core; the sandwich cannot win)
  pointer  — adaptivity-gap family: adaptive vs nonadaptive optimum

Methods:
  dp_naive   memoized Bellman DP, all informative experiments, no pruning
  dp_pruned  memoized Bellman DP with exact branch pruning
  sandwich   core-guided optimality sandwich (+ independent check of its certificate)
  greedy     recursive one-step greedy (no optimality claim)
  nonadaptive exhaustive best nonadaptive design (k <= 14)

Every reported optimal value is cross-checked between methods; any disagreement
aborts the run.  Time is wall-clock (time.perf_counter) on the machine recorded in
the output; memory is the tracemalloc peak in a separate run.
"""
from __future__ import annotations

import csv
import json
import os
import platform
import sys
import time
import tracemalloc
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "python"))

from prism.core import INF, policy_size  # noqa: E402
from prism.generators import lesion_family, or_family, pointer_family, random_problem  # noqa: E402
from prism.reference import checker  # noqa: E402
from prism.search.baselines import best_nonadaptive, greedy_policy, worst_cost  # noqa: E402
from prism.search.bellman import Bellman, BudgetExceeded, NaiveBellman  # noqa: E402
from prism.search.sandwich import sandwich_certify  # noqa: E402

TIME_LIMIT = float(os.environ.get("PRISM_BENCH_TIME_LIMIT", "20"))


def fr(x):
    return None if x is None else str(x)


def run_dp(cls, P, K, eps, measure_mem=False):
    t0 = time.perf_counter()
    dp = cls(P, eps, time_limit=TIME_LIMIT)
    try:
        v = dp.value(K)
        status = "ok"
    except BudgetExceeded:
        v, status = None, "timeout"
    t = time.perf_counter() - t0
    mem = None
    if measure_mem and status == "ok":
        tracemalloc.start()
        cls(P, eps).value(K)
        mem = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    return {"status": status, "value": v, "time": t, "states": dp.expanded, "peak_mem": mem}


def run_sandwich(P, K, eps, measure_mem=False):
    t0 = time.perf_counter()
    res = sandwich_certify(P, K, eps, time_limit=TIME_LIMIT)
    t = time.perf_counter() - t0
    out = {"status": res["status"], "time": t, "rounds": res.get("rounds"),
           "core_size": res.get("core_size"), "states": res.get("dp_states")}
    if res["status"] == "optimal":
        cert = {"policy": res["policy"], "bound": res["value"], "core": res["core"],
                "adversary": list(res["adversary"].items())}
        t1 = time.perf_counter()
        checker.check_optimal(P, K, eps, cert)
        out["check_time"] = time.perf_counter() - t1
        out["value"] = res["value"]
        out["cert_policy_nodes"] = policy_size(res["policy"])
        out["cert_adversary_entries"] = len(res["adversary"])
    elif res["status"] == "impossible":
        t1 = time.perf_counter()
        checker.check_impossible(P, K, eps, *res["pair"])
        out["check_time"] = time.perf_counter() - t1
        out["value"] = "inf"
    else:
        out["lower"] = res.get("lower")
    if measure_mem and res["status"] in ("optimal", "impossible"):
        tracemalloc.start()
        sandwich_certify(P, K, eps)
        out["peak_mem"] = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    return out


def agree(rec):
    vals = set()
    for k in ("dp_naive", "dp_pruned", "sandwich"):
        r = rec.get(k, {})
        if r.get("status") in ("ok", "optimal", "impossible"):
            v = r.get("value")
            vals.add("inf" if v in (None, "inf") or v is INF else str(v))
    if len(vals) > 1:
        raise AssertionError(f"methods disagree: {rec}")


def bench_instance(family, params, P, eps, nonadaptive=True, mem=False):
    K = P.full
    rec = {"family": family, "params": params, "n_models": P.n, "n_experiments": P.k,
           "n_outcomes_max": max(len(o) for o in P.outcomes), "eps": str(eps)}
    rec["dp_naive"] = run_dp(NaiveBellman, P, K, eps, mem)
    rec["dp_pruned"] = run_dp(Bellman, P, K, eps, mem)
    rec["sandwich"] = run_sandwich(P, K, eps, mem)
    agree(rec)
    opt = rec["sandwich"].get("value") if rec["sandwich"]["status"] == "optimal" else (
        rec["dp_pruned"]["value"] if rec["dp_pruned"]["status"] == "ok" else None)
    t0 = time.perf_counter()
    g = greedy_policy(P, K, eps)
    rec["greedy"] = {"time": time.perf_counter() - t0,
                     "cost": None if g is None else worst_cost(P, g, K)}
    if opt is not None and opt != "inf" and opt is not INF and rec["greedy"]["cost"] is not None:
        rec["greedy"]["gap"] = rec["greedy"]["cost"] - opt
    if nonadaptive and P.k <= 14:
        t0 = time.perf_counter()
        c, T = best_nonadaptive(P, K, eps)
        rec["nonadaptive"] = {"time": time.perf_counter() - t0, "cost": c}
    return rec


def jsonable(o):
    if isinstance(o, dict):
        return {k: jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, Fraction):
        return str(o)
    return o


def main(quick=False):
    records = []
    machine = {"python": sys.version.split()[0], "platform": platform.platform(),
               "processor": platform.processor() or "unknown", "cpus": os.cpu_count(),
               "time_limit_s": TIME_LIMIT}
    # random workload: tuning seeds 0..99 (used during development), held-out 1000+
    sizes = [(8, 4, 2), (12, 5, 2), (16, 6, 3), (20, 6, 3), (24, 8, 3)] if not quick else [(8, 4, 2), (12, 5, 2)]
    seeds = range(1000, 1010) if not quick else range(1000, 1003)
    for (n, k, r) in sizes:
        for s in seeds:
            P = random_problem(s * 7919 + n, n, k, r, qmax=6, oracle_cost=2 * k)
            for eps in [Fraction(0), Fraction(1)]:
                records.append(bench_instance("random", {"n": n, "k": k, "r": r, "seed": s}, P, eps,
                                              mem=(s == seeds[0])))
    # lesion family
    lesion = [(8, k) for k in range(0, 9)] + [(16, k) for k in (0, 2, 4, 6, 8)] + [(32, k) for k in (0, 3, 6)]
    if quick:
        lesion = [(8, k) for k in range(0, 5)]
    for (n, k) in lesion:
        P = lesion_family(n, k)
        records.append(bench_instance("lesion", {"n": n, "k": k}, P, Fraction(0), nonadaptive=False,
                                      mem=True))
    # OR family (negative control)
    for n in (range(2, 12) if not quick else range(2, 7)):
        P = or_family(n)
        records.append(bench_instance("or", {"n": n}, P, Fraction(0), nonadaptive=(n <= 10), mem=True))
    # pointer family
    for n in (range(2, 6) if not quick else range(2, 4)):
        P = pointer_family(n)
        records.append(bench_instance("pointer", {"n": n}, P, Fraction(0), nonadaptive=True))
    out = {"machine": machine, "records": jsonable(records)}
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "benchmarks.json"), "w") as f:
        json.dump(out, f, indent=1)
    with open(os.path.join(ROOT, "results", "benchmarks.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["family", "params", "n_models", "k", "eps", "dp_naive_status", "dp_naive_time",
                    "dp_naive_states", "dp_pruned_status", "dp_pruned_time", "dp_pruned_states",
                    "sandwich_status", "sandwich_time", "sandwich_rounds", "core_size",
                    "sandwich_states", "check_time", "cert_policy_nodes", "cert_adversary_entries",
                    "value", "greedy_cost", "nonadaptive_cost", "dp_pruned_peak_mem", "sandwich_peak_mem"])
        for r in out["records"]:
            w.writerow([r["family"], json.dumps(r["params"]), r["n_models"], r["n_experiments"], r["eps"],
                        r["dp_naive"]["status"], f"{r['dp_naive']['time']:.4f}", r["dp_naive"]["states"],
                        r["dp_pruned"]["status"], f"{r['dp_pruned']['time']:.4f}", r["dp_pruned"]["states"],
                        r["sandwich"]["status"], f"{r['sandwich']['time']:.4f}", r["sandwich"].get("rounds"),
                        r["sandwich"].get("core_size"), r["sandwich"].get("states"),
                        r["sandwich"].get("check_time"), r["sandwich"].get("cert_policy_nodes"),
                        r["sandwich"].get("cert_adversary_entries"), r["sandwich"].get("value"),
                        r["greedy"]["cost"], (r.get("nonadaptive") or {}).get("cost"),
                        r["dp_pruned"].get("peak_mem"), r["sandwich"].get("peak_mem")])
    return out


if __name__ == "__main__":
    main(quick="--quick" in sys.argv)
