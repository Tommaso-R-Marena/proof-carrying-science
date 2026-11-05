"""Bounded, independently replayable proof construction for the OLD checker.

Python proposes a partition or scalar counterexample. Lean checks every proof;
neither a Python comparison nor an external caller supplies a verifier verdict.
This research interface does not authorize PCS artifacts or empirical science.
"""
from __future__ import annotations

from fractions import Fraction
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

from pcs import transport_kernel_v1 as model
from pcs import transport_trace_kernel_v1 as trace
from pcs.canonical_json import canonicalize_jcs_bytes

HERE = Path(__file__).resolve().parent
GENERAL = ["PCSPortableTransportV2." + n for n in (
    "rows_sound", "initial_fault_rejects", "recurrence_fault_rejects", "time_fault_rejects")]


def sources():
    return {**trace.sources(), **{name: (HERE / name).read_bytes()
                                 for name in ["RawDecide.lean", "Certificate.lean", "replay.py"]}}


def find_fault(data):
    """Untrusted deterministic witness proposal; the kernel checks its claim."""
    trace.validate(data)
    states = [[Fraction(x) for x in row] for row in data["states"]]
    initial = [Fraction(x) for x in data["model"]["initial"]]
    matrix = [[Fraction(x) for x in row] for row in data["model"]["matrix"]]
    def fault(kind, k, i, observed, expected):
        return {"kind": kind, "step": k, "cell": i, "observed": str(observed),
                "expected": str(expected), "residual": str(observed - expected)}
    for i, expected in enumerate(initial):
        if states[0][i] != expected:
            return fault("initial", 0, i, states[0][i], expected)
    for k in range(data["steps"]):
        for i, row in enumerate(matrix):
            expected = sum((p * x for p, x in zip(row, states[k])), Fraction())
            if states[k + 1][i] != expected:
                return fault("recurrence", k, i, states[k + 1][i], expected)
    dt = Fraction(data["dt"])
    for k, value in enumerate(data["times"]):
        if Fraction(value) != k * dt:
            return fault("time", k, None, Fraction(value), k * dt)
    return None


