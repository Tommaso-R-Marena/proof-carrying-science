#!/usr/bin/env python3
"""Execute reproducible first-party model controls and fresh kernel replay."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pcs.action_shield_v1 import evaluate, formal_source, kernel_replay, proof_source, propose
from pcs.canonical_json import canonicalize_jcs_bytes


def write(path: Path, value: dict) -> bytes:
    raw = canonicalize_jcs_bytes(value)
    path.write_bytes(raw)
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=24)
    args = parser.parse_args()
    if not 1 <= args.seeds <= 64:
        parser.error("seeds must be in 1..64")
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    initial_resource = resource.getrusage(resource.RUSAGE_CHILDREN)
    template = json.loads((ROOT / "examples/action_shield_v1/model.json").read_bytes())
    source = formal_source()
    (args.output / "PCSActionShield.lean").write_bytes(source)
    (args.output / "adapter.py.txt").write_bytes((ROOT / "pcs/action_shield_v1.py").read_bytes())
    (args.output / "campaign.py.txt").write_bytes(Path(__file__).read_bytes())
    protocol = {"format": "pcs-action-shield-campaign-v1", "seed_start": 20261014,
        "random_models": args.seeds, "cases_per_random_model": 2,
        "first_party_authored_finite_models": True, "external_validation": False,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "adapter_sha256": hashlib.sha256((ROOT / "pcs/action_shield_v1.py").read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "deployed_correspondence": "OPEN", "training": False}
    write(args.output / "PROTOCOL.json", protocol)
    outcomes = []
    def run_case(name: str, model: dict, shield: dict, expected: bool) -> None:
        case = args.output / name
        case.mkdir()
        model_raw = write(case / "model.json", model)
        shield_raw = write(case / "shield.json", shield)
        report = evaluate(model_raw, shield_raw)
        write(case / "report.json", report)
        (case / "Replay.lean").write_bytes(proof_source(model_raw, shield_raw))
        kernel = kernel_replay(model_raw, shield_raw)
        write(case / "kernel.json", kernel)
        okay = (report["outcome"] == ("PASS" if expected else "FAIL")
                and kernel["kernel_checked"] is expected)
        if not okay:
            raise RuntimeError(f"independent model/kernel mismatch: {name}: {kernel}")
        outcomes.append({"case": name, "expected_pass": expected, "python_outcome": report["outcome"],
            "kernel_status": kernel["status"], "model_sha256": report["model_sha256"],
            "shield_sha256": report["shield_sha256"], "proof_sha256": kernel["proof_sha256"],
            "kernel_axioms": kernel["kernel_axioms"]})
    model_raw = canonicalize_jcs_bytes(template)
    shield = propose(model_raw)
    run_case("tool-positive", template, shield, True)
    nondet = deepcopy(shield)
    nondet["allowed"] = sorted([*nondet["allowed"], [2, 3]])
    run_case("tool-unsafe-nondeterministic", template, nondet, False)
    forbidden = deepcopy(shield)
    forbidden["allowed"] = sorted([*forbidden["allowed"], [0, 5]])
    run_case("tool-forbidden-safe-target", template, forbidden, False)
    denial = deepcopy(shield)
    denial["allowed"] = []
    run_case("tool-safe-deadlocked", template, denial, True)
    omitted = deepcopy(template)
    omitted["transitions"] = [e for e in omitted["transitions"] if e != {"source": 2, "action": 3, "target": 5}]
    run_case("tool-incomplete-model-only", omitted, propose(canonicalize_jcs_bytes(omitted)), True)
    for index in range(args.seeds):
        rng = random.Random(20261014 + index)
        n = rng.randint(4, 8)
        triples = {(s, 0, s) for s in range(n - 1)} | {(0, 1, n - 1)}
        for _ in range(3 * n):
            triples.add((rng.randrange(n), rng.randrange(4), rng.randrange(n)))
        model = {**deepcopy(template), "states": list(range(n)), "actions": list(range(4)),
            "initial": [0], "safe": list(range(n - 1)), "forbidden": [3],
            "transitions": [{"source": s, "action": a, "target": t} for s, a, t in sorted(triples)]}
        model_raw = canonicalize_jcs_bytes(model)
        proposed = propose(model_raw)
        run_case(f"seed-{20261014 + index}-safe", model, proposed, True)
        malicious = deepcopy(proposed)
        malicious["allowed"] = sorted([*malicious["allowed"], [0, 1]])
        run_case(f"seed-{20261014 + index}-unsafe", model, malicious, False)
    final_resource = resource.getrusage(resource.RUSAGE_CHILDREN)
    summary = {"format": "pcs-action-shield-campaign-summary-v1", "case_count": len(outcomes),
        "fresh_kernel_acceptances": sum(x["expected_pass"] for x in outcomes),
        "fresh_kernel_rejections": sum(not x["expected_pass"] for x in outcomes),
        "mismatches": 0, "cases": outcomes, "elapsed_seconds": round(time.monotonic() - started, 6),
        "child_user_cpu_seconds": round(final_resource.ru_utime - initial_resource.ru_utime, 6),
        "child_system_cpu_seconds": round(final_resource.ru_stime - initial_resource.ru_stime, 6),
        "largest_child_rss_kib_linux": final_resource.ru_maxrss,
        "external_empirical_validation": False, "deployment_safety": "OPEN", "scientific_acceptance": False}
    write(args.output / "SUMMARY.json", summary)
    seal = {p.relative_to(args.output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(args.output.rglob("*")) if p.is_file()}
    write(args.output / "ARTIFACT_SHA256.json", seal)
    print(json.dumps({k: v for k, v in summary.items() if k != "cases"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
