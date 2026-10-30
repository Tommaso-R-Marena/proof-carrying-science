"""Agreement between the Python checker and the Lean kernel checker.

For a handful of small random instances:
  * the honest certificate (exact optimality or two-model impossibility) is exported
    to Lean and must compile (the Lean kernel re-runs `checkOptimal` /
    `checkImpossible` via `decide +kernel`);
  * a tampered certificate (understated optimal cost, or a distinguishable
    impossibility pair) is rejected by the Python checker AND fails to compile in Lean.

Requires `lake` and a built PRISM library (`lake build PRISM`).  Each Lean run takes
a few seconds; set PRISM_LEAN_AGREEMENT_N to change the number of instances.
"""
import os
import subprocess
import sys
import tempfile
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "python"))

from prism.generators import random_problem  # noqa: E402
from prism.lean_export import export  # noqa: E402
from prism.reference import checker  # noqa: E402
from prism.search.sandwich import sandwich_certify  # noqa: E402


def lean_accepts(src: str) -> bool:
    with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False) as f:
        f.write(src)
        path = f.name
    try:
        r = subprocess.run(["lake", "env", "lean", path], cwd=ROOT, capture_output=True,
                           text=True, timeout=600)
        return r.returncode == 0
    finally:
        os.unlink(path)


def run(n_instances=None):
    n_instances = n_instances or int(os.environ.get("PRISM_LEAN_AGREEMENT_N", "6"))
    stats = {"honest_accepted": 0, "tampered_rejected": 0, "disagreements": 0}
    seed = 0
    done = 0
    while done < n_instances:
        seed += 1
        P = random_problem(seed, 4 + seed % 3, 3, 2, qmax=4)
        eps = Fraction(0)
        res = sandwich_certify(P, P.full, eps)
        name = f"Agree{seed}"
        if res["status"] == "optimal":
            v = res["value"]
            if v == 0:
                continue
            cert = {"policy": res["policy"], "bound": v, "core": res["core"],
                    "adversary": list(res["adversary"].items())}
            checker.check_optimal(P, P.full, eps, cert)
            ok = lean_accepts(export(P, name, eps=eps, optimal=cert))
            bad = dict(cert, bound=v - 1)
            try:
                checker.check_optimal(P, P.full, eps, bad)
                py_bad = True
            except checker.Reject:
                py_bad = False
            lean_bad = lean_accepts(export(P, name + "T", eps=eps, optimal=bad))
        elif res["status"] == "impossible":
            m1, m2 = res["pair"]
            checker.check_impossible(P, P.full, eps, m1, m2)
            ok = lean_accepts(export(P, name, eps=eps, impossible=(m1, m2)))
            # tamper: a pair that is distinguishable (exists since n >= 2 random rows differ)
            pair = next(((a, b) for a in range(P.n) for b in range(P.n)
                         if P.obs[a] != P.obs[b] and P.q[a] - P.q[b] > eps), None)
            if pair is None:
                continue
            try:
                checker.check_impossible(P, P.full, eps, *pair)
                py_bad = True
            except checker.Reject:
                py_bad = False
            lean_bad = lean_accepts(export(P, name + "T", eps=eps, impossible=pair))
        else:
            continue
        done += 1
        stats["honest_accepted"] += int(ok)
        stats["tampered_rejected"] += int(not lean_bad)
        if not ok or py_bad != lean_bad or lean_bad:
            stats["disagreements"] += 1
        print(f"seed {seed}: {res['status']}: honest Lean={'accept' if ok else 'REJECT'}, "
              f"tampered Python={'ACCEPT' if py_bad else 'reject'} Lean={'ACCEPT' if lean_bad else 'reject'}")
    assert stats["disagreements"] == 0, stats
    return stats


if __name__ == "__main__":
    print(run())
