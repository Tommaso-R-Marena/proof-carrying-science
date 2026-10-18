from __future__ import annotations

import json
from pathlib import Path

from python_harness.card import build_assurance_card
from python_harness.paths import package_root


def _validate_against_schema(instance: dict, schema: dict) -> list[str]:
    """Minimal offline subset validator for the card schema (no jsonschema dep)."""
    errors: list[str] = []
    required = schema.get("required") or []
    for key in required:
        if key not in instance:
            errors.append(f"missing required key: {key}")
    props = schema.get("properties") or {}
    if "format" in props and "const" in props["format"]:
        if instance.get("format") != props["format"]["const"]:
            errors.append("format const mismatch")
    if instance.get("card_issues_accept") is not False:
        errors.append("card_issues_accept must be false")
    if instance.get("inspection_is_not_authority") is not True:
        errors.append("inspection_is_not_authority must be true")
    integrity = instance.get("card_integrity") or {}
    integ_schema = props.get("card_integrity", {}).get("properties", {})
    if integrity.get("algorithm") != integ_schema.get("algorithm", {}).get("const"):
        errors.append("integrity algorithm mismatch")
    digest = integrity.get("digest_sha256") or ""
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        errors.append("digest_sha256 pattern mismatch")
    efficiency = (instance.get("provenance") or {}).get("efficiency") or {}
    if efficiency.get("network") is not False:
        errors.append("efficiency.network must be false")
    if efficiency.get("verify_only") is not True:
        errors.append("efficiency.verify_only must be true")
    lane = instance.get("lane_consistency") or {}
    if lane.get("overall") not in {"agreement", "disagreement", "inconclusive"}:
        errors.append("lane_consistency.overall enum mismatch")
    return errors


def test_schema_file_exists_and_validates_card(fixture_bundle: Path):
    schema_path = package_root() / "schema" / "pcs-assurance-card-v1.json"
    assert schema_path.is_file()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    card = build_assurance_card(
        fixture_bundle,
        skip_verify=True,
        generated_at_utc="2026-10-17T21:00:00Z",
    )
    errors = _validate_against_schema(card, schema)
    assert errors == []