def render(data, fault=None):
    trace.validate(data)
    if fault is None:
        original = trace.render(data).decode()
        start = original.index("theorem trace_checked :")
        end = original.index("theorem recorded_states_and_times :", start)
        rows = ""
        names = []
        for k in range(data["steps"]):
            name = f"row_{k}"
            cells = []
            for i in range(len(data["model"]["initial"])):
                cell = f"{name}_cell_{i}"
                rows += (f"theorem {cell} : states {k + 1} {i} = "
                         f"step matrix (states {k}) {i} := by pcs_kernel_decide_raw\n")
                cells.append(cell)
                names.append("PCSTransportTraceReplay." + cell)
            cell_cases = "fun impossible => Fin.elim0 impossible"
            for cell in reversed(cells):
                cell_cases = f"Fin.cases {cell} ({cell_cases})"
            rows += (f"theorem {name} : ∀ i, states {k + 1} i = "
                     f"step matrix (states {k}) i := by\n  exact {cell_cases}\n")
            names.append("PCSTransportTraceReplay." + name)
        cases = "fun impossible => Fin.elim0 impossible"
        for k in reversed(range(data["steps"])):
            cases = f"Fin.cases row_{k} ({cases})"
        assembly = "  exact " + cases + "\n"
        rows += (f"theorem recurrence_rows : ∀ k : Fin {data['steps']}, ∀ i, "
                 "states (k.val + 1) i = step matrix (states k.val) i := by\n" + assembly)
        names.append("PCSTransportTraceReplay.recurrence_rows")
        rows += (f"theorem trace_checked : PCSReal.TransportTrace.check matrix initial states times dt {data['steps']} = true := by\n"
                 "  exact PCSPortableTransportV2.rows_sound (by pcs_kernel_decide_raw) "
                 "recurrence_rows (by pcs_kernel_decide_raw)\n")
        text = original[:start] + rows + original[end:]
        text += "\n" + "\n".join("#print axioms " + n for n in names) + "\n"
        expected = model.REPLAY_THEOREMS + trace.LITERAL + names
    else:
        # A proposed witness is never trusted: an invalid location, equality,
        # or source mismatch makes the generated Lean proof fail.
        if set(fault) != {"kind", "step", "cell", "observed", "expected", "residual"}:
            raise ValueError("Exact fault fields required")
        k, i, kind = fault["step"], fault["cell"], fault["kind"]
        if type(k) is not int or not 0 <= k <= data["steps"]:
            raise ValueError("Bounded integer fault index required")
        if kind in {"initial", "recurrence"} and (type(i) is not int or not 0 <= i < len(data["model"]["initial"])):
            raise ValueError("Bounded cell index required")
        if kind == "initial" and k == 0:
            proposition = f"states 0 {i} ≠ initial {i}"
            application = f"PCSPortableTransportV2.initial_fault_rejects {i} counterexample"
        elif kind == "recurrence" and k < data["steps"]:
            proposition = f"states {k + 1} {i} ≠ step matrix (states {k}) {i}"
            application = f"PCSPortableTransportV2.recurrence_fault_rejects ⟨{k}, by decide⟩ {i} counterexample"
        elif kind == "time" and i is None:
            proposition = f"times {k} ≠ ({k} : ℚ) * dt"
            application = f"PCSPortableTransportV2.time_fault_rejects ⟨{k}, by decide⟩ counterexample"
        else:
            raise ValueError("Supported fault kind/location required")
        literals = {}
        for field in ["observed", "expected", "residual"]:
            value = fault[field]
            if type(value) is not str or len(value) > 4096 or str(Fraction(value)) != value:
                raise ValueError("Canonical bounded rational fault values required")
            literals[field] = model._literal(value)
        observed_expr, expected_expr = proposition.split(" ≠ ", 1)
        value_proofs = (
            f"theorem fault_observed : {observed_expr} = {literals['observed']} := by pcs_kernel_decide_raw\n"
            f"theorem fault_expected : {expected_expr} = {literals['expected']} := by pcs_kernel_decide_raw\n"
            f"theorem fault_residual : ({observed_expr}) - ({expected_expr}) = {literals['residual']} := by pcs_kernel_decide_raw\n")
        original = trace.render(data, negative=True).decode()
        start = original.index("theorem trace_rejected :")
        end = original.index("end PCSTransportTraceReplay", start)
        text = (original[:start] + value_proofs + f"theorem counterexample : {proposition} := by pcs_kernel_decide_raw\n"
                f"theorem trace_rejected : PCSReal.TransportTrace.check matrix initial states times dt {data['steps']} = false :=\n"
                f"  {application}\n" + original[end:] + "\n#print axioms PCSTransportTraceReplay.counterexample\n")
        value_names = ["PCSTransportTraceReplay.fault_" + field for field in ["observed", "expected", "residual"]]
        text += "\n" + "\n".join("#print axioms " + name for name in value_names) + "\n"
        expected = model.REPLAY_THEOREMS + [trace.NEGATIVE, "PCSTransportTraceReplay.counterexample"] + value_names
    text = "import RawDecide\nimport Certificate\n" + text.replace("by decide +kernel", "by pcs_kernel_decide_raw")
    return text.encode(), expected


