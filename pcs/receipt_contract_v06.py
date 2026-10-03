from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .formal_coverage_v06 import (
    CERTIFIED_BUILTIN_CHECK_TYPES_V06,
    FORMAL_COVERAGE_FORMAT_V06,
)
from .jsonio import StrictJSONError, strict_json_load


RECEIPT_FORMAT_V06 = "pcs-end-to-end-verifier-v06-v1"
RECEIPT_CONTRACT_AUDIT_FORMAT_V06 = "pcs-receipt-contract-audit-v1"
LEAN_AUTHORITY_RESULT_FORMAT_V06 = "pcs-lean-authority-result-v1"

_CANONICAL_ARCHIVE_ASSURANCE = "lean-decoded-canonical-zip"
_LEGACY_ARCHIVE_ASSURANCE = "python-materialized-legacy-zip"


class V06ReceiptContractError(ValueError):
    pass


def _is_hex64(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _file_sha256(path: str | Path) -> str:
    p = Path(path)
    digest = hashlib.sha256()
    try:
        with p.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    return digest.hexdigest()
                digest.update(chunk)
    except OSError as exc:
        raise V06ReceiptContractError(
            f"cannot hash external receipt anchor {p}: {type(exc).__name__}: {exc}"
        ) from exc


def _ed25519_fingerprint(path: str | Path) -> str:
    p = Path(path)
    try:
        key = serialization.load_pem_public_key(p.read_bytes())
    except (OSError, ValueError, TypeError) as exc:
        raise V06ReceiptContractError(
            f"cannot load producer Ed25519 public key {p}: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(key, Ed25519PublicKey):
        raise V06ReceiptContractError("producer public key is not Ed25519")
    raw = key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    return hashlib.sha256(raw).hexdigest()


def _sequence(value: Any) -> Sequence[Any] | None:
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return value
    return None


def _audit_formal_coverage(
    coverage: Mapping[str, Any],
    *,
    authoritative: bool,
    lean_accepted: bool,
    errors: list[str],
    checks: dict[str, bool],
) -> None:
    checks["formal_coverage_format"] = (
        coverage.get("format") == FORMAL_COVERAGE_FORMAT_V06
    )
    if not checks["formal_coverage_format"]:
        errors.append("formal_coverage has unsupported format")

    certified = coverage.get("certified_checker_types")
    expected_types = sorted(CERTIFIED_BUILTIN_CHECK_TYPES_V06)
    checks["formal_coverage_certified_type_set"] = certified == expected_types
    if not checks["formal_coverage_certified_type_set"]:
        errors.append("formal_coverage certified checker type set drift")

    checks["formal_coverage_scopes"] = (
        coverage.get("checker_classification_scope") == "CHECK_TYPE_ONLY"
        and coverage.get("execution_authority_scope")
        == "EXACT_PACKAGE_VERIFICATION"
    )
    if not checks["formal_coverage_scopes"]:
        errors.append("formal_coverage scope declaration mismatch")

    expected_package_authority = (
        "LEAN_AUTHORITATIVE_ACCEPT"
        if authoritative and lean_accepted
        else None
    )
    actual_package_authority = coverage.get("package_authority")
    if expected_package_authority is not None:
        checks["formal_coverage_package_authority"] = (
            actual_package_authority == expected_package_authority
        )
    else:
        checks["formal_coverage_package_authority"] = (
            actual_package_authority != "LEAN_AUTHORITATIVE_ACCEPT"
        )
    if not checks["formal_coverage_package_authority"]:
        errors.append("formal_coverage package authority contradicts Lean authority")

    rows = _sequence(coverage.get("evidence"))
    if rows is None:
        checks["formal_coverage_evidence_shape"] = False
        errors.append("formal_coverage evidence must be an array")
        return

    valid_rows = [row for row in rows if isinstance(row, Mapping)]
    checks["formal_coverage_evidence_shape"] = len(valid_rows) == len(rows)
    if not checks["formal_coverage_evidence_shape"]:
        errors.append("formal_coverage evidence contains non-object entries")

    certified_count = 0
    seen_ids: set[str] = set()
    unique_ids = True
    row_semantics_ok = True
    row_authority_ok = True

    for row in valid_rows:
        evidence_id = row.get("evidence_id")
        if isinstance(evidence_id, str):
            if evidence_id in seen_ids:
                unique_ids = False
            seen_ids.add(evidence_id)

        check_type = row.get("check_type")
        in_certified_set = check_type in CERTIFIED_BUILTIN_CHECK_TYPES_V06
        if in_certified_set:
            certified_count += 1

        expected_semantics = (
            "PROVED_IN_LEAN_FOR_THIS_CHECK_TYPE"
            if in_certified_set
            else "NOT_IN_CERTIFIED_BUILTIN_SET"
        )
        if row.get("checker_semantics") != expected_semantics:
            row_semantics_ok = False

        if in_certified_set and authoritative and lean_accepted:
            expected_execution = "AUTHORITATIVELY_REPLAYED_BY_LEAN"
        elif in_certified_set:
            expected_execution = "CHECKER_TYPE_PROVED_PACKAGE_NOT_LEAN_ACCEPTED"
        else:
            expected_execution = "OUTSIDE_CERTIFIED_BUILTIN_SET"
        if row.get("execution_authority") != expected_execution:
            row_authority_ok = False

    checks["formal_coverage_unique_evidence_ids"] = unique_ids
    if not unique_ids:
        errors.append("formal_coverage contains duplicate evidence_id values")

    checks["formal_coverage_checker_semantics"] = row_semantics_ok
    if not row_semantics_ok:
        errors.append("formal_coverage checker semantics contradict check_type")

    checks["formal_coverage_execution_authority"] = row_authority_ok
    if not row_authority_ok:
        errors.append("formal_coverage execution authority contradicts package authority")

    total = len(valid_rows)
    counts_ok = (
        coverage.get("evidence_total") == total
        and coverage.get("certified_type_evidence") == certified_count
        and coverage.get("outside_certified_type_evidence")
        == total - certified_count
    )
    checks["formal_coverage_counts"] = counts_ok
    if not counts_ok:
        errors.append("formal_coverage evidence counts are inconsistent")


def audit_verification_receipt_v06(
    receipt: Mapping[str, Any],
    *,
    expected_bundle_sha256: str | None = None,
    expected_producer_fingerprint: str | None = None,
    expected_authority_sha256: str | None = None,
) -> dict[str, Any]:
    """Audit internal PCS receipt invariants and optional external anchors.

    This does not re-run the scientific verification. It proves that the receipt is a
    coherent PCS verification attestation and, when external expected hashes are
    supplied, that it names those exact external objects.
    """

    errors: list[str] = []
    checks: dict[str, bool] = {}

    checks["receipt_format"] = receipt.get("format") == RECEIPT_FORMAT_V06
    if not checks["receipt_format"]:
        errors.append("unsupported verification receipt format")

    boolean_fields = ("valid", "accepted", "authoritative", "authority_required")
    for field in boolean_fields:
        ok = isinstance(receipt.get(field), bool)
        checks[f"boolean_{field}"] = ok
        if not ok:
            errors.append(f"receipt field {field!r} must be boolean")

    valid = receipt.get("valid") is True
    accepted = receipt.get("accepted") is True
    authoritative = receipt.get("authoritative") is True
    authority_required = receipt.get("authority_required") is True

    checks["authority_required"] = authority_required
    if not authority_required:
        errors.append("v0.6 production receipt must require Lean authority")

    checks["accepted_implies_valid"] = not accepted or valid
    if not checks["accepted_implies_valid"]:
        errors.append("accepted=true contradicts valid=false")

    checks["valid_authoritative_equivalence"] = valid == authoritative
    if not checks["valid_authoritative_equivalence"]:
        errors.append("valid and authoritative must agree after mandatory Lean authority")

    authority = receipt.get("lean_authority")
    lean_accepted = False
    if authority is None:
        checks["lean_authority_present_when_authoritative"] = not authoritative
        if authoritative:
            errors.append("authoritative receipt lacks lean_authority")
    elif not isinstance(authority, Mapping):
        checks["lean_authority_shape"] = False
        errors.append("lean_authority must be an object")
    else:
        checks["lean_authority_shape"] = True
        checks["lean_authority_format"] = (
            authority.get("format") == LEAN_AUTHORITY_RESULT_FORMAT_V06
        )
        if not checks["lean_authority_format"]:
            errors.append("lean_authority has unsupported format")

        lean_accepted = authority.get("accepted") is True
        checks["lean_authority_accepted_boolean"] = isinstance(
            authority.get("accepted"), bool
        )
        if not checks["lean_authority_accepted_boolean"]:
            errors.append("lean_authority.accepted must be boolean")

        checks["lean_acceptance_matches_authoritative"] = (
            lean_accepted == authoritative
        )
        if not checks["lean_acceptance_matches_authoritative"]:
            errors.append("lean_authority.accepted contradicts authoritative")

        verdict = authority.get("verdict")
        verdict_ok = (
            (lean_accepted and verdict == "ACCEPT")
            or (
                not lean_accepted
                and verdict in {"REJECT", "NOT_RUN_PYTHON_PRECHECK_FAILED"}
            )
        )
        checks["lean_authority_verdict"] = verdict_ok
        if not verdict_ok:
            errors.append("lean_authority verdict contradicts accepted state")

        if lean_accepted:
            for field in ("authority_sha256", "observation_transcript_sha256"):
                ok = _is_hex64(authority.get(field))
                checks[f"lean_authority_{field}"] = ok
                if not ok:
                    errors.append(f"accepted Lean authority lacks valid {field}")

            receipt_cert = receipt.get("certificate_semantic_hash")
            authority_cert = authority.get("certificate_semantic_hash")
            checks["authority_certificate_binding"] = (
                _is_hex64(receipt_cert) and authority_cert == receipt_cert
            )
            if not checks["authority_certificate_binding"]:
                errors.append(
                    "Lean authority certificate semantic hash does not match receipt"
                )

    stages = receipt.get("stages")
    if isinstance(stages, Mapping) and "lean_authority" in stages:
        checks["lean_authority_stage"] = stages.get("lean_authority") is authoritative
        if not checks["lean_authority_stage"]:
            errors.append("stages.lean_authority contradicts authoritative")

    if valid:
        for field in (
            "certificate_semantic_hash",
            "certificate_integrity_hash",
            "normalized_index_semantic_hash",
            "public_key_fingerprint",
        ):
            ok = _is_hex64(receipt.get(field))
            checks[f"valid_receipt_{field}"] = ok
            if not ok:
                errors.append(f"valid receipt lacks 64-hex {field}")

    archive_format = receipt.get("archive_format")
    archive_assurance = receipt.get("archive_assurance")
    if archive_format is not None:
        checks["archive_format"] = archive_format == "zip"
        if not checks["archive_format"]:
            errors.append("unsupported archive_format in v0.6 receipt")
        bundle_ok = _is_hex64(receipt.get("bundle_sha256"))
        checks["bundle_sha256"] = bundle_ok
        if not bundle_ok:
            errors.append("ZIP receipt lacks 64-hex bundle_sha256")
        assurance_ok = archive_assurance in {
            _CANONICAL_ARCHIVE_ASSURANCE,
            _LEGACY_ARCHIVE_ASSURANCE,
        }
        checks["archive_assurance"] = assurance_ok
        if not assurance_ok:
            errors.append("ZIP receipt has unsupported archive_assurance")

        if isinstance(authority, Mapping) and authority.get("archive_mode") is not None:
            expected_archive_mode = (
                _CANONICAL_ARCHIVE_ASSURANCE
                if archive_assurance == _CANONICAL_ARCHIVE_ASSURANCE
                else "python-materialized-members"
            )
            checks["archive_authority_mode"] = (
                authority.get("archive_mode") == expected_archive_mode
            )
            if not checks["archive_authority_mode"]:
                errors.append("archive_assurance contradicts Lean authority archive_mode")

    coverage = receipt.get("formal_coverage")
    if coverage is None:
        checks["formal_coverage_present_when_valid"] = not valid
        if valid:
            errors.append("valid receipt lacks formal_coverage")
    elif not isinstance(coverage, Mapping):
        checks["formal_coverage_shape"] = False
        errors.append("formal_coverage must be an object")
    else:
        checks["formal_coverage_shape"] = True
        _audit_formal_coverage(
            coverage,
            authoritative=authoritative,
            lean_accepted=lean_accepted,
            errors=errors,
            checks=checks,
        )

    reviewer_policy = receipt.get("reviewer_policy")
    if not isinstance(reviewer_policy, Mapping):
        checks["reviewer_policy_shape"] = False
        errors.append("receipt lacks reviewer_policy object")
    else:
        checks["reviewer_policy_shape"] = True
        applied = reviewer_policy.get("applied")
        policy_pass = reviewer_policy.get("pass")
        if applied is False:
            policy_ok = (
                policy_pass is None
                and reviewer_policy.get("policy_sha256") is None
                and accepted == valid
            )
        elif applied is True:
            policy_ok = (
                isinstance(policy_pass, bool)
                and _is_hex64(reviewer_policy.get("policy_sha256"))
                and accepted == (valid and policy_pass)
            )
        else:
            policy_ok = False
        checks["reviewer_policy_acceptance"] = policy_ok
        if not policy_ok:
            errors.append("reviewer_policy contradicts accepted/valid state")

    if expected_bundle_sha256 is not None:
        expected = expected_bundle_sha256.lower()
        actual = receipt.get("bundle_sha256")
        ok = _is_hex64(expected) and isinstance(actual, str) and actual.lower() == expected
        checks["external_bundle_binding"] = ok
        if not ok:
            errors.append("receipt does not bind the expected bundle SHA-256")

    if expected_producer_fingerprint is not None:
        expected = expected_producer_fingerprint.lower()
        actual = receipt.get("public_key_fingerprint")
        ok = _is_hex64(expected) and isinstance(actual, str) and actual.lower() == expected
        checks["external_producer_key_binding"] = ok
        if not ok:
            errors.append("receipt does not bind the expected producer public key")

    if expected_authority_sha256 is not None:
        expected = expected_authority_sha256.lower()
        actual = authority.get("authority_sha256") if isinstance(authority, Mapping) else None
        ok = _is_hex64(expected) and isinstance(actual, str) and actual.lower() == expected
        checks["external_authority_binary_binding"] = ok
        if not ok:
            errors.append("receipt does not bind the expected Lean authority binary")

    return {
        "format": RECEIPT_CONTRACT_AUDIT_FORMAT_V06,
        "valid": not errors,
        "errors": errors,
        "checks": checks,
        "receipt_format": receipt.get("format"),
        "pcs_valid": receipt.get("valid"),
        "authoritative": receipt.get("authoritative"),
        "reviewer_accepted": receipt.get("accepted"),
        "bundle_sha256": receipt.get("bundle_sha256"),
        "producer_public_key_fingerprint": receipt.get("public_key_fingerprint"),
        "lean_authority_sha256": (
            authority.get("authority_sha256")
            if isinstance(authority, Mapping)
            else None
        ),
    }


def assert_verification_receipt_contract_v06(receipt: Mapping[str, Any]) -> None:
    audited = audit_verification_receipt_v06(receipt)
    if not audited["valid"]:
        raise V06ReceiptContractError(
            "verification receipt contract failed: " + "; ".join(audited["errors"])
        )


def audit_verification_receipt_file_v06(
    receipt_path: str | Path,
    *,
    bundle_path: str | Path | None = None,
    producer_public_key_path: str | Path | None = None,
    authority_path: str | Path | None = None,
) -> dict[str, Any]:
    try:
        receipt = strict_json_load(receipt_path)
    except (OSError, StrictJSONError) as exc:
        return {
            "format": RECEIPT_CONTRACT_AUDIT_FORMAT_V06,
            "valid": False,
            "errors": [f"verification receipt is not strict JSON: {exc}"],
            "checks": {},
        }
    if not isinstance(receipt, Mapping):
        return {
            "format": RECEIPT_CONTRACT_AUDIT_FORMAT_V06,
            "valid": False,
            "errors": ["verification receipt root must be an object"],
            "checks": {},
        }

    try:
        bundle_sha = _file_sha256(bundle_path) if bundle_path is not None else None
        producer_fp = (
            _ed25519_fingerprint(producer_public_key_path)
            if producer_public_key_path is not None
            else None
        )
        authority_sha = (
            _file_sha256(authority_path) if authority_path is not None else None
        )
    except V06ReceiptContractError as exc:
        return {
            "format": RECEIPT_CONTRACT_AUDIT_FORMAT_V06,
            "valid": False,
            "errors": [str(exc)],
            "checks": {},
        }

    return audit_verification_receipt_v06(
        receipt,
        expected_bundle_sha256=bundle_sha,
        expected_producer_fingerprint=producer_fp,
        expected_authority_sha256=authority_sha,
    )
