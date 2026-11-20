"""Replay three scoped reference judgments and preserve the generated kernel inputs."""
from __future__ import annotations

import json
from .lean_compile_oracle import compare_reference

CASES = [
    ("alpha-renaming", "theorem proposal (k : Nat) : k = k", "example (n : Nat) : n = n", "PROOF_VERIFIED"),
    ("same-unprovable", "theorem proposal : False", "example : False", "SEMANTICALLY_EQUIVALENT"),
    ("changed-conclusion", "theorem proposal : True", "example : False", "WELL_TYPED_UNVALIDATED"),
]


def replay() -> list[dict]:
    rows = []
    for case, candidate, reference, expected in CASES:
        receipt = compare_reference(candidate, reference)
        if receipt["status"] != expected:
            raise RuntimeError(f"{case}: expected {expected}, received {receipt}")
        rows.append(dict(case=case, candidate=candidate, reference=reference, receipt=receipt))
    return rows


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2, sort_keys=True))
