"""PCS research v9: exact-rational OLS from source CSV bytes in one Lean script.

A bounded two-variable regression is recomputed from the complete CSV *inside*
Lean: parse every cell, convert separately declared units, compute the exact
least-squares slope/intercept/SSE, and prove/refute individually reported values.

The input claim is not assumed true. Source units, model choice, scientific
sampling, rounding error, causality and semantics are outside the kernel proof.
This never promotes results to PCS production authority.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
import json
from pathlib import Path
import re
import sys

from .byte_bridge import LEAN_BYTE_LIBRARY, MAX_BRIDGE_BYTES, MAX_BRIDGE_CELLS, _bytes
from .core import Source, canonical, sha
from .csv_integrated_v8 import LEAN_CSV_LIBRARY, _check_pin, _rat
from .pipeline import LeanChecker
from .replay_table import InvalidReceipt, _write_private_json, parse_receipt
from .table_evidence import TableSpec, CSVRow, parse_table_rows, parse_table_spec, _strict_pairs
from .typed import LEAN_LIBRARY, unit_value

SCHEMA = "pcs-ols-integrated-v9-research"
REPLAY_SCHEMA = "pcs-ols-integrated-v9-replay-research"
AUTHORITY = "EXPERIMENTAL_NOT_PCS_V06_AUTHORITY"
# The entire CSV is certified, never a handpicked record subset.
REPORT_KEYS = ("slope", "intercept", "sse")
REPORTED = re.compile(r"-?(?:0|[1-9][0-9]{0,5})(?:\.[0-9]{1,6}|/[1-9][0-9]{0,5})?\Z")


class UnsupportedOLS(ValueError):
    """Unsupported regression or malformed reported metric."""


@dataclass(frozen=True)
class OLSProposal:
    x: str
    y: str
    reported: tuple[Fraction, Fraction, Fraction]
    original: tuple[str, str, str]
    digest: str


def parse_ols_proposal(raw: bytes, spec: TableSpec) -> OLSProposal:
    if not 0 < len(raw) <= 2048:
        raise UnsupportedOLS("OLS proposal byte bound exceeded or empty")
    try:
        obj = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(UnsupportedOLS("nonfinite number")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UnsupportedOLS("proposal is not strict UTF-8 JSON") from exc
    if type(obj) is not dict or set(obj) != {"schema", "x", "y", "reported"} or obj["schema"] != SCHEMA:
        raise UnsupportedOLS("incorrect OLS proposal schema")
    x, y = obj["x"], obj["y"]
    allowed = {c.name for c in spec.columns}
    if type(x) is not str or type(y) is not str or x == y or x not in allowed or y not in allowed:
        raise UnsupportedOLS("x/y columns must be distinct declared names")
    reported = obj["reported"]
    if type(reported) is not dict or set(reported) != set(REPORT_KEYS):
        raise UnsupportedOLS("reported must contain exactly slope/intercept/sse")
    vals = []
    original = []
    for name in REPORT_KEYS:
        item = reported[name]
        if type(item) is not str or len(item) > 32 or not REPORTED.fullmatch(item):
            raise UnsupportedOLS("reported values must be bounded exact numeric strings")
        val = Fraction(item)
        if abs(val.numerator) > 10**12 or val.denominator > 10**12:
            raise UnsupportedOLS("reported value exceeds exact-rational bound")
        vals.append(val)
        original.append(item)
    if vals[2] < 0:
        raise UnsupportedOLS("negative reported SSE is unsupported")
    return OLSProposal(x, y, tuple(vals), tuple(original), sha(raw))


def exact_fit(rows: tuple[CSVRow, ...], spec: TableSpec, proposal: OLSProposal) -> tuple[Fraction, Fraction, Fraction]:
    columns = {c.name: (i, c.unit) for i, c in enumerate(spec.columns)}
    xidx, xu = columns[proposal.x]
    yidx, yu = columns[proposal.y]
    xscale, _ = unit_value(xu)
    yscale, _ = unit_value(yu)
    if len(rows) < 2:
        raise UnsupportedOLS("at least two complete records required")
    points = [(Fraction(r.cells[xidx].value) * xscale, Fraction(r.cells[yidx].value) * yscale)
              for r in rows]
    n = len(points)
    sx, sy = sum(x for x, _ in points), sum(y for _, y in points)
    sxx = sum(x*x for x, _ in points)
    sxy = sum(x*y for x, y in points)
    delta = n*sxx - sx*sx
    if delta <= 0:
        raise UnsupportedOLS("degenerate x values (zero design variance)")
    slope = (n*sxy - sx*sy) / delta
    intercept = (sy - slope*sx) / n
    sse = sum((y-(slope*x+intercept))**2 for x, y in points)
    if max(abs(x.numerator) for x in (slope, intercept, sse)) > 10**16 or max(x.denominator for x in (slope, intercept, sse)) > 10**16:
        raise UnsupportedOLS("OLS result exceeds rational proof budget")
    return slope, intercept, sse


LEAN_OLS_LIBRARY = '''-- Finite ordinary least squares, computed from the CSV decoder's values.
structure PCSOLS where
  slope : Rat
  intercept : Rat
  sse : Rat
  deriving DecidableEq

def pcsOLSPairs (csv : List (List (List Nat)))
    (n xcol ycol : Nat) (xscale yscale : Rat) : Option (List (Rat × Rat)) :=
  (List.range n).mapM (fun i => do
    let x ← pcsCSVRead csv i xcol
    let y ← pcsCSVRead csv i ycol
    pure (x * xscale, y * yscale))

def pcsSumX (points : List (Rat × Rat)) : Rat :=
  points.foldl (fun v p => v + p.1) 0

def pcsSumY (points : List (Rat × Rat)) : Rat :=
  points.foldl (fun v p => v + p.2) 0

def pcsSumXX (points : List (Rat × Rat)) : Rat :=
  points.foldl (fun v p => v + p.1 * p.1) 0

def pcsSumXY (points : List (Rat × Rat)) : Rat :=
  points.foldl (fun v p => v + p.1 * p.2) 0

def pcsOLSDelta (points : List (Rat × Rat)) : Rat :=
  (points.length : Rat) * pcsSumXX points - pcsSumX points * pcsSumX points

def pcsOLSSSE (points : List (Rat × Rat)) (slope intercept : Rat) : Rat :=
  points.foldl (fun v p => v + (p.2 - (slope * p.1 + intercept)) ^ 2) 0

def pcsOLSFit (points : List (Rat × Rat)) : Option PCSOLS :=
  if points.length < 2 then none else
  if pcsOLSDelta points <= 0 then none else
    let n : Rat := points.length
    let sx := pcsSumX points
    let sy := pcsSumY points
    let a := (n * pcsSumXY points - sx * sy) / pcsOLSDelta points
    let b := (sy - a * sx) / n
    some ⟨a, b, pcsOLSSSE points a b⟩

def pcsOLSMetric (fit : Option PCSOLS) (index : Nat) (value : Rat) : Option Bool :=
  fit.map (fun result =>
    if index == 0 then decide (result.slope = value) else
    if index == 1 then decide (result.intercept = value) else
    if index == 2 then decide (result.sse = value) else false)
'''


def _prepare(source: Source, manifest: bytes, proposal_bytes: bytes):
    spec = parse_table_spec(manifest)
    rows = parse_table_rows(source, spec)
    proposal = parse_ols_proposal(proposal_bytes, spec)
    if len(source.raw) > MAX_BRIDGE_BYTES or len(rows) * len(spec.columns) > MAX_BRIDGE_CELLS:
        raise UnsupportedOLS("source exceeds integrated CSV bound")
    if len(rows) > 8:
        raise UnsupportedOLS("bounded regression supports at most eight observations")
    predicted = exact_fit(rows, spec, proposal)
    return spec, rows, proposal, predicted


def make_ols_lean_source(source: Source, manifest: bytes, proposal_bytes: bytes) -> tuple[str, tuple[dict, ...]]:
    spec, rows, prop, predicted = _prepare(source, manifest, proposal_bytes)
    n, width = len(rows), len(spec.columns)
    header = "[" + ", ".join(_bytes(c.name.encode("ascii")) for c in spec.columns) + "]"
    columns = {c.name: (i, c.unit) for i, c in enumerate(spec.columns)}
    xi, xu = columns[prop.x]
    yi, yu = columns[prop.y]
    xscale, _ = unit_value(xu)
    yscale, _ = unit_value(yu)
    src = [
        LEAN_LIBRARY, LEAN_BYTE_LIBRARY, LEAN_CSV_LIBRARY, LEAN_OLS_LIBRARY,
        f"def pcsOLSRawCSV : List Nat := {_bytes(source.raw)}",
        "def pcsOLSCSVRecords : List (List (List Nat)) := pcsCSVFields pcsOLSRawCSV",
        f"example : pcsOLSCSVRecords.length = {n+1} := by decide +kernel",
        f"example : pcsOLSCSVRecords.head? = some ({header} : List (List Nat)) := by decide +kernel",
        f"example : pcsCSVValidWidths pcsOLSCSVRecords {width} = true := by decide +kernel",
        f"example : pcsCSVAllNumeric pcsOLSCSVRecords {n} {width} = true := by decide +kernel",
        f"def pcsOLSOriginalPairs : Option (List (Rat × Rat)) := "
        f"pcsOLSPairs pcsOLSCSVRecords {n} {xi} {yi} {_rat(xscale)} {_rat(yscale)}",
        "example : pcsOLSOriginalPairs.isSome = true := by decide +kernel",
        "def pcsOLSOriginalFit : Option PCSOLS := pcsOLSOriginalPairs.bind pcsOLSFit",
        "example : pcsOLSOriginalFit.isSome = true := by decide +kernel",
    ]
    reports: list[dict] = []
    for i, field in enumerate(REPORT_KEYS):
        truth = predicted[i] == prop.reported[i]
        status = "true" if truth else "false"
        src.append(f"example : pcsOLSMetric pcsOLSOriginalFit {i} {_rat(prop.reported[i])} = some {status} := by decide +kernel")
        reports.append({"metric": field, "reported": prop.original[i],
                        "computed_exact_si_by_external_python": str(predicted[i]),
                        "candidate_matches_by_external_python": truth,
                        "lean_metric_index": i})
    # Kernel-confirm the actual expected fit from the complete CSV, not only three comparisons.
    src.append(f"example : pcsOLSOriginalFit = some ⟨{_rat(predicted[0])}, {_rat(predicted[1])}, {_rat(predicted[2])}⟩ := by decide +kernel")
    return "\n\n".join(src) + "\n", tuple(reports)


def run_ols(source: Source, manifest: bytes, proposal: bytes, *, lean: LeanChecker | None = None,
            expected_data_sha256: str | None = None, expected_manifest_sha256: str | None = None,
            expected_proposal_sha256: str | None = None) -> dict:
    _check_pin(expected_data_sha256, source.digest, "data")
    _check_pin(expected_manifest_sha256, sha(manifest), "manifest")
    _check_pin(expected_proposal_sha256, sha(proposal), "proposal")
    code, reports = make_ols_lean_source(source, manifest, proposal)
    check = (lean or LeanChecker("__pcs_missing_lean_executable__"))._check_generated(code, True, "OLS_INTEGRATED")
    return {
        "schema_version": SCHEMA, "authority": AUTHORITY,
        "data_sha256": source.digest, "manifest_sha256": sha(manifest), "proposal_sha256": sha(proposal),
        "expected_data_sha256": expected_data_sha256, "expected_manifest_sha256": expected_manifest_sha256,
        "expected_proposal_sha256": expected_proposal_sha256,
        "pins_origin": "CALLER_SUPPLIED_NOT_INDEPENDENTLY_AUTHENTICATED",
        "submitted_rows": len(parse_table_rows(source, parse_table_spec(manifest))),
        "metrics": list(reports), "kernel_checked": check["kernel_checked"], "formal_status": check["status"],
        "semantic_fidelity": "UNREVIEWED", "scientific_status": "NOT_ASSESSED",
        "scope": "Exact OLS arithmetic on every row of the submitted CSV, with source bytes and quantities re-evaluated inside one Lean file. Statistical model suitability, independent data custody, semantics, and physical meaning remain unproved.",
        **{k: v for k, v in check.items() if k not in {"kernel_checked", "status"}},
    }


def replay_ols(source: Source, manifest: bytes, proposal: bytes, receipt: bytes, *, lean: LeanChecker | None = None,
               expected_data_sha256: str | None = None, expected_manifest_sha256: str | None = None,
               expected_proposal_sha256: str | None = None) -> dict:
    original = parse_receipt(receipt)
    base = {"schema_version": REPLAY_SCHEMA, "authority": AUTHORITY,
            "receipt_sha256": sha(receipt), "data_sha256": source.digest, "manifest_sha256": sha(manifest),
            "proposal_sha256": sha(proposal), "matched": False, "status": "RECEIPT_REJECTED",
            "scientific_status": "NOT_ASSESSED"}
    _check_pin(expected_data_sha256, source.digest, "data")
    _check_pin(expected_manifest_sha256, sha(manifest), "manifest")
    _check_pin(expected_proposal_sha256, sha(proposal), "proposal")
    if (original.get("schema_version") != SCHEMA or original.get("authority") != AUTHORITY or
        original.get("data_sha256") != source.digest or original.get("manifest_sha256") != sha(manifest) or
        original.get("proposal_sha256") != sha(proposal) or
        original.get("expected_data_sha256") != expected_data_sha256 or
        original.get("expected_manifest_sha256") != expected_manifest_sha256 or
        original.get("expected_proposal_sha256") != expected_proposal_sha256):
        base["reason"] = "source/manifest/proposal/commitment mismatch"
        return base
    current = run_ols(source, manifest, proposal, lean=lean, expected_data_sha256=expected_data_sha256,
                      expected_manifest_sha256=expected_manifest_sha256, expected_proposal_sha256=expected_proposal_sha256)
    if not current["kernel_checked"]:
        base["status"] = "KERNEL_UNAVAILABLE_OR_REJECTED"
    elif canonical(original) != canonical(current):
        base["reason"] = "fresh numerical computation or proof receipt differs"
    else:
        base["status"] = "REPLAYED_INTEGRATED_OLS"
        base["matched"] = True
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research-only exact OLS CSV-to-Lean verification")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--table-spec", type=Path, required=True)
    parser.add_argument("--ols-proposal", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--lean", default="lean")
    parser.add_argument("--expected-data-sha256")
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--expected-proposal-sha256")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        source = Source.from_bytes(args.source.read_bytes())
        manifest, proposed = args.table_spec.read_bytes(), args.ols_proposal.read_bytes()
        checker = LeanChecker(args.lean, timeout=55)
        if args.receipt is None:
            result = run_ols(source, manifest, proposed, lean=checker,
                             expected_data_sha256=args.expected_data_sha256,
                             expected_manifest_sha256=args.expected_manifest_sha256,
                             expected_proposal_sha256=args.expected_proposal_sha256)
            good = result["kernel_checked"]
            print(f"OLS: {result['formal_status']}; {len(result['metrics'])} exact reported metrics")
        else:
            result = replay_ols(source, manifest, proposed, args.receipt.read_bytes(), lean=checker,
                                expected_data_sha256=args.expected_data_sha256,
                                expected_manifest_sha256=args.expected_manifest_sha256,
                                expected_proposal_sha256=args.expected_proposal_sha256)
            good = result["matched"]
            print(f"OLS replay: {result['status']}")
        _write_private_json(args.out, result)
        return 0 if good else 2
    except (OSError, ValueError, TypeError, KeyError, OverflowError, InvalidReceipt) as exc:
        print(f"OLS rejected: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
