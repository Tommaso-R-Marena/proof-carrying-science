"""Allow `python -m independent_eval.reviewer_adoption.workbench`."""

from __future__ import annotations

import sys

from .generate_report import main

if __name__ == "__main__":
    sys.exit(main())
