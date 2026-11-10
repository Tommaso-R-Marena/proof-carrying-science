"""Experimental v8: one Lean obligation binds CSV structure, bytes and all-row math.

The LLM/analyst supplies a *separately pinned* template. For a strict bounded
ASCII CSV, Lean reconstructs ALL cells from the raw byte list, checks the exact
header and shape, parses decimals, attaches the declared exact unit scales and
then re-evaluates complete typed ASTs in a single generated proof source.

Untrusted external inputs never produce Lean syntax. Scientific provenance,
semantic adequacy of the caller-supplied manifest and original study population
remain outside the proof. This module is separate from PCS production authority.
"""
from __future__ import annotations

import argparse
import re
import sys
from fractions import Fraction
from pathlib import Path

from .byte_bridge import LEAN_BYTE_LIBRARY, MAX_BRIDGE_BYTES, MAX_BRIDGE_CELLS, _bytes
from .core import Source, canonical, sha
from .finite_universe import LEAN_FINITE_AGGREGATOR
from .pipeline import LeanChecker
from .replay_table import InvalidReceipt, _write_private_json, parse_receipt
from .table_evidence import TableSpec, CSVRow, parse_table_rows, parse_table_spec, row_claim
from .typed import LEAN_LIBRARY, LEAN_RELPOS, QExpr, TypedClaim, unit_value, typed_truth

SCHEMA = "pcs-integrated-csv-v8-research"
REPLAY_SCHEMA = "pcs-integrated-csv-replay-v8-research"
AUTHORITY = "EXPERIMENTAL_NOT_PCS_V06_AUTHORITY"

LEAN_CSV_LIBRARY = '''-- Parse all rows and columns INSIDE Lean from original embedded bytes.
def pcsDropFinalEmpty : List (List Nat) → List (List Nat)
  | [] => []
  | [[]] => []
  | x :: xs => x :: pcsDropFinalEmpty xs

def pcsDropFinalCR : List Nat → List Nat
  | [] => []
  | [13] => []
  | x :: xs => x :: pcsDropFinalCR xs

def pcsCSVFields (raw : List Nat) : List (List (List Nat)) :=
  ((pcsDropFinalEmpty (pcsByteChunks 10 raw)).map pcsDropFinalCR).map (pcsByteChunks 44)

def pcsCSVValidWidths (records : List (List (List Nat))) (width : Nat) : Bool :=
  records.all (fun r => r.length == width)

def pcsCSVRead (records : List (List (List Nat))) (row col : Nat) : Option Rat := do
  let record ← records[row + 1]?
  let field ← record[col]?
  pcsAsciiDecimal field

def pcsCSVAllNumeric (records : List (List (List Nat))) (rows cols : Nat) : Bool :=
  (List.range rows).all (fun r =>
    (List.range cols).all (fun c => (pcsCSVRead records r c).isSome))

def pcsCSVQuantity (records : List (List (List Nat)))
    (row col : Nat) (scale : Rat) (dims : List Int) : Option PCSQty :=
  (pcsCSVRead records row col).map (fun value => ⟨value * scale, dims⟩)
'''


def _rat(value: Fraction) -> str:
    return f"(({value.numerator} : Rat) / ({value.denominator} : Rat))"


def _dims(values: tuple[int, ...]) -> str:
    return "[" + ", ".join(f"({v} : Int)" for v in values) + "]"


def _expression(node: QExpr, row: int, spec: TableSpec) -> str:
    """Generate only from the locally parsed and validated typed AST.

    Binding leaves DO NOT serialize Python's precomputed source-cell value.
    They use the Lean CSV parser applied to embedded raw bytes and the template's
    unit coefficient. Literal leaves are evaluated separately in the typed DSL.
    """
    if node.kind == "binding":
        name = node.token
        idx = next((i for i, c in enumerate(spec.columns) if c.name == name), None)
        if idx is None:
            raise ValueError("binding not declared in pinned table manifest")
        scale, dims = unit_value(spec.columns[idx].unit)
        return f"(pcsCSVQuantity pcsCSVRecords {row} {idx} {_rat(scale)} {_dims(dims)})"
    if node.kind == "literal":
        return f"(pcsLit {_rat(node.quantity.value)} {_dims(node.quantity.dim)})"
    if node.kind == "neg":
        return f"(pcsNeg {_expression(node.args[0], row, spec)})"
    if node.kind in ("add", "sub", "mul", "div") and len(node.args) == 2:
        fn = {"add": "pcsAdd", "sub": "pcsSub", "mul": "pcsMul", "div": "pcsDiv"}[node.kind]
        return f"({fn} {_expression(node.args[0], row, spec)} {_expression(node.args[1], row, spec)})"
    raise ValueError("unsupported AST node (fail closed)")


