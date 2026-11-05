#!/usr/bin/env python3
"""Fresh kernel and native checks of the exact selected CertiForge checked wrapper.

This audits a small iterator/early-return Rust fragment, not the native compiler
or top-level program interpreter. Native executions are independent regression
controls; the universal refinement theorem is about the bound fragment semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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
from verify_runtime_refinement import check_sources

SNAPSHOT = ROOT / "formal/source_reference/certiforge/checked-wrapper-v2.rs.txt"
MODULE = ROOT / "formal/tools/RuntimeCheckedBoundary.lean"
CONTROLS = ROOT / "research/runtime-checked-boundary-v2/native_controls.rs"
START, STOP = 168, 179


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_current_source(path: Path) -> str:
    """Bind exact current bytes before executing any proof or native control."""
    lines = path.read_bytes().split(b"\n")
    if len(lines) < STOP:
        raise ValueError("checked-wrapper source window outside file")
    selected = b"\n".join(lines[START - 1:STOP]) + b"\n"
    if selected != SNAPSHOT.read_bytes():
        raise ValueError("checked-wrapper source window changed")
    return hashlib.sha256(selected).hexdigest()


def run_native(certiforge: Path) -> dict:
    started = time.monotonic()
    # Fixed, reviewed test source; the caller can select a checkout but cannot
    # supply commands or submitted code to this local verification utility.
    with tempfile.TemporaryDirectory(prefix="pcs-checked-rust-") as folder:
        fixture = Path(folder)
        (fixture / "src").mkdir()
        (fixture / "src/main.rs").write_bytes(CONTROLS.read_bytes())
        deps = {
            "certir": certiforge / "crates/certir",
            "certir-interpreter": certiforge / "crates/certir-interpreter",
        }
        manifest = '[package]\nname="pcs-checked-native-controls"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\n'
        for name, path in deps.items():
            manifest += f"{name} = {{ path = {json.dumps(str(path))} }}\n"
        (fixture / "Cargo.toml").write_text(manifest)
        proc = subprocess.run(
            ["cargo", "run", "--offline", "--quiet", "--manifest-path", str(fixture / "Cargo.toml"),
             "--target-dir", str(certiforge / "target")],
            cwd=certiforge, text=True, capture_output=True, timeout=180,
        )
    if proc.returncode:
        raise RuntimeError("native checked-wrapper controls failed\n" + proc.stdout + proc.stderr)
    result = json.loads(proc.stdout)
    if result != {"checks": 31, "widths": 4, "failed": 0}:
        raise ValueError("native controls returned an unexpected inventory")
    return {**result, "wall_seconds": round(time.monotonic() - started, 6),
            "test_source_sha256": digest(CONTROLS)}


def run_kernel_negatives(names: list[str]) -> list[dict]:
    """A stale positive AST must not certify changed source, even in fresh Lean."""
    records = []
    for name, old, replacement in (
        ("inverted-condition", b"*bits !=", b"*bits =="),
        ("changed-mask", b"width.mask()", b"0"),
    ):
        with tempfile.TemporaryDirectory(prefix="pcs-checked-negative-") as folder:
            fixture = Path(folder)
            (fixture / "tools").mkdir()
            (fixture / "source_reference/certiforge").mkdir(parents=True)
            module = fixture / "tools/RuntimeCheckedBoundary.lean"
            module.write_bytes(MODULE.read_bytes())
            altered = SNAPSHOT.read_bytes().replace(old, replacement)
            (fixture / "source_reference/certiforge/checked-wrapper-v2.rs.txt").write_bytes(altered)
            started = time.monotonic()
            proc = subprocess.run(["lake", "env", "lean", str(module)], cwd=ROOT / "formal",
                                  text=True, capture_output=True, timeout=180)
        log = proc.stdout + proc.stderr
        if proc.returncode == 0 or "lexLines currentWrapperSource = checkedFn.toks\nis false" not in log:
            raise ValueError("kernel negative did not fail at the source-binding proposition")
        try:
            check_inventory(proc.stdout, names)
        except ValueError:
            pass
        else:
            raise ValueError("failed source-binding axiom inventory was accepted")
        records.append({"name": name, "source_mutation_sha256": hashlib.sha256(altered).hexdigest(),
                        "returncode": proc.returncode, "rejected": True,
                        "wall_seconds": round(time.monotonic() - started, 6), "log": log})
    return records


def verify(certiforge: Path, *, native: bool = False, negatives: bool = False) -> dict:
    certiforge = certiforge.resolve()
    current = certiforge / "crates/certir-interpreter/src/lib.rs"
    binding = check_current_source(current)
    frozen = {path: digest(path) for path in (current, SNAPSHOT, MODULE, CONTROLS)}
    # Existing evaluator and Width helpers retain their original bound windows.
    windows = check_sources({"proof-carrying-science": ROOT, "certiforge": certiforge})
    findings = audit([MODULE])
    if findings:
        raise ValueError("\n".join(findings))
    names = re.findall(r"^#print axioms (\S+)$", MODULE.read_text(), re.M)
    if len(names) != 17 or len(set(names)) != len(names):
        raise ValueError("unexpected checked-wrapper theorem inventory")
    started = time.monotonic()
    result = subprocess.run(["lake", "env", "lean", str(MODULE)], cwd=ROOT / "formal",
                            text=True, capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    axioms = check_inventory(result.stdout, names)
    report = {
        "format": "pcs-runtime-checked-boundary-v2",
        "current_certiforge_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=certiforge, text=True).strip(),
        "current_source_sha256": digest(current),
        "source_window": [START, STOP], "window_sha256": binding,
        "wrapper_snapshot_sha256": digest(SNAPSHOT), "proof_source_sha256": digest(MODULE),
        "existing_certiforge_windows": [row for row in windows if row["component"] == "certiforge"],
        "kernel_theorems": axioms, "axiom_log": result.stdout,
        "kernel_wall_seconds": round(time.monotonic() - started, 6),
        "checked_wrapper_fragment_refinement_proved": True,
        "rust_top_level_eval_extracted": False, "native_compiler_refinement_proved": False,
        "hashmap_implementation_refinement_proved": False,
        "conditional_python_javascript_refinements_proved": False,
        "pcs_scientific_authority": False,
        "scope": "Exact wrapper tokens; finite HashMap values snapshots in arbitrary iteration order; transparent immutable references; existing source-extracted Rust expression semantics; sufficient separate call-depth and iterator fuel. Native controls are testing, not a Rust compiler proof. Nat payloads above u64 are model-only; native u64 values are within this stronger domain.",
    }
    if native:
        report["native_controls"] = run_native(certiforge)
    if negatives:
        report["kernel_negative_controls"] = run_kernel_negatives(names)
    if any(digest(path) != expected for path, expected in frozen.items()):
        raise ValueError("checked-boundary source changed during verification")
    check_current_source(current)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certiforge", type=Path, required=True)
    parser.add_argument("--native", action="store_true", help="Also compile and execute 31 native regressions offline")
    parser.add_argument("--negative-controls", action="store_true", help="Freshly reject two changed-source snapshots in Lean")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify(args.certiforge, native=args.native, negatives=args.negative_controls)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"fresh_theorems": len(report["kernel_theorems"]),
                      "native_checks": report.get("native_controls", {}).get("checks", 0),
                      "kernel_negative_controls": len(report.get("kernel_negative_controls", [])),
                      "wrapper_fragment_refinement_proved": True,
                      "top_level_eval_extracted": False, "pcs_scientific_authority": False}))


if __name__ == "__main__":
    main()
