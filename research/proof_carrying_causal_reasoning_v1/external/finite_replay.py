"""Reference verifier for a bounded binary-SCM ATE, independent of the PCCR solver.

The trusted caller supplies the intended problem and claim identifier separately.
The certificate is canonical ASCII JSON. No code, theorem names, approximate
tolerances or fields chosen by the producer can extend the checker.
"""

from __future__ import annotations

import hashlib
import json
import re
from fractions import Fraction
from itertools import product

ASSUMPTIONS = (
    "binary Markovian mechanisms; modular perfect intervention; supplied CPTs are exact"
)
LIMITATION = "conditional on the supplied model and estimand"
VERSION = "pccr-finite-ate/1"
MAX_NODES = 8
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}")
RATE = re.compile(r"(?:0|[1-9][0-9]{0,79})(?:/[1-9][0-9]{0,79})?")


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def check_problem(problem):
    fields = {
        "assumptions",
        "domain",
        "treatment",
        "outcome",
        "direction",
        "nodes",
        "estimand",
    }
    if type(problem) is not dict or set(problem) != fields:
        raise ValueError("unexpected problem fields")
    if (
        problem["assumptions"] != ASSUMPTIONS
        or problem["domain"] != [0, 1]
        or any(type(x) is not int for x in problem["domain"])
        or problem["direction"] not in ("increase", "decrease")
        or problem["estimand"] != "ATE"
    ):
        raise ValueError("unknown assumptions, domain or estimand")
    nodes = problem["nodes"]
    if type(nodes) is not list or not 2 <= len(nodes) <= MAX_NODES:
        raise ValueError("unsupported graph size")
    seen = set()
    for row in nodes:
        if type(row) is not dict or set(row) != {"name", "parents", "p1"}:
            raise ValueError("unexpected mechanism fields")
        name, parents, probs = row["name"], row["parents"], row["p1"]
        if type(name) is not str or not NAME.fullmatch(name) or name in seen:
            raise ValueError("bad node identity")
        if type(parents) is not list or any(type(p) is not str for p in parents):
            raise ValueError("invalid parent type")
        if len(set(parents)) != len(parents) or not set(parents) <= seen:
            raise ValueError("duplicate parent or invalid topological order")
        if type(probs) is not list or len(probs) != 2 ** len(parents):
            raise ValueError("incomplete mechanism")
        for s in probs:
            if (
                type(s) is not str
                or not RATE.fullmatch(s)
                or Fraction(s) > 1
                or str(Fraction(s)) != s
            ):
                raise ValueError("invalid canonical probability")
        seen.add(name)
    if {problem["treatment"], problem["outcome"]} - seen or problem[
        "treatment"
    ] == problem["outcome"]:
        raise ValueError("invalid intervention")


def decision(effect, direction):
    # CLadder uses a dead band of 0.005 in its ATE verbalization.
    return (
        "yes"
        if (effect if direction == "increase" else -effect) >= Fraction(1, 200)
        else "no"
    )


def certificate(claim_id, problem, p0, p1):
    return {
        "schema": VERSION,
        "claim_id": claim_id,
        "source_sha256": digest(problem),
        "strategy": "truncated_binary_factorization",
        "limitation": LIMITATION,
        "p_do0": str(p0),
        "p_do1": str(p1),
        "effect": str(p1 - p0),
        "prediction": decision(p1 - p0, problem["direction"]),
    }


def verify(claim_id, problem, encoded):
    """Check exact bytes by regenerating both intervention arms by full enumeration."""
    if type(encoded) is not bytes or len(encoded) > 2048 or type(claim_id) is not int:
        return False
    try:
        check_problem(problem)
        nodes = problem["nodes"]
        arms = [Fraction(0), Fraction(0)]
        # Sum weights of all worlds with outcome=1. Omitting the treatment
        # factor gives the truncated law for each of the two fixed arms.
        for bits in product((0, 1), repeat=len(nodes)):
            env = {node["name"]: bit for node, bit in zip(nodes, bits)}
            if env[problem["outcome"]] == 0:
                continue
            weight = Fraction(1)
            for node in nodes:
                if node["name"] == problem["treatment"]:
                    continue
                index = 0
                for p in node["parents"]:
                    index = 2 * index + env[p]
                prob = Fraction(node["p1"][index])
                weight *= prob if env[node["name"]] else 1 - prob
            arms[env[problem["treatment"]]] += weight
        return encoded == canonical(certificate(claim_id, problem, *arms))
    except (ValueError, KeyError, TypeError, ZeroDivisionError):
        return False


def replay_frozen(public_bytes, frozen_bytes, expected_public, expected_predictions):
    """Verify a complete structured batch without the generator, solver or labels.

    expected_public authenticates the canonical issued object (without newline);
    expected_predictions authenticates the full frozen file (including newline).
    """
    if hashlib.sha256(frozen_bytes).hexdigest() != expected_predictions:
        raise ValueError("unrecognized prediction digest")
    public, frozen = json.loads(public_bytes), json.loads(frozen_bytes)
    if (
        public_bytes != canonical(public) + b"\n"
        or frozen_bytes != canonical(frozen) + b"\n"
        or digest(public) != expected_public
        or frozen.get("public_sha256") != expected_public
    ):
        raise ValueError("noncanonical or unrecognized batch")
    if (
        set(public) != {"protocol", "rows"}
        or set(frozen) != {"protocol", "public_sha256", "rows"}
        or public["protocol"] != "B"
        or frozen["protocol"] != "B"
    ):
        raise ValueError("expected a structured batch")
    seen = set()
    count = 0
    for issued, result in zip(public["rows"], frozen["rows"], strict=True):
        qid = issued["id"]
        if (
            set(issued) != {"id", "task"}
            or type(qid) is not int
            or qid in seen
            or type(result["id"]) is not int
            or result["id"] != qid
        ):
            raise ValueError("invalid claim identity")
        seen.add(qid)
        if issued["task"] is None:
            if result != {
                "id": qid,
                "prediction": None,
                "reason": "missing_or_unsupported_input",
            }:
                raise ValueError("prediction for unissued estimand")
            continue
        if (
            set(result) != {"id", "prediction", "certificate"}
            or not verify(qid, issued["task"], canonical(result["certificate"]))
            or result["prediction"] != result["certificate"]["prediction"]
        ):
            raise ValueError("failed structured claim verification")
        count += 1
    return {
        "total": len(seen),
        "accepted_certificates": count,
        "unissued": len(seen) - count,
    }


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    ap = argparse.ArgumentParser(
        description="Check Protocol B from public inputs and pinned prediction bytes."
    )
    ap.add_argument("public", type=Path)
    ap.add_argument("predictions", type=Path)
    ap.add_argument("expected_public")
    ap.add_argument("expected_predictions")
    args = ap.parse_args()
    print(
        json.dumps(
            replay_frozen(
                args.public.read_bytes(),
                args.predictions.read_bytes(),
                args.expected_public,
                args.expected_predictions,
            )
        )
    )