def _row_relation(claim: TypedClaim, index: int, spec: TableSpec) -> str:
    return (f"(pcsCompare {LEAN_RELPOS[claim.op]} "
            f"{_expression(claim.lhs, index, spec)} "
            f"{_expression(claim.rhs, index, spec)})")


def _check_pin(expected: str | None, actual: str, what: str) -> None:
    if expected is not None:
        if type(expected) is not str or re.fullmatch(r"[a-f0-9]{64}", expected) is None:
            raise ValueError(f"{what} SHA256 pin must be 64 lowercase hex characters")
        if expected != actual:
            raise ValueError(f"{what} differs from the caller-provided pin")


def _prepare(source: Source, manifest: bytes):
    spec = parse_table_spec(manifest)
    rows = parse_table_rows(source, spec)
    if len(source.raw) > MAX_BRIDGE_BYTES:
        raise ValueError("integrated CSV source exceeds bound; no partial certification")
    if len(rows) * len(spec.columns) > MAX_BRIDGE_CELLS:
        raise ValueError("integrated CSV cell cap exceeded; no partial certification")
    prepared = tuple((assertion, tuple(row_claim(row, spec, assertion) for row in rows))
                     for assertion in spec.assertions)
    return spec, rows, prepared


def make_integrated_lean_source(source: Source, manifest: bytes) -> tuple[str, tuple[dict, ...]]:
    """Generate ONE Lean file proving CSV structure, numbers and every claim.

    No partial positive result is possible: any malformed record, invented
    expected value, shifted column, or missing obligation fails the whole script.
    """
    spec, rows, prepared = _prepare(source, manifest)
    n, width = len(rows), len(spec.columns)
    header = "[" + ", ".join(_bytes(c.name.encode("ascii")) for c in spec.columns) + "]"
    src = [
        LEAN_LIBRARY, LEAN_BYTE_LIBRARY, LEAN_CSV_LIBRARY, LEAN_FINITE_AGGREGATOR,
        f"def pcsOriginalCSVBytes : List Nat := {_bytes(source.raw)}",
        "def pcsCSVRecords : List (List (List Nat)) := pcsCSVFields pcsOriginalCSVBytes",
        # The complete structure is recomputed inside Lean, not derived from a
        # Python-selected list of cell spans or numeric cell constants.
        f"example : pcsCSVRecords.length = {n + 1} := by decide +kernel",
        f"example : pcsCSVRecords.head? = some ({header} : List (List Nat)) := by decide +kernel",
        f"example : pcsCSVValidWidths pcsCSVRecords {width} = true := by decide +kernel",
        f"example : pcsCSVAllNumeric pcsCSVRecords {n} {width} = true := by decide +kernel",
    ]
    reports: list[dict] = []
    for i, (assertion, claims) in enumerate(prepared):
        terms = [_row_relation(claim, index, spec) for index, claim in enumerate(claims)]
        group = f"pcsCSVClaim_{i}"
        src.append(f"def {group} : List (Option Bool) := [\n  " + ",\n  ".join(terms) + "\n]")
        truth = all(typed_truth(c) for c in claims)
        first_bad = next((j for j, c in enumerate(claims) if not typed_truth(c)), None)
        src.append(f"example : {group}.length = {n} := by decide +kernel")
        src.append(f"example : (pcsAllChecks {group}) = some {str(truth).lower()} := by decide +kernel")
        if first_bad is not None:
            src.append(f"example : {group}[{first_bad}]? = some (some false) := by decide +kernel")
        reports.append({
            "id": assertion.claim_id,
            "expected_relation_by_external_python": truth,
            "first_counterexample_row": (rows[first_bad].number if first_bad is not None else None),
            "template_expression_sha256": sha(assertion.expression.encode("utf-8")),
            "record_count": n,
            "record_ast_sha256": [c.to_dict()["ast_sha256"] for c in claims],
        })
    return "\n\n".join(src) + "\n", tuple(reports)


