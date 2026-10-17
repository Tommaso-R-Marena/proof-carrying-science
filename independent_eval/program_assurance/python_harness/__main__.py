"""Allow ``python -m python_harness`` to run the smoke suite."""

from __future__ import annotations

from .run_all import main

if __name__ == "__main__":
    raise SystemExit(main())
