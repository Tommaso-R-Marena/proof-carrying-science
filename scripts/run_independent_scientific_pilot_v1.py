#!/usr/bin/env python3
"""Run the independent scientific-assurance pilot (synthetic PK/PD)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pcs.independent_pilot_v1 import IndependentPilotError, run_independent_pilot_v1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Execute the bounded independent scientific pilot: intake freeze, "
            "discovery/confirmation, Lean-authoritative attestation, second-"
            "environment verification, adversarial fail-closed checks, and "
            "closeout planning. Synthetic/public inputs only."
        )
    )
    parser.add_argument(
        "--output",
        required=True,
        help="new output directory for lab/producer/reviewer/archive evidence",
    )
    parser.add_argument(
        "--lean-authority",
        default=None,
        help="path to receiver-owned pcs-lean-authority (optional if resolvable)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing output directory",
    )
    parser.add_argument(
        "--apply-closeout",
        action="store_true",
        help="apply the demo producer-key closeout plan after archival packaging",
    )
    parser.add_argument(
        "--deterministic-fixture",
        action="store_true",
        help=(
            "fixture-only: pin frozen_at/generated_at for byte-comparable regenerations; "
            "not a production reproducibility claim"
        ),
    )
    args = parser.parse_args(argv)
    try:
        evidence = run_independent_pilot_v1(
            args.output,
            lean_authority_path=args.lean_authority,
            overwrite=args.overwrite,
            apply_closeout=args.apply_closeout,
            deterministic_fixture=args.deterministic_fixture,
        )
    except IndependentPilotError as exc:
        print(f"ERROR: IndependentPilotError: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
