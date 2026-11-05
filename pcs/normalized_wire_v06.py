from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .canonical_json import (
    CanonicalJSONError,
    canonicalize_jcs_bytes,
    parse_jcs_json,
)
from .crypto_domains_v06 import (
    NORMALIZED_DECISION_DOMAIN,
    PREDICATE_COMMITMENT_DOMAIN,
    domain_sha256,
)
from .decision import assess_claim
from .replay_v06 import verify_certificate_replay_v06
from .schema_validation import (
    SchemaValidationError,
    validate_v06_normalized_decision_shape,
)


WIRE_FORMAT_V06 = "pcs-normalized-decision-v2"
PREDICATE_COMMITMENT_PREFIX_V06 = "pcs-predicate-sha256-v2:"
MAX_NORMALIZED_WIRE_BYTES_V06 = 10 * 1024 * 1024
UTF8_BOM = b"\xef\xbb\xbf"


class V06NormalizationError(ValueError):
    pass


def predicate_commitment_v06(predicate: dict[str, Any]) -> str:
    return (
        PREDICATE_COMMITMENT_PREFIX_V06
        + domain_sha256(PREDICATE_COMMITMENT_DOMAIN, predicate)
    )


def _wire_projection(wire: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(wire)
    out.pop("wire_semantic_hash", None)
    return out


def wire_semantic_hash_v06(wire: dict[str, Any]) -> str:
    return domain_sha256(NORMALIZED_DECISION_DOMAIN, _wire_projection(wire))


def validate_normalized_wire_v06(wire: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_v06_normalized_decision_shape(wire)
    except SchemaValidationError as exc:
        return {"valid": False, "errors": [str(exc)]}

    supplied_hash = wire["wire_semantic_hash"]
    expected_hash = wire_semantic_hash_v06(wire)
    if supplied_hash != expected_hash:
        errors.append("v0.6 normalized decision semantic hash mismatch")

    source = wire["source"]
    claim = wire["claim"]
    if source["claim_id"] != claim["id"]:
        errors.append("normalized source claim id differs from normalized claim id")

    required_ids = list(claim["required_evidence"])
    evidence = list(wire["evidence"])
    evidence_ids = [item["id"] for item in evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        errors.append("normalized evidence ids are not unique")
    if evidence_ids != required_ids:
        errors.append("normalized evidence scope/order differs from required evidence")

    assumption_ids = list(claim["assumptions"])
    context_ids = [item["id"] for item in wire["context"]]
    if len(context_ids) != len(set(context_ids)):
        errors.append("normalized context ids are not unique")
    if context_ids != assumption_ids:
        errors.append("normalized context scope/order differs from claim assumptions")

    claim_commitment = claim["predicate_commitment"]
    for item in evidence:
        if item["predicate_commitment"] != claim_commitment:
            errors.append(
                f"normalized evidence {item['id']} predicate commitment differs from claim"
            )

    evidence_map = {item["id"]: item for item in evidence}
    fresh = assess_claim(claim, evidence_map)
    if fresh["status"] != wire["decision"]:
        errors.append(
            "normalized decision mismatch: "
            f"recorded={wire['decision']} recomputed={fresh['status']}"
        )

    return {
        "valid": not errors,
        "errors": errors,
        "wire_semantic_hash": supplied_hash,
        "recomputed_wire_semantic_hash": expected_hash,
        "recomputed_decision": fresh["status"],
        "claim_id": claim["id"],
    }


def normalize_claim_after_replay_v06(
    certificate: dict[str, Any],
    replay: dict[str, Any],
    claim_id: str,
) -> dict[str, Any]:
    if not replay.get("valid"):
        raise V06NormalizationError(
            "certificate must pass executable v0.6 replay before normalization: "
            + "; ".join(replay.get("errors", []))
        )

    claim_map = {claim["id"]: claim for claim in certificate["claims"]}
    claim = claim_map.get(claim_id)
    if claim is None:
        raise V06NormalizationError(f"unknown claim id: {claim_id}")

    assumption_map = {item["id"]: item for item in certificate["assumptions"]}
    evidence_map = {item["id"]: item for item in certificate["evidence"]}

    claim_commitment = predicate_commitment_v06(claim["predicate"])
    context = [
        {
            "id": assumption_map[assumption_id]["id"],
            "statement": assumption_map[assumption_id]["statement"],
        }
        for assumption_id in claim["assumptions"]
    ]

    wire_evidence: list[dict[str, Any]] = []
    for evidence_id in claim["required_evidence"]:
        item = evidence_map[evidence_id]
        evidence_commitment = predicate_commitment_v06(item["predicate"])
        if evidence_commitment != claim_commitment:
            raise V06NormalizationError(
                f"required evidence {evidence_id} is not exactly predicate-bound to claim {claim_id}"
            )
        wire_evidence.append(
            {
                "id": item["id"],
                "kind": item["kind"],
                "outcome": item["outcome"],
                "predicate_commitment": evidence_commitment,
            }
        )

    decision = replay["claim_statuses"][claim_id]
    if decision != claim["assessment"]["status"]:
        raise V06NormalizationError(
            f"replayed claim decision differs from recorded assessment for {claim_id}"
        )

    wire: dict[str, Any] = {
        "wire_format": WIRE_FORMAT_V06,
        "canonical_json_profile": "pcs-jcs-rfc8785-v1",
        "wire_hash_format": NORMALIZED_DECISION_DOMAIN,
        "predicate_hash_format": PREDICATE_COMMITMENT_DOMAIN,
        "source": {
            "spec_version": certificate["spec_version"],
            "checker_version": certificate["checker_version"],
            "certificate_semantic_hash": certificate["semantic_hash"],
            "certificate_integrity_hash": certificate["integrity_hash"],
            "claim_id": claim_id,
        },
        "context": context,
        "claim": {
            "id": claim["id"],
            "kind": claim["kind"],
            "predicate_commitment": claim_commitment,
            "required_evidence": list(claim["required_evidence"]),
            "assumptions": list(claim["assumptions"]),
        },
        "evidence": wire_evidence,
        "decision": decision,
        "wire_semantic_hash": "",
    }
    wire["wire_semantic_hash"] = wire_semantic_hash_v06(wire)
    checked = validate_normalized_wire_v06(wire)
    if not checked["valid"]:
        raise V06NormalizationError(
            "internal v0.6 normalized wire invariant failure: "
            + "; ".join(checked["errors"])
        )
    return wire


def normalize_replayed_certificate_v06(
    certificate: dict[str, Any],
    package_files: Mapping[str, bytes],
    claim_id: str,
) -> dict[str, Any]:
    replay = verify_certificate_replay_v06(certificate, package_files)
    return normalize_claim_after_replay_v06(certificate, replay, claim_id)


def verify_normalized_against_certificate_v06(
    wire: dict[str, Any],
    certificate: dict[str, Any],
    package_files: Mapping[str, bytes],
) -> dict[str, Any]:
    internal = validate_normalized_wire_v06(wire)
    if not internal["valid"]:
        return {**internal, "source_certificate_match": False}

    try:
        expected = normalize_replayed_certificate_v06(
            certificate,
            package_files,
            wire["source"]["claim_id"],
        )
    except V06NormalizationError as exc:
        return {
            **internal,
            "valid": False,
            "errors": [*internal["errors"], str(exc)],
            "source_certificate_match": False,
        }

    source_match = expected == wire
    errors = list(internal["errors"])
    if not source_match:
        errors.append(
            "normalized decision does not exactly equal replay-derived certificate normalization"
        )
    return {
        **internal,
        "valid": not errors,
        "errors": errors,
        "source_certificate_match": source_match,
        "source_certificate_semantic_hash": certificate["semantic_hash"],
        "source_certificate_integrity_hash": certificate["integrity_hash"],
    }


def normalized_wire_bytes_v06(wire: dict[str, Any]) -> bytes:
    checked = validate_normalized_wire_v06(wire)
    if not checked["valid"]:
        raise V06NormalizationError(
            "refusing canonical bytes for invalid v0.6 normalized decision: "
            + "; ".join(checked["errors"])
        )
    return canonicalize_jcs_bytes(wire)


def parse_normalized_wire_bytes_v06(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        raise V06NormalizationError("v0.6 normalized decision must be immutable bytes")
    if len(raw) > MAX_NORMALIZED_WIRE_BYTES_V06:
        raise V06NormalizationError(
            f"v0.6 normalized decision exceeds byte limit: "
            f"{len(raw)} > {MAX_NORMALIZED_WIRE_BYTES_V06}"
        )
    if raw.startswith(UTF8_BOM):
        raise V06NormalizationError("v0.6 normalized decision must not contain a UTF-8 BOM")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = parse_jcs_json(text)
        canonical = canonicalize_jcs_bytes(value)
    except (UnicodeDecodeError, CanonicalJSONError, RecursionError) as exc:
        raise V06NormalizationError(
            f"invalid v0.6 normalized decision JSON: {exc}"
        ) from exc
    if canonical != raw:
        raise V06NormalizationError(
            "v0.6 normalized decision is not the exact canonical JCS byte representation"
        )
    if not isinstance(value, dict):
        raise V06NormalizationError("v0.6 normalized decision root must be an object")

    checked = validate_normalized_wire_v06(value)
    if not checked["valid"]:
        raise V06NormalizationError("; ".join(checked["errors"]))
    return value


def verify_normalized_bytes_against_certificate_v06(
    raw: bytes,
    certificate: dict[str, Any],
    package_files: Mapping[str, bytes],
) -> dict[str, Any]:
    try:
        wire = parse_normalized_wire_bytes_v06(raw)
    except V06NormalizationError as exc:
        return {"valid": False, "errors": [str(exc)], "source_certificate_match": False}
    return verify_normalized_against_certificate_v06(
        wire,
        certificate,
        package_files,
    )