def replay(contract_raw: bytes, trajectory_raw: bytes, *, timeout=120):
    if type(timeout) not in {int, float} or not math.isfinite(timeout) or not 0 < timeout <= 180:
        raise ValueError("Finite wall budget in (0,180] required")
    start = time.monotonic()
    deadline = start + timeout
    result = {"format": "pcs-portable-transport-replay-v2", "kernel_supported": False,
              "negative_kernel_checked": False, "all_time_model_kernel_supported": False,
              "status": "UNAVAILABLE_OR_EXHAUSTED", "scientific_acceptance": False,
              "pcs_authority": False, "empirical_validity": "OPEN",
              "implementation_correspondence": "OPEN", "continuum_accuracy": "OPEN",
              "executions": [], "axiom_closures": {}}
    def remaining():
        value = deadline - time.monotonic()
        if value <= 0:
            raise subprocess.TimeoutExpired("portable trace", timeout)
        return value
    try:
        if type(contract_raw) is not bytes or type(trajectory_raw) is not bytes:
            raise ValueError("Captured immutable input bytes required")
        data = trace.prepare(contract_raw, trajectory_raw)
        frozen = sources()
        hashes = {n: model.sha(v) for n, v in frozen.items()}
        fault = find_fault(data)
        proof, expected = render(data, fault)
        result.update(contract_sha256=model.sha(contract_raw), trajectory_sha256=model.sha(trajectory_raw),
                      certificate_sha256=model.sha(canonicalize_jcs_bytes(data)),
                      source_sha256=hashes, proof_sha256=model.sha(proof),
                      proof=proof.decode(), trace_certificate=data, fault=fault)
        lean, env, version = model._environment(min(30, remaining()))
        result.update(lean_version=version, lean_sha256=model.sha(Path(lean).read_bytes()))
        with tempfile.TemporaryDirectory(prefix="pcs-portable-replay-") as folder:
            private = Path(folder)
            (private / "PCSReal").mkdir()
            env = dict(env, LEAN_PATH=str(private) + os.pathsep + env["LEAN_PATH"])
            def run(path, raw, output=False):
                path.write_bytes(raw)
                cmd = [lean, "-j1", "-M2048", "-D", "Elab.async=false", "--root=" + folder]
                if output:
                    cmd += ["-o", str(path.with_suffix(".olean"))]
                cmd.append(str(path))
                p = subprocess.run(cmd, cwd=private, env=env, capture_output=True,
                                   text=True, timeout=remaining())
                result["executions"].append({"command": cmd, "source_sha256": model.sha(raw),
                                              "exitcode": p.returncode, "stdout": p.stdout, "stderr": p.stderr})
                if p.returncode != 0:
                    raise ValueError("Actual Lean proof/source rejected")
                return p.stdout
            for name, names in [("PCSReal/Transport.lean", model.GENERAL_THEOREMS),
                                ("PCSReal/TransportTrace.lean", trace.GENERAL),
                                ("RawDecide.lean", []), ("Certificate.lean", GENERAL)]:
                raw = frozen[name]
                if name.startswith("PCSReal/"):
                    raw += ("\n" + "\n".join("#print axioms " + n for n in names) + "\n").encode()
                stdout = run(private / name, raw, output=True)
                if names:
                    result["axiom_closures"].update(model._inventory(stdout, names))
            stdout = run(private / "Replay.lean", proof)
            result["axiom_closures"].update(model._inventory(stdout, expected))
        if hashes != {n: model.sha(v) for n, v in sources().items()}:
            raise ValueError("Sources changed during replay")
        result.update(status="TRACE_FALSIFIED" if fault else "KERNEL_CHECKED",
                      kernel_supported=fault is None, negative_kernel_checked=fault is not None,
                      all_time_model_kernel_supported=True, sources_stable=True)
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError, RecursionError) as e:
        result.update(kernel_supported=False, negative_kernel_checked=False,
                      all_time_model_kernel_supported=False, error=f"{type(e).__name__}: {e}")
    result["wall_seconds"] = round(time.monotonic() - start, 6)
    return result


