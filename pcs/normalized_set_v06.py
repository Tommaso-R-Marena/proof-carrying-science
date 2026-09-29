from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any, Mapping

from .canonical_json import (
    CanonicalJSONError,
    canonicalize_jcs_bytes,
    parse_jcs_json,
)
from .crypto_domains_v06 import NORMALIZED_INDEX_DOMAIN, domain_sha256
from .normalized_wire_v06 import (
    V06NormalizationError,
    normalize_claim_after_replay_v06,
    normalized_wire_bytes_v06,
    parse_normalized_wire_bytes_v06,
)
from .replay_v06 import verify_certificate_replay_v06
from .schema_validation import (
    SchemaValidationError,
    validate_v06_normalized_decision_index_shape,
)


INDEX_FORMAT_V06 = "pcs-normalized-decision-index-v2"
INDEX_PATH_V06 = "normalized/index.json"
MAX_NORMALIZED_INDEX_BYTES_V06 = 10 * 1024 * 1024
UTF8_BOM = b"\xef\xbb\xbf"


class V06NormalizedSetError(ValueError):
    pass


def normalized_storage_key_v06(claim_id: str) -> str:
    return hashlib.sha256(claim_id.encode("utf-8")).hexdigest()[:24]


def normalized_wire_path_v06(claim_id: str) -> str:
    return f"normalized/{normalized_storage_key_v06(claim_id)}.json"


