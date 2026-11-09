"""Research-only native Lean replay of a previously issued CSV evidence receipt.

The incoming receipt is *untrusted*: its declared `kernel_checked` bit, proof
source, statuses, cell hashes and arithmetic values are never accepted at face
value. The verifier reconstructs all obligations from the independent source
bytes + a caller-supplied manifest and invokes pinned Lean afresh. It uses the
same Python parser/compiler as the producer, so it does NOT eliminate that TCB.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

from .core import Source, canonical, sha
from .pipeline import LeanChecker
from .table_evidence import UnsupportedTable, _strict_pairs, parse_table_spec, run_table

MAX_RECEIPT_BYTES = 2_000_000


class InvalidReceipt(ValueError):
    """Untrusted, noncanonical or altered receipt."""


def parse_receipt(raw: bytes) -> dict:
    if not 0 < len(raw) <= MAX_RECEIPT_BYTES:
        raise InvalidReceipt("receipt exceeds size bound or is empty")
    try:
        obj = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_strict_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(InvalidReceipt("nonfinite JSON value")))
    except (UnicodeError, json.JSONDecodeError, UnsupportedTable) as exc:
        raise InvalidReceipt("receipt is not strict unique-key JSON") from exc
    if type(obj) is not dict or raw not in {canonical(obj), canonical(obj) + b"\n"}:
        raise InvalidReceipt("receipt must use canonical JSON with at most one terminal newline")
    return obj


def replay_table(source: Source, manifest: bytes, receipt: bytes, *, lean: LeanChecker | None = None) -> dict:
    """Independently re-execute *the same v5 receiver* and compare the full receipt.

    Acceptance means only that a locally pinned Lean implementation freshly
    proved/refuted every closed row proposition from the re-parsed input bytes.
    The manifest's scientific meaning and Python parser remain unproved.
    """
    incoming = parse_receipt(receipt)
    spec = parse_table_spec(manifest)
    base = {
        "schema_version": "pcs-tabular-replay-v5-research",
        "authority": "EXPERIMENTAL_NOT_PCS_V06_AUTHORITY",
        "original_receipt_sha256": sha(receipt),
        "data_sha256": source.digest,
        "manifest_sha256": spec.raw_sha256,
        "matched": False,
        "kernel_replayed": 0,
        "status": "RECEIPT_REJECTED",
        "scientific_status": "NOT_ASSESSED",
        "scope": "Replay same experimental Python translation with fresh Lean checks; not semantic or independent scientific certification",
    }
    # Avoid any Lean work for obviously altered or mismatched inputs.
    if (incoming.get("schema_version") != "pcs-tabular-evidence-v5-research" or
        incoming.get("authority") != "EXPERIMENTAL_NOT_PCS_V06_AUTHORITY" or
        incoming.get("data_sha256") != source.digest or
        incoming.get("manifest_sha256") != spec.raw_sha256 or
        type(incoming.get("claims")) is not list):
        base["reason"] = "source/manifest/schema authority mismatch"
        return base
    if lean is None:
        lean = LeanChecker(executable="__pcs_missing_lean_executable__")
    fresh = run_table(source, manifest, lean=lean)
    base["kernel_replayed"] = fresh["counts"]["kernel_checked"]
    expected_len = fresh["counts"]["accepted_grounding"]
    if expected_len != len(incoming["claims"]):
        base["reason"] = "claim count mismatch"
    elif base["kernel_replayed"] != expected_len:
        base["status"] = "KERNEL_UNAVAILABLE_OR_REJECTED"
        base["reason"] = "every row requires a fresh pinned kernel check"
    elif canonical(incoming) != canonical(fresh):
        base["reason"] = "recomputed receipt mismatch"
    else:
        base["matched"] = True
        base["status"] = "REPLAYED_MATHEMATICAL_RECEIPT"
    return base


def _write_private_json(path: Path, doc: dict) -> None:
    if path.is_symlink():
        raise ValueError("output must not be symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if tmp.is_symlink():
        raise ValueError("temporary output must not be symlink")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(canonical(doc) + b"\n")
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PCS research table receipt re-verifier; never production authority")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--table-spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--lean", default="lean")
    args = parser.parse_args(argv)
    try:
        source = Source.from_bytes(args.source.read_bytes())
        result = replay_table(source, args.table_spec.read_bytes(), args.receipt.read_bytes(), lean=LeanChecker(args.lean))
        _write_private_json(args.out, result)
        print(f"Experimental replay: {result['status']}; {result['kernel_replayed']} fresh Lean checks")
        return 0 if result["status"] == "REPLAYED_MATHEMATICAL_RECEIPT" else 2
    except (OSError, ValueError, TypeError) as exc:
        print(f"table replay rejected: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
