"""Exhaustive differential tests: Bellman DP vs independent reference solvers vs
explicit policy enumeration vs the independent certificate checker, plus
certificate-tampering tests (false-acceptance search)."""
import os
import random
import sys
from fractions import Fraction

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from prism.core import INF, bits, simulate  # noqa: E402
from prism.generators import random_problem  # noqa: E402
from prism.reference import checker  # noqa: E402
from prism.reference.exhaustive import brute_force_value, reference_value  # noqa: E402
from prism.search.baselines import best_nonadaptive, greedy_policy, worst_cost  # noqa: E402
from prism.search.bellman import solve  # noqa: E402
from prism.search.sandwich import sandwich_certify  # noqa: E402


def run(n_instances=400, seed0=0, verbose=False):
    stats = {"instances": 0, "impossible": 0, "optimal": 0, "brute_checked": 0,
             "greedy_suboptimal": 0, "nonadaptive_gap": 0, "tamper_rejected": 0,
             "tamper_attempts": 0, "false_accepts": 0}
    rng = random.Random(1234)
    for i in range(n_instances):
        seed = seed0 + i
        n = 3 + seed % 6
        k = 2 + seed % 3
        r = 2 + seed % 2
        P = random_problem(seed, n, k, r)
        eps = Fraction(rng.choice([0, 0, 1, Fraction(1, 2)]))
        K = P.full
        v, pol, dp = solve(P, K, eps)
        ref = reference_value(P, range(P.n), eps)
        assert v == ref, (seed, v, ref)
        if n <= 5 and k <= 3:
            bf, _ = brute_force_value(P, range(P.n), eps)
            assert bf == v, (seed, bf, v)
            stats["brute_checked"] += 1
        stats["instances"] += 1
        res = sandwich_certify(P, K, eps)
        if v is INF:
            stats["impossible"] += 1
            assert res["status"] == "impossible"
            checker.check_impossible(P, K, eps, *res["pair"])
            continue
        stats["optimal"] += 1
        assert res["status"] == "optimal" and res["value"] == v, (seed, res, v)
        cert = {"policy": res["policy"], "bound": res["value"], "core": res["core"],
                "adversary": list(res["adversary"].items())}
        assert checker.check_optimal(P, K, eps, cert) == v
        # DP policy itself must check
        checker.check_policy(P, pol, K, eps, v)
        # greedy and nonadaptive baselines
        g = greedy_policy(P, K, eps)
        if g is not None:
            gc = worst_cost(P, g, K)
            assert gc >= v
            if gc > v:
                stats["greedy_suboptimal"] += 1
        na, _ = best_nonadaptive(P, K, eps)
        assert na is not INF and na >= v
        if na > v:
            stats["nonadaptive_gap"] += 1
        # ---- tampering: claim a strictly better bound; must be rejected
        if v > 0:
            for bad in [v - Fraction(1, 2), v - 1, Fraction(0)]:
                if bad < 0 or bad >= v:
                    continue
                stats["tamper_attempts"] += 1
                c2 = dict(cert, bound=bad)
                try:
                    checker.check_optimal(P, K, eps, c2)
                    stats["false_accepts"] += 1
                except checker.Reject:
                    stats["tamper_rejected"] += 1
            # inflate adversary values
            if cert["adversary"]:
                stats["tamper_attempts"] += 1
                adv2 = [(S, b + 1) for S, b in cert["adversary"]]
                c3 = dict(cert, bound=v + 1, adversary=adv2)
                try:
                    checker.check_optimal(P, K, eps, c3)
                    stats["false_accepts"] += 1
                except checker.Reject:
                    stats["tamper_rejected"] += 1
        # claim higher bound with honest policy: must be rejected (adversary too weak)
        stats["tamper_attempts"] += 1
        try:
            checker.check_optimal(P, K, eps, dict(cert, bound=v + 1))
            stats["false_accepts"] += 1
        except checker.Reject:
            stats["tamper_rejected"] += 1
        # core not inside K
        if P.n >= 2 and res["core"] != K:
            sub = K & ~(1 << next(iter(bits(res["core"]))))
            stats["tamper_attempts"] += 1
            try:
                checker.check_optimal(P, sub, eps, cert)
                # acceptable only if the claim is in fact true on sub
                if solve(P, sub, eps)[0] != v:
                    stats["false_accepts"] += 1
                else:
                    stats["tamper_rejected"] += 1
            except checker.Reject:
                stats["tamper_rejected"] += 1
    assert stats["false_accepts"] == 0, stats
    return stats


if __name__ == "__main__":
    print(run())
