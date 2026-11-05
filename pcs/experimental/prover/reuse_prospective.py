"""Prospective elementary mathematics evaluation of the frozen reuse portfolio.

Protocol and previously unexecuted statements are saved before any search. No
new fitting or model selection occurs. The existing public benchmark has been
exposed; this authored extension is not an external or private blind evaluation.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

from .environment import LeanEnvironment, search
from .ir import digest
from .language import formalize
from .library import LibraryEnvironment, replay_library_receipt
from .portfolio import search_portfolio
from .reuse_model import ReuseNetwork
from .reuse_experiment import metrics, write


def evaluate(experiment, output):
    folder, output = Path(experiment), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    statements = [
        ("nat_order_transitivity", "For all natural numbers a, b and c, if ((a is less than or equal to b) and (b is less than or equal to c)) then (a is less than or equal to c)."),
        ("int_order_transitivity", "For all integers x, y and z, if ((x is less than or equal to y) and (y is less than or equal to z)) then (x is less than or equal to z)."),
        ("nat_order_antisymmetry", "For all natural numbers a and b, if ((a is less than or equal to b) and (b is less than or equal to a)) then (a equals b)."),
        ("int_order_antisymmetry", "For all integers x and y, if ((x is less than or equal to y) and (y is less than or equal to x)) then (x equals y)."),
        ("nat_composite_witness", "For all natural numbers n, there exists a natural number m such that (m equals n and (m * 1) + 0 equals n)."),
        ("int_identity_witness", "For all integers z, there exists an integer w such that w equals z."),
        ("integer_arithmetic_exchange", "For all integers x, y and z, if ((x + 0 equals y) and (y + 0 equals z)) then ((y + 0 equals z) and (x + 0 equals y))."),
        ("function_composition_congruence", "For all functions from natural numbers to natural numbers f and g, if (∀ (a : Nat), f(a) equals g(a)) then (∀ (b : Nat), f(f(b)) equals g(g(b)))."),
        ("function_argument_congruence", "For all functions from natural numbers to natural numbers f and g, if (∀ (a : Nat), f(a) equals g(a)) then (∀ (b : Nat), f(g(b)) equals g(g(b)))."),
        ("predicate_rule_retention", "For all predicates on natural numbers P, Q and R, if ((∀ (a : Nat), P(a) implies Q(a)) and (∀ (b : Nat), Q(b) implies R(b))) then (∀ (c : Nat), P(c) implies Q(c))."),
        ("missing_order_assumption", "For all natural numbers a and b, a is less than or equal to b."),
        ("invalid_function_equivalence", "For all functions from natural numbers to natural numbers f and g, if (∀ (a : Nat), f(a) equals g(a)) then (∀ (b : Nat), f(f(b)) equals g(b))."),
    ]
    tasks = []
    for name, statement in statements:
        parsed = formalize(statement)
        if parsed["status"] != "supported": raise ValueError(name + str(parsed))
        tasks.append({"id": name, "original_statement": statement, "goal": parsed["candidates"][0]["ir"],
                      "license": "Apache-2.0", "split": "prospective", "source": "PCS authored"})
    registry = json.loads((folder / "registry.json").read_text())
    entry = next(e for e in registry["models"] if e["id"] == registry["selected_local_experiment"])
    protocol = {"format": "pcs-reuse-prospective-v1", "tasks_sha256": digest(tasks), "budget": 64, "beam": 4,
                "portfolio_allocation": "one-quarter learned shortcut; remaining actual budget symbolic fallback",
                "checkpoint_sha256": entry["sha256"], "no_training_or_reselection": True,
                "cache": "empty observation cache before each policy", "interpretation": "controlled typed grammar, no independent general English certification",
                "evaluation_exposure": "previous public suite exposed; these elementary statements written and frozen before their first search"}
    write(output / "protocol.json", protocol); write(output / "tasks.json", tasks)
    source_files = list(Path(__file__).parent.glob("*.py"))
    root = Path(__file__).resolve().parents[3]
    source_files += [root / "formal/PCSProofProbe.lean", root / "formal/PCSProofWorker.lean", root / "formal/PCSReuseWorker.lean"]
    write(output / "source-manifest.json", {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_files)})
    model = ReuseNetwork.load(folder / entry["checkpoint"], entry["sha256"])
    base = LeanEnvironment(timeout=30)
    lib = LibraryEnvironment(json.loads((folder / "library.json").read_text()), heldout=tasks, timeout=30)
    started = time.monotonic()
    try:
        evaluations, summaries = {}, {}
        for name, env, runner in [("symbolic", base, lambda g: search(base,g,budget=64,beam=4)),
                                  ("raw_selected_reuse", lib, lambda g: search(lib,g,model.rank,budget=64,beam=4)),
                                  ("reuse_portfolio", lib, lambda g: search_portfolio(lib,g,model.rank,budget=64,beam=4))]:
            env.observations.clear(); begin=time.monotonic(); calls=env.invocations
            records = []
            for t in tasks:
                result = runner(t["goal"])
                records.append({**t,"result":result})
                print(name,t["id"],result["status"],result["expansions"],flush=True)
            evaluations[name]=records
            summaries[name]={**metrics(records),"all_observe_and_verify_invocations":env.invocations-calls,
                             "whole_evaluation_wall_seconds":time.monotonic()-begin}
        independent=[]
        for r in evaluations["reuse_portfolio"]:
            if r["result"]["status"]=="verified":
                checked=replay_library_receipt(r["goal"],r["result"]["receipt"],cache=base.cache)
                independent.append({"id":r["id"],"receipt_sha256":digest(checked),"axioms":checked["kernel"]["axioms"]})
        write(output/"independent-replay.json",independent)
        write(output/"summary.json",{"metrics":summaries,"selected_unchanged":entry["id"],"library_construction_seconds":lib.construction_seconds,
              "library_construction_invocations":lib.construction_invocations,"total_wall_seconds":time.monotonic()-started,"financial_spend":0,"gpu_used":False})
        (output/"evaluations.json.gz").write_bytes(gzip.compress(json.dumps(evaluations,sort_keys=True,separators=(",",":")).encode(),mtime=0))
        write(output/"SHA256.json",{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()})
    finally: base.close();lib.close()


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--experiment",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();evaluate(a.experiment,a.output)
