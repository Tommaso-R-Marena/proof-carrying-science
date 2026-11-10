"""Experimental independent Lean byte-to-rational cross-check for PCS CSV evidence.

V7 research boundary: source bytes are embedded as an ordered Nat list. Lean
independently splits raw ASCII lines, extracts every accepted CSV cell by its
source offsets and computes exact decimal Rational values. Python chooses the
expected reconstruction; successful Lean evaluation checks that choice against
all embedded bytes. External file custody and compiler/host integrity remain
explicit assumptions. Not a proof of scientific semantics or full PCS authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import Source, canonical, sha
from .pipeline import LeanChecker
from .replay_table import parse_receipt, _write_private_json
from .table_evidence import parse_table_rows, parse_table_spec
from fractions import Fraction

SCHEMA = "pcs-csv-byte-bridge-v7-research"
AUTHORITY = "EXPERIMENTAL_NOT_PCS_V06_AUTHORITY"
MAX_BRIDGE_BYTES = 512
MAX_BRIDGE_CELLS = 32

LEAN_BYTE_LIBRARY = '''-- Generated-only research byte/rational cross-check; no imported model code.
def pcsByteChunks (sep : Nat) : List Nat → List (List Nat)
  | [] => [[]]
  | b :: rest =>
      let chunks := pcsByteChunks sep rest
      if b == sep then [] :: chunks
      else match chunks with
      | [] => [[b]]
      | front :: back => (b :: front) :: back

def pcsByteSlice (raw : List Nat) (start finish : Nat) : List Nat :=
  (raw.drop start).take (finish - start)

def pcsAsciiDigit (b : Nat) : Option Nat :=
  if b >= 48 && b <= 57 then some (b - 48) else none

def pcsUnsignedDigits (xs : List Nat) : Option Nat :=
  if xs.isEmpty then none else
    xs.foldl (fun result b =>
      match result, pcsAsciiDigit b with
      | some n, some d => some (n * 10 + d)
      | _, _ => none) (some 0)

def pcsAsciiDecimal (raw : List Nat) : Option Rat :=
  let (negative, unsigned) := match raw with
    | 45 :: rest => (true, rest)
    | _ => (false, raw)
  let val : Option Rat := match pcsByteChunks 46 unsigned with
    | [whole] =>
        match pcsUnsignedDigits whole with
        | some n => some (n : Rat)
        | none => none
    | [whole, fractional] =>
        match pcsUnsignedDigits whole, pcsUnsignedDigits fractional with
        | some n, some fraction =>
            some ((n : Rat) + (fraction : Rat) / ((10 ^ fractional.length : Nat) : Rat))
        | _, _ => none
    | _ => none
  val.map (fun n => if negative then -n else n)
'''


def _bytes(xs: bytes) -> str:
    return "[" + ",".join(str(b) for b in xs) + "]"


def _rat(x: Fraction) -> str:
    return f"(({x.numerator} : Rat) / ({x.denominator} : Rat))"


def make_byte_lean_source(source: Source, manifest: bytes) -> tuple[str, int]:
    spec = parse_table_spec(manifest)
    rows = parse_table_rows(source, spec)
    if len(source.raw) > MAX_BRIDGE_BYTES:
        raise ValueError("byte bridge source too large; no partial certification")
    cells = [cell for row in rows for cell in row.cells]
    if len(cells) > MAX_BRIDGE_CELLS:
        raise ValueError("byte bridge cell count exceeded; no partial certification")
    # The independent Lean scanner splits exact bytes. The expected line and
    # cell results are supplied by Python but proved by Lean on these bytes.
    chunks = source.raw.split(b"\n")
    expected_lines = "[" + ",".join(_bytes(chunk) for chunk in chunks) + "]"
    src = _bytes(source.raw)
    lines = [LEAN_BYTE_LIBRARY, f"def pcsRawBytes : List Nat := {src}",
             f"example : pcsByteChunks 10 pcsRawBytes = {expected_lines} := by decide +kernel"]
    checks = []
    for cell in cells:
        raw = source.raw[cell.start:cell.end]
        assert raw == cell.value.encode("ascii")
        checks.append("(pcsAsciiDecimal (pcsByteSlice pcsRawBytes " +
                      f"{cell.start} {cell.end}))")
    expected = ["some " + _rat(Fraction(cell.value)) for cell in cells]
    # One proof re-parses EVERY anchored cell; a wrong offset, decimal meaning,
    # or Python-proposed value is rejected by the Lean evaluator.
    lines.append("example : ([\n  " + ",\n  ".join(checks) +
                 "\n] : List (Option Rat)) = ([\n  " + ",\n  ".join(expected) +
                 "\n] : List (Option Rat)) := by decide +kernel")
    return "\n\n".join(lines), len(cells)


def run_byte_bridge(source: Source, manifest: bytes, *, lean: LeanChecker | None = None) -> dict:
    code, count = make_byte_lean_source(source, manifest)
    checker = lean if lean is not None else LeanChecker("__pcs_missing_lean_executable__")
    checked = checker._check_generated(code, True, "BYTE_GROUNDING")
    return {
        "schema_version": SCHEMA,
        "authority": AUTHORITY,
        "data_sha256": source.digest,
        "manifest_sha256": sha(manifest),
        "source_byte_count": len(source.raw),
        "cell_count": count,
        "verified_object": "Lean evaluates embedded ASCII bytes to reconstruct every selected cell as exact Rat; UTF-8 CSV/text origin and scientific meaning remain external",
        "formal_status": checked["status"],
        "kernel_checked": checked["kernel_checked"],
        "semantic_fidelity": "UNREVIEWED",
        "scientific_status": "NOT_ASSESSED",
        **{k: v for k, v in checked.items() if k not in {"status", "kernel_checked"}},
    }


def replay_byte_bridge(source: Source, manifest: bytes, receipt: bytes, *, lean: LeanChecker | None = None) -> dict:
    incoming = parse_receipt(receipt)
    base = {
        "schema_version": "pcs-csv-byte-bridge-replay-v7-research",
        "authority": AUTHORITY,
        "data_sha256": source.digest,
        "manifest_sha256": sha(manifest),
        "original_receipt_sha256": sha(receipt),
        "status": "RECEIPT_REJECTED",
        "matched": False,
        "scientific_status": "NOT_ASSESSED",
    }
    if (incoming.get("schema_version") != SCHEMA or incoming.get("authority") != AUTHORITY or
            incoming.get("data_sha256") != source.digest or incoming.get("manifest_sha256") != sha(manifest)):
        base["reason"] = "source or schema mismatch"
        return base
    current = run_byte_bridge(source, manifest, lean=lean)
    if not current["kernel_checked"]:
        base["status"] = "KERNEL_UNAVAILABLE_OR_REJECTED"
    elif canonical(incoming) != canonical(current):
        base["reason"] = "byte cross-check receipt mismatch"
    else:
        base["status"] = "REPLAYED_BYTE_GROUNDING"
        base["matched"] = True
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experimental Lean byte-to-decimal source bridge")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--table-spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--lean", default="lean")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        source = Source.from_bytes(args.source.read_bytes())
        manifest = args.table_spec.read_bytes()
        checker = LeanChecker(args.lean)
        if args.receipt is None:
            result = run_byte_bridge(source, manifest, lean=checker)
            print(f"Byte-grounding: {result['formal_status']}; {result['cell_count']} cells")
            rc = 0 if result["kernel_checked"] else 2
        else:
            result = replay_byte_bridge(source, manifest, args.receipt.read_bytes(), lean=checker)
            print(f"Byte-grounding replay: {result['status']}")
            rc = 0 if result["matched"] else 2
        _write_private_json(args.out, result)
        return rc
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"byte grounding rejected: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
