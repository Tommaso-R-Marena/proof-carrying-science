"""Fresh, source-pinned Lean checking of abstract integer residual semantics.

The receipt concerns only the nine elementary Lean statements. Python Fraction
arithmetic, key joining, source correspondence and empirical refinement remain
OPEN. No receipt grants scientific authority or establishes scientific meaning.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

# Reuse the existing lexical inspection and Lean audit parser without changing
# their historical implementation or the earlier formal/runtime namespaces.
from research.scientific_understanding_v2 import verify_formal as _shared
from research.scientific_understanding_v2.verify_formal import inspect_source, parse_axiom_audit

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "formal" / "Residuals.lean"
_ONBOARDING_LEAN = Path("/workspace/.onboarding/tools/lean-4.28.0-linux/bin/lean")
DEFAULT_LEAN = Path(os.environ.get("PCS_LEAN") or shutil.which("lean") or
                    (str(_ONBOARDING_LEAN) if _ONBOARDING_LEAN.is_file() else "lean"))
REVIEWED_SOURCE_SHA256 = "9400e0afa7e11630c18240e08b61519c8244249cda8db8c824ad41503c07cd7d"
NAMESPACE = "ScientificReviewV4.Residuals"
REQUIRED_THEOREMS = (
    "aligned_pair_keys_equal", "mismatched_keys_cannot_form_aligned_pair",
    "square_nonnegative", "square_eq_zero_iff", "residual_zero_iff_values_equal",
    "sse_nonnegative", "sse_zero_iff_aligned_values_equal",
    "nonzero_residual_rules_out_zero_sse", "sse_preserved_by_permutation",
)
EXPECTED_AXIOMS = {name: ([] if index < 3 else ["propext"])
                   for index, name in enumerate(REQUIRED_THEOREMS)}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_lean(lean_binary: str | Path | None) -> Path:
    candidate = Path(lean_binary) if lean_binary is not None else Path(
        os.environ.get("PCS_LEAN") or shutil.which("lean") or str(DEFAULT_LEAN))
    if not candidate.is_file():
        located = shutil.which(str(candidate))
        if located:
            candidate = Path(located)
    return candidate.resolve()


def verify(lean_binary: str | Path | None = None, *, source: str | Path | None = None,
           timeout: int = 120) -> dict[str, Any]:
    """Actually compile and audit the reviewed source; missing resources are UNKNOWN.

    A modified source is REFUTED even if it still compiles. The pinned source and
    exact theorem/dependency census are review inputs, not mathematical novelty
    claims. Every invocation starts a new bounded Lean process; no positive cache
    or claimed receipt is used as evidence.
    """
    source_path = (Path(source) if source is not None else SOURCE).resolve()
    lean = _resolve_lean(lean_binary)
    harness = Path(__file__).resolve()
    shared_harness = Path(_shared.__file__).resolve()
    receipt: dict[str, Any] = {
        "schema": "scientific-residual-formal-receipt/v4", "status": "UNKNOWN",
        "authority": False, "scientific_meaning": "OPEN", "python_lean_refinement": "OPEN",
        "python_fraction_refinement": "OPEN", "key_join_refinement": "OPEN",
        "source_correspondence": "OPEN", "empirical_refinement": "OPEN",
        "scope": "finite exact integer residuals and SSE under explicit pair-key equality; abstract algebra only",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source_path), "compiler_path": str(lean),
        "reviewed_source_sha256": REVIEWED_SOURCE_SHA256,
        "harness_sha256": _sha256(harness),
        "shared_harness_sha256": _sha256(shared_harness),
        "required_theorems": list(REQUIRED_THEOREMS),
        "allowed_lean_axioms": ["propext"],
        "expected_axiom_census": {name: list(axioms) for name, axioms in EXPECTED_AXIOMS.items()},
        "diagnostics": [],
    }
    if not source_path.is_file() or not lean.is_file():
        receipt["diagnostics"].append("Lean compiler or isolated residual source is unavailable")
        return receipt
    try:
        inspection = inspect_source(source_path, REQUIRED_THEOREMS)
        # The shared historical helper predates the explicit native_decide ban.
        native = re.findall(r"\bnative_decide\b", _shared._lean_code(source_path.read_text()))
        inspection["forbidden_tokens"] = sorted(set(inspection["forbidden_tokens"] + native))
        receipt.update(inspection)
        receipt["source_matches_reviewed_sha256"] = receipt["source_sha256"] == REVIEWED_SOURCE_SHA256
        receipt["compiler_sha256"] = _sha256(lean)
        shared_library = lean.parent.parent / "lib" / "lean" / "libleanshared.so"
        if not shared_library.is_file():
            receipt["diagnostics"].append("Lean shared-library identity is unavailable")
            return receipt
        receipt["compiler_shared_library_sha256"] = _sha256(shared_library)
        version = subprocess.run([str(lean), "--version"], capture_output=True, text=True,
                                 timeout=min(timeout, 15), check=False)
        receipt["compiler_version"] = version.stdout.strip()
        receipt["compiler_version_returncode"] = version.returncode
        command = [str(lean), "-M1024", "-j1", str(source_path)]
        receipt["command"] = command
        result = subprocess.run(command, cwd=str(source_path.parent),
                                env={"PATH": str(lean.parent) + ":/usr/bin:/bin",
                                     "LANG": "C.UTF-8", "LEAN_NUM_THREADS": "1"},
                                capture_output=True, text=True, timeout=timeout, check=False)
        receipt.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr,
                       stdout_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(),
                       stderr_sha256=hashlib.sha256(result.stderr.encode()).hexdigest())
        audit = parse_axiom_audit(result.stdout)
        receipt["axiom_audit"] = audit
        names = inspection["theorem_declarations"]
        receipt["theorem_count"] = len(names)
        receipt["axiom_audit_count"] = len(audit)
        receipt["theorem_census_exact"] = names == list(REQUIRED_THEOREMS)
        receipt["axiom_census_exact"] = set(audit) == set(REQUIRED_THEOREMS) and all(
            audit[name]["name"] == NAMESPACE + "." + name and
            audit[name]["axioms"] == EXPECTED_AXIOMS[name]
            for name in REQUIRED_THEOREMS if name in audit)
        receipt["all_declared_theorems_audited"] = all(name in audit for name in names)
        receipt["all_declared_axiom_audits_empty"] = all(
            name in audit and audit[name]["empty"] for name in names)
        receipt["all_declared_axiom_audits_permitted"] = all(
            name in audit and set(audit[name]["axioms"]) <= {"propext"} for name in names)
        receipt["source_stable_during_compile"] = _sha256(source_path) == receipt["source_sha256"]
        receipt["compiler_stable_during_compile"] = _sha256(lean) == receipt["compiler_sha256"]
        receipt["shared_library_stable_during_compile"] = (
            _sha256(shared_library) == receipt["compiler_shared_library_sha256"])
        receipt["harness_stable_during_compile"] = (
            _sha256(harness) == receipt["harness_sha256"] and
            _sha256(shared_harness) == receipt["shared_harness_sha256"])
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        receipt["diagnostics"].append("Compiler invocation or source inspection unavailable: " + type(exc).__name__)
        return receipt
    passed = (
        version.returncode == 0 and "version 4.28.0," in receipt["compiler_version"] and
        result.returncode == 0 and not receipt["forbidden_tokens"] and
        not receipt["unexpected_imports"] and receipt["source_matches_reviewed_sha256"] and
        receipt["theorem_census_exact"] and receipt["axiom_census_exact"] and
        receipt["all_declared_theorems_audited"] and receipt["all_declared_axiom_audits_permitted"] and
        receipt["source_stable_during_compile"] and receipt["compiler_stable_during_compile"] and
        receipt["shared_library_stable_during_compile"] and receipt["harness_stable_during_compile"])
    receipt["status"] = "VERIFIED" if passed else "REFUTED"
    if not passed:
        receipt["diagnostics"].append("Reviewed-source binding, compilation, source policy or exact axiom census failed")
    return receipt
