#!/usr/bin/env python3
"""Stand-alone certificate verifier (does not import the search engine).

    python3 python/verify.py PROBLEM.json CERT.json          # Python checker
    python3 python/verify.py PROBLEM.json CERT.json --lean   # + Lean kernel re-check

The problem file is parsed and validated (schema prism-problem/1); the version
space K(D, A) is recomputed from the declared assumptions and data; the
certificate (schema prism-certificate/1) must be bound to the problem's canonical
SHA-256.  The checker then re-derives every claim:
  * the policy succeeds on every model of K at the declared tolerance,
  * every path costs at most the claimed bound,
  * the adversary table is locally consistent (Lean: IsAdversary) and certifies
    value(core) >= bound, with core ⊆ K,
so the bound is the exact minimax optimal cost (Lean: checkOptimal_sound).
With --lean the same certificate is emitted as a Lean module and checked by the
Lean kernel (`decide +kernel` on the proved checker), requiring `lake`.
Exit code 0 = ACCEPT, 1 = REJECT, 2 = usage / malformed input.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

from prism import serialize  # noqa: E402
from prism.reference import checker  # noqa: E402


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        return 2
    try:
        spec = serialize.load_problem(args[0])
        with open(args[1], "rb") as f:
            cert = serialize.parse_optimal_cert(spec, serialize.loads(f.read()))
    except (serialize.SchemaError, OSError) as ex:
        print(f"REJECT (malformed input): {ex}")
        return 2
    K = spec.version_space()
    if K == 0:
        print("REJECT: the version space is empty (INCONSISTENT); no optimality claim is meaningful")
        return 1
    try:
        v = checker.check_optimal(spec.P, K, spec.eps, cert)
    except checker.Reject as ex:
        print(f"REJECT: {ex}")
        return 1
    print(f"ACCEPT (Python checker): exact minimax optimal cost {v} at tolerance {spec.eps} "
          f"over {bin(K).count('1')} admissible models")
    if "--lean" in argv:
        from prism.lean_export import export
        src = export(spec.P, "Verify", eps=spec.eps, K_mask=K,
                     assumption_mask=None if not spec.assumptions else
                     __import__("functools").reduce(lambda a, b: a & b,
                                                    [a["mask"] for a in spec.assumptions]),
                     data=spec.data, problem_hash=spec.hash,
                     optimal={"policy": cert["policy"], "bound": cert["bound"], "core": cert["core"],
                              "adversary": cert["adversary"]})
        with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False) as f:
            f.write(src)
            path = f.name
        try:
            r = subprocess.run(["lake", "env", "lean", path], cwd=ROOT, capture_output=True, text=True)
        finally:
            os.unlink(path)
        if r.returncode != 0:
            print("REJECT (Lean kernel):\n" + (r.stdout + r.stderr)[-2000:])
            return 1
        print("ACCEPT (Lean kernel): checkOptimal = true, hence by checkOptimal_sound the policy "
              "succeeds, its worst-case cost equals the bound, no successful policy is cheaper, "
              "and value = bound")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
