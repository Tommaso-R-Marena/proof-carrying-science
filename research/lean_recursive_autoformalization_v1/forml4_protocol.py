"""Pinned FormL4 Basic protocol. Only problem text crosses into candidate generation."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from math import sqrt
from pathlib import Path

REVISION = "7f65d2c27e79239d754e08af2de84a4cea58acc7"
DATA_SHA256 = "942313eded48cdf6d329a0076ac3935f633fc2e156a9e507ad24ee16dcfd9dde"
SEED = "pgra-forml4-basic-v1"
DEFAULT_DATA = Path("/tmp/ext_bench/forml4/basic_test.json")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def select(path: Path, n: int) -> list[dict[str, str]]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DATA_SHA256:
        raise ValueError("FormL4 Basic input differs from the pinned release")
    data = json.loads(raw)
    if not 0 <= n <= len(data):
        raise ValueError("sample size outside the population")
    # Four equally sized strata of problem-text length. Only English and source
    # row number enter sampling. Take round-robin from seeded orders.
    by_length = sorted(range(len(data)), key=lambda i: (len(data[i]["nl_problem"]), i))
    strata = []
    for j in range(4):
        group = by_length[len(data) * j // 4:len(data) * (j + 1) // 4]
        strata.append(sorted(group, key=lambda i: digest(f"{SEED}/{i}")))
    order = [s[k] for k in range(max(map(len, strata))) for s in strata if k < len(s)]
    return [{"id": f"forml4_basic_{i}", "english": data[i]["nl_problem"]} for i in order[:n]]


def protocol(items: list[dict[str, str]]) -> dict:
    return {"release": REVISION, "file_sha256": DATA_SHA256, "population": 970, "seed": SEED,
            "sampling": "length quartiles, seeded SHA-256 order within quartiles, round robin",
            "demo_count": 0, "model_input_fields": ["english"],
            "items": [{"id": r["id"], "english_sha256": digest(r["english"])} for r in items]}


def wilson(successes: int, n: int) -> list[float] | None:
    if not n:
        return None
    z = 1.959963984540054
    p = successes / n
    center = p + z**2 / (2*n)
    radius = z * sqrt(p*(1-p)/n + z**2/(4*n*n))
    return [max(0., (center-radius)/(1+z*z/n)), min(1., (center+radius)/(1+z*z/n))]


def grammar_census(path: Path) -> dict:
    from .capability import formalize_with_rules
    from .grammar_extensions import RULE_IDS
    items = select(path, 970)
    counts: Counter[str] = Counter()
    supported = []
    for row in items:
        proposal = formalize_with_rules(row["english"], frozenset(RULE_IDS))
        counts[proposal["status"]] += 1
        if proposal.get("candidates"):
            supported.append(row["id"])
    return {"release": REVISION, "file_sha256": DATA_SHA256, "population": len(items),
            "distinct_prompts": len({r["english"] for r in items}), "statuses": dict(counts),
            "candidate_ids": supported, "kernel_checks": 0, "model_requests": 0,
            "metric": "existing controlled-grammar parser coverage on entire external Basic split"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--n", type=int, default=80)
    parser.add_argument("--grammar-census", action="store_true")
    args = parser.parse_args()
    print(json.dumps(grammar_census(args.path) if args.grammar_census else protocol(select(args.path, args.n)),
                     indent=2, sort_keys=True))
