"""V9.1 research note-to-data-to-Lean bridge (strict declarative input).

The *note* and the *CSV* are distinct complete byte artifacts. The note pins the
CSV and schema hashes; locally checked note grammar selects exact byte ranges
for each reported metric. The Lean certificate evaluates the CSV fit and re-reads
all reported numbers from the raw note bytes in the SAME generated script.

This is a deliberately narrow author/reviewer-controlled claim language, not a
general paper parser or a proof that author provenance/scientific meaning is true.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import argparse
import json
import re
import sys

from .byte_bridge import _bytes
from .core import Source, sha, canonical
from .csv_integrated_v8 import _check_pin
from .ols_integrated_v9 import (
    SCHEMA as OLS_SCHEMA, REPORTED as OLS_NUM, make_ols_lean_source,
    REPORT_KEYS, AUTHORITY,
)
from .pipeline import LeanChecker
from .replay_table import parse_receipt, InvalidReceipt, _write_private_json
from .table_evidence import parse_table_spec

SCHEMA = "pcs-ols-note-v9-research"
REPLAY_SCHEMA = "pcs-ols-note-replay-v9-research"
HEADER = "PCS-OLS-NOTE/1"
HEX = re.compile(r"[0-9a-f]{64}\Z")
SAFE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}\Z")
DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]{0,5})(?:\.[0-9]{1,6})?\Z")


class UnsupportedNote(ValueError):
    """Unsupported evidence-bound note or ambiguity."""


@dataclass(frozen=True)
class BoundNote:
    x: str
    y: str
    reported: tuple[str, str, str]
    numeric_spans: tuple[tuple[int, int], ...]
    digest: str


def parse_ols_note(note: Source, source: Source, table_spec: bytes) -> BoundNote:
    """Parse exact ordered note grammar, with no partial/ambiguous acceptance."""
    raw = note.raw
    if len(raw) > 800 or not raw.isascii() or b"\r" in raw or b"\x00" in raw:
        raise UnsupportedNote("note must be bounded ASCII LF with no CR/NUL")
    physical = raw.split(b"\n")
    if physical[-1] == b"":
        physical.pop()  # one terminal LF is allowed
    if len(physical) != 8 or any(not item for item in physical):
        raise UnsupportedNote("note requires exactly eight nonempty source lines")
    try:
        lines = [line.decode("ascii") for line in physical]
    except UnicodeDecodeError as exc:
        raise UnsupportedNote("note is not ASCII") from exc
    if lines[0] != HEADER:
        raise UnsupportedNote("wrong note version")
    keys = ("data_sha256", "manifest_sha256", "x", "y", "slope", "intercept", "sse")
    fields = {}
    spans = {}
    offset = len(physical[0]) + 1
    for line, key, raw_line in zip(lines[1:], keys, physical[1:]):
        prefix = key + "="
        if not line.startswith(prefix):
            raise UnsupportedNote("note lines must be canonical ordered fields")
        fields[key] = line[len(prefix):]
        if key in REPORT_KEYS:
            spans[key] = (offset + len(prefix), offset + len(raw_line))
        offset += len(raw_line) + 1
    if not HEX.fullmatch(fields["data_sha256"]) or not HEX.fullmatch(fields["manifest_sha256"]):
        raise UnsupportedNote("note hash fields must be lowercase SHA-256")
    if fields["data_sha256"] != source.digest or fields["manifest_sha256"] != sha(table_spec):
        raise UnsupportedNote("note does not match complete supplied data/schema hashes")
    spec = parse_table_spec(table_spec)
    allowed = {col.name for col in spec.columns}
    x, y = fields["x"], fields["y"]
    if not SAFE_NAME.fullmatch(x) or not SAFE_NAME.fullmatch(y) or x == y or x not in allowed or y not in allowed:
        raise UnsupportedNote("note's predictor/response must be distinct manifest columns")
    for key in REPORT_KEYS:
        if not DECIMAL.fullmatch(fields[key]):
            raise UnsupportedNote("source metrics must be exact bounded decimal literals")
    if Fraction(fields["sse"]) < 0:
        raise UnsupportedNote("negative SSE report rejected")
    values = tuple(fields[key] for key in REPORT_KEYS)
    slices = tuple(spans[key] for key in REPORT_KEYS)
    for value, (start, end) in zip(values, slices):
        if raw[start:end] != value.encode("ascii"):
            raise UnsupportedNote("byte offset did not reproduce note value")
    return BoundNote(x, y, values, slices, note.digest)


def make_note_lean_source(data: Source, table_spec: bytes, note: Source) -> tuple[str, tuple[dict, ...]]:
    parsed = parse_ols_note(note, data, table_spec)
    # The author's report is mechanically extracted from the note; a model
    # cannot choose a different numeric expectation or an alternate column.
    proposal = canonical({"schema": OLS_SCHEMA, "x": parsed.x, "y": parsed.y,
                          "reported": dict(zip(REPORT_KEYS, parsed.reported))})
    base, metrics = make_ols_lean_source(data, table_spec, proposal)
    lines = [base, f"def pcsOLSReportRaw : List Nat := {_bytes(note.raw)}"]
    receipts = []
    for i, (metric, text, (start, end)) in enumerate(zip(REPORT_KEYS, parsed.reported, parsed.numeric_spans)):
        # The numeric value on the right side is NOT a Python literal in this
        # Lean proposition: Lean directly decodes the original report bytes.
        decoded = f"(pcsAsciiDecimal (pcsByteSlice pcsOLSReportRaw {start} {end}))"
        truth = metrics[i]["candidate_matches_by_external_python"]
        result = "true" if truth else "false"
        lines.append(f"example : {decoded}.isSome = true := by decide +kernel")
        lines.append(f"example : ({decoded}.bind (fun n => pcsOLSMetric pcsOLSOriginalFit {i} n)) = some {result} := by decide +kernel")
        receipts.append({"metric": metric, "reported_quote": text,
                         "report_byte_start": start, "report_byte_end": end,
                         "candidate_matches_by_external_python": truth,
                         "computed_exact_si_by_external_python": metrics[i]["computed_exact_si_by_external_python"]})
    return "\n\n".join(lines) + "\n", tuple(receipts)


def run_ols_note(data: Source, table_spec: bytes, note: Source, *, lean: LeanChecker | None = None,
                 expected_data_sha256: str | None = None,
                 expected_manifest_sha256: str | None = None,
                 expected_note_sha256: str | None = None) -> dict:
    _check_pin(expected_data_sha256, data.digest, "data")
    _check_pin(expected_manifest_sha256, sha(table_spec), "manifest")
    _check_pin(expected_note_sha256, note.digest, "note")
    code, metrics = make_note_lean_source(data, table_spec, note)
    check = (lean or LeanChecker("__pcs_missing_lean_executable__"))._check_generated(code, True, "OLS_NOTE")
    return {
        "schema_version": SCHEMA,
        "authority": AUTHORITY,
        "data_sha256": data.digest,
        "manifest_sha256": sha(table_spec),
        "report_note_sha256": note.digest,
        "expected_data_sha256": expected_data_sha256,
        "expected_manifest_sha256": expected_manifest_sha256,
        "expected_note_sha256": expected_note_sha256,
        "claim_source_type": "EXACT_AUTHOR_OR_REVIEWER_CONTROLLED_NOTE_UNAUTHENTICATED",
        "reported_metric_sources": list(metrics),
        "kernel_checked": check["kernel_checked"], "formal_status": check["status"],
        "semantic_fidelity": "UNREVIEWED",
        "scientific_status": "NOT_ASSESSED",
        "scope": "One Lean file reads exact metric bytes from declarative note and computes regression from exact CSV bytes. Note authorship, fidelity to original research paper, units, sampling and statistical validity are not certified.",
        **{k:v for k,v in check.items() if k not in {"kernel_checked","status"}},
    }


def replay_ols_note(data: Source, table_spec: bytes, note: Source, receipt: bytes, *, lean: LeanChecker | None = None,
                    expected_data_sha256: str | None = None,
                    expected_manifest_sha256: str | None = None,
                    expected_note_sha256: str | None = None) -> dict:
    original = parse_receipt(receipt)
    base = {"schema_version": REPLAY_SCHEMA, "authority": AUTHORITY,
            "original_receipt_sha256": sha(receipt), "data_sha256": data.digest,
            "manifest_sha256": sha(table_spec), "report_note_sha256": note.digest,
            "matched": False, "status": "RECEIPT_REJECTED", "scientific_status": "NOT_ASSESSED"}
    _check_pin(expected_data_sha256, data.digest, "data")
    _check_pin(expected_manifest_sha256, sha(table_spec), "manifest")
    _check_pin(expected_note_sha256, note.digest, "note")
    if (original.get("schema_version") != SCHEMA or original.get("authority") != AUTHORITY or
        original.get("data_sha256") != data.digest or original.get("manifest_sha256") != sha(table_spec) or
        original.get("report_note_sha256") != note.digest or
        original.get("expected_data_sha256") != expected_data_sha256 or
        original.get("expected_manifest_sha256") != expected_manifest_sha256 or
        original.get("expected_note_sha256") != expected_note_sha256):
        base["reason"] = "source, schema or external pin mismatch"
        return base
    now = run_ols_note(data, table_spec, note, lean=lean, expected_data_sha256=expected_data_sha256,
                       expected_manifest_sha256=expected_manifest_sha256, expected_note_sha256=expected_note_sha256)
    if not now["kernel_checked"]:
        base["status"] = "KERNEL_UNAVAILABLE_OR_REJECTED"
    elif canonical(now) != canonical(original):
        base["reason"] = "fresh proof source/status differs from receipt"
    else:
        base["status"] = "REPLAYED_OLS_NOTE"
        base["matched"] = True
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experimental source-note-to-CSV-to-Lean exact regression")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--table-spec", required=True, type=Path)
    parser.add_argument("--report-note", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--lean", default="lean")
    parser.add_argument("--expected-data-sha256")
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--expected-note-sha256")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        data = Source.from_bytes(args.source.read_bytes())
        manifest = args.table_spec.read_bytes()
        note = Source.from_bytes(args.report_note.read_bytes())
        lean = LeanChecker(args.lean, timeout=55)
        if args.receipt is None:
            report = run_ols_note(data, manifest, note, lean=lean,
                                  expected_data_sha256=args.expected_data_sha256,
                                  expected_manifest_sha256=args.expected_manifest_sha256,
                                  expected_note_sha256=args.expected_note_sha256)
            good = report["kernel_checked"]
            print(f"OLS note: {report['formal_status']} / {len(report['reported_metric_sources'])} metrics")
        else:
            report = replay_ols_note(data, manifest, note, args.receipt.read_bytes(), lean=lean,
                                     expected_data_sha256=args.expected_data_sha256,
                                     expected_manifest_sha256=args.expected_manifest_sha256,
                                     expected_note_sha256=args.expected_note_sha256)
            good = report["matched"]
            print(f"OLS note replay: {report['status']}")
        _write_private_json(args.out, report)
        return 0 if good else 2
    except (OSError, ValueError, KeyError, TypeError, OverflowError, InvalidReceipt) as exc:
        print(f"OLS note refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
