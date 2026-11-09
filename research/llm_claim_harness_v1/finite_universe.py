"""PCS experimental v6: complete, source-bound finite CSV universality certificates.

The verified object is *only* the Boolean conjunction over every record of the
submitted CSV for each caller-supplied, exact typed arithmetic assertion. This
prevents silently selecting favorable rows WITHIN the submitted artifact, but
cannot prove that the artifact contains all observations in a scientific study.

The generated Lean source re-evaluates every expression from fixed AST nodes,
folds the entire list, verifies the length, and (on failure) rechecks the first
failing row. Source parsing, template interpretation and scientific adequacy are
explicitly outside the formal assurance claim.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from .core import Source, canonical, sha
from .pipeline import LeanChecker
from .replay_table import InvalidReceipt, parse_receipt, _write_private_json
from .table_evidence import (
    Assertion, CSVRow, parse_table_rows, parse_table_spec, row_claim,
)
from .typed import LEAN_LIBRARY, LEAN_RELPOS, TypedClaim, typed_truth

if TYPE_CHECKING:
    from typing import Any

SCHEMA = "pcs-finite-universe-v6-research"
REPLAY_SCHEMA = "pcs-finite-universe-replay-v6-research"
_AUTHORITY = "EXPERIMENTAL_NOT_PCS_V06_AUTHORITY"

# Lean's Option Bool distinguishes an invalid computation (none) from a false
# mathematical proposition (some false). One invalid item invalidates the batch.
LEAN_FINITE_AGGREGATOR = '''
def pcsAllChecks (xs : List (Option Bool)) : Option Bool :=
  xs.foldl (fun acc item =>
    match acc, item with
    | some a, some b => some (a && b)
    | _, _ => none) (some true)
'''


def _row_term(claim: TypedClaim) -> str:
    """Only program-constructed typed ASTs reach this Lean expression."""
    return f"(pcsCompare {LEAN_RELPOS[claim.op]} {claim.lhs.lean()} {claim.rhs.lean()})"


def make_finite_lean_source(claims: tuple[TypedClaim, ...]) -> tuple[str, bool, int | None]:
    """Prove or refute an all-record relation, with a checked negative witness.

    Python selects the candidate proposition and expected result, but success is
    contingent on Lean checking the expression tree AND the complete finite fold.
    """
    if not 1 <= len(claims) <= 16:
        raise ValueError("finite certificate requires 1..16 ordered rows")
    terms = [_row_term(claim) for claim in claims]
    members = ",\n  ".join(terms)
    whole_list = f"([\n  {members}\n] : List (Option Bool))"
    truth = all(typed_truth(c) for c in claims)
    first_bad = next((i for i, c in enumerate(claims) if not typed_truth(c)), None)
    goal = "true" if truth else "false"
    lines = [
        LEAN_LIBRARY,
        LEAN_FINITE_AGGREGATOR,
        f"example : {whole_list}.length = {len(claims)} := by decide +kernel",
        f"example : (pcsAllChecks {whole_list}) = some {goal} := by decide +kernel",
    ]
    if first_bad is not None:
        # The counterexample uses the same program-built AST embedded in the fold.
        lines.append(f"example : {terms[first_bad]} = some false := by decide +kernel")
    return "\n".join(lines), truth, first_bad


def _prepared(source: Source, manifest: bytes):
    """Fully reparse all rows and obligations BEFORE invoking the Lean checker."""
    spec = parse_table_spec(manifest)
    rows = parse_table_rows(source, spec)
    prepared = tuple((a, tuple(row_claim(row, spec, a) for row in rows))
                     for a in spec.assertions)
    return spec, rows, prepared


def run_finite_universe(source: Source, manifest: bytes, *, lean: LeanChecker | None = None,
                        expected_data_sha256: str | None = None) -> dict:
    if expected_data_sha256 is not None:
        if type(expected_data_sha256) is not str or re.fullmatch(r"[a-f0-9]{64}", expected_data_sha256) is None:
            raise ValueError("expected data SHA-256 must be 64 lowercase hex characters")
        if source.digest != expected_data_sha256:
            raise ValueError("submitted CSV does not match caller-supplied data commitment")
    spec, rows, prepared = _prepared(source, manifest)
    checker = lean if lean is not None else LeanChecker("__pcs_missing_lean_executable__")
    reports = []
    for assertion, claims in prepared:
        code, truth, first_bad = make_finite_lean_source(claims)
        # Only trusted generated text is passed to Lean, never external proof text.
        checked = checker._check_generated(code, truth, "FINITE_UNIVERSE")
        witness = None
        if first_bad is not None:
            row = rows[first_bad]
            witness = {
                "row_number": row.number,
                "csv_row_span": {"start": row.start, "end": row.end},
                "csv_row_sha256": row.raw_sha256,
                "cell_anchors": [cell.receipt() for cell in row.cells],
                "ast_sha256": claims[first_bad].to_dict()["ast_sha256"],
                "assertion_expression_sha256": sha(assertion.expression.encode("utf-8")),
            }
        reports.append({
            "id": assertion.claim_id,
            "expression_sha256": sha(assertion.expression.encode("utf-8")),
            "record_count": len(rows),
            "record_ast_sha256": [c.to_dict()["ast_sha256"] for c in claims],
            "submitted_universe_sha256": source.digest,
            "finite_relation_true_by_external_exact_arithmetic": truth,
            # Witness indicates a Python-selected candidate only. Trust requires
            # kernel_checked AND a matching witness proof in the generated script.
            "first_counterexample": witness,
            "formal_status": checked["status"],
            "kernel_checked": checked["kernel_checked"],
            "status": "SCIENTIFIC_REVIEW_REQUIRED",
            "semantic_fidelity": "UNREVIEWED",
            "scientific_status": "NOT_ASSESSED",
            **{key: value for key, value in checked.items() if key not in {"status", "kernel_checked"}},
        })
    return {
        "schema_version": SCHEMA,
        "authority": _AUTHORITY,
        "data_sha256": source.digest,
        "expected_data_sha256": expected_data_sha256,
        "data_pin_origin": "CALLER_SUPPLIED_UNAUTHENTICATED" if expected_data_sha256 is not None else "NONE",
        "manifest_sha256": spec.raw_sha256,
        "universe_size": len(rows),
        "universe_scope": "Every syntactically accepted record of the exact supplied CSV; not an external study population",
        "row_anchors": [{"row_number": r.number,
                         "csv_row_span": {"start": r.start, "end": r.end},
                         "csv_row_sha256": r.raw_sha256} for r in rows],
        "template_origin": "CALLER_SUPPLIED_UNATTESTED",
        "semantic_fidelity": "UNREVIEWED",
        "scientific_status": "NOT_ASSESSED",
        "scope": "All-record finite conjunction; source/manifest semantics and dataset completeness outside supplied bytes are unproved",
        "claims": reports,
        "counts": {"assertions": len(reports),
                   "rows_per_assertion": len(rows),
                   "total_obligations": len(rows) * len(reports),
                   "kernel_checked_aggregate_statements": sum(r["kernel_checked"] for r in reports)},
    }


def replay_finite_universe(source: Source, manifest: bytes, receipt: bytes, *, lean: LeanChecker | None = None,
                           expected_data_sha256: str | None = None) -> dict:
    """Fresh Lean replay; equality of all result fields is mandatory for success."""
    incoming = parse_receipt(receipt)
    if expected_data_sha256 is not None:
        if type(expected_data_sha256) is not str or re.fullmatch(r"[a-f0-9]{64}", expected_data_sha256) is None:
            raise ValueError("expected data SHA-256 must be 64 lowercase hex characters")
        if source.digest != expected_data_sha256:
            raise ValueError("submitted CSV does not match caller-supplied data commitment")
    base = {
        "schema_version": REPLAY_SCHEMA,
        "authority": _AUTHORITY,
        "original_receipt_sha256": sha(receipt),
        "data_sha256": source.digest,
        "manifest_sha256": sha(manifest),
        "status": "RECEIPT_REJECTED",
        "matched": False,
        "scientific_status": "NOT_ASSESSED",
        "scope": "Same compiler re-executed, pinned kernel freshly invoked; not independent semantic verification",
    }
    if (incoming.get("schema_version") != SCHEMA
            or incoming.get("authority") != _AUTHORITY
            or incoming.get("data_sha256") != source.digest
            or incoming.get("expected_data_sha256") != expected_data_sha256
            or incoming.get("manifest_sha256") != sha(manifest)
            or type(incoming.get("claims")) is not list):
        base["reason"] = "source/manifest/schema authority mismatch"
        return base
    checker = lean if lean is not None else LeanChecker("__pcs_missing_lean_executable__")
    fresh = run_finite_universe(source, manifest, lean=checker, expected_data_sha256=expected_data_sha256)
    if any(not c["kernel_checked"] for c in fresh["claims"]):
        base["status"] = "KERNEL_UNAVAILABLE_OR_REJECTED"
        base["reason"] = "all aggregate obligations require fresh Lean checks"
    elif canonical(incoming) != canonical(fresh):
        base["reason"] = "recomputed receipt mismatch"
    else:
        base["status"] = "REPLAYED_FINITE_UNIVERSE"
        base["matched"] = True
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research-only finite CSV universe auditor (never PCS production authority)")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--table-spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--lean", default="lean")
    parser.add_argument("--expected-data-sha256", help="external data-byte commitment, not an attested scientific data source")
    parser.add_argument("--receipt", type=Path, help="untrusted previous finite-universe receipt to replay")
    args = parser.parse_args(argv)
    try:
        source = Source.from_bytes(args.source.read_bytes())
        manifest = args.table_spec.read_bytes()
        checker = LeanChecker(args.lean)
        if args.receipt is None:
            result = run_finite_universe(source, manifest, lean=checker, expected_data_sha256=args.expected_data_sha256)
            _write_private_json(args.out, result)
            print(f"Finite universe: {len(result['claims'])} quantified statements; "
                  f"{result['counts']['kernel_checked_aggregate_statements']} kernel checked")
            return 0 if all(c["kernel_checked"] for c in result["claims"]) else 2
        result = replay_finite_universe(source, manifest, args.receipt.read_bytes(), lean=checker, expected_data_sha256=args.expected_data_sha256)
        _write_private_json(args.out, result)
        print(f"Finite universe replay: {result['status']}")
        return 0 if result["status"] == "REPLAYED_FINITE_UNIVERSE" else 2
    except (OSError, ValueError, TypeError, KeyError, InvalidReceipt) as exc:
        print(f"finite universe rejected: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
