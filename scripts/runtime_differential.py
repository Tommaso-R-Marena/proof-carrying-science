#!/usr/bin/env python3
"""Seeded native Rust/Lean and Python/browser-JS/Lean differential executions.

Testing is NOT a runtime refinement proof. Every mismatch retains exact inputs,
native/reference outputs, source digests and a bounded deterministic minimized case.
No evaluator, source window, toolchain or production configuration is changed.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time

try:
    import resource
except ImportError:  # Windows still supports generation/unit tests; POSIX resource data is optional.
    resource = None

ROOT = Path(__file__).resolve().parents[1]
ADAPTERS = ROOT / "scripts/runtime_differential"
sys.path.insert(0, str(ROOT))
BINOPS = ("add", "sub", "mul", "and", "or", "xor", "shl", "lshr")
CMPOPS = ("eq", "ne", "ult", "ule", "ugt", "uge")
WIDTHS = (8, 16, 32, 64)


def run(argv, *, cwd=None, input=None, timeout=300):
    p = subprocess.run(argv, cwd=cwd, input=input, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {argv}\n{p.stdout[-8000:]}{p.stderr[-8000:]}")
    return p.stdout


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def provenance(path, files):
    return {"revision": run(["git", "rev-parse", "HEAD"], cwd=path).strip(),
            "origin": run(["git", "remote", "get-url", "origin"], cwd=path).strip(),
            "dirty": bool(run(["git", "status", "--porcelain"], cwd=path).strip()),
            "files": {f: sha(path / f) for f in files}}


def lean_string(x):
    # JSON escaping is valid for the bounded ASCII symbol/name domain used here.
    return json.dumps(x, ensure_ascii=True)


def lean_ty(t):
    return ".bool" if t == "bool" else f"(.bv .{t['bitvec']})"


def lean_expr(e):
    k = e["kind"]
    if k == "const_bool": return f"(.constBool {str(e['value']).lower()})"
    if k == "const_bv": return f"(.constBv .{e['width']} {e['value']})"
    if k == "var": return f"(.var {lean_string(e['name'])})"
    if k == "un_op": return f"(.unop .{e['op']} {lean_expr(e['expr'])})"
    if k in ("bin_op", "cmp"):
        return f"(.{'binop' if k == 'bin_op' else 'cmp'} .{e['op']} {lean_expr(e['lhs'])} {lean_expr(e['rhs'])})"
    if k == "select": return f"(.select {lean_expr(e['cond'])} {lean_expr(e['then_expr'])} {lean_expr(e['else_expr'])})"
    raise ValueError("unsupported AST")


def lean_program(c):
    p = c["program"]
    params = ",".join("⟨" + lean_string(x["name"]) + "," + lean_ty(x["ty"]) + "⟩" for x in p["params"])
    inputs = ",".join(f"(.bool {str(x['value']).lower()})" if x["kind"] == "bool" else
                      f"(.bitvec .{x['width']} {x['bits']})" for x in c["inputs"])
    return f"({{ name := {lean_string(p['name'])}, params := [{params}], body := {lean_expr(p['body'])}, retTy := {lean_ty(p['ret_ty'])} }} : Program)", f"([{inputs}] : List Value)"


def random_expr(rng, depth, width):
    if depth == 0 or rng.randrange(5) == 0:
        return rng.choice([{"kind": "var", "name": rng.choice(("x", "y", "missing"))},
                           {"kind": "const_bool", "value": rng.choice((True, False))},
                           {"kind": "const_bv", "width": f"u{width}", "value": rng.getrandbits(64)}])
    kind = rng.choice(("un_op", "bin_op", "cmp", "select"))
    child = lambda: random_expr(rng, depth - 1, width)
    if kind == "un_op": return {"kind": kind, "op": rng.choice(("not", "neg")), "expr": child()}
    if kind in ("bin_op", "cmp"):
        return {"kind": kind, "op": rng.choice(BINOPS if kind == "bin_op" else CMPOPS), "lhs": child(), "rhs": child()}
    return {"kind": kind, "cond": child(), "then_expr": child(), "else_expr": child()}


def typed_expr(rng, depth, width, boolean=False):
    """Generate genuine deeper well-typed programs, separately from malformed/error probes."""
    if depth == 0:
        if boolean:
            return rng.choice(({"kind":"var","name":"b"},{"kind":"const_bool","value":bool(rng.getrandbits(1))}))
        return rng.choice(({"kind":"var","name":rng.choice(("x","y"))},
                           {"kind":"const_bv","width":f"u{width}","value":rng.getrandbits(64)}))
    kind=rng.choice(("un_op","cmp","select") if boolean else ("un_op","bin_op","select"))
    child=lambda is_bool=boolean:typed_expr(rng,depth-1,width,is_bool)
    if kind=="un_op":return {"kind":kind,"op":"not" if boolean else rng.choice(("not","neg")),"expr":child()}
    if kind in ("bin_op","cmp"):
        return {"kind":kind,"op":rng.choice(CMPOPS if boolean else BINOPS),"lhs":child(False),"rhs":child(False)}
    return {"kind":kind,"cond":child(True),"then_expr":child(),"else_expr":child()}


def forge_cases(seed, count):
    rng = random.Random(seed)
    out = []
    for w in WIDTHS:
        ty = {"bitvec": f"u{w}"}
        params = [{"name": "x", "ty": ty}, {"name": "y", "ty": ty}]
        inputs = [{"kind": "bv", "width": f"u{w}", "bits": (1 << w) - 1},
                  {"kind": "bv", "width": f"u{w}", "bits": 1 << 32}]
        for kind, ops in (("bin_op", BINOPS), ("cmp", CMPOPS)):
            for op in ops:
                body = {"kind": kind, "op": op, "lhs": {"kind": "var", "name": "x"}, "rhs": {"kind": "var", "name": "y"}}
                out.append({"program": {"name": "edge", "params": params, "body": body, "ret_ty": ty if kind == "bin_op" else "bool"}, "inputs": inputs})
    # Boolean ordering, lazy select, first-error order, duplicate binding, arity and type mismatches.
    for op in CMPOPS:
        out.append({"program": {"name": "bool_cmp", "params": [], "body": {"kind": "cmp", "op": op,
                    "lhs": {"kind": "const_bool", "value": False}, "rhs": {"kind": "const_bool", "value": True}}, "ret_ty": "bool"}, "inputs": []})
    for _ in range(count):
        w = rng.choice(WIDTHS); ty = {"bitvec": f"u{w}"}
        p = {"name": "seeded", "params": [{"name": "x", "ty": ty}, {"name": rng.choice(("x", "y")), "ty": rng.choice((ty, "bool"))}],
             "body": random_expr(rng, rng.randrange(1, 5), w), "ret_ty": rng.choice((ty, "bool"))}
        vals = [{"kind": "bv", "width": f"u{w}", "bits": rng.getrandbits(64)}, {"kind": "bool", "value": bool(rng.getrandbits(1))}]
        rng.shuffle(vals)
        out.append({"program": p, "inputs": vals[:rng.randrange(3)]})
    for _ in range(count):
        w=rng.choice(WIDTHS); ty={"bitvec":f"u{w}"}; boolean=bool(rng.getrandbits(1))
        out.append({"program":{"name":"typed_depth","params":[{"name":"x","ty":ty},{"name":"y","ty":ty},{"name":"b","ty":"bool"}],
                               "body":typed_expr(rng,rng.randrange(1,5),w,boolean),"ret_ty":"bool" if boolean else ty},
                    "inputs":[{"kind":"bv","width":f"u{w}","bits":rng.getrandbits(64)},
                              {"kind":"bv","width":f"u{w}","bits":rng.getrandbits(64)},
                              {"kind":"bool","value":bool(rng.getrandbits(1))}]})
    # Explicit deeper well-typed coverage, rather than random cases mostly rejected at arity.
    for w in WIDTHS:
        ty = {"bitvec": f"u{w}"}
        for op in ("not", "neg"):
            out.append({"program": {"name": "unary", "params": [], "body": {"kind": "un_op", "op": op,
                         "expr": {"kind": "const_bv", "width": f"u{w}", "value": 18446744073709551615}}, "ret_ty": ty}, "inputs": []})
        for condition in (True, False):
            out.append({"program": {"name": "lazy", "params": [], "body": {"kind": "select",
                        "cond": {"kind": "const_bool", "value": condition},
                        "then_expr": {"kind": "const_bv", "width": f"u{w}", "value": 13},
                        "else_expr": {"kind": "var", "name": "missing"}}, "ret_ty": ty}, "inputs": []})
    return out


def shrink_candidates(case):
    """Structural and numeric one-step candidates. Strict byte-size order ensures termination."""
    def walk(value, path=()):
        if isinstance(value, dict):
            for k, v in value.items():
                yield from walk(v, (*path, k))
            if value.get("kind") in ("un_op", "bin_op", "cmp", "select"):
                for k in ("expr", "lhs", "rhs", "cond", "then_expr", "else_expr"):
                    if k in value: yield path, value[k]
        elif isinstance(value, list):
            for i, v in enumerate(value): yield from walk(v, (*path, i))
            for i in range(len(value)): yield path, value[:i] + value[i+1:]
        elif type(value) is int and value > 0:
            for x in sorted({0, 1, value // 2}):
                if x < value: yield path, x
    size = len(json.dumps(case, sort_keys=True))
    for path, value in walk(case):
        candidate = copy.deepcopy(case)
        cursor = candidate
        for k in path[:-1]: cursor = cursor[k]
        if path: cursor[path[-1]] = value
        else: candidate = copy.deepcopy(value)
        if len(json.dumps(candidate, sort_keys=True)) < size: yield candidate


def minimize(case, diverges, budget=64):
    """Only retain a simplification when fresh executions still disagree; report budget exhaustion."""
    current, attempts = copy.deepcopy(case), 0
    while attempts < budget:
        changed = False
        for candidate in shrink_candidates(current):
            attempts += 1
            if diverges(candidate): current, changed = candidate, True; break
            if attempts >= budget: break
        if not changed: break
    return {"input": current, "attempts": attempts, "budget": budget, "budget_exhausted": attempts >= budget}


class ForgeRunner:
    def __init__(self, checkout, folder):
        self.folder = folder
        crate = folder / "probe"; (crate / "src").mkdir(parents=True)
        (crate / "src/main.rs").write_bytes((ADAPTERS / "forge_probe.rs").read_bytes())
        deps = {"certir": checkout / "crates/certir", "certir-interpreter": checkout / "crates/certir-interpreter"}
        toml = '[package]\nname="pcs-runtime-differential"\nversion="0.1.0"\nedition="2021"\n[dependencies]\nserde_json="1"\n'
        toml += "".join(f"{k}={{path={json.dumps(str(v))}}}\n" for k,v in deps.items())
        (crate / "Cargo.toml").write_text(toml)
        run(["cargo", "build", "--offline", "--manifest-path", str(crate / "Cargo.toml")], timeout=300)
        self.binary = crate / "target/debug/pcs-runtime-differential"
        self.counter = 0

    def evaluate(self, cases, *, patched=True):
        native = [json.loads(x) for x in run([str(self.binary)], input="".join(json.dumps(c)+"\n" for c in cases)).splitlines()]
        reference = []
        # Small independent Lean source batches avoid enormous elaborator memory use.
        for offset in range(0, len(cases), 48):
            lines = [(ADAPTERS / "ForgeNormalize.lean").read_text(), "open PCSForgeRefinement PCSRuntimeDifferential"]
            for c in cases[offset:offset+48]:
                p, vals = lean_program(c)
                lines.append(f'#eval IO.println (normalizeEval (eval {p} {vals}) ++ "\\t" ++ normalizeCheck ({p}.checkG {str(patched).lower()}))')
            source = self.folder / f"Forge-{self.counter}.lean"; self.counter += 1
            source.write_text("\n".join(lines)+"\n")
            for line in run(["lake", "env", "lean", str(source)], cwd=ROOT / "formal", timeout=300).splitlines():
                parts = line.split("\t")
                if len(parts) != 2: raise ValueError("unexpected Lean output: " + line)
                reference.append(dict(zip(("eval", "check"), parts)))
        if len(native) != len(cases) or len(reference) != len(cases): raise ValueError("incomplete execution outputs")
        return list(zip(native, reference))


def boolean_formula(rng, names, depth):
    if depth == 0 or rng.randrange(4) == 0:
        return {"op": "atom", "symbol": rng.choice(names), "args": []} if names and rng.randrange(3) else {"op": rng.choice(("true", "false"))}
    op = rng.choice(("not", "and", "or", "implies"))
    if op == "not": return {"op": op, "body": boolean_formula(rng, names, depth-1)}
    return {"op": op, "left": boolean_formula(rng, names, depth-1), "right": boolean_formula(rng, names, depth-1)}


def conditional_cases(seed, count):
    rng = random.Random(seed); out = []
    for i in range(count):
        names = list("ABCD"[:i % 5]); source = boolean_formula(rng, names, 3)
        t = {"format": "pcs-conditional-boolean-task-v1", "variables": names, "source": source,
             "candidate": copy.deepcopy(source) if i % 5 == 0 else boolean_formula(rng, names, 3),
             "assumptions": [boolean_formula(rng, names, 2) for _ in range(i % 4)]}
        out.append({"task": t, "limits": {"nodes": (1, 3, 4096)[i % 3], "operations": (1, 8, 100000)[i % 3]}})
    return out


def lean_boolean(f, names):
    op = f["op"]
    if op == "atom": return f"(.atom ⟨{names.index(f['symbol'])}, by decide⟩)"
    if op in ("true", "false"): return ".tt" if op == "true" else ".ff"
    if op == "not": return f"(.not {lean_boolean(f['body'], names)})"
    return f"(.{'imp' if op == 'implies' else op} {lean_boolean(f['left'], names)} {lean_boolean(f['right'], names)})"


def modeled_receipt(r, names):
    def assignment(a): return [a[n] for n in names] if a is not None else None
    x = {k: copy.deepcopy(r[k]) for k in ("decision", "unsat_core", "diagram", "limit_reached", "work", "pcs_authority", "lean_kernel_checked")}
    x["context_example"] = assignment(r["context_example"])
    x["counterexample"] = copy.deepcopy(r["counterexample"])
    if x["counterexample"] is not None: x["counterexample"]["assignment"] = assignment(x["counterexample"]["assignment"])
    x["core_necessity_witnesses"] = None if r["core_necessity_witnesses"] is None else [
        {"removed_assumption": w["removed_assumption"], "assignment": assignment(w["assignment"])} for w in r["core_necessity_witnesses"]]
    return x


class ConditionalRunner:
    def __init__(self, site, folder): self.site, self.folder, self.counter = site, folder, 0

    def evaluate(self, cases):
        from pcs.experimental.conditional import check
        native_js = [json.loads(x) for x in run(["node", str(ADAPTERS / "conditional_probe.mjs"), str(self.site / "public/conditional-core.mjs")],
                         input="".join(json.dumps(c)+"\n" for c in cases)).splitlines()]
        if len(native_js) != len(cases): raise ValueError("incomplete JS output")
        python = []
        for c in cases:
            try: python.append({"accepted": True, "receipt": check(c["task"], c["limits"])})
            except (ValueError, RecursionError) as e: python.append({"accepted": False, "error": str(e)})
        lean_outputs = {}
        valid = [i for i,c in enumerate(python) if c["accepted"]]
        for offset in range(0, len(valid), 24):
            batch = valid[offset:offset+24]
            lines = [(ADAPTERS / "ConditionalNormalize.lean").read_text(), "open PCSOmega PCSDD PCSRuntimeDifferential"]
            for i in batch:
                t, l = cases[i]["task"], cases[i]["limits"]; ns = t["variables"]
                premises = ",".join(lean_boolean(f,ns) for f in t["assumptions"])
                task = f"({{ source := {lean_boolean(t['source'],ns)}, candidate := {lean_boolean(t['candidate'],ns)}, assumptions := [{premises}] }} : CTask {len(ns)})"
                lines.append(f'#eval IO.println (normalizeConditional (check {task} ⟨{l["nodes"]},{l["operations"]}⟩)).compress')
            source = self.folder / f"Conditional-{self.counter}.lean"; self.counter += 1
            source.write_text("\n".join(lines)+"\n")
            outputs = [json.loads(x) for x in run(["lake", "env", "lean", str(source)], cwd=ROOT / "formal", timeout=300).splitlines()]
            if len(outputs) != len(batch): raise ValueError("incomplete Lean output")
            lean_outputs.update(zip(batch, outputs))
        results=[]
        for i,(py,js) in enumerate(zip(python,native_js)):
            outputs = {"python": py, "javascript": js, "lean": lean_outputs.get(i)}
            agrees = py["accepted"] == js["accepted"]
            if agrees and py["accepted"]:
                agrees = py["receipt"] == js["receipt"] and modeled_receipt(py["receipt"], cases[i]["task"]["variables"]) == outputs["lean"]
            results.append((agrees, outputs))
        return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certiforge", type=Path, required=True)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", type=int, default=256)
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--mode", choices=("all", "forge", "conditional"), default="all")
    parser.add_argument("--exercise-historical-control", action="store_true",
                        help="Detect and minimize the explicitly labeled pre-repair Boolean-ordering typechecker mismatch")
    parser.add_argument("--exercise-canonical-boundary", action="store_true",
                        help="Replay actual native/API inputs excluded by the canonical-input optimization theorem")
    args = parser.parse_args()
    if not 1 <= args.cases <= 4096: parser.error("--cases must be 1..4096")
    started = time.monotonic(); initial_resource = resource.getrusage(resource.RUSAGE_CHILDREN) if resource else None
    report = {"format": "pcs-runtime-differential-v1", "seed": args.seed, "refinement_proved": False,
              "scientific_authority": False, "sources": {
                  "core": provenance(ROOT, ["pcs/experimental/conditional.py", "formal/PCSForgeRefinement/Syntax.lean", "formal/PCSDecisionDiagram/Conditional.lean"]),
                  "site": provenance(args.site, ["public/conditional-core.mjs", "public/omega-core.mjs"]),
                  "certiforge": provenance(args.certiforge, ["crates/certir/src/lib.rs", "crates/certir-interpreter/src/lib.rs", "Cargo.lock"])},
              "executed_driver_sha256": sha(Path(__file__)),
              "formal_reference_sha256": {str(p.relative_to(ROOT)):sha(p) for p in [ROOT/"formal/PCSForgeRefinement/Syntax.lean", ROOT/"formal/PCSOmega/Formula.lean", *sorted((ROOT/"formal/PCSDecisionDiagram").glob("*.lean"))]},
              "adapter_sha256": {p.name: sha(p) for p in sorted(ADAPTERS.iterdir()) if p.is_file()}, "cases": [], "mismatches": [], "negative_controls": [], "boundary_counterexamples": []}
    with tempfile.TemporaryDirectory(prefix="pcs-runtime-differential-") as tmp:
        folder = Path(tmp)
        if args.mode in ("all", "forge"):
            runner = ForgeRunner(args.certiforge.resolve(), folder)
            vectors = forge_cases(args.seed, args.cases)
            for i,(case,(native,lean)) in enumerate(zip(vectors,runner.evaluate(vectors))):
                row={"domain": "certiforge", "input": case, "rust": native, "lean": lean, "agrees": native == lean}
                report["cases"].append(row)
                if not row["agrees"]:
                    row["minimized"] = minimize(case, lambda c: (lambda p:p[0]!=p[1])(runner.evaluate([c])[0]))
                    report["mismatches"].append(len(report["cases"])-1)
            report["native_probe_sha256"] = sha(runner.binary)
            lock=runner.binary.parents[2]/"Cargo.lock"
            report["native_probe_cargo_lock_sha256"]=sha(lock)
            report["native_probe_cargo_lock"]=lock.read_text()
            if args.exercise_historical_control:
                bad={"kind":"cmp","op":"ult","lhs":{"kind":"const_bool","value":False},"rhs":{"kind":"const_bool","value":True}}
                c={"program":{"name":"historical_bool_ordering","params":[],"body":{"kind":"select","cond":{"kind":"const_bool","value":True},"then_expr":bad,"else_expr":{"kind":"const_bool","value":False}},"ret_ty":"bool"},"inputs":[]}
                native,legacy=runner.evaluate([c],patched=False)[0]
                if native==legacy:raise ValueError("Historical false-reference negative control was not detected")
                minimized=minimize(c,lambda x:(lambda pair:pair[0]!=pair[1])(runner.evaluate([x],patched=False)[0]),budget=16)
                pair=runner.evaluate([minimized["input"]],patched=False)[0]
                report["negative_controls"].append({"name":"pre-repair-typechecker-Boolean-ordering", "input":c,"native_current":native,"lean_explicitly_unpatched":legacy,"minimized":minimized,"minimized_outputs":pair,
                                                    "production_divergence":False,"scope":"Deliberately selects the existing pre-repair Lean checker; current native and patched Lean checker still must agree. This is a shrinking detection control, not a newly discovered runtime bug."})
            if args.exercise_canonical_boundary:
                for width in (8,16,32):
                    ty={"bitvec":f"u{width}"}; x={"kind":"var","name":"x"}
                    p={"name":"canonical_boundary","params":[{"name":"x","ty":ty}],
                       "body":{"kind":"bin_op","op":"or","lhs":x,"rhs":copy.deepcopy(x)},"ret_ty":ty}
                    q={**p,"body":x}; raw={"kind":"bv","width":f"u{width}","bits":1<<width}
                    canonical={**raw,"bits":0}
                    vectors=[{"program":program,"inputs":[value]} for value in (raw,canonical) for program in (p,q)]
                    outputs=runner.evaluate(vectors)
                    if any(native!=lean for native,lean in outputs):raise ValueError("Boundary native/reference executions disagree")
                    if outputs[0][0]["eval"]==outputs[1][0]["eval"] or outputs[2][0]["eval"]!=outputs[3][0]["eval"]:
                        raise ValueError("Canonical-input boundary control failed")
                    report["boundary_counterexamples"].append({"width":width,"rewrite":"or_idempotent", "original":p,"candidate":q,"raw_input":raw,"canonical_input":canonical,
                                                               "native_and_reference_outputs":outputs,"existing_theorem_contradicted":False,
                                                               "scope":"Actual Rust public raw enum input passes type tags but violates Value.WF. The proven rewrite theorem expressly assumes canonical inputs; the CLI's Value::bitvec constructor masks payloads. Not a claim of a reachable website or package vulnerability."})
        if args.mode in ("all", "conditional"):
            runner = ConditionalRunner(args.site.resolve(), folder)
            vectors = conditional_cases(args.seed+1,args.cases)
            # Malformed protocol cases test the actual Python/JS validators only; no Lean decoder claim.
            for change in ({"variables": ["A", "A"]}, {"variables": ["TRUE"]}, {"assumptions": [{}]}, {"source": {"op": "eval"}}):
                c=copy.deepcopy(vectors[0]); c["task"].update(change); vectors.append(c)
            for case,(agrees,outputs) in zip(vectors,runner.evaluate(vectors)):
                row={"domain": "conditional", "input": case, "outputs": outputs, "agrees": agrees}
                report["cases"].append(row)
                if not agrees:
                    # Conditional shrinking must preserve validated schema; failure to execute is not a disagreement.
                    def diverges(c):
                        try: return not runner.evaluate([c])[0][0]
                        except (KeyError,TypeError,ValueError,RuntimeError): return False
                    row["minimized"] = minimize(case,diverges)
                    report["mismatches"].append(len(report["cases"])-1)
    measured=resource.getrusage(resource.RUSAGE_CHILDREN) if resource else None
    report.update({"elapsed_seconds":time.monotonic()-started,"passed":len(report["cases"])-len(report["mismatches"]),
                   "resources":{"child_user_cpu_seconds":measured.ru_utime-initial_resource.ru_utime if measured else None,
                                "child_system_cpu_seconds":measured.ru_stime-initial_resource.ru_stime if measured else None,
                                "largest_child_max_rss_kib_linux":measured.ru_maxrss if measured and sys.platform.startswith("linux") else None,
                                "scope":"Includes native probe build and sequential Lean/native/JS child processes. Linux ru_maxrss is the largest child peak, not simultaneous process-tree memory; parent CPU/RSS and shared services are not included."},
                   "coverage": {"forge":"Native top-level eval, patched type checker, all four widths, eight binary/six comparison/two unary operators, lazy select, arity, duplicate bindings, mismatched inputs/returns and error categories. Formatted mismatch payloads are abstracted.",
                                "conditional":"Python and JavaScript whole receipts (including hashes) compared; Lean all modeled semantic/work/diagram fields compared on valid typed tasks. Malformed validators compared only Python/JS; hashing and JSON decoding are not Lean-proved."}})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x") as file: json.dump(report,file,indent=2,sort_keys=True); file.write("\n")
    print(json.dumps({k:report[k] for k in ("passed","mismatches","elapsed_seconds","refinement_proved")}))
    if report["mismatches"]: raise SystemExit(1)


if __name__ == "__main__": main()
