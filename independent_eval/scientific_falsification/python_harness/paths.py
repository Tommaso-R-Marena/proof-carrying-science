from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
FIXTURES = ROOT / "fixtures"
CASEBOOK = ROOT / "casebook"
INADEQUACY = ROOT / "inadequacy"
METAMORPHIC = ROOT / "metamorphic"
DISCOVERY = ROOT / "discovery_benchmark"
EXTERNAL = ROOT / "external_validity"
RESULTS = ROOT / "results"
HASH_MANIFEST = FIXTURES / "FIXTURE_HASHES.json"
