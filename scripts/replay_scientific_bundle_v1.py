#!/usr/bin/env python3
"""Credential-free independent process replay of a bounded scientific PCS bundle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pcs.scientific_assurance_v1 import verify_scientific_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("public_key", type=Path)
    parser.add_argument("--expected-fingerprint", required=True)
    parser.add_argument("--lean-authority", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify_scientific_bundle(args.bundle, args.public_key,
        expected_fingerprint=args.expected_fingerprint, lean_authority_path=args.lean_authority)
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        if args.output.exists():
            parser.error("refusing to replace an existing replay receipt")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0 if result["pcs_package_valid"] and result["independent_replay_consistent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
