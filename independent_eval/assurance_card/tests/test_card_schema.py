from __future__ import annotations

import json
from pathlib import Path

from python_harness.card import build_and_write, build_assurance_card
from python_harness.inspect_lane import inspect_evidence


REQUIRED_TOP_KEYS = {
    "format",
    "card_issues_accept",
    "inspection_is_not_authority",
    "disclaimer",
    "limitations_banner",
    "authority",
    "inspection",
    "provenance",
    "lane_consistency",
    "non_claims",
}


def test_inspect_fixture_claims_and_flags(fixture_bundle: Path):
    inspection = inspect_evidence(fixture_bundle)
    assert inspection["card_issues_accept"] is False
    assert inspection["inspection_is_not_authority"] is True
    ids = {c["id"] for c in inspection["claims"]}
    assert ids >= {"C_REPLAY", "C_INTEGRITY", "C_BIOLOGY"}
    replay = next(c for c in inspection["claims"] if c["id"] == "C_REPLAY")
    biology = next(c for c in inspection["claims"] if c["id"] == "C_BIOLOGY")
    integrity = next(c for c in inspection["claims"] if c["id"] == "C_INTEGRITY")
    assert replay["inspection_class"] == "computationally_supported"
    assert biology["inspection_class"] == "scientific_adequacy_open"
    assert integrity["inspection_class"] == "cryptographic_validity"
    assert inspection["limitations_text"] and "biological" in inspection["limitations_text"].lower()
    assert any(a["id"] == "A_MODEL" for a in inspection["assumptions"])
    assert any(a.get("sha256") for a in inspection["artifacts"])


def test_card_json_schema_fields(fixture_bundle: Path, tmp_path: Path):
    card, written = build_and_write(
        fixture_bundle,
        tmp_path / "card",
        fmt="json",
        skip_verify=True,
    )
    assert REQUIRED_TOP_KEYS <= set(card)
    assert card["format"] == "pcs-assurance-card-v1"
    assert card["card_issues_accept"] is False
    assert card["inspection_is_not_authority"] is True
    assert "computational PASS" in card["limitations_banner"] or "computational" in card[
        "limitations_banner"
    ].lower()
    assert "authority" in card and card["authority"]["cli_is_authority"] is True
    assert card["inspection"]["card_issues_accept"] is False
    assert card["inspection"]["inspection_is_not_authority"] is True
    prov = card["provenance"]
    assert "generated_at_utc" in prov
    assert "input_sha256" in prov
    assert prov["efficiency"]["network"] is False
    assert prov["efficiency"]["lean_rebuild"] is False
    assert prov["efficiency"]["verify_only"] is True
    assert written["json"].is_file()
    loaded = json.loads(written["json"].read_text(encoding="utf-8"))
    assert loaded["card_issues_accept"] is False


def test_build_assurance_card_provenance_hashes(fixture_bundle: Path):
    card = build_assurance_card(fixture_bundle, skip_verify=True)
    hashes = card["provenance"]["input_sha256"]
    assert hashes
    assert any(path.endswith("certificate.json") for path in hashes)
