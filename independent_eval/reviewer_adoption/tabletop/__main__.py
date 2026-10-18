"""Allow `python -m independent_eval.reviewer_adoption.tabletop`."""

from __future__ import annotations

import sys

from .simulator import main

if __name__ == "__main__":
    sys.exit(main())
