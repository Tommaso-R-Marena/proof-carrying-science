"""Replay the abstract dependency theorem with an actual, bounded Lean process.

Run ``python -m research.scientific_intake_v1.verify_formal``. The receipt binds
the checked source, compiler executable, verifier and emitted proof object. It
does not certify refinement of Python dependency discovery or filesystem access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import tempfile
from typing import Any

SOURCE = Path(__file__).resolve().parent / "formal" / "Incremental.lean"
DEFAULT_LEAN = Path("/workspace/.onboarding/tools/lean-4.28.0-linux/bin/lean")
THEOREMS = (
    "PCSScientificIntake.projection_congr",
    "PCSScientificIntake.fixed_checker_reuse",
    "PCSScientificIntake.policy_bound_reuse",
    "PCSScientificIntake.closed_contains_reachable",
    "PCSScientificIntake.closed_dependency_reuse",
)
ASSUMPTIONS = [
    "The checker is one fixed pure function of the projected inputs and fixed policy.",
    "The declared dependency projection contains every source input used by that checker.",
    "Retained dependencies are closed under the supplied dependency relation.",
    "Snapshot equality means equality of the actual named source bytes, not merely a claimed digest.",
]
LIMITATIONS = [
    "Abstract conditional theorem only; Python parser/dependency discovery refinement is unproved.",
    "Host integrity, authentic byte observations, digest collision resistance and external tool semantics are assumptions.",
    "No scientific claim, imported proof, neural prediction or production admission receives authority from this receipt.",
]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def lean_path(explicit: str | Path | None = None) -> Path | None:
    requested = explicit or os.environ.get("PCS_LEAN")
    if requested:
        candidate = Path(requested).expanduser().resolve()
        return candidate if candidate.is_file() and os.access(candidate, os.X_OK) else None
    if DEFAULT_LEAN.is_file():
        return DEFAULT_LEAN.resolve()
    found = shutil.which("lean")
    return Path(found).resolve() if found else None


def _limits() -> None:
    # Lean reserves virtual address space for its runtime and mapped oleans;
    # its separate -M512 limit bounds allocated elaborator memory.
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, 2 * 1024 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _axiom_audit(stdout: str) -> dict[str, list[str]]:
    reports = {}
    for theorem in THEOREMS:
        pattern = r"'" + re.escape(theorem) + r"' (does not depend on any axioms|depends on axioms: \[([^\]]*)\])"
        matches = list(re.finditer(pattern, stdout))
        if len(matches) != 1:
            raise ValueError("missing or duplicate actual axiom report for " + theorem)
        axioms = [] if matches[0].group(1).startswith("does not") else [part.strip() for part in matches[0].group(2).split(",") if part.strip()]
        if axioms:
            raise ValueError("theorem depends on an axiom: " + theorem)
        reports[theorem] = axioms
    return reports


def verify(*, lean: str | Path | None = None, output: str | Path | None = None) -> dict[str, Any]:
    source_raw = SOURCE.read_bytes()
    receipt: dict[str, Any] = {
        "format": "pcs-scientific-intake-formal-v1", "status": "ERROR",
        "source": {"path": "research/scientific_intake_v1/formal/Incremental.lean", "sha256": _sha(source_raw)},
        "verifier_sha256": _sha(Path(__file__).read_bytes()),
        "theorems": list(THEOREMS), "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS), "production_authority": "NONE",
    }
    executable = lean_path(lean)
    if executable is None:
        receipt.update(status="UNAVAILABLE", reason="Lean executable unavailable; no proof replay occurred")
    else:
        try:
            if len(source_raw) > 100_000 or re.search(rb"(?m)^\s*(?:axiom|unsafe)\b|\bsorry\b", source_raw):
                raise ValueError("source bound or forbidden declaration")
            compiler_raw = executable.read_bytes()
            compiler_sha = _sha(compiler_raw)
            env = {"PATH": str(executable.parent) + ":/usr/bin:/bin", "LANG": "C.UTF-8", "LEAN_NUM_THREADS": "1"}
            version = subprocess.run([str(executable), "--version"], capture_output=True, check=False, timeout=10, env=env)
            version_text = version.stdout.decode("utf-8", errors="strict").strip()
            receipt["toolchain"] = {"path": str(executable), "sha256": compiler_sha, "version": version_text}
            if version.returncode or not re.search(r"version 4\.28\.0(?:,|\))", version_text):
                raise ValueError("Lean 4.28.0 is required for this receipt format")
            with tempfile.TemporaryDirectory(prefix="pcs-intake-formal-") as directory:
                root = Path(directory)
                source = root / "Incremental.lean"
                proof = root / "Incremental.olean"
                source.write_bytes(source_raw)
                completed = subprocess.run([str(executable), "-j1", "-M512", "-o", str(proof), str(source)],
                    cwd=root, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                    check=False, timeout=30, preexec_fn=_limits, close_fds=True)
                receipt["build"] = {"exit_code": completed.returncode,
                    "stdout_sha256": _sha(completed.stdout), "stderr_sha256": _sha(completed.stderr)}
                if completed.returncode or not proof.is_file():
                    raise ValueError("actual Lean compilation failed: " + completed.stderr.decode("utf-8", errors="replace")[:300] + completed.stdout.decode("utf-8", errors="replace")[:300])
                if len(completed.stdout) > 65_536 or len(completed.stderr) > 65_536:
                    raise ValueError("Lean diagnostic bound exceeded")
                stdout = completed.stdout.decode("utf-8", errors="strict")
                audit = _axiom_audit(stdout)
                if SOURCE.read_bytes() != source_raw or _sha(executable.read_bytes()) != compiler_sha:
                    raise ValueError("source or compiler changed during proof replay")
                receipt["build"].update(proof_object_sha256=_sha(proof.read_bytes()), actual_compilation=True)
                receipt.update(status="VERIFIED", axiom_audit=audit, actual_axiom_output=stdout.strip())
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            receipt.update(status="ERROR", reason=type(exc).__name__ + ": " + str(exc)[:700])
    if output is not None:
        Path(output).write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean", help="explicit Lean 4.28.0 executable")
    parser.add_argument("--output", help="optional source-bound JSON receipt path")
    arguments = parser.parse_args()
    receipt = verify(lean=arguments.lean, output=arguments.output)
    print(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False))
    return 0 if receipt["status"] == "VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