def _index_projection(index: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(index)
    out.pop("index_semantic_hash", None)
    return out


def index_semantic_hash_v06(index: dict[str, Any]) -> str:
    return domain_sha256(NORMALIZED_INDEX_DOMAIN, _index_projection(index))


def validate_normalized_index_v06(index: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_v06_normalized_decision_index_shape(index)
    except SchemaValidationError as exc:
        return {"valid": False, "errors": [str(exc)]}

    supplied_hash = index["index_semantic_hash"]
    expected_hash = index_semantic_hash_v06(index)
    if supplied_hash != expected_hash:
        errors.append("v0.6 normalized index semantic hash mismatch")

    claim_ids = [entry["claim_id"] for entry in index["entries"]]
    paths = [entry["path"] for entry in index["entries"]]
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("v0.6 normalized index contains duplicate claim ids")
    if len(paths) != len(set(paths)):
        errors.append("v0.6 normalized index contains duplicate wire paths")

    for entry in index["entries"]:
        expected_path = normalized_wire_path_v06(entry["claim_id"])
        if entry["path"] != expected_path:
            errors.append(
                f"v0.6 normalized index path mismatch for {entry['claim_id']}: "
                f"recorded={entry['path']} expected={expected_path}"
            )

    return {
        "valid": not errors,
        "errors": errors,
        "index_semantic_hash": supplied_hash,
        "recomputed_index_semantic_hash": expected_hash,
        "claim_ids": claim_ids,
    }


def build_normalized_set_v06(
    certificate: dict[str, Any],
    package_files: Mapping[str, bytes],
) -> dict[str, Any]:
    replay = verify_certificate_replay_v06(certificate, package_files)
    if not replay["valid"]:
        raise V06NormalizedSetError(
            "certificate must pass executable replay before normalized-set derivation: "
            + "; ".join(replay["errors"])
        )

    entries: list[dict[str, Any]] = []
    files: dict[str, bytes] = {}

    for claim in certificate["claims"]:
        claim_id = claim["id"]
        wire = normalize_claim_after_replay_v06(certificate, replay, claim_id)
        raw = normalized_wire_bytes_v06(wire)
        path = normalized_wire_path_v06(claim_id)
        files[path] = raw
        entries.append(
            {
                "claim_id": claim_id,
                "path": path,
                "decision": wire["decision"],
                "wire_semantic_hash": wire["wire_semantic_hash"],
            }
        )

    index: dict[str, Any] = {
        "index_format": INDEX_FORMAT_V06,
        "canonical_json_profile": "pcs-jcs-rfc8785-v1",
        "index_hash_format": NORMALIZED_INDEX_DOMAIN,
        "certificate_semantic_hash": certificate["semantic_hash"],
        "certificate_integrity_hash": certificate["integrity_hash"],
        "entries": entries,
        "index_semantic_hash": "",
    }
    index["index_semantic_hash"] = index_semantic_hash_v06(index)
    checked = validate_normalized_index_v06(index)
    if not checked["valid"]:
        raise V06NormalizedSetError(
            "internal normalized-index invariant failure: "
            + "; ".join(checked["errors"])
        )

    files[INDEX_PATH_V06] = canonicalize_jcs_bytes(index)
    return {
        "index": index,
        "files": files,
        "replay": replay,
    }


def parse_normalized_index_bytes_v06(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        raise V06NormalizedSetError("v0.6 normalized index must be immutable bytes")
    if len(raw) > MAX_NORMALIZED_INDEX_BYTES_V06:
        raise V06NormalizedSetError(
            f"v0.6 normalized index exceeds byte limit: "
            f"{len(raw)} > {MAX_NORMALIZED_INDEX_BYTES_V06}"
        )
    if raw.startswith(UTF8_BOM):
        raise V06NormalizedSetError("v0.6 normalized index must not contain a UTF-8 BOM")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = parse_jcs_json(text)
        canonical = canonicalize_jcs_bytes(value)
    except (UnicodeDecodeError, CanonicalJSONError, RecursionError) as exc:
        raise V06NormalizedSetError(f"invalid v0.6 normalized index JSON: {exc}") from exc
    if canonical != raw:
        raise V06NormalizedSetError(
            "v0.6 normalized index is not the exact canonical JCS byte representation"
        )
    if not isinstance(value, dict):
        raise V06NormalizedSetError("v0.6 normalized index root must be an object")
    checked = validate_normalized_index_v06(value)
    if not checked["valid"]:
        raise V06NormalizedSetError("; ".join(checked["errors"]))
    return value


def verify_normalized_set_v06(
    certificate: dict[str, Any],
    package_files: Mapping[str, bytes],
) -> dict[str, Any]:
    errors: list[str] = []
    raw_index = package_files.get(INDEX_PATH_V06)
    if not isinstance(raw_index, bytes):
        return {
            "valid": False,
            "errors": [f"missing immutable normalized index bytes at {INDEX_PATH_V06}"],
        }

    try:
        delivered_index = parse_normalized_index_bytes_v06(raw_index)
        expected = build_normalized_set_v06(certificate, package_files)
    except (V06NormalizedSetError, V06NormalizationError) as exc:
        return {"valid": False, "errors": [str(exc)]}

    certificate_claim_ids = [claim["id"] for claim in certificate["claims"]]
    delivered_claim_ids = [entry["claim_id"] for entry in delivered_index["entries"]]
    if delivered_claim_ids != certificate_claim_ids:
        errors.append(
            "normalized index claim scope/order differs from certificate claim scope/order"
        )

    if delivered_index["certificate_semantic_hash"] != certificate["semantic_hash"]:
        errors.append("normalized index certificate semantic hash mismatch")
    if delivered_index["certificate_integrity_hash"] != certificate["integrity_hash"]:
        errors.append("normalized index certificate integrity hash mismatch")

    expected_files: dict[str, bytes] = expected["files"]
    delivered_names = {
        name for name in package_files if isinstance(name, str) and name.startswith("normalized/")
    }
    expected_names = set(expected_files)
    missing = sorted(expected_names - delivered_names)
    unexpected = sorted(delivered_names - expected_names)
    if missing:
        errors.append(f"normalized package members missing: {missing}")
    if unexpected:
        errors.append(f"unexpected normalized package members: {unexpected}")

    for path in sorted(expected_names & delivered_names):
        delivered = package_files[path]
        if not isinstance(delivered, bytes):
            errors.append(f"normalized package member {path!r} is not immutable bytes")
            continue
        if delivered != expected_files[path]:
            errors.append(f"normalized package member differs from replay-derived bytes: {path}")

    for entry in delivered_index["entries"]:
        raw = package_files.get(entry["path"])
        if not isinstance(raw, bytes):
            continue
        try:
            wire = parse_normalized_wire_bytes_v06(raw)
        except V06NormalizationError as exc:
            errors.append(f"invalid normalized wire {entry['path']}: {exc}")
            continue
        if wire["source"]["claim_id"] != entry["claim_id"]:
            errors.append(f"normalized index/wire claim mismatch: {entry['claim_id']}")
        if wire["decision"] != entry["decision"]:
            errors.append(f"normalized index/wire decision mismatch: {entry['claim_id']}")
        if wire["wire_semantic_hash"] != entry["wire_semantic_hash"]:
            errors.append(f"normalized index/wire hash mismatch: {entry['claim_id']}")

    return {
        "valid": not errors,
        "errors": errors,
        "index_semantic_hash": delivered_index["index_semantic_hash"],
        "claim_ids": delivered_claim_ids,
        "entries": delivered_index["entries"],
    }
