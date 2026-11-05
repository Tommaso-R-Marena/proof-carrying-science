"""Deterministic actual-Lean replay; positive data use an independent flux oracle."""
from __future__ import annotations

import argparse
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import random

from pcs.canonical_json import canonicalize_jcs_bytes as encode
from .replay import export, replay

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = (ROOT / "examples/scientific_workflow_v3/contract.json").read_bytes()
CSV = (ROOT / "examples/scientific_workflow_v3/trajectory.csv").read_bytes()


def generated(width, steps, seed):
    rng = random.Random(seed)
    contract = json.loads(CONTRACT)
    contract["cells"] = [{"id": f"C{i}", "volume": str(Fraction(rng.randrange(1, 7), 2)),
                          "initial_concentration": str(Fraction(rng.randrange(0, 9), 8))}
                         for i in range(width)]
    contract["edges"] = [{"left": f"C{i}", "right": f"C{i+1}", "conductance": "1/8"}
                         for i in range(width - 1)]
    contract["steps"], contract["time_step"] = steps, "1/16"
    volumes = [Fraction(c["volume"]) for c in contract["cells"]]
    state = [Fraction(c["initial_concentration"]) for c in contract["cells"]]
    rows = ["time_s," + ",".join(c["id"] for c in contract["cells"])]
    for k in range(steps + 1):
        rows.append(",".join([str(Fraction(k, 16)), *map(str, state)]))
        # Independent edge-flux implementation; not the matrix/dot-product generator.
        amounts = [v * x for v, x in zip(volumes, state)]
        for i in range(width - 1):
            transfer = Fraction(1, 16) * Fraction(1, 8) * (state[i] - state[i + 1])
            amounts[i] -= transfer
            amounts[i + 1] += transfer
        state = [a / v for a, v in zip(amounts, volumes)]
    return encode(contract), ("\n".join(rows) + "\n").encode()


def corrupt(raw, kind):
    lines = raw.decode().splitlines()
    index = 1 if kind == "initial" else len(lines) - 1
    row = lines[index].split(",")
    column = 0 if kind == "time" else 1
    row[column] = str(Fraction(row[column]) + 1)
    lines[index] = ",".join(row)
    return ("\n".join(lines) + "\n").encode()


def cases():
    yield "original-five-cell-sixteen-step", CONTRACT, CSV, True
    for kind in ["initial", "recurrence", "time"]:
        yield "original-fault-" + kind, CONTRACT, corrupt(CSV, kind), False
    for width in [2, 4, 8, 16]:
        contract, raw = generated(width, 4, 20261021 + width)
        yield f"flux-{width}-cells", contract, raw, True
        if width == 16:
            yield "flux-16-cells-fault", contract, corrupt(raw, "recurrence"), False
    contract, raw = generated(16, 16, 20261021 + 1000 + 100 * 16 + 16)
    yield "flux-16-cells-sixteen-steps", contract, raw, True
    contract = json.loads(CONTRACT)
    contract["cells"] = [{"id": "A", "volume": "1", "initial_concentration": "1"},
                         {"id": "B", "volume": "1", "initial_concentration": "0"}]
    contract["edges"] = [{"left": "A", "right": "B", "conductance": "1"}]
    contract["steps"], contract["time_step"] = 64, "1"
    raw = ("time_s,A,B\n" + "".join(f"{k},{1-k%2},{k%2}\n" for k in range(65))).encode()
    yield "sixty-four-step-oscillation", encode(contract), raw, True
    yield "oscillation-last-step-fault", encode(contract), corrupt(raw, "recurrence"), False


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    protocol = [{"name": name, "expected_kernel_support": good,
                 "contract_sha256": __import__("hashlib").sha256(c).hexdigest(),
                 "trajectory_sha256": __import__("hashlib").sha256(raw).hexdigest()}
                for name, c, raw, good in cases()]
    (args.out / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    results = []
    for name, c, raw, good in cases():
        r = replay(c, raw, timeout=180)
        export(args.out / name, r, c, raw)
        okay = (r["kernel_supported"] if good else r["negative_kernel_checked"])
        okay = okay and r["all_time_model_kernel_supported"] and not r["pcs_authority"] and not r["scientific_acceptance"]
        row = {"name": name, "passed": okay, "status": r["status"],
               "fault": r.get("fault"), "wall_seconds": r["wall_seconds"],
               "audited_theorems": len(r["axiom_closures"]), "error": r.get("error")}
        results.append(row)
        print(json.dumps(row), flush=True)
    summary = {"format": "pcs-portable-transport-campaign-v2", "cases": len(results),
               "passed": sum(r["passed"] for r in results), "results": results,
               "empirical_validation": False, "production_authority": False}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if summary["passed"] != summary["cases"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
