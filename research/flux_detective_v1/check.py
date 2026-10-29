"""Replay an untrusted Flux Detective export using the existing fixed Lean checker."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.jsonio import strict_json_loads
from pcs.transport_trace_kernel_v1 import prepare
from research.portable_transport_v2.replay import export, replay

MAX_BYTES = 256 * 1024


def capture(raw: bytes) -> tuple[bytes, bytes]:
    """Metadata never supplies a verdict, path, executable, proof or certificate."""
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise ValueError("Bounded immutable puzzle bytes required")
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except RecursionError as exc:
        raise ValueError("Puzzle JSON nesting exceeds the parser budget") from exc
    fields = {"format", "seed", "level", "choice", "contract", "trajectory"}
    if type(value) is not dict or set(value) != fields or value["format"] != "pcs-flux-detective-export-v1":
        raise ValueError("Exact versioned puzzle export required")
    for name, upper in (("seed", 4294967295), ("level", 5), ("choice", 2)):
        if type(value[name]) is not int or not 0 <= value[name] <= upper:
            raise ValueError("Bounded integer puzzle metadata required")
    if type(value["contract"]) is not dict or type(value["trajectory"]) is not str:
        raise ValueError("Model object and CSV text required")
    contract = canonicalize_jcs_bytes(value["contract"])
    csv = value["trajectory"].encode("utf-8")
    prepare(contract, csv)  # Current PCS strict parsing, dimensions and rational bounds.
    return contract, csv


def main() -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("out", type=Path, help="Fresh evidence directory; never overwritten")
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise ValueError("Fresh evidence directory required")
        with args.bundle.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        contract, csv = capture(raw)
        result = replay(contract, csv)
        if "proof" in result:
            export(args.out, result, contract, csv)
        print(json.dumps({k: result[k] for k in ("status", "kernel_supported", "negative_kernel_checked", "pcs_authority", "scientific_acceptance")}))
        return 0 if result["kernel_supported"] else 10 if result["negative_kernel_checked"] else 20
    except (ValueError, OSError, UnicodeError, RecursionError) as exc:
        print(json.dumps({"status": "REFUSED", "error": str(exc), "kernel_supported": False,
                          "negative_kernel_checked": False, "pcs_authority": False, "scientific_acceptance": False}))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
