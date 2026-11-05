"""Pytest path bootstrap for Workstream C tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
# Allow `import independent_eval.repro_tcb...` and direct harness imports.
for path in (REPO, ROOT):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)
