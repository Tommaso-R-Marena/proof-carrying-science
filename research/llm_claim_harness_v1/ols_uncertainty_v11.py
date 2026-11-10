"""Research v11: complete finite-corner OLS sensitivity under bounded response error.

Exact source-note bytes bind response error and coefficient tolerances.  Lean
rebuilds the CSV/fit, enumerates EVERY corner of the response uncertainty box,
and decides the finite universal tolerance statement, with explicit witnesses.

The theorem extending the finite-corner extrema to *all continuous* errors is
mathematically available for fixed predictors (OLS is affine in responses), but
is not kernel-proved by this module.  We report its exact affine range as a
separate external mathematical analysis, never as additional Lean authority.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import re
import sys

from .byte_bridge import _bytes
from .core import Source, sha, canonical
from .csv_integrated_v8 import _check_pin, _rat
from .ols_integrated_v9 import SCHEMA as OLS_SCHEMA, make_ols_lean_source, exact_fit, UnsupportedOLS
from .ols_note_v9 import HEX, SAFE_NAME, DECIMAL
from .ols_stability_v10 import LEAN_LOO_LIBRARY
from .pipeline import LeanChecker
from .replay_table import parse_receipt, InvalidReceipt, _write_private_json
from .table_evidence import parse_table_spec, parse_table_rows
from .typed import unit_value

SCHEMA = "pcs-ols-uncertainty-v11-research"
REPLAY_SCHEMA = "pcs-ols-uncertainty-replay-v11-research"
AUTHORITY = "EXPERIMENTAL_NOT_PCS_V06_AUTHORITY"
HEADER = "PCS-OLS-UNCERTAINTY/1"
NUMERICAL_FIELDS = ("response_error_si", "max_slope_shift_si", "max_intercept_shift_si")
FIELDS = ("data_sha256", "manifest_sha256", "x", "y", *NUMERICAL_FIELDS)
MIN_ROWS, MAX_ROWS = 3, 6


class UnsupportedUncertainty(ValueError):
    """Source, model, or bounded uncertainty request is unsupported."""


@dataclass(frozen=True)
class UncertaintyNote:
    x: str
    y: str
    bounds: tuple[Fraction, Fraction, Fraction]
    originals: tuple[str, str, str]
    spans: tuple[tuple[int, int], ...]
    digest: str


def parse_uncertainty_note(note: Source, source: Source, manifest: bytes) -> UncertaintyNote:
    raw = note.raw
    if not 0 < len(raw) <= 640 or b"\r" in raw or b"\0" in raw or not raw.isascii():
        raise UnsupportedUncertainty("uncertainty note must be bounded ASCII with LF")
    lines = raw.split(b"\n")
    if lines[-1] == b"":
        lines.pop()
    if len(lines) != len(FIELDS) + 1 or any(not ln for ln in lines) or lines[0] != HEADER.encode():
        raise UnsupportedUncertainty("uncertainty note must use exact canonical fields")
    values: dict[str, str] = {}
    spans: dict[str, tuple[int, int]] = {}
    offset = len(lines[0]) + 1
    for key, ln in zip(FIELDS, lines[1:]):
        prefix = (key + "=").encode("ascii")
        if not ln.startswith(prefix):
            raise UnsupportedUncertainty("unexpected field, duplicate field or ordering")
        value = ln[len(prefix):].decode("ascii")
        values[key] = value
        if key in NUMERICAL_FIELDS:
            spans[key] = (offset + len(prefix), offset + len(ln))
        offset += len(ln) + 1
    if (not HEX.fullmatch(values["data_sha256"]) or
        not HEX.fullmatch(values["manifest_sha256"]) or
        values["data_sha256"] != source.digest or values["manifest_sha256"] != sha(manifest)):
        raise UnsupportedUncertainty("source hashes do not match committed complete inputs")
    spec = parse_table_spec(manifest)
    valid_names = {c.name for c in spec.columns}
    x, y = values["x"], values["y"]
    if (not SAFE_NAME.fullmatch(x) or not SAFE_NAME.fullmatch(y) or
            x == y or x not in valid_names or y not in valid_names):
        raise UnsupportedUncertainty("predictor and response must be distinct declared columns")
    bounds = []
    for name in NUMERICAL_FIELDS:
        value = values[name]
        if not DECIMAL.fullmatch(value):
            raise UnsupportedUncertainty("bounds must be bounded exact decimal values")
        rational = Fraction(value)
        if not 0 <= rational <= 1000000:
            raise UnsupportedUncertainty("nonnegative finite and bounded error/tolerance required")
        start, end = spans[name]
        if raw[start:end] != value.encode("ascii"):
            raise UnsupportedUncertainty("numeric byte span mismatch")
        bounds.append(rational)
    return UncertaintyNote(x, y, tuple(bounds),
                           tuple(values[key] for key in NUMERICAL_FIELDS),
                           tuple(spans[key] for key in NUMERICAL_FIELDS), note.digest)


def _prepare(data: Source, manifest: bytes, note: Source):
    parsed = parse_uncertainty_note(note, data, manifest)
    spec = parse_table_spec(manifest)
    rows = parse_table_rows(data, spec)
    if not MIN_ROWS <= len(rows) <= MAX_ROWS:
        raise UnsupportedUncertainty("response uncertainty requires 3..6 complete rows")
    xs = {c.name: (i, c.unit) for i, c in enumerate(spec.columns)}
    xi, xunit = xs[parsed.x]
    yi, yunit = xs[parsed.y]
    xscale, _ = unit_value(xunit)
    yscale, _ = unit_value(yunit)
    points = tuple((Fraction(r.cells[xi].value) * xscale, Fraction(r.cells[yi].value) * yscale) for r in rows)
    n = len(points)
    sx = sum((x for x, _ in points), Fraction())
    delta = n * sum((x*x for x, _ in points), Fraction()) - sx * sx
    if delta <= 0:
        raise UnsupportedUncertainty("predictor is degenerate")
    # The exact affine functional (for fixed predictor x):
    #   slope(y) = sum_i [(n*x_i - sum x)/delta] * y_i
    #   intercept(y) = sum_i [1/n - (sum x/n)*w_i] * y_i.
    sw = tuple((n*x-sx) / delta for x, _ in points)
    bw = tuple(Fraction(1, n) - Fraction(sx, n)*w for w in sw)
    slope = sum((w*y for w, (_, y) in zip(sw, points)), Fraction())
    intercept = sum((w*y for w, (_, y) in zip(bw, points)), Fraction())
    err = parsed.bounds[0]
    sr = err * sum((abs(w) for w in sw), Fraction())
    br = err * sum((abs(w) for w in bw), Fraction())
    # Independent direct least-squares computation cross-check, not promotion.
    from .ols_integrated_v9 import parse_ols_proposal
    proposal = canonical({"schema": OLS_SCHEMA, "x": parsed.x, "y": parsed.y,
                          "reported": {"slope": "0", "intercept": "0", "sse": "0"}})
    prop = parse_ols_proposal(proposal, spec)
    original = exact_fit(rows, spec, prop)
    if (slope, intercept) != original[:2]:
        raise UnsupportedUncertainty("independent affine OLS computation disagreement")
    if any(max(abs(q.numerator), q.denominator) > 10**16 for q in (slope, intercept, sr, br)):
        raise UnsupportedUncertainty("rational bound exceeds verification budget")
    # Explicit corner enumeration to verify the affine formula numerically, too.
    corners: list[tuple[Fraction, Fraction]] = []
    for mask in range(1 << n):
        yy = tuple(y + (err if (mask >> i) & 1 else -err) for i, (_, y) in enumerate(points))
        aa = sum((w*y for w, y in zip(sw, yy)), Fraction())
        bb = sum((w*y for w, y in zip(bw, yy)), Fraction())
        # A deliberately separate direct closed-form fit guards against a bad
        # sign, ordering or affine-weight implementation in the proposal path.
        direct_sy = sum(yy, Fraction())
        direct_sxy = sum((x*y for (x, _), y in zip(points, yy)), Fraction())
        direct_a = (n*direct_sxy - sx*direct_sy) / delta
        direct_b = (direct_sy - direct_a*sx) / n
        if (aa, bb) != (direct_a, direct_b):
            raise UnsupportedUncertainty("independent corner refit mismatch")
        corners.append((aa, bb))
    min_slope, max_slope = min(a for a, _ in corners), max(a for a, _ in corners)
    min_int, max_int = min(b for _, b in corners), max(b for _, b in corners)
    if (min_slope, max_slope) != (slope-sr, slope+sr) or (min_int, max_int) != (intercept-br, intercept+br):
        raise UnsupportedUncertainty("direct corner extrema disagree with affine envelope")
    flags = tuple(abs(a-slope) <= parsed.bounds[1] and abs(b-intercept) <= parsed.bounds[2]
                  for a, b in corners)
    return parsed, proposal, original, (sr, br), corners, flags


LEAN_UNCERTAINTY_LIBRARY = '''-- All 2^n independent response-endpoint perturbations. Fixed x.
-- This certifies a FINITE corner claim; it does not by itself formally prove
-- extrema for arbitrary interior perturbations of a continuous response box.
def pcsOLSResponseCorners : List (Rat × Rat) → Rat → List (List (Rat × Rat))
  | [], _ => [[]]
  | p :: ps, error =>
      let tails := pcsOLSResponseCorners ps error
      tails.map (fun rest => (p.1, p.2 - error) :: rest) ++
      tails.map (fun rest => (p.1, p.2 + error) :: rest)

def pcsOLSResponseCornerFits (points : List (Rat × Rat)) (error : Rat) :
    List (Option PCSOLS) :=
  (pcsOLSResponseCorners points error).map pcsOLSFit

def pcsOLSResponseCornerFlags (base : Option PCSOLS) (points : List (Rat × Rat))
    (error slopeBound interceptBound : Option Rat) : Option (List (Option Bool)) := do
  let baseFit ← base
  let eps ← error
  let s ← slopeBound
  let b ← interceptBound
  pure ((pcsOLSResponseCornerFits points eps).map fun fit =>
    fit.map fun candidate => pcsOLSWithin baseFit candidate s b)
'''


def make_uncertainty_lean_source(data: Source, manifest: bytes, note: Source) -> tuple[str, dict]:
    parsed, proposal, original, radii, corners, flags = _prepare(data, manifest, note)
    base, _ = make_ols_lean_source(data, manifest, proposal)
    lines = [base, LEAN_LOO_LIBRARY, LEAN_UNCERTAINTY_LIBRARY,
             f"def pcsOLSUncertaintyRawNote : List Nat := {_bytes(note.raw)}"]
    for i, key in enumerate(NUMERICAL_FIELDS):
        start, end = parsed.spans[i]
        lines.append(f"def pcsOLSUncertaintyBound_{i} : Option Rat := "
                     f"pcsAsciiDecimal (pcsByteSlice pcsOLSUncertaintyRawNote {start} {end})")
        lines.append(f"example : pcsOLSUncertaintyBound_{i} = some {_rat(parsed.bounds[i])} := by decide +kernel")
    n = len(corners)
    lines.extend([
        "def pcsOLSRobustCorners : Option (List (List (Rat × Rat))) :=\n"
        "  do\n    let points ← pcsOLSOriginalPairs\n    let eps ← pcsOLSUncertaintyBound_0\n"
        "    pure (pcsOLSResponseCorners points eps)",
        f"example : pcsOLSRobustCorners.map List.length = some {n} := by decide +kernel",
        "def pcsOLSRobustFlags : Option (List (Option Bool)) :=\n"
        "  do\n    let points ← pcsOLSOriginalPairs\n"
        "    pcsOLSResponseCornerFlags pcsOLSOriginalFit points "
        "pcsOLSUncertaintyBound_0 pcsOLSUncertaintyBound_1 pcsOLSUncertaintyBound_2",
        f"example : pcsOLSRobustFlags.map List.length = some {n} := by decide +kernel",
        "def pcsOLSRobustVerdict : Option Bool :=\n  pcsOLSRobustFlags.bind pcsOLSAllStable",
        f"example : pcsOLSRobustVerdict = some {str(all(flags)).lower()} := by decide +kernel",
    ])
    for i, flag in enumerate(flags):
        lines.append(f"example : (pcsOLSRobustFlags.bind (fun flags => flags[{i}]?)) "
                     f"= some (some {str(flag).lower()}) := by decide +kernel")
    first_bad = next((i for i, x in enumerate(flags) if not x), None)
    if first_bad is not None:
        lines.append(f"example : (pcsOLSRobustFlags.bind (fun flags => flags[{first_bad}]?)) "
                     "= some (some false) := by decide +kernel")
    outcome = {
        "row_count": n.bit_length()-1,
        "complete_corner_count": n,
        "error_bound_source_span": list(parsed.spans[0]),
        "tolerance_source_spans": [list(p) for p in parsed.spans[1:]],
        "nominal_slope_si_by_external_python": str(original[0]),
        "nominal_intercept_si_by_external_python": str(original[1]),
        "exact_affine_slope_radius_by_external_python": str(radii[0]),
        "exact_affine_intercept_radius_by_external_python": str(radii[1]),
        "corner_slopes_si_by_external_python": [str(a) for a, _ in corners],
        "corner_intercepts_si_by_external_python": [str(b) for _, b in corners],
        "corner_flags_by_external_python": list(flags),
        "first_violating_corner_index": first_bad,
        "all_corners_within_tolerances_by_external_python": all(flags),
    }
    return "\n\n".join(lines)+"\n", outcome


def run_uncertainty(data: Source, manifest: bytes, note: Source, *,
                    lean: LeanChecker | None = None,
                    expected_data_sha256: str | None = None,
                    expected_manifest_sha256: str | None = None,
                    expected_note_sha256: str | None = None) -> dict:
    _check_pin(expected_data_sha256, data.digest, "data")
    _check_pin(expected_manifest_sha256, sha(manifest), "manifest")
    _check_pin(expected_note_sha256, note.digest, "note")
    code, metrics = make_uncertainty_lean_source(data, manifest, note)
    checked = (lean or LeanChecker("__pcs_missing_lean_executable__", timeout=55))._check_generated(code, True, "OLS_RESPONSE_CORNERS")
    success = bool(checked["kernel_checked"])
    return {
        "schema_version": SCHEMA, "authority": AUTHORITY,
        "data_sha256": data.digest, "manifest_sha256": sha(manifest), "note_sha256": note.digest,
        "expected_data_sha256": expected_data_sha256,
        "expected_manifest_sha256": expected_manifest_sha256,
        "expected_note_sha256": expected_note_sha256,
        "kernel_checked": success, "formal_status": checked["status"],
        "finite_corner_verdict": (
            "ALL_CORNERS_WITHIN_THRESHOLDS" if metrics["all_corners_within_tolerances_by_external_python"]
            else "COUNTEREXAMPLE_CORNER") if success else "UNVERIFIED",
        "continuous_response_envelope": "EXTERNAL_AFFINE_DERIVATION_NOT_KERNEL_PROVED",
        "meaning_status": "SEMANTIC_REVIEW_REQUIRED", "scientific_status": "NOT_ASSESSED",
        "scope": "All 2^n exact-rational independent +/- response-error CORNERS for 3..6 complete fixed-x rows, with source-decoded bounds. Interior-box extremum theorem and statistical measurement validity NOT established by this Lean file.",
        "metrics": metrics,
        **{k:v for k,v in checked.items() if k not in {"status", "kernel_checked"}},
    }


def replay_uncertainty(data: Source, manifest: bytes, note: Source, receipt: bytes, *,
                       lean: LeanChecker | None = None,
                       expected_data_sha256: str | None = None,
                       expected_manifest_sha256: str | None = None,
                       expected_note_sha256: str | None = None) -> dict:
    incoming = parse_receipt(receipt)
    result = {"schema_version": REPLAY_SCHEMA, "authority": AUTHORITY,
              "receipt_sha256": sha(receipt), "data_sha256": data.digest,
              "manifest_sha256": sha(manifest), "note_sha256": note.digest,
              "status": "RECEIPT_REJECTED", "matched": False, "scientific_status": "NOT_ASSESSED"}
    _check_pin(expected_data_sha256, data.digest, "data")
    _check_pin(expected_manifest_sha256, sha(manifest), "manifest")
    _check_pin(expected_note_sha256, note.digest, "note")
    if (incoming.get("schema_version") != SCHEMA or incoming.get("authority") != AUTHORITY or
        incoming.get("data_sha256") != data.digest or incoming.get("manifest_sha256") != sha(manifest) or
        incoming.get("note_sha256") != note.digest or
        incoming.get("expected_data_sha256") != expected_data_sha256 or
        incoming.get("expected_manifest_sha256") != expected_manifest_sha256 or
        incoming.get("expected_note_sha256") != expected_note_sha256):
        result["reason"] = "source, schema, or caller pin mismatch"
        return result
    fresh = run_uncertainty(data, manifest, note, lean=lean,
                            expected_data_sha256=expected_data_sha256,
                            expected_manifest_sha256=expected_manifest_sha256,
                            expected_note_sha256=expected_note_sha256)
    if not fresh["kernel_checked"]:
        result["status"] = "KERNEL_UNAVAILABLE_OR_REJECTED"
    elif canonical(fresh) != canonical(incoming):
        result["reason"] = "fresh checked source/metrics disagree with incoming receipt"
    else:
        result["status"], result["matched"] = "REPLAYED_OLS_RESPONSE_CORNERS", True
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exact source-bound OLS response-error corner audit")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--table-spec", required=True, type=Path)
    parser.add_argument("--uncertainty-note", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--lean", default="lean")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--expected-data-sha256")
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--expected-note-sha256")
    args = parser.parse_args(argv)
    try:
        data = Source.from_bytes(args.source.read_bytes())
        manifest = args.table_spec.read_bytes()
        note = Source.from_bytes(args.uncertainty_note.read_bytes())
        checker = LeanChecker(args.lean, timeout=55)
        if args.receipt:
            out = replay_uncertainty(data, manifest, note, args.receipt.read_bytes(), lean=checker,
                                     expected_data_sha256=args.expected_data_sha256,
                                     expected_manifest_sha256=args.expected_manifest_sha256,
                                     expected_note_sha256=args.expected_note_sha256)
            ok = out["matched"]
        else:
            out = run_uncertainty(data, manifest, note, lean=checker,
                                  expected_data_sha256=args.expected_data_sha256,
                                  expected_manifest_sha256=args.expected_manifest_sha256,
                                  expected_note_sha256=args.expected_note_sha256)
            ok = out["kernel_checked"]
        _write_private_json(args.out, out)
        print(out.get("finite_corner_verdict", out.get("status")))
        return 0 if ok else 2
    except (OSError, ValueError, OverflowError, TypeError, KeyError, InvalidReceipt) as exc:
        print(f"uncertainty audit refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
