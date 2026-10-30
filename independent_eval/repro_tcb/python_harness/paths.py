"""Filesystem anchors for the repro_tcb independent evaluation package."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
FIXTURES = ROOT / "fixtures"
RESULTS = ROOT / "results"
EVIDENCE_FIXTURES = FIXTURES / "evidence_bundle"
CLAIMS_FIXTURES = FIXTURES / "claims"
HASH_MANIFEST = FIXTURES / "hashes.json"
