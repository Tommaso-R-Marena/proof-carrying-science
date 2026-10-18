"""Allow ``python -m python_harness`` to delegate to the Assurance Card CLI."""
from .card import main

if __name__ == "__main__":
    raise SystemExit(main())
