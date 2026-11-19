"""Independently enumerate all allowed withdrawals and compare with the Lean checker."""
from __future__ import annotations

import hashlib
import json
import random
import shutil
import subprocess
import tempfile
from itertools import combinations, product
from pathlib import Path

HERE = Path(__file__).resolve().parent


def domain_cases():
    # Four equally weighted latent response types per population, group observations
    # drawn from an untreated arm, treated arm, and a separate outcome registry.
    causal = []
    for n00, n01, n10, n11 in product(range(5), repeat=4):
        if n00 + n01 + n10 + n11 == 4:
            control, treated = n10 + n11, n01 + n11
            causal.append((f"pop{n00}{n01}{n10}{n11}", treated > control,
                           [control == 1, treated == 3, control + treated == 4]))
    yield "causal-model", "positive-risk-difference", ["arm0", "arm1", "registry"], causal

    # Action proposal, target and approval before the move. A correcting controller
    # always writes the approved destination. Distinct readings share one source per group.
    traces = []
    for proposal, destination, authorized in product(range(2), repeat=3):
        allowed = proposal == destination and bool(authorized)
        traces.append((f"trace{proposal}{destination}{authorized}", allowed,
                       [proposal == 1, destination == 1, authorized == 1, True]))
    yield "policy", "proposed-move-permitted", ["request", "order", "approval", "execution"], traces

    # Possible interpretations of an ambiguous Boolean connective; input and output
    # probes are grouped by their source. The reference is implication (bits 1101
    # in the fixed order 00,01,10,11). Two reviewers each cover the full table.
    reference = (1, 1, 0, 1)
    forms = []
    for values in product(range(2), repeat=4):
        forms.append(("f" + "".join(map(str, values)), values == reference,
                      [values[:2] == reference[:2], values[2:] == reference[2:],
                       values == reference, values == reference]))
    yield "formal-reference", "matches-implication", ["part1", "part2", "fullA", "fullB"], forms


def encode(domain, subject, groups, rows, k):
    lines = [f"{domain} {subject} {k}", " ".join(groups)]
    for name, target, cells in rows:
        bits = " ".join(str(int(b)) for b in cells)
        lines.append(f"{name} {int(target)} {bits}")
    return "|".join(lines)


def independent(rows, k):
    if not any(all(v) for _, _, v in rows):
        return "INCONSISTENT"
    width = len(rows[0][2])
    for n in range(k + 1):
        for forgotten in combinations(range(width), n):
            if any(not target and all(bit or i in forgotten for i, bit in enumerate(cells))
                   for _, target, cells in rows):
                return "COUNTEREXAMPLE"
    return "ROBUST"


def replay():
    rng = random.Random(20261119)
    cases = list(domain_cases())
    for i in range(120):
        cols = rng.randrange(1, 9)
        rows = [(f"w{j}", rng.choice([False, True]), [rng.randrange(2) for _ in range(cols)])
                for j in range(rng.randrange(1, 13))]
        if i % 2 == 0:
            rows.append(("anchor", True, [1] * cols))
        cases.append(("policy", f"random{i}", [f"g{g}" for g in range(cols)], rows))
    issued, expectations = [], []
    for domain, subject, groups, rows in cases:
        for k in range(len(groups) + 1):
            issued.append(encode(domain, subject, groups, rows, k))
            expectations.append((domain, subject, groups, rows, k, independent(rows, k)))
    invalid = [
        "policy x 0|dup dup|m 1 1 1", "policy x 0|g|m 0 1|m 1 0",
        "formal-reference x 1|g|m 1 2", "formal-reference x 0|g h|m 1 0",
        "causal-model x 02|g h|m 1 1 1", "causal-model x 3|g h|m 1 1 1",
        "universal x 0|g|m 1 1", "policy x 0|group",
    ]
    with tempfile.TemporaryDirectory() as td:
        import os
        for name in ("Withdrawal.lean", "CheckWithdrawal.lean"):
            shutil.copyfile(HERE / name, Path(td) / name)
        env = dict(os.environ, LEAN_PATH=td)
        version = subprocess.check_output(["lean", "--version"], cwd=td, env=env, text=True)
        if "version 4.28.0," not in version:
            raise RuntimeError("Lean 4.28.0 required")
        audit = subprocess.check_output(["lean", "-DwarningAsError=true", "-o", "Withdrawal.olean",
                                        "Withdrawal.lean"], cwd=td, env=env, text=True)
        data = "\n".join([*issued, *invalid]) + "\n"
        result = subprocess.check_output(["lean", "-DwarningAsError=true", "--run", "CheckWithdrawal.lean"],
                                        input=data, cwd=td, env=env, text=True).splitlines()
    if result[len(issued):] != ["INVALID"] * len(invalid):
        raise AssertionError("invalid matrix accepted or unexpected output length")
    counts = {}
    thresholds = {}
    for row, (domain, subject, groups, worlds, k, verdict) in zip(result[:len(issued)], expectations, strict=True):
        tag, claim, actual, *witness = row.split()
        if (tag, claim, actual) != (domain, subject, verdict):
            raise AssertionError("disagreement with independent mask enumeration")
        if verdict == "COUNTEREXAMPLE":
            name, *deleted = witness
            world = next(w for w in worlds if w[0] == name)
            omitted = deleted[0].split(",") if deleted else []
            if world[1] or len(omitted) > k or set(omitted) != {g for g, b in zip(groups, world[2]) if not b}:
                raise AssertionError("invalid counterinterpretation")
        elif witness:
            raise AssertionError("unexpected witness")
        counts[verdict] = counts.get(verdict, 0) + 1
        if not subject.startswith("random"):
            thresholds.setdefault(subject, []).append(verdict)
    return dict(lean_axioms=audit.strip().splitlines(), matrices=len(cases), budgets=len(issued),
                malformed=len(invalid), counts=counts, by_example=thresholds, seed=20261119,
                wire_sha256=hashlib.sha256(data.encode()).hexdigest())


if __name__ == "__main__":
    print(json.dumps(replay(), sort_keys=True, indent=2))