def run_integrated(source: Source, manifest: bytes, *, lean: LeanChecker | None = None,
                   expected_data_sha256: str | None = None,
                   expected_manifest_sha256: str | None = None) -> dict:
    _check_pin(expected_data_sha256, source.digest, "data")
    _check_pin(expected_manifest_sha256, sha(manifest), "manifest")
    code, claims = make_integrated_lean_source(source, manifest)
    checker = lean if lean is not None else LeanChecker("__pcs_missing_lean_executable__")
    result = checker._check_generated(code, True, "INTEGRATED_CSV")
    return {
        "schema_version": SCHEMA,
        "authority": AUTHORITY,
        "data_sha256": source.digest,
        "manifest_sha256": sha(manifest),
        "expected_data_sha256": expected_data_sha256,
        "expected_manifest_sha256": expected_manifest_sha256,
        "commitment_origin": "CALLER_PINNED_UNAUTHENTICATED" if expected_data_sha256 or expected_manifest_sha256 else "NONE",
        "submitted_record_count": claims[0]["record_count"],
        "manifest_source": "CALLER_SUPPLIED_UNATTESTED",
        "formal_status": result["status"],
        "kernel_checked": result["kernel_checked"],
        "claims": list(claims),
        "semantic_fidelity": "UNREVIEWED",
        "scientific_status": "NOT_ASSESSED",
        "scope": "Single Lean script checks all strict CSV structure, decimal cells and complete finite typed assertions on embedded bytes. External file custody, template-unit meaning, dataset completeness, and source-to-Lean generator semantics are not proved.",
        **{k: v for k, v in result.items() if k not in {"status", "kernel_checked"}},
    }


def replay_integrated(source: Source, manifest: bytes, receipt: bytes, *, lean: LeanChecker | None = None,
                      expected_data_sha256: str | None = None,
                      expected_manifest_sha256: str | None = None) -> dict:
    incoming = parse_receipt(receipt)
    base = {
        "schema_version": REPLAY_SCHEMA, "authority": AUTHORITY,
        "original_receipt_sha256": sha(receipt),
        "data_sha256": source.digest, "manifest_sha256": sha(manifest),
        "matched": False, "status": "RECEIPT_REJECTED",
        "scientific_status": "NOT_ASSESSED",
    }
    _check_pin(expected_data_sha256, source.digest, "data")
    _check_pin(expected_manifest_sha256, sha(manifest), "manifest")
    if (incoming.get("schema_version") != SCHEMA
            or incoming.get("authority") != AUTHORITY
            or incoming.get("data_sha256") != source.digest
            or incoming.get("manifest_sha256") != sha(manifest)
            or incoming.get("expected_data_sha256") != expected_data_sha256
            or incoming.get("expected_manifest_sha256") != expected_manifest_sha256):
        base["reason"] = "pin, schema, source or manifest mismatch"
        return base
    current = run_integrated(source, manifest, lean=lean,
                             expected_data_sha256=expected_data_sha256,
                             expected_manifest_sha256=expected_manifest_sha256)
    if not current["kernel_checked"]:
        base["status"] = "KERNEL_UNAVAILABLE_OR_REJECTED"
    elif canonical(incoming) != canonical(current):
        base["reason"] = "fresh computation does not match exact receipt"
    else:
        base["status"] = "REPLAYED_INTEGRATED_CSV"
        base["matched"] = True
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PCS v8 integrated research CSV certificate (NOT production authority)")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--table-spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--lean", default="lean")
    parser.add_argument("--expected-data-sha256")
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        source = Source.from_bytes(args.source.read_bytes())
        manifest = args.table_spec.read_bytes()
        lean = LeanChecker(args.lean, timeout=50)
        if args.receipt is None:
            report = run_integrated(source, manifest, lean=lean,
                                    expected_data_sha256=args.expected_data_sha256,
                                    expected_manifest_sha256=args.expected_manifest_sha256)
            ok = report["kernel_checked"]
            print(f"CSV integrated: {report['formal_status']}; {len(report['claims'])} all-row claims")
        else:
            report = replay_integrated(source, manifest, args.receipt.read_bytes(), lean=lean,
                                       expected_data_sha256=args.expected_data_sha256,
                                       expected_manifest_sha256=args.expected_manifest_sha256)
            ok = report["matched"]
            print(f"CSV integrated replay: {report['status']}")
        _write_private_json(args.out, report)
        return 0 if ok else 2
    except (OSError, ValueError, TypeError, KeyError, OverflowError, InvalidReceipt) as exc:
        print(f"integrated CSV rejected: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
