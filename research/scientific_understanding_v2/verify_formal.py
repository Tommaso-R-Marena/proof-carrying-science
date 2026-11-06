"""Compile and axiom-audit the isolated research Lean source with bound receipts.

This checks Lean source, never the Python checker implementation. A successful
receipt explicitly leaves Python-to-Lean refinement OPEN and authority false.
The dimensions profile requires an empty axiom audit; conservation reports and
permits only Lean's standard propext, as a separate, explicitly named profile.
The sampling profile checks a closed finite counterexample with an empty audit.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_LEAN = Path(os.environ.get("PCS_LEAN") or shutil.which("lean") or "/workspace/.onboarding/tools/lean-4.28.0-linux/bin/lean")
REQUIRED_THEOREMS = (
    "check_sound", "check_complete", "undeclared_symbol_untypable", "dimension_unique",
    "research_has_no_authority", "nat_mul_assoc_constructive", "nat_product_reorder",
    "scale_multiplicative_compatibility", "minutes_to_seconds_exact",
)

CONSERVATION_THEOREMS = (
    "dot_zero_vector", "add_vector_length", "dot_add", "dot_scale",
    "null_columns_have_shape", "linear_combination_length", "dot_linear_combination",
    "conserved_weighted_flux", "conserved_linear_combination",
)
SAMPLING_THEOREMS = (
    "sampling_zeros", "ghost_fifty_nonzero", "sample_agreement_does_not_imply_global_equality",
)
PROFILES = {
    "dimensions": {"file": "Dimensions.lean", "theorems": REQUIRED_THEOREMS, "allowed_axioms": ()},
    "conservation": {"file": "Conservation.lean", "theorems": CONSERVATION_THEOREMS, "allowed_axioms": ("propext",)},
    "sampling": {"file": "Sampling.lean", "theorems": SAMPLING_THEOREMS, "allowed_axioms": ()},
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _lean_code(source: str) -> str:
    """Remove comments and string literals before checking source declarations."""
    result: list[str] = []
    i, depth, string = 0, 0, False
    while i < len(source):
        pair = source[i:i + 2]
        if depth:
            if pair == "/-":
                depth += 1
                i += 2
            elif pair == "-/":
                depth -= 1
                i += 2
            else:
                result.append("\n" if source[i] == "\n" else " ")
                i += 1
        elif string:
            if source[i] == "\\":
                i += 2
            elif source[i] == '"':
                string = False
                i += 1
            else:
                result.append("\n" if source[i] == "\n" else " ")
                i += 1
        elif pair == "/-":
            depth = 1
            i += 2
        elif pair == "--":
            end = source.find("\n", i)
            i = len(source) if end < 0 else end
        elif source[i] == '"':
            string = True
            i += 1
        else:
            result.append(source[i])
            i += 1
    return "".join(result)


def inspect_source(path: Path, required_theorems: tuple[str, ...] = REQUIRED_THEOREMS) -> dict[str, Any]:
    code = _lean_code(path.read_text())
    forbidden = sorted(set(re.findall(r"\b(?:sorry|admit|axiom|unsafe|extern|implemented_by)\b", code)))
    imports = re.findall(r"^\s*import\s+([^\n]+)", code, flags=re.MULTILINE)
    bad_imports = [module for line in imports for module in line.split() if not (module == "Init" or module.startswith("Init.") or module == "Std" or module.startswith("Std."))]
    declarations = re.findall(r"^\s*(?:private\s+)?theorem\s+([A-Za-z_][A-Za-z_0-9]*)", code, flags=re.MULTILINE)
    return {"source_sha256": _sha256(path), "forbidden_tokens": forbidden,
            "unexpected_imports": bad_imports, "theorem_declarations": declarations,
            "required_theorems_present": all(name in declarations for name in required_theorems)}


def parse_axiom_audit(stdout: str) -> dict[str, dict[str, Any]]:
    audit: dict[str, dict[str, Any]] = {}
    empty_pattern = r"'([^']+)' does not depend on any axioms"
    for name in re.findall(empty_pattern, stdout):
        audit[name.rsplit(".", 1)[-1]] = {"name": name, "axioms": [], "empty": True}
    for name, dependencies in re.findall(r"'([^']+)' depends on axioms:\s*\[([^\]]*)\]", stdout):
        audit[name.rsplit(".", 1)[-1]] = {"name": name, "axioms": [x.strip() for x in dependencies.split(",") if x.strip()], "empty": not dependencies.strip()}
    return audit


def verify_formal(lean_binary: str | Path | None = None, *, source: str | Path | None = None, timeout: int = 120, profile: str = "dimensions") -> dict[str, Any]:
    """Run a fresh bounded Lean process and return a source/compiler-bound receipt."""
    if profile not in PROFILES:
        raise ValueError("Unsupported isolated formal profile")
    selected = PROFILES[profile]
    source_path = Path(source) if source is not None else ROOT / "formal" / selected["file"]
    required_theorems = selected["theorems"]
    allowed_axioms = set(selected["allowed_axioms"])
    lean = Path(lean_binary) if lean_binary is not None else DEFAULT_LEAN
    if not lean.is_file() and lean_binary is None:
        lean = Path(shutil.which("lean") or str(DEFAULT_LEAN))
    receipt: dict[str, Any] = {
        "schema": "scientific-formal-receipt/v2", "status": "UNKNOWN", "authority": False,
        "profile": profile, "allowed_lean_axioms": sorted(allowed_axioms),
        "required_theorems": list(required_theorems),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source_path.resolve()), "compiler_path": str(lean.resolve()),
        "python_lean_refinement": "OPEN",
        "scope": ("isolated Lean expression typing, exact pair-rational unit scaling, and research policy" if profile == "dimensions"
                  else "finite exact integer stoichiometry and weighted conservation under explicit shape/nullspace hypotheses" if profile == "conservation"
                  else "closed integer polynomial counterexample to inferring global equality from twelve fixed samples; rational rescaling is separate, Python refinement OPEN"),
        "diagnostics": [],
    }
    if not source_path.is_file() or not lean.is_file():
        receipt["diagnostics"].append("Lean compiler or isolated source is unavailable")
        return receipt
    inspection = inspect_source(source_path, required_theorems)
    receipt.update(inspection)
    receipt["compiler_sha256"] = _sha256(lean)
    shared = lean.parent.parent / "lib" / "lean" / "libleanshared.so"
    if shared.is_file():
        receipt["compiler_shared_library_sha256"] = _sha256(shared)
    try:
        version = subprocess.run([str(lean), "--version"], capture_output=True, text=True, timeout=15, check=False)
        receipt["compiler_version"] = version.stdout.strip()
        command = [str(lean), "-M512", "-j1", str(source_path.resolve())]
        receipt["command"] = command
        result = subprocess.run(command, cwd=str(source_path.parent), env={"PATH": str(lean.parent)+":/usr/bin:/bin", "LANG":"C.UTF-8", "LEAN_NUM_THREADS":"1"}, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        receipt["diagnostics"].append(f"Compiler invocation unavailable or timed out: {type(exc).__name__}")
        return receipt
    receipt.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr,
                   stdout_sha256=hashlib.sha256(result.stdout.encode()).hexdigest())
    audit = parse_axiom_audit(result.stdout)
    receipt["axiom_audit"] = audit
    names = set(inspection["theorem_declarations"])
    receipt["all_declared_theorems_audited"] = all(name in audit for name in names)
    receipt["all_declared_axiom_audits_empty"] = all(name in audit and audit[name]["empty"] for name in names)
    receipt["all_declared_axiom_audits_permitted"] = all(name in audit and set(audit[name]["axioms"]) <= allowed_axioms for name in names)
    receipt["required_audit_empty"] = all(name in audit and audit[name]["empty"] for name in required_theorems)
    receipt["required_audit_permitted"] = all(name in audit and set(audit[name]["axioms"]) <= allowed_axioms for name in required_theorems)
    receipt["source_stable_during_compile"] = _sha256(source_path) == receipt["source_sha256"]
    passed = ("version 4.28.0," in receipt["compiler_version"] and result.returncode == 0 and not receipt["forbidden_tokens"] and not receipt["unexpected_imports"]
              and receipt["required_theorems_present"] and receipt["all_declared_theorems_audited"]
              and receipt["all_declared_axiom_audits_permitted"] and receipt["required_audit_permitted"]
              and receipt["source_stable_during_compile"])
    receipt["status"] = "VERIFIED" if passed else "REFUTED"
    if not passed:
        receipt["diagnostics"].append("Compilation, isolated-source policy, or complete declared-axiom audit failed")
    return receipt


def replay_formal_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Recompile current source and compare bindings; claimed status is not trusted."""
    fresh = verify_formal(receipt.get("compiler_path"), source=receipt.get("source_path"), profile=receipt.get("profile", "dimensions"))
    fields = ("source_sha256", "compiler_sha256", "compiler_shared_library_sha256", "compiler_version")
    fresh["replay_bindings_match"] = all(fresh.get(key) == receipt.get(key) for key in fields)
    if not fresh["replay_bindings_match"]:
        fresh["status"] = "REFUTED"
        fresh["diagnostics"].append("Source or compiler binding differs from the supplied receipt")
    return fresh


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean", type=Path)
    parser.add_argument("--profile", choices=tuple(PROFILES), default="dimensions")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    result = replay_formal_receipt(json.loads(args.replay.read_text())) if args.replay else verify_formal(args.lean, profile=args.profile)
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)
    print(serialized, end="")
    return 0 if result["status"] == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
