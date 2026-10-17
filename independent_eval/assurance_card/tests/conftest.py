from __future__ import annotations

from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = PACKAGE_ROOT / "fixtures" / "sample_bundle"
REPO_ROOT = PACKAGE_ROOT.parents[1]


@pytest.fixture
def fixture_bundle() -> Path:
    return FIXTURE


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT
