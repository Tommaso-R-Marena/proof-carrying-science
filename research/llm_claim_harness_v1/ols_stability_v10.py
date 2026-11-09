"""Experimental v10: complete leave-one-out (LOO) sensitivity from exact source bytes.

One generated Lean program decodes the complete CSV and strict source-note bounds,
refits every deletion, and checks/refutes the *finite* all-deletions claim.
This is mathematical sensitivity, not statistical generalization or causal evidence.
No Python/LLM-selected subset is admitted as an all-rows certificate.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
import re
import sys
from pathlib import Path

from .byte_bridge import _bytes
from .core import Source, canonical, sha
from .csv_integrated_v8 import _check_pin, _rat
from .ols_integrated_v9 import (
    AUTHORITY, LEAN_OLS_LIBRARY, UnsupportedOLS, exact_fit,
    make_ols_lean_source, parse_ols_proposal, _prepare as prepare_ols,
)
from .ols_note_v9 import HEX, SAFE_NAME, DECIMAL
from .pipeline import LeanChecker
from .replay_table import InvalidReceipt, parse_receipt, _write_private_json
from .table_evidence import parse_table_rows, parse_table_spec

SCHEMA = "pcs-ols-loo-v10-research"
REPLAY_SCHEMA = "pcs-ols-loo-replay-v10-research"
HEADER = "PCS-OLS-LOO/1"
NUMBERS = ("max_slope_delta", "max_intercept_delta")
KEYS = ("data_sha256", "manifest_sha256", "x", "y", *NUMBERS)


class UnsupportedStability(ValueError):
    """Source note, regression, or stability obligation is unsupported."""


@dataclass(frozen=True)
class StabilityNote:
    x: str
    y: str
    thresholds: tuple[Fraction, Fraction]
    originals: tuple[str, str]
    spans: tuple[tuple[int, int], tuple[int, int]]
    digest: str


def parse_stability_note(note: Source, data: Source, manifest: bytes) -> StabilityNote:
    raw = note.raw
    if not 0 < len(raw) <= 512 or b"\r" in raw or b"\x00" in raw or not raw.isascii():
        raise UnsupportedStability("note must be bounded ASCII with LF line endings")
    parts = raw.split(b"\n")
    if parts[-1] == b"":
        parts.pop()
    if len(parts) != 7 or any(not p for p in parts):
        raise UnsupportedStability("note must have exactly seven nonempty lines")
    if parts[0] != HEADER.encode():
        raise UnsupportedStability("incorrect note grammar version")
    fields: dict[str, str] = {}
    spans: dict[str, tuple[int, int]] = {}
    offset = len(parts[0]) + 1
    for key, line in zip(KEYS, parts[1:]):
        prefix = (key + "=").encode()
        if not line.startswith(prefix):
            raise UnsupportedStability("note keys missing or not in canonical order")
        value = line[len(prefix):].decode("ascii")
        fields[key] = value
        if key in NUMBERS:
            spans[key] = (offset + len(prefix), offset + len(line))
        offset += len(line) + 1
    if not all(HEX.fullmatch(fields[k]) for k in ("data_sha256", "manifest_sha256")):
        raise UnsupportedStability("note commitment must use lowercase SHA-256")
    if fields["data_sha256"] != data.digest or fields["manifest_sha256"] != sha(manifest):
        raise UnsupportedStability("note does not refer to exact submitted data and manifest")
    spec = parse_table_spec(manifest)
    allowed = {col.name for col in spec.columns}
    x, y = fields["x"], fields["y"]
    if not SAFE_NAME.fullmatch(x) or not SAFE_NAME.fullmatch(y) or x == y or x not in allowed or y not in allowed:
        raise UnsupportedStability("predictor/response must be distinct manifest columns")
    bounds: list[Fraction] = []
    for field in NUMBERS:
        v = fields[field]
        if not DECIMAL.fullmatch(v):
            raise UnsupportedStability("thresholds must be bounded exact decimal numerals")
        q = Fraction(v)
        if q < 0 or q > 1000000:
            raise UnsupportedStability("thresholds must be nonnegative and bounded")
        start, end = spans[field]
        if raw[start:end] != v.encode("ascii"):
            raise UnsupportedStability("threshold not reproduced from original note bytes")
        bounds.append(q)
    return StabilityNote(x, y, tuple(bounds), tuple(fields[k] for k in NUMBERS),
                         tuple(spans[k] for k in NUMBERS), note.digest)


def _loo_values(data: Source, manifest: bytes, note: StabilityNote):
    spec = parse_table_spec(manifest)
    rows = parse_table_rows(data, spec)
    if len(rows) < 3 or len(rows) > 8:
        raise UnsupportedStability("LOO requires 3..8 complete records")
    # Parent validates limits, exact units, columns and all original source numerals.
    from .ols_integrated_v9 import SCHEMA as OLS_SCHEMA
    proposal = canonical({"schema": OLS_SCHEMA, "x": note.x, "y": note.y,
                          "reported": {"slope": "0", "intercept": "0", "sse": "0"}})
    _, _, prop, baseline = prepare_ols(data, manifest, proposal)
    fits = []
    for i in range(len(rows)):
        try:
            fits.append(exact_fit(rows[:i] + rows[i + 1:], spec, prop))
        except UnsupportedOLS as exc:
            # Never claim robustness if a deletion makes the regression undefined.
            raise UnsupportedStability(f"deleting row {rows[i].number} makes OLS undefined") from exc
    return rows, proposal, baseline, tuple(fits)


LEAN_LOO_LIBRARY = '''-- All single-row deletions of the source-decoded, unit-scaled pairs.
-- Uses the same fully reconstructed complete CSV as the v9 OLS verifier.
def pcsOLSLOOFits (points : List (Rat × Rat)) : List (Option PCSOLS) :=
  (List.range points.length).map (fun i =>
    pcsOLSFit ((points.take i) ++ (points.drop (i + 1))))

def pcsOLSAbs (x : Rat) : Rat := if x < 0 then -x else x

def pcsOLSWithin (full deleted : PCSOLS) (slopeBound interceptBound : Rat) : Bool :=
  decide (pcsOLSAbs (full.slope - deleted.slope) <= slopeBound) &&
  decide (pcsOLSAbs (full.intercept - deleted.intercept) <= interceptBound)

def pcsOLSLOOFlags (base : Option PCSOLS) (fits : List (Option PCSOLS))
    (slopeBound interceptBound : Option Rat) : List (Option Bool) :=
  fits.map (fun optionFit => do
    let baseline ← base
    let deleted ← optionFit
    let bs ← slopeBound
    let bi ← interceptBound
    pure (pcsOLSWithin baseline deleted bs bi))

def pcsOLSAllStable (flags : List (Option Bool)) : Option Bool :=
  flags.foldl (fun result current => do
    let old ← result
    let now ← current
    pure (old && now)) (some true)
'''


def make_stability_lean_source(data: Source, manifest: bytes, note: Source) -> tuple[str, dict]:
    parsed = parse_stability_note(note, data, manifest)
    rows, proposal, baseline, deleted = _loo_values(data, manifest, parsed)
    # Reuse v9 integrated source-byte, CSV and full-fit definitions. It also
    # validates all CSV rows, independent of Python's precomputed normal form.
    original, _ = make_ols_lean_source(data, manifest, proposal)
    start_s, end_s = parsed.spans[0]
    start_i, end_i = parsed.spans[1]
    flags = [abs(baseline[0] - fit[0]) <= parsed.thresholds[0] and
             abs(baseline[1] - fit[1]) <= parsed.thresholds[1] for fit in deleted]
    first_bad = next((i for i, flag in enumerate(flags) if not flag), None)
    src = [
        original, LEAN_LOO_LIBRARY,
        f"def pcsOLSLOORawNote : List Nat := {_bytes(note.raw)}",
        f"def pcsOLSLOOSlopeThreshold : Option Rat := pcsAsciiDecimal (pcsByteSlice pcsOLSLOORawNote {start_s} {end_s})",
        f"def pcsOLSLOOInterceptThreshold : Option Rat := pcsAsciiDecimal (pcsByteSlice pcsOLSLOORawNote {start_i} {end_i})",
        f"example : pcsOLSLOOSlopeThreshold = some {_rat(parsed.thresholds[0])} := by decide +kernel",
        f"example : pcsOLSLOOInterceptThreshold = some {_rat(parsed.thresholds[1])} := by decide +kernel",
        "def pcsOLSDeletedFits : Option (List (Option PCSOLS)) := pcsOLSOriginalPairs.map pcsOLSLOOFits",
        f"example : pcsOLSDeletedFits.map List.length = some {len(rows)} := by decide +kernel",
        "def pcsOLSStabilityFlags : Option (List (Option Bool)) :=\n" 
        "  pcsOLSDeletedFits.map (fun fs => pcsOLSLOOFlags pcsOLSOriginalFit fs "
        "pcsOLSLOOSlopeThreshold pcsOLSLOOInterceptThreshold)",
        f"example : pcsOLSStabilityFlags.map List.length = some {len(rows)} := by decide +kernel",
        "def pcsOLSStabilityVerdict : Option Bool :=\n"
        "  pcsOLSStabilityFlags.bind pcsOLSAllStable",
        f"example : pcsOLSStabilityVerdict = some {str(all(flags)).lower()} := by decide +kernel",
    ]
    # Positive coverage: all expected deletions return a defined OLS fit, not none.
    for i in range(len(rows)):
        src.append(f"example : (pcsOLSDeletedFits.bind (fun fs => fs[{i}]?)).isSome = true := by decide +kernel")
        src.append(f"example : (pcsOLSStabilityFlags.bind (fun fs => fs[{i}]?)) = some (some {str(flags[i]).lower()}) := by decide +kernel")
    # NOTE: .isSome above checks outer Option, and is weaker than checking the
    # inner `Option PCSOLS`; the per-index flag equality *does* rule out none.
    if first_bad is not None:
        src.append(f"example : (pcsOLSStabilityFlags.bind (fun fs => fs[{first_bad}]?)) = some (some false) := by decide +kernel")
    metrics = {
        "reported_max_slope_delta": parsed.originals[0],
        "reported_max_intercept_delta": parsed.originals[1],
        "threshold_source_spans": [list(span) for span in parsed.spans],
        "complete_record_count": len(rows),
        "observed_all_deletions_within_bounds_by_external_python": all(flags),
        "first_counterexample_row": rows[first_bad].number if first_bad is not None else None,
        "per_deletion": [
            {"deleted_row": rows[i].number, "slope_exact_si": str(fit[0]),
             "intercept_exact_si": str(fit[1]), "sse_exact_si": str(fit[2]),
             "slope_change_exact_si": str(abs(fit[0] - baseline[0])),
             "intercept_change_exact_si": str(abs(fit[1] - baseline[1])),
             "within_threshold_by_external_python": flags[i]} for i, fit in enumerate(deleted)
        ],
    }
    return "\n\n".join(src) + "\n", metrics


def run_stability(data: Source, manifest: bytes, note: Source, *, lean: LeanChecker | None = None,
                  expected_data_sha256: str | None = None,
                  expected_manifest_sha256: str | None = None,
                  expected_note_sha256: str | None = None) -> dict:
    _check_pin(expected_data_sha256, data.digest, "data")
    _check_pin(expected_manifest_sha256, sha(manifest), "manifest")
    _check_pin(expected_note_sha256, note.digest, "note")
    code, metrics = make_stability_lean_source(data, manifest, note)
    checked = (lean or LeanChecker("__pcs_missing_lean_executable__", timeout=55))._check_generated(code, True, "OLS_LOO")
    success = bool(checked["kernel_checked"])
    return {
        "schema_version": SCHEMA,
        "authority": AUTHORITY,
        "data_sha256": data.digest, "manifest_sha256": sha(manifest), "note_sha256": note.digest,
        "expected_data_sha256": expected_data_sha256,
        "expected_manifest_sha256": expected_manifest_sha256,
        "expected_note_sha256": expected_note_sha256,
        "kernel_checked": success, "formal_status": checked["status"],
        "finite_loo_verdict": ("ALL_DELETIONS_WITHIN_THRESHOLDS" if metrics["observed_all_deletions_within_bounds_by_external_python"]
                               else "COUNTEREXAMPLE_TO_ALL_DELETIONS") if success else "UNVERIFIED",
        "claim_source": "STRICT_EXACT_BYTE_NOTE_NOT_INDEPENDENTLY_AUTHENTICATED",
        "meaning_status": "SEMANTIC_REVIEW_REQUIRED", "scientific_status": "NOT_ASSESSED",
        "metrics": metrics,
        "scope": "All individual row-deletion OLS refits within 3..8 exact-rational CSV observations; note thresholds interpreted in SI slope/intercept units. No theorem about external records, sampling, generalization, outlier resistance beyond deletion-one or domain meaning.",
        **{k: v for k, v in checked.items() if k not in {"status", "kernel_checked"}},
    }


def replay_stability(data: Source, manifest: bytes, note: Source, receipt: bytes,
                     *, lean: LeanChecker | None = None,
                     expected_data_sha256: str | None = None,
                     expected_manifest_sha256: str | None = None,
                     expected_note_sha256: str | None = None) -> dict:
    incoming = parse_receipt(receipt)
    result = {"schema_version": REPLAY_SCHEMA, "authority": AUTHORITY,
              "data_sha256": data.digest, "manifest_sha256": sha(manifest), "note_sha256": note.digest,
              "receipt_sha256": sha(receipt), "matched": False, "status": "RECEIPT_REJECTED",
              "scientific_status": "NOT_ASSESSED"}
    _check_pin(expected_data_sha256, data.digest, "data")
    _check_pin(expected_manifest_sha256, sha(manifest), "manifest")
    _check_pin(expected_note_sha256, note.digest, "note")
    if (incoming.get("schema_version") != SCHEMA or incoming.get("authority") != AUTHORITY
        or incoming.get("data_sha256") != data.digest or incoming.get("manifest_sha256") != sha(manifest)
        or incoming.get("note_sha256") != note.digest
        or incoming.get("expected_data_sha256") != expected_data_sha256
        or incoming.get("expected_manifest_sha256") != expected_manifest_sha256
        or incoming.get("expected_note_sha256") != expected_note_sha256):
        result["reason"] = "source identity or caller pin mismatch"
        return result
    current = run_stability(data, manifest, note, lean=lean,
                            expected_data_sha256=expected_data_sha256,
                            expected_manifest_sha256=expected_manifest_sha256,
                            expected_note_sha256=expected_note_sha256)
    if not current["kernel_checked"]:
        result["status"] = "KERNEL_UNAVAILABLE_OR_REJECTED"
    elif canonical(current) != canonical(incoming):
        result["reason"] = "fresh calculation does not match original receipt"
    else:
        result["status"], result["matched"] = "REPLAYED_OLS_LOO", True
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experimental exact source CSV leave-one-out OLS certificate")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--table-spec", type=Path, required=True)
    parser.add_argument("--stability-note", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--lean", default="lean")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--expected-data-sha256")
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--expected-note-sha256")
    args = parser.parse_args(argv)
    try:
        data = Source.from_bytes(args.source.read_bytes())
        manifest = args.table_spec.read_bytes()
        note = Source.from_bytes(args.stability_note.read_bytes())
        checker = LeanChecker(args.lean, timeout=55)
        if args.receipt:
            result = replay_stability(data, manifest, note, args.receipt.read_bytes(), lean=checker,
                                      expected_data_sha256=args.expected_data_sha256,
                                      expected_manifest_sha256=args.expected_manifest_sha256,
                                      expected_note_sha256=args.expected_note_sha256)
            good = result["matched"]
        else:
            result = run_stability(data, manifest, note, lean=checker,
                                   expected_data_sha256=args.expected_data_sha256,
                                   expected_manifest_sha256=args.expected_manifest_sha256,
                                   expected_note_sha256=args.expected_note_sha256)
            good = result["kernel_checked"]
        _write_private_json(args.out, result)
        print(f"Exact leave-one-out: {result.get('finite_loo_verdict', result.get('status'))}")
        return 0 if good else 2
    except (OSError, ValueError, TypeError, KeyError, OverflowError, InvalidReceipt) as exc:
        print(f"LOO refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
