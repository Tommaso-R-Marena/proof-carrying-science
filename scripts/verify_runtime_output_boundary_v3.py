#!/usr/bin/env python3
"""Source-bound output continuation checking against a receiver-selected Rust checkout.

Input binding, native compilation, and HashMap implementation remain outside the
proof. This utility freshly compiles its v2 and Value::ty dependencies into an
isolated temporary Lean search path, so no existing tool olean substitutes for them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_lean_source import audit
from verify_omega_dd_formal import check_inventory
from verify_runtime_refinement import check_sources, check_window

MODULE = ROOT / "formal/tools/RuntimeOutputBoundaryV3.lean"
FOLDER = ROOT / "research/runtime-refinement-v3"
CONTROLS = FOLDER / "native_output_controls.rs"
WINDOWS = [
    ("crates/certir-interpreter/src/lib.rs", 158, 162, "eval-output.rs.txt"),
    ("crates/certir/src/lib.rs", 10, 17, "width-equality.rs.txt"),
    ("crates/certir/src/lib.rs", 59, 64, "type-equality.rs.txt"),
]
SNAPSHOTS = ROOT / "formal/source_reference/certiforge/runtime-v3"
DEPENDENCIES = [ROOT / "formal/tools/RuntimeCheckedBoundary.lean", ROOT / "formal/tools/RuntimeValueType.lean"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_selected_window(current: Path, start: int, stop: int, snapshot: Path) -> str:
    lines = current.read_bytes().split(b"\n")
    if not 1 <= start <= stop <= len(lines):
        raise ValueError("output-boundary source window outside file")
    selected = b"\n".join(lines[start - 1:stop]) + b"\n"
    if selected != snapshot.read_bytes():
        raise ValueError(f"output-boundary source window changed: {snapshot.name}")
    return hashlib.sha256(selected).hexdigest()


def theorem_names(module: Path) -> list[str]:
    names = re.findall(r"^#print axioms (\S+)$", module.read_text(), re.M)
    if not names or len(names) != len(set(names)):
        raise ValueError("missing or duplicate theorem inventory")
    return names


def execute(command: list[str], *, cwd: Path, env: dict | None = None) -> dict:
    try:
        import resource
    except ImportError:
        resource = None
    usage = resource.getrusage(resource.RUSAGE_CHILDREN) if resource else None
    started = time.monotonic()
    proc = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, timeout=180)
    cost = {"wall_seconds": round(time.monotonic() - started, 6)}
    if resource:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        rss_kib = after.ru_maxrss / 1024 if sys.platform == "darwin" else after.ru_maxrss
        cost.update({"child_cpu_user_seconds": round(after.ru_utime - usage.ru_utime, 6),
                     "child_cpu_system_seconds": round(after.ru_stime - usage.ru_stime, 6),
                     "process_cumulative_max_child_rss_kib": rss_kib})
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr, "cost": cost}


def native_controls(certiforge: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="pcs-output-native-v3-") as folder:
        fixture = Path(folder)
        (fixture / "src").mkdir()
        (fixture / "src/main.rs").write_bytes(CONTROLS.read_bytes())
        manifest = '[package]\nname="pcs-output-native-controls-v3"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\n'
        for name in ("certir", "certir-interpreter"):
            manifest += f"{name} = {{ path = {json.dumps(str(certiforge / 'crates' / name))} }}\n"
        (fixture / "Cargo.toml").write_text(manifest)
        record = execute(["cargo", "run", "--offline", "--quiet", "--manifest-path", str(fixture / "Cargo.toml"),
                          "--target-dir", str(certiforge / "target")], cwd=certiforge)
    if record["returncode"]:
        raise RuntimeError("native output-boundary controls failed\n" + record["stdout"] + record["stderr"])
    result = json.loads(record["stdout"])
    if result != {"checks": 40, "type_pairs": 25, "widths": 4, "failed": 0}:
        raise ValueError("unexpected native control inventory")
    return {**result, "cost": record["cost"], "test_source_sha256": sha(CONTROLS)}


def verify(certiforge: Path, *, native: bool = False, negatives: bool = False) -> dict:
    certiforge = certiforge.resolve()
    current = [certiforge / "crates/certir-interpreter/src/lib.rs", certiforge / "crates/certir/src/lib.rs"]
    wrapper = ROOT / "formal/source_reference/certiforge/checked-wrapper-v2.rs.txt"
    value_type_snapshot = ROOT / "formal/source_reference/certiforge/crates/certir-interpreter/src/lib.rs.txt"
    frozen_paths = [MODULE, CONTROLS, wrapper, value_type_snapshot, *DEPENDENCIES, *current,
                    *(SNAPSHOTS / row[3] for row in WINDOWS)]
    frozen = {path: sha(path) for path in frozen_paths}
    windows = [{"source": source, "lines": [start, stop], "snapshot": filename,
                "sha256": check_selected_window(certiforge / source, start, stop, SNAPSHOTS / filename)}
               for source, start, stop, filename in WINDOWS]
    original_windows = check_sources({"proof-carrying-science": ROOT, "certiforge": certiforge})
    # Value::ty and the v2 checked wrapper are direct dependencies beyond the original windows.
    type_helper = check_window(value_type_snapshot.read_bytes(), current[0].read_bytes(), 21, 26)
    check_selected_window(current[0], 168, 179, wrapper)
    findings = audit([MODULE, *DEPENDENCIES])
    if findings:
        raise ValueError("\n".join(findings))
    names = theorem_names(MODULE)
    if len(names) != 9:
        raise ValueError("unexpected v3 theorem inventory")
    dependency_receipts = []
    negative_receipts = []
    with tempfile.TemporaryDirectory(prefix="pcs-output-lean-v3-") as folder:
        fixture = Path(folder)
        (fixture / "tools").mkdir()
        for dependency in DEPENDENCIES:
            output = fixture / "tools" / (dependency.stem + ".olean")
            result = execute(["lake", "env", "lean", "-o", str(output), str(dependency)], cwd=ROOT / "formal")
            if result["returncode"]:
                raise RuntimeError(result["stdout"] + result["stderr"])
            inventory = check_inventory(result["stdout"], theorem_names(dependency))
            dependency_receipts.append({"module": str(dependency.relative_to(ROOT)), "source_sha256": sha(dependency),
                                        "kernel_theorems": inventory, "cost": result["cost"]})
        env = dict(os.environ)
        env["LEAN_PATH"] = str(fixture) + (os.pathsep + env["LEAN_PATH"] if env.get("LEAN_PATH") else "")
        result = execute(["lake", "env", "lean", str(MODULE)], cwd=ROOT / "formal", env=env)
        if result["returncode"]:
            raise RuntimeError(result["stdout"] + result["stderr"])
        inventory = check_inventory(result["stdout"], names)
        if negatives:
            negative_root = fixture / "negative"
            (negative_root / "tools").mkdir(parents=True)
            snapshots = negative_root / "source_reference/certiforge/runtime-v3"
            snapshots.mkdir(parents=True)
            negative_module = negative_root / "tools/RuntimeOutputBoundaryV3.lean"
            negative_module.write_bytes(MODULE.read_bytes())
            for snapshot in SNAPSHOTS.iterdir():
                (snapshots / snapshot.name).write_bytes(snapshot.read_bytes())
            original = (SNAPSHOTS / "eval-output.rs.txt").read_bytes()
            for name, old, new in (("inverted-return-guard", b"!=", b"=="),
                                   ("unchecked-expression-call", b"eval_expr_checked", b"eval_expr")):
                changed = original.replace(old, new)
                (snapshots / "eval-output.rs.txt").write_bytes(changed)
                negative = execute(["lake", "env", "lean", str(negative_module)], cwd=ROOT / "formal", env=env)
                log = negative["stdout"] + negative["stderr"]
                if negative["returncode"] == 0 or "Tactic `decide` proved that the proposition" not in log or "is false" not in log:
                    raise ValueError("source mutation did not fail its source-binding theorem")
                try:
                    check_inventory(negative["stdout"], names)
                except ValueError:
                    pass
                else:
                    raise ValueError("failed source-binding inventory was accepted")
                negative_receipts.append({"name": name, "rejected": True, "returncode": negative["returncode"],
                                          "changed_source_sha256": hashlib.sha256(changed).hexdigest(),
                                          "cost": negative["cost"], "log": log})
    report = {
        "format": "pcs-runtime-output-boundary-v3",
        "certiforge_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=certiforge, text=True).strip(),
        "actual_source_sha256": {str(path.relative_to(certiforge)): frozen[path] for path in current},
        "source_windows": windows,
        "original_certiforge_windows": [row for row in original_windows if row["component"] == "certiforge"],
        "value_type_helper_lines": [21, 26], "value_type_helper_sha256": type_helper,
        "proof_source_sha256": frozen[MODULE], "fresh_dependency_checks": dependency_receipts,
        "verifier_source_sha256": sha(Path(__file__)),
        "kernel_theorems": inventory, "axiom_log": result["stdout"], "cost": result["cost"],
        "kernel_negative_controls": negative_receipts,
        "source_bound_output_continuation_refinement_proved": True,
        "complete_top_level_eval_extracted": False, "input_binding_loop_extracted": False,
        "native_compiler_correctness_proved": False, "hashmap_implementation_refinement_proved": False,
        "python_javascript_conditional_refinements_proved": False, "pcs_scientific_authority": False,
        "scope": "Current eval lines 158–162 after input binding; exact Value::ty helper, derived typed enum equality, checked expression wrapper, question-mark error propagation and return-type rejection. Store is receiver-supplied result of the unextracted input phase. Native executions test the complete function without proving the omitted phase or compiler.",
    }
    if native:
        report["native_controls"] = native_controls(certiforge)
    if any(sha(path) != expected for path, expected in frozen.items()):
        raise ValueError("source changed during output-boundary verification")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certiforge", type=Path, required=True)
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--negative-controls", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify(args.certiforge, native=args.native, negatives=args.negative_controls)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"fresh_theorems": len(report["kernel_theorems"]),
                      "fresh_dependency_theorems": sum(len(row["kernel_theorems"]) for row in report["fresh_dependency_checks"]),
                      "native_checks": report.get("native_controls", {}).get("checks", 0),
                      "kernel_negative_controls": len(report["kernel_negative_controls"]),
                      "source_bound_output_continuation_refinement_proved": True,
                      "complete_top_level_eval_extracted": False, "pcs_scientific_authority": False}))


if __name__ == "__main__":
    main()