def export(out: Path, result: dict, contract_raw: bytes, trajectory_raw: bytes):
    """Evidence convenience, not a signed receipt or a verifier verdict API."""
    frozen = sources()
    if result.get("source_sha256") != {n: model.sha(v) for n, v in frozen.items()}:
        raise ValueError("Evidence does not match current sources")
    if (result.get("contract_sha256") != model.sha(contract_raw)
            or result.get("trajectory_sha256") != model.sha(trajectory_raw)
            or model.sha(result["proof"].encode()) != result["proof_sha256"]):
        raise ValueError("Evidence does not match captured input/proof bytes")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    (out / "contract.json").write_bytes(contract_raw)
    (out / "trajectory.csv").write_bytes(trajectory_raw)
    (out / "Replay.lean").write_text(result["proof"])
    for name, raw in frozen.items():
        path = out / "sources" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    inventory = {str(p.relative_to(out)): model.sha(p.read_bytes())
                 for p in sorted(out.rglob("*")) if p.is_file()}
    (out / "SHA256.json").write_text(json.dumps(inventory, indent=2) + "\n")


def verify_export(folder: Path, *, timeout=120):
    """Reviewer reexecutes actual Lean; no stored result is a verifier verdict.

    Source authenticity still requires the reviewer's independently reviewed
    checkout. Hashes alone are not provenance authentication.
    """
    from pcs.jsonio import strict_json_loads
    folder = Path(folder)
    def read(path, limit):
        with path.open("rb") as f:
            raw = f.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("Bounded evidence file required")
        return raw
    inventory = strict_json_loads(read(folder / "SHA256.json", 128 * 1024))
    frozen = sources()
    names = {"contract.json", "trajectory.csv", "Replay.lean", "result.json"} | {"sources/" + name for name in frozen}
    if type(inventory) is not dict or set(inventory) != names:
        raise ValueError("Exact evidence inventory required")
    snapshot = {}
    total = 0
    for name in sorted(names):
        raw = read(folder / name, 8 * 1024 * 1024)
        total += len(raw)
        if total > 32 * 1024 * 1024 or model.sha(raw) != inventory[name]:
            raise ValueError("Changed or oversized evidence material")
        snapshot[name] = raw
    if any(snapshot["sources/" + name] != raw for name, raw in frozen.items()):
        raise ValueError("Evidence source differs from independently reviewed checkout")
    # Result JSON is captured/hash checked but never read as a success verdict.
    # Exact source-bound proof must match receiving-side regeneration, too.
    contract, trajectory = snapshot["contract.json"], snapshot["trajectory.csv"]
    data = trace.prepare(contract, trajectory)
    proof, _ = render(data, find_fault(data))
    if snapshot["Replay.lean"] != proof:
        raise ValueError("Changed or noncanonical generated proof")
    return replay(contract, trajectory, timeout=timeout)


def main():
    import argparse
    p = argparse.ArgumentParser(__doc__)
    sub = p.add_subparsers(dest="operation", required=True)
    check = sub.add_parser("check")
    check.add_argument("contract", type=Path)
    check.add_argument("trajectory", type=Path)
    check.add_argument("out", type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("evidence", type=Path)
    args = p.parse_args()
    try:
        if args.operation == "verify":
            result = verify_export(args.evidence)
        else:
            def capture(path):
                with path.open("rb") as f:
                    raw = f.read(trace.workflow.MAX_BYTES + 1)
                if len(raw) > trace.workflow.MAX_BYTES:
                    raise ValueError("Bounded captured input required")
                return raw
            contract, trajectory = capture(args.contract), capture(args.trajectory)
            result = replay(contract, trajectory)
            if "proof" in result:
                export(args.out, result, contract, trajectory)
        print(json.dumps({k: result.get(k) for k in [
            "status", "kernel_supported", "negative_kernel_checked", "fault",
            "proof_sha256", "wall_seconds", "error", "pcs_authority", "scientific_acceptance"]}))
        raise SystemExit(0 if result["kernel_supported"] else 10 if result["negative_kernel_checked"] else 20)
    except (OSError, ValueError, KeyError) as e:
        print(json.dumps({"status": "REJECTED", "error": f"{type(e).__name__}: {e}",
                          "kernel_supported": False, "pcs_authority": False}))
        raise SystemExit(20)


if __name__ == "__main__":
    main()
