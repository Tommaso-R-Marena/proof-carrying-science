#!/usr/bin/env python3
"""CLI for the incubation epistemic calculus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .checker import CheckerError, verify_path
from .dialectic import dialectic_report
from .invalidate import compute_impact, nonimpact


def _print(data: dict) -> int:
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pcs-epistemic",
        description="PCS Epistemic Calculus v1 (incubation; not production authority)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify", help="independently verify an epistemic certificate")
    v.add_argument("certificate", type=Path)

    i = sub.add_parser("impact", help="compute declared-graph invalidation impact")
    i.add_argument("graph", type=Path)
    i.add_argument("--changed", nargs="+", required=True)

    n = sub.add_parser("nonimpact", help="evaluate conditional non-impact")
    n.add_argument("graph", type=Path)
    n.add_argument("--changed", nargs="+", required=True)
    n.add_argument("--claim", required=True)
    n.add_argument("--complete", action="store_true")

    d = sub.add_parser("dialectic", help="compute agreement core and dispute frontier")
    d.add_argument("ensemble", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "verify":
            receipt = verify_path(str(args.certificate))
            code = 0 if receipt.get("accepted") else 1
            print(json.dumps(receipt, indent=2, sort_keys=True))
            return code
        if args.cmd == "impact":
            graph = json.loads(Path(args.graph).read_text(encoding="utf-8"))
            return _print(compute_impact(graph, args.changed))
        if args.cmd == "nonimpact":
            graph = json.loads(Path(args.graph).read_text(encoding="utf-8"))
            return _print(
                nonimpact(graph, args.changed, args.claim, dependency_complete=args.complete)
            )
        if args.cmd == "dialectic":
            ens = json.loads(Path(args.ensemble).read_text(encoding="utf-8"))
            return _print(dialectic_report(ens["models"], ens["candidates"]))
    except (CheckerError, OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(json.dumps({"error": str(exc), "production_authority": False}), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
