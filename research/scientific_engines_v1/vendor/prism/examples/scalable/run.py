"""Demonstration C: scalable parameterized families.

1. Lesion localisation with nuisance switches (lesion_family(n, k), |M| = n·2^k).
   Same wall-clock budget for: memoised naive Bellman DP, pruned Bellman DP, and the
   core-guided optimality sandwich.  Every sandwich certificate is re-checked by the
   independent checker against the FULL explicit model space.
2. OR / regulator-activity family (negative control): the adversarial core has n+1
   models, so the sandwich cannot be small; the exact value n is proved for every n
   in Lean (PRISM.Examples.Families.or_value).
3. Pointer family: adaptive optimum 2 versus nonadaptive optimum n+1 (Lean:
   ptr_adaptive / ptr_nonadaptive).

Output: results/demo_scalable.txt
"""
import os
import sys
import time
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "python"))

from prism.core import policy_size  # noqa: E402
from prism.generators import lesion_family, or_family, pointer_family  # noqa: E402
from prism.reference import checker  # noqa: E402
from prism.search.baselines import best_nonadaptive  # noqa: E402
from prism.search.bellman import Bellman, BudgetExceeded, NaiveBellman  # noqa: E402
from prism.search.sandwich import sandwich_certify  # noqa: E402

BUDGET = float(os.environ.get("PRISM_DEMO_BUDGET", "10"))


def timed_dp(cls, P):
    t0 = time.perf_counter()
    try:
        v = cls(P, Fraction(0), time_limit=BUDGET).value(P.full)
        return f"{v} in {time.perf_counter()-t0:.3f}s"
    except BudgetExceeded:
        return f"TIMEOUT (> {BUDGET}s)"


def main():
    out = []
    w = out.append
    w(f"Demonstration C — scalable families (per-method wall-clock budget {BUDGET}s)\n")
    w("== Lesion family: n pathway steps, k nuisance switches, |M| = n*2^k, eps = 0 ==")
    w(f"{'n':>3} {'k':>3} {'|M|':>7} | {'naive DP':>22} | {'pruned DP':>22} | sandwich (value, time, core, check)")
    for (n, k) in [(8, 4), (8, 8), (8, 10), (8, 12), (8, 14), (16, 8), (16, 10), (32, 8), (64, 6)]:
        P = lesion_family(n, k)
        a = timed_dp(NaiveBellman, P)
        b = timed_dp(Bellman, P)
        t0 = time.perf_counter()
        res = sandwich_certify(P, P.full, Fraction(0), time_limit=BUDGET)
        ts = time.perf_counter() - t0
        if res["status"] == "optimal":
            cert = {"policy": res["policy"], "bound": res["value"], "core": res["core"],
                    "adversary": list(res["adversary"].items())}
            t1 = time.perf_counter()
            checker.check_optimal(P, P.full, Fraction(0), cert)
            tc = time.perf_counter() - t1
            s = (f"{res['value']} in {ts:.3f}s, core {res['core_size']}, policy nodes "
                 f"{policy_size(res['policy'])}, independent check ACCEPT in {tc:.3f}s")
        else:
            s = f"{res['status']} after {ts:.3f}s (lower={res.get('lower')}, upper={res.get('upper')})"
        w(f"{n:>3} {k:>3} {P.n:>7} | {a:>22} | {b:>22} | {s}")
    w("\nInterpretation: the optimal cost is ceil(log2 n) (binary search on the probes);")
    w("the nuisance switches are irrelevant.  The sandwich solves the Bellman DP only on a")
    w("core of n models and validates the candidate policy on all n*2^k models.  The full")
    w("explicit model list is still materialised (no symbolic representation), so the")
    w("method remains linear in |M|; the gain is avoiding DP over subsets of the full space.\n")

    w("== OR family (negative control): n regulators, |M| = 2^n, query = OR ==")
    for n in range(2, 11):
        P = or_family(n)
        t0 = time.perf_counter()
        res = sandwich_certify(P, P.full, Fraction(0), time_limit=BUDGET)
        ts = time.perf_counter() - t0
        b = timed_dp(Bellman, P)
        w(f"n={n:>2} |M|={P.n:>5}  pruned DP: {b:>22}   sandwich: {res['status']} "
          f"value={res.get('value')} core={res.get('core_size')} in {ts:.3f}s")
    w("Lean: PRISM.Examples.Families.or_value proves value = n for EVERY n, using an")
    w("(n+1)-model adversary core (orLB_isAdversary) instead of the 2^n-model space.\n")

    w("== Pointer family: adaptive vs nonadaptive ==")
    for n in range(2, 6):
        P = pointer_family(n)
        v = Bellman(P, Fraction(0)).value(P.full)
        c, _ = best_nonadaptive(P, P.full, Fraction(0))
        w(f"n={n}: adaptive optimum {v}, best nonadaptive {c}")
    w("Lean: ptr_adaptive (adaptive cost <= 2) and ptr_nonadaptive (>= n+1 for n >= 2).")
    text = "\n".join(out) + "\n"
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "demo_scalable.txt"), "w") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
