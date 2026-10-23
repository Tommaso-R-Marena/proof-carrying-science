"""Adversarial parser / schema tests: every malformed input must be rejected
explicitly; canonical encoding must be invariant under key reordering."""
import copy
import json
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from prism.generators import random_problem  # noqa: E402
from prism.search.sandwich import sandwich_certify  # noqa: E402
from prism.serialize import (SchemaError, canonical_bytes, loads, optimal_cert_to_json,  # noqa: E402
                             parse_optimal_cert, parse_problem, problem_to_json, sha256, str_to_rat)
from prism.reference import checker  # noqa: E402


def expect_reject(fn, label, results):
    try:
        fn()
        results.append((label, "ACCEPTED (BUG)"))
    except SchemaError:
        results.append((label, "rejected"))
    except checker.Reject:
        results.append((label, "rejected"))


def run():
    results = []
    P = random_problem(7, 6, 3, 2, oracle_cost=5)
    raw = problem_to_json(P, "t", "q", data=[], eps=Fraction(0))
    spec = parse_problem(raw)
    # rationals
    for bad in ["1/1", "2/4", "-0", "01", "1/0", "1.5", "1e3", "", "1/-2", " 1", "0/5"]:
        expect_reject(lambda b=bad: str_to_rat(b), f"rational {bad!r}", results)
    assert str_to_rat("-3/4") == Fraction(-3, 4)
    # JSON-level
    expect_reject(lambda: loads(b'{"a":1,"a":2}'), "duplicate keys", results)
    expect_reject(lambda: loads(b'{"a":NaN}'), "NaN constant", results)
    expect_reject(lambda: loads(b'{"a":'), "truncated JSON", results)
    expect_reject(lambda: loads(b'\xff\xfe'), "non-UTF-8", results)

    def mutate(f, label):
        r = copy.deepcopy(raw)
        f(r)
        expect_reject(lambda: parse_problem(r), label, results)

    mutate(lambda r: r.update(schema="prism-problem/2"), "wrong schema version")
    mutate(lambda r: r.update(extra=1), "unknown top-level field")
    mutate(lambda r: r["experiments"][0].update(cost="-1"), "negative cost")
    mutate(lambda r: r["experiments"].append(copy.deepcopy(r["experiments"][0])), "duplicate experiment id")
    mutate(lambda r: r["models"].append(copy.deepcopy(r["models"][0])), "duplicate model id")
    mutate(lambda r: r["models"][0]["obs"].pop("e0"), "missing observation")
    mutate(lambda r: r["models"][0]["obs"].update(e0="zzz"), "undeclared outcome")
    mutate(lambda r: r["models"][0].update(q="1/1"), "non-canonical query")
    mutate(lambda r: r.update(models=[]), "empty model set")
    mutate(lambda r: r.update(tolerance="-1/2"), "negative tolerance")
    mutate(lambda r: r.update(data=[{"experiment": "nope", "outcome": "o0"}]), "datum unknown experiment")
    mutate(lambda r: r["models"][0].update(id="bad id with spaces"), "invalid identifier")
    mutate(lambda r: r["experiments"][0].update(outcomes=["o0", "o0"]), "duplicate outcome id")
    # canonical encoding invariance under reordering
    r2 = json.loads(json.dumps(raw), object_pairs_hook=lambda kv: dict(reversed(kv)))
    assert canonical_bytes(r2) == canonical_bytes(raw) and sha256(r2) == sha256(raw)
    results.append(("reordered keys: same canonical hash", "ok"))
    # certificate-level
    res = sandwich_certify(spec.P, spec.version_space(), spec.eps)
    cj = optimal_cert_to_json(spec, res)
    c = parse_optimal_cert(spec, cj)
    checker.check_optimal(spec.P, spec.version_space(), spec.eps, c)

    def cmut(f, label, check=False):
        j = copy.deepcopy(cj)
        f(j)
        if check:
            expect_reject(lambda: checker.check_optimal(spec.P, spec.version_space(), spec.eps,
                                                        parse_optimal_cert(spec, j)), label, results)
        else:
            expect_reject(lambda: parse_optimal_cert(spec, j), label, results)

    cmut(lambda j: j.update(problem_sha256="0" * 64), "certificate bound to other problem")
    cmut(lambda j: j.update(core=j["core"] + ["unknown_model"]), "unknown model id in core")
    cmut(lambda j: j.update(core=j["core"] + j["core"][:1]), "duplicate model id in core")
    cmut(lambda j: j.update(policy={"experiment": "nope", "next": {}}), "policy unknown experiment")
    cmut(lambda j: j.update(policy={"experiment": "e0"}), "truncated policy node")
    cmut(lambda j: j.pop("adversary"), "missing adversary")
    cmut(lambda j: j.update(bound="-1"), "negative bound")
    if Fraction(cj["bound"]) > 0:
        cmut(lambda j: j.update(bound=str(Fraction(cj["bound"]) - 1) if Fraction(cj["bound"]) >= 1 else "0"),
             "understated optimal cost", check=True)
    cmut(lambda j: j.update(adversary=[]), "emptied adversary (lower bound unjustified)",
         check=Fraction(cj["bound"]) > 0)
    cmut(lambda j: j.update(policy="stop"), "policy replaced by stop", check=True)
    bugs = [r for r in results if "BUG" in r[1]]
    assert not bugs, bugs
    return results


if __name__ == "__main__":
    for label, status in run():
        print(f"{status:10s} {label}")
