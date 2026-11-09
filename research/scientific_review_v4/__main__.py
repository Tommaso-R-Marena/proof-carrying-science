"""Review captured scientific sources and replay their independent evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    review = sub.add_parser("review", help="Review a directory or ZIP; open output/review.html")
    review.add_argument("source", type=Path)
    review.add_argument("--output", type=Path, required=True)
    review.add_argument("--check", action="store_true", help="Authorize the fixed independent source and computation checks")
    review.add_argument("--formal", action="store_true", help="Also run the actual Lean theorem audit; requires --check")
    review.add_argument("--cache", type=Path, help="Optional host-private cache for unchanged parent checks")
    repeat = sub.add_parser("replay", help="Rebuild source meanings and independently recompute v4 checks")
    repeat.add_argument("directory", type=Path)
    repeat.add_argument("--integrity-only", action="store_true", help="Skip parent computational rechecks; v4 check authenticity is still recomputed")
    repeat.add_argument("--expected-manifest-sha256")
    bench = sub.add_parser("benchmark", help="Run a frozen evaluation split")
    bench.add_argument("--split", choices=["development", "final"], default="development")
    bench.add_argument("--output", type=Path, required=True)
    bench.add_argument("--allow-final", action="store_true")
    bench.add_argument("--software-sha256")
    bench.add_argument("--source-root", type=Path)
    bench.add_argument("--reference-root", type=Path)
    args = parser.parse_args()
    if args.command == "review":
        if args.formal and not args.check:
            parser.error("--formal requires --check")
        from .pipeline import run
        result = run(args.source, args.output, check=args.check, formal_check=args.formal, cache_dir=args.cache)
    elif args.command == "replay":
        from .pipeline import replay
        result = replay(args.directory, recheck=not args.integrity_only, expected_manifest_sha256=args.expected_manifest_sha256)
    else:
        from .benchmark import run_benchmark
        result = run_benchmark(args.output, split=args.split, allow_final=args.allow_final, source_root=args.source_root, reference_root=args.reference_root, expected_software_sha256=args.software_sha256)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
