#!/usr/bin/env python3
"""Clean-room independent pilot: fresh venv, hash-pinned deps, no user site."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pcs.independent_pilot_v1 import (
    IndependentPilotError,
    run_cleanroom_independent_pilot_v1,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct the independent scientific pilot inside a fresh "
            "virtualenv with hash-pinned dependencies and without user-site "
            "packages or pip caches. Does not use production credentials."
        )
    )
    parser.add_argument("--output", required=True, help="new clean-room output directory")
    parser.add_argument(
        "--lean-authority",
        default=None,
        help="receiver-owned pcs-lean-authority binary path",
    )
    parser.add_argument("--python", default=None, help="Python executable for venv creation")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        summary = run_cleanroom_independent_pilot_v1(
            args.output,
            python_executable=args.python,
            lean_authority_path=args.lean_authority,
            overwrite=args.overwrite,
        )
    except IndependentPilotError as exc:
        print(f"ERROR: IndependentPilotError: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
