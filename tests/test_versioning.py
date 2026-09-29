from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pcs
from pcs.kernel import CHECKER_VERSION


ROOT = Path(__file__).resolve().parents[1]


def test_executable_version_declarations_are_consistent():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_version = pyproject["project"]["version"]

    assert pcs.__version__ == package_version
    assert CHECKER_VERSION == f"pcs-python-kernel/{package_version}"


def test_normalized_wire_schema_pins_current_checker_version():
    schema = json.loads(
        (ROOT / "pcs/schemas/normalized_decision.schema.json").read_text(encoding="utf-8")
    )
    expected = schema["properties"]["source"]["properties"]["checker_version"]["const"]
    assert expected == CHECKER_VERSION


def test_public_and_packaged_normalized_schemas_are_identical():
    packaged = (ROOT / "pcs/schemas/normalized_decision.schema.json").read_bytes()
    public = (ROOT / "schemas/normalized_decision.schema.json").read_bytes()
    assert packaged == public

    packaged_index = (ROOT / "pcs/schemas/normalized_decision_index.schema.json").read_bytes()
    public_index = (ROOT / "schemas/normalized_decision_index.schema.json").read_bytes()
    assert packaged_index == public_index
