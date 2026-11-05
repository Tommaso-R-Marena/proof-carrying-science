"""CLI entry: ``python -m python_harness [run-all|preflight]``."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"run-all", "smoke"}:
        from .run_all import main as run_all_main

        return run_all_main([])
    if args[0] == "preflight":
        from .preflight import main as preflight_main

        return preflight_main(args[1:])
    if args[0] in {"-h", "--help"}:
        print("usage: python -m python_harness [run-all|preflight] ...")
        return 0
    print(f"unknown command: {args[0]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
