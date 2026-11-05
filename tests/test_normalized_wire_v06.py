from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pcs.byte_contract_v06 import parse_certificate_bytes_v06
from pcs.certificate_v06 import finalize_certificate_hashes_v06
from pcs.normalized_wire_v06 import (
    V06NormalizationError,
    normalize_replayed_certificate_v06,
    normalized_wire_bytes_v06,
    parse_normalized_wire_bytes_v06,
    predicate_commitment_v06,
    validate_normalized_wire_v06,
    verify_normalized_against_certificate_v06,
    verify_normalized_bytes_against_certificate_v06,
    wire_semantic_hash_v06,
)


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))


def certificate() -> dict:
    return parse_certificate_bytes_v06((GOLDEN / "certificate.json").read_bytes())


def package_files() -> dict[str, bytes]:
    return {
        "certificate.json": (GOLDEN / "certificate.json").read_bytes(),
        "artifacts/fixture.bin": (GOLDEN / "artifacts/fixture.bin").read_bytes(),
        META["normalized_wire_path"]: (GOLDEN / META["normalized_wire_path"]).read_bytes(),
        "normalized/index.json": (GOLDEN / "normalized/index.json").read_bytes(),
    }


def normalized() -> dict:
    return normalize_replayed_certificate_v06(certificate(), package_files(), "C1")


def rehash(wire: dict) -> dict:
    out = deepcopy(wire)
    out["wire_semantic_hash"] = wire_semantic_hash_v06(out)
    return out


def test_golden_normalized_wire_reproduces_exactly():
    wire = normalized()
    raw = normalized_wire_bytes_v06(wire)
    assert raw == (GOLDEN / META["normalized_wire_path"]).read_bytes()
    assert wire["wire_semantic_hash"] == META["normalized_wire_semantic_hash"]
    assert wire["claim"]["predicate_commitment"] == META["predicate_commitment"]
    assert predicate_commitment_v06(certificate()["claims"][0]["predicate"]) == META[
        "predicate_commitment"
    ]


def test_golden_normalized_wire_round_trip_from_bytes():
    raw = (GOLDEN / META["normalized_wire_path"]).read_bytes()
    parsed = parse_normalized_wire_bytes_v06(raw)
    checked = verify_normalized_bytes_against_certificate_v06(
        raw,
        certificate(),
        package_files(),
    )
    assert checked["valid"], checked["errors"]
    assert checked["source_certificate_match"]
    assert parsed == normalized()


def test_noncanonical_normalized_bytes_rejected():
    raw = (GOLDEN / META["normalized_wire_path"]).read_bytes()
    with pytest.raises(V06NormalizationError, match="canonical JCS"):
        parse_normalized_wire_bytes_v06(raw + b"\n")


def test_wire_hash_tamper_rejected():
    wire = normalized()
    wire["wire_semantic_hash"] = "0" * 64
    checked = validate_normalized_wire_v06(wire)
    assert not checked["valid"]
    assert any("semantic hash mismatch" in error for error in checked["errors"])


def test_validly_rehashed_decision_substitution_still_fails_internal_check():
    wire = normalized()
    wire["decision"] = "OPEN"
    wire = rehash(wire)
    checked = validate_normalized_wire_v06(wire)
    assert not checked["valid"]
    assert any("decision mismatch" in error for error in checked["errors"])


def test_validly_rehashed_context_statement_substitution_fails_source_regeneration():
    wire = normalized()
    wire["context"][0]["statement"] = "different statement"
    wire = rehash(wire)
    assert validate_normalized_wire_v06(wire)["valid"]

    checked = verify_normalized_against_certificate_v06(
        wire,
        certificate(),
        package_files(),
    )
    assert not checked["valid"]
    assert not checked["source_certificate_match"]


def test_validly_rehashed_predicate_commitment_substitution_fails_source_regeneration():
    wire = normalized()
    forged = "pcs-predicate-sha256-v2:" + ("0" * 64)
    wire["claim"]["predicate_commitment"] = forged
    wire["evidence"][0]["predicate_commitment"] = forged
    wire = rehash(wire)
    assert validate_normalized_wire_v06(wire)["valid"]

    checked = verify_normalized_against_certificate_v06(
        wire,
        certificate(),
        package_files(),
    )
    assert not checked["valid"]
    assert not checked["source_certificate_match"]


def test_validly_rehashed_source_hash_substitution_fails_source_regeneration():
    wire = normalized()
    wire["source"]["certificate_semantic_hash"] = "0" * 64
    wire = rehash(wire)
    assert validate_normalized_wire_v06(wire)["valid"]

    checked = verify_normalized_against_certificate_v06(
        wire,
        certificate(),
        package_files(),
    )
    assert not checked["valid"]
    assert not checked["source_certificate_match"]


def test_normalization_refuses_rehashed_but_replay_false_certificate():
    cert = certificate()
    bad = {
        "type": "reaction_balance",
        "reactants": [{"formula": "H2", "coefficient": 1}],
        "products": [{"formula": "H2O", "coefficient": 1}],
    }
    cert["claims"][0]["predicate"] = deepcopy(bad)
    cert["evidence"][0]["predicate"] = deepcopy(bad)
    cert["evidence"][0]["check_spec"] = deepcopy(bad)
    cert["semantic_hash"] = ""
    cert["integrity_hash"] = ""
    cert = finalize_certificate_hashes_v06(cert)

    with pytest.raises(V06NormalizationError, match="must pass executable v0.6 replay"):
        normalize_replayed_certificate_v06(cert, {}, "C1")


def test_unknown_claim_cannot_be_normalized():
    with pytest.raises(V06NormalizationError, match="unknown claim id"):
        normalize_replayed_certificate_v06(certificate(), package_files(), "NOPE")
