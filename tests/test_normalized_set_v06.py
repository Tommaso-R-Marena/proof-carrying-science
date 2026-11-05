from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pcs.byte_contract_v06 import parse_certificate_bytes_v06
from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.certificate_v06 import finalize_certificate_hashes_v06
from pcs.normalized_set_v06 import (
    INDEX_PATH_V06,
    V06NormalizedSetError,
    build_normalized_set_v06,
    index_semantic_hash_v06,
    normalized_storage_key_v06,
    normalized_wire_path_v06,
    parse_normalized_index_bytes_v06,
    validate_normalized_index_v06,
    verify_normalized_set_v06,
)
from pcs.normalized_wire_v06 import wire_semantic_hash_v06


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
        INDEX_PATH_V06: (GOLDEN / INDEX_PATH_V06).read_bytes(),
    }


def rehash_index(index: dict) -> dict:
    out = deepcopy(index)
    out["index_semantic_hash"] = index_semantic_hash_v06(out)
    return out


def test_storage_key_uses_full_sha256():
    key = normalized_storage_key_v06("C1")
    assert key == "ab861dc170dc2e43224e45278d3d31a675b9ebc34c9b0f48c066ca1eeaed8ee6"
    assert len(key) == 64
    assert normalized_wire_path_v06("C1") == META["normalized_wire_path"]


def test_golden_normalized_set_reproduces_exactly():
    built = build_normalized_set_v06(certificate(), package_files())
    assert built["files"][INDEX_PATH_V06] == (GOLDEN / INDEX_PATH_V06).read_bytes()
    assert built["files"][META["normalized_wire_path"]] == (
        GOLDEN / META["normalized_wire_path"]
    ).read_bytes()
    assert built["index"]["index_semantic_hash"] == META["normalized_index_semantic_hash"]


def test_golden_normalized_set_verifies():
    result = verify_normalized_set_v06(certificate(), package_files())
    assert result["valid"], result["errors"]
    assert result["claim_ids"] == ["C1"]
    assert result["index_semantic_hash"] == META["normalized_index_semantic_hash"]


def test_golden_index_round_trip_is_exact_canonical_bytes():
    raw = (GOLDEN / INDEX_PATH_V06).read_bytes()
    parsed = parse_normalized_index_bytes_v06(raw)
    assert canonicalize_jcs_bytes(parsed) == raw
    assert parsed["entries"][0]["path"] == META["normalized_wire_path"]


def test_noncanonical_index_bytes_are_rejected():
    raw = (GOLDEN / INDEX_PATH_V06).read_bytes()
    with pytest.raises(V06NormalizedSetError, match="canonical JCS"):
        parse_normalized_index_bytes_v06(raw + b"\n")


def test_duplicate_json_key_in_index_is_rejected():
    raw = (GOLDEN / INDEX_PATH_V06).read_bytes()
    duplicate = b'{"index_format":"pcs-normalized-decision-index-v2",' + raw[1:]
    with pytest.raises(V06NormalizedSetError, match="duplicate JSON object key"):
        parse_normalized_index_bytes_v06(duplicate)


def test_index_hash_tamper_is_rejected():
    index = parse_normalized_index_bytes_v06((GOLDEN / INDEX_PATH_V06).read_bytes())
    index["index_semantic_hash"] = "0" * 64
    checked = validate_normalized_index_v06(index)
    assert not checked["valid"]
    assert any("semantic hash mismatch" in error for error in checked["errors"])


def test_validly_rehashed_wrong_storage_path_is_rejected():
    index = parse_normalized_index_bytes_v06((GOLDEN / INDEX_PATH_V06).read_bytes())
    index["entries"][0]["path"] = "normalized/" + ("0" * 64) + ".json"
    index = rehash_index(index)
    checked = validate_normalized_index_v06(index)
    assert not checked["valid"]
    assert any("path mismatch" in error for error in checked["errors"])


