from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
FIXTURES = ROOT / "fixtures"
RESULTS = ROOT / "results"
RUST_CRATE = ROOT / "rust_jcs_ref"
