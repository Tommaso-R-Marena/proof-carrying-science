"""Allow `python -m independent_eval.reviewer_adoption.external_lab`."""

from __future__ import annotations

import sys

from .burden_tracker import main

if __name__ == "__main__":
    sys.exit(main())