def test_missing_wire_member_is_rejected():
    files = package_files()
    del files[META["normalized_wire_path"]]
    result = verify_normalized_set_v06(certificate(), files)
    assert not result["valid"]
    assert any("missing" in error for error in result["errors"])


def test_unexpected_normalized_member_is_rejected():
    files = package_files()
    files["normalized/" + ("f" * 64) + ".json"] = b"{}"
    result = verify_normalized_set_v06(certificate(), files)
    assert not result["valid"]
    assert any("unexpected normalized package members" in error for error in result["errors"])


def test_empty_rehashed_index_cannot_hide_certificate_claim():
    files = package_files()
    index = parse_normalized_index_bytes_v06(files[INDEX_PATH_V06])
    index["entries"] = []
    index = rehash_index(index)
    files[INDEX_PATH_V06] = canonicalize_jcs_bytes(index)
    result = verify_normalized_set_v06(certificate(), files)
    assert not result["valid"]
    assert any("claim scope/order differs" in error for error in result["errors"])


def test_rehashed_certificate_hash_substitution_in_index_is_rejected():
    files = package_files()
    index = parse_normalized_index_bytes_v06(files[INDEX_PATH_V06])
    index["certificate_semantic_hash"] = "0" * 64
    index = rehash_index(index)
    files[INDEX_PATH_V06] = canonicalize_jcs_bytes(index)
    result = verify_normalized_set_v06(certificate(), files)
    assert not result["valid"]
    assert any("certificate semantic hash mismatch" in error for error in result["errors"])


def test_fully_rehashed_wire_and_index_forgery_still_fails_source_regeneration():
    files = package_files()
    wire = json.loads(files[META["normalized_wire_path"]])
    wire["context"][0]["statement"] = "attacker-controlled statement"
    wire["wire_semantic_hash"] = wire_semantic_hash_v06(wire)
    forged_wire = canonicalize_jcs_bytes(wire)

    index = parse_normalized_index_bytes_v06(files[INDEX_PATH_V06])
    index["entries"][0]["wire_semantic_hash"] = wire["wire_semantic_hash"]
    index = rehash_index(index)

    files[META["normalized_wire_path"]] = forged_wire
    files[INDEX_PATH_V06] = canonicalize_jcs_bytes(index)

    result = verify_normalized_set_v06(certificate(), files)
    assert not result["valid"]
    assert any("replay-derived bytes" in error for error in result["errors"])


def test_aggregate_normalized_set_limit_is_enforced(monkeypatch):
    import pcs.normalized_set_v06 as normalized_set

    monkeypatch.setattr(normalized_set, "MAX_NORMALIZED_SET_BYTES_V06", 100)
    with pytest.raises(V06NormalizedSetError, match="aggregate byte limit"):
        build_normalized_set_v06(certificate(), package_files())


def test_two_claim_set_preserves_certificate_claim_order_and_has_distinct_paths():
    cert = certificate()
    cert["assumptions"][0]["scope"] = ["C1", "C2"]

    second_claim = deepcopy(cert["claims"][0])
    second_claim["id"] = "C2"
    second_claim["required_evidence"] = ["E2"]
    second_claim["statement"] = "The second fixture reaction is atom-balanced."
    cert["claims"].append(second_claim)

    second_evidence = deepcopy(cert["evidence"][0])
    second_evidence["id"] = "E2"
    second_evidence["claim_ids"] = ["C2"]
    cert["evidence"].append(second_evidence)

    cert["semantic_hash"] = ""
    cert["integrity_hash"] = ""
    cert = finalize_certificate_hashes_v06(cert)

    built = build_normalized_set_v06(cert, {})
    entries = built["index"]["entries"]
    assert [entry["claim_id"] for entry in entries] == ["C1", "C2"]
    assert entries[0]["path"] != entries[1]["path"]
    assert all(len(Path(entry["path"]).stem) == 64 for entry in entries)
