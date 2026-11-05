"""Execute finite Lean/Python/JavaScript comparisons; never claim refinement.

The typed Lean program is generated only from validated local Boolean fixtures.
Every comparison includes diagram tables, exact work, witnesses and Bellman cells.
An independent exhaustive oracle also checks resolved tasks with at most six names.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pcs.experimental.conditional import DEFAULT_LIMITS, from_text
from pcs.experimental.intervention import TASK, plan, validate_task


def fixtures() -> list[dict]:
    rows = []
    def add(target, assumptions="", *, baseline=None, costs=None, locked=None, limits=None):
        problem = from_text(target, "FALSE", assumptions)
        names = problem["variables"]
        task = {"format": TASK, "problem": problem, "baseline": baseline or dict.fromkeys(names, False),
                "costs": costs or dict.fromkeys(names, 1), "locked": [] if locked is None else locked}
        rows.append({"task": validate_task(task), "limits": limits or DEFAULT_LIMITS})
    for target, assumptions in [("TRUE", ""), ("FALSE", ""), ("TRUE", "FALSE"),
                                ("A OR B", ""), ("B", "A\nA -> B"),
                                ("A AND B", "A\nNOT A\nB"),
                                ("A OR (B AND NOT B)", "")]:
        add(target, assumptions)
    add("A OR B", costs={"A": 3, "B": 1})
    for locked in [[], ["A"], ["B"], ["A", "B"]]:
        for baseline in itertools.product((False, True), repeat=2):
            add("A OR B", baseline=dict(zip("AB", baseline)), locked=locked)
    rng = random.Random(20261010)
    names = list("ABCDEF")
    def formula(depth):
        if depth == 0 or rng.random() < .25:
            return rng.choice(names + ["TRUE", "FALSE"])
        if rng.random() < .2:
            return "NOT (" + formula(depth - 1) + ")"
        return "(" + formula(depth - 1) + rng.choice([" AND ", " OR ", " -> "]) + formula(depth - 1) + ")"
    for i in range(64):
        problem = from_text(formula(3), "FALSE", "\n".join(formula(2) for _ in range(rng.randrange(4))))
        present = problem["variables"]
        task = {"format": TASK, "problem": problem, "baseline": {n: bool(rng.randrange(2)) for n in present},
                "costs": {n: rng.randrange(1, 10) for n in present},
                "locked": [n for n in present if rng.random() < .25]}
        limits = {"nodes": 1, "operations": 100000} if i % 8 == 0 else {"nodes": 4096, "operations": 1} if i % 8 == 1 else DEFAULT_LIMITS
        rows.append({"task": validate_task(task), "limits": limits})
    v = [f"V{i:02}" for i in range(24)]
    add(" AND ".join(f"({v[i]} OR {v[i+1]})" for i in range(0, 24, 2)))
    add("NOT (" + " AND ".join(v) + ")", "")
    add(" OR ".join(f"({v[i]} AND {v[i+12]})" for i in range(12)), limits={"nodes": 40, "operations": 100000})
    return rows


def lower(f, names):
    op = f["op"]
    if op in {"true", "false"}:
        return ".tt" if op == "true" else ".ff"
    if op == "atom":
        return f"(.atom ⟨{names.index(f['symbol'])}, by decide⟩)"
    if op == "not":
        return f"(.not {lower(f['body'], names)})"
    return f"(.{'imp' if op == 'implies' else op} {lower(f['left'], names)} {lower(f['right'], names)})"


def list_lean(xs):
    return "[" + ",".join(str(x).lower() for x in xs) + "]"


def program(rows):
    code = (ROOT / "formal/tools/OmegaDDParity.lean").read_text()
    code += "\nopen PCSOmega PCSDD OmegaDDParity\n"
    for i, row in enumerate(rows):
        t, lim = row["task"], row["limits"]
        p = t["problem"]; names = p["variables"]
        assumptions = "[" + ",".join(lower(f, names) for f in p["assumptions"]) + "]"
        base = list_lean([t["baseline"][n] for n in names])
        costs = list_lean([t["costs"][n] for n in names])
        locks = list_lean([names.index(n) for n in t["locked"]])
        code += f"def t{i} : ITask {len(names)} := ⟨⟨{lower(p['source'], names)}, .ff, {assumptions}⟩, {base}, {costs}, {locks}⟩\n"
    code += "def main : IO Unit := do\n"
    for i, row in enumerate(rows):
        lim = row["limits"]
        code += f"  emit {i} t{i} ⟨{lim['nodes']}, {lim['operations']}⟩\n"
    return code


def normalized(r, names):
    c = deepcopy(r["symbolic_receipt"])
    c = {k: c[k] for k in ["decision", "context_example", "counterexample", "unsat_core",
                           "core_necessity_witnesses", "diagram", "limit_reached", "work",
                           "pcs_authority", "lean_kernel_checked"]}
    def assignment(x):
        return None if x is None else [x[n] for n in names]
    c["context_example"] = assignment(c["context_example"])
    if c["counterexample"]:
        c["counterexample"]["assignment"] = assignment(c["counterexample"]["assignment"])
    if c["core_necessity_witnesses"]:
        for w in c["core_necessity_witnesses"]:
            w["assignment"] = assignment(w["assignment"])
    p = {k: r[k] for k in ["decision", "minimum_cost", "optimal_count", "assignment", "flips",
                           "mandatory_flips", "possible_flips", "bellman_cells", "dp_nodes",
                           "pcs_authority", "lean_kernel_checked"]}
    p["assignment"] = assignment(p["assignment"])
    for key in ["flips", "mandatory_flips", "possible_flips"]:
        p[key] = None if p[key] is None else [names.index(n) for n in p[key]]
    return {"conditional": c, "intervention": p}


def independent_oracle(t, r):
    """Truth-table optimization, independent of the BDD and Bellman algorithms."""
    names = t["problem"]["variables"]
    if len(names) > 6 or r["decision"] == "resource_limit":
        return False
    def truth(f, w):
        op = f["op"]
        if op == "atom": return w[f["symbol"]]
        if op == "true": return True
        if op == "false": return False
        if op == "not": return not truth(f["body"], w)
        a, b = truth(f["left"], w), truth(f["right"], w)
        return (a and b) if op == "and" else (a or b) if op == "or" else (not a or b)
    contexts, feasible = [], []
    for values in itertools.product((False, True), repeat=len(names)):
        w = dict(zip(names, values))
        if not all(truth(f, w) for f in t["problem"]["assumptions"]): continue
        contexts.append(w)
        if not truth(t["problem"]["source"], w) or any(w[n] != t["baseline"][n] for n in t["locked"]): continue
        feasible.append((sum(t["costs"][n] for n in names if w[n] != t["baseline"][n]), w))
    if not contexts:
        assert r["decision"] == "inconsistent_assumptions"
    elif not feasible:
        assert r["decision"] == "no_feasible_plan"
    else:
        minimum = min(c for c, _ in feasible)
        optima = [w for c, w in feasible if c == minimum]
        expected = {"decision": "optimal_plan", "minimum_cost": minimum, "optimal_count": len(optima),
                    "assignment": optima[0],
                    "mandatory_flips": [n for n in names if all(w[n] != t["baseline"][n] for w in optima)],
                    "possible_flips": [n for n in names if any(w[n] != t["baseline"][n] for w in optima)]}
        assert {k: r[k] for k in expected} == expected
    return True


def verify(site: Path, formal: Path, output: Path):
    output.mkdir(parents=True, exist_ok=False)
    rows = fixtures()
    (output / "tasks.json").write_text(json.dumps(rows, indent=2) + "\n")
    code = program(rows)
    (output / "Parity.lean").write_text(code)
    lean = subprocess.run(["lake", "env", "lean", "--run", str((output / "Parity.lean").resolve())],
                          cwd=formal, capture_output=True, text=True, timeout=240)
    (output / "lean-output.jsonl").write_text(lean.stdout)
    (output / "lean-stderr.log").write_text(lean.stderr)
    if lean.returncode: raise ValueError(lean.stdout + lean.stderr)
    actual = [json.loads(line) for line in lean.stdout.splitlines()]
    assert len(actual) == len(rows) and [r["id"] for r in actual] == list(range(len(rows)))
    module = site / "public/intervention-core.mjs"
    js = "import {planIntervention} from " + json.dumps(module.resolve().as_uri()) + ";\n"
    js += "const chunks=[];for await(const c of process.stdin)chunks.push(c);const rows=JSON.parse(Buffer.concat(chunks));console.log(JSON.stringify(await Promise.all(rows.map(r=>planIntervention(r.task,{limits:r.limits})))));"
    node = subprocess.run(["node", "--input-type=module", "-e", js], input=json.dumps(rows),
                          capture_output=True, text=True, timeout=60)
    if node.returncode: raise ValueError(node.stderr)
    browser = json.loads(node.stdout)
    assert len(browser) == len(rows)
    oracle_count = 0; decisions = {}
    py = []
    for i, row in enumerate(rows):
        r = plan(row["task"], row["limits"]); py.append(r)
        names = row["task"]["problem"]["variables"]
        expected = normalized(r, names)
        if {k: v for k, v in actual[i].items() if k != "id"} != expected:
            raise ValueError(f"Lean/Python mismatch in task {i}; retain outputs and investigate")
        if normalized(browser[i], names) != expected or browser[i] != r:
            raise ValueError(f"JavaScript/Python mismatch in task {i}")
        oracle_count += independent_oracle(row["task"], r)
        decisions[r["decision"]] = decisions.get(r["decision"], 0) + 1
    (output / "python-receipts.json").write_text(json.dumps(py, indent=2) + "\n")
    (output / "javascript-receipts.json").write_text(json.dumps(browser, indent=2) + "\n")
    result = {"format": "pcs-omega-dd-finite-runtime-parity-v1", "tasks": len(rows),
              "conditional_and_intervention_receipt_pairs": len(rows), "decisions": decisions,
              "independent_exhaustive_oracle_tasks": oracle_count, "disagreements": 0,
              "javascript_sources": {name: hashlib.sha256((site / "public" / name).read_bytes()).hexdigest()
                                     for name in ["conditional-core.mjs", "intervention-core.mjs", "omega-core.mjs"]},
              "implementation_refinement_proved": False, "pcs_authority": False}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--formal-dir", type=Path, default=ROOT / "formal")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify(args.site.resolve(), args.formal_dir.resolve(), args.output.resolve())
