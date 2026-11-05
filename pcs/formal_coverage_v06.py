from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .check_registry_v06 import CERTIFIED_BUILTIN_CHECK_TYPES_V06
from .external_validator_v06 import is_signed_external_validator_spec_v06


FORMAL_COVERAGE_FORMAT_V06 = "pcs-formal-coverage-v1"


def _authority_status(
    *,
    package_authoritative: bool,
    lean_authority: Mapping[str, Any] | None,
) -> str:
    if (
        package_authoritative
        and isinstance(lean_authority, Mapping)
        and lean_authority.get("accepted") is True
    ):
        return "LEAN_AUTHORITATIVE_ACCEPT"
    if isinstance(lean_authority, Mapping):
        verdict = lean_authority.get("verdict")
        if verdict == "NOT_RUN_PYTHON_PRECHECK_FAILED":
            return "LEAN_AUTHORITY_NOT_RUN_PRECHECK_FAILED"
        if lean_authority.get("accepted") is False:
            return "LEAN_AUTHORITY_REJECT"
    return "LEAN_AUTHORITY_NOT_ESTABLISHED"


def classify_formal_coverage_v06(
    certificate: Mapping[str, Any],
    *,
    package_authoritative: bool = False,
    lean_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe checker theorem scope separately from exact-package authority.

    checker_semantics is a property of a check type: it says whether PCS has a
    proved Lean checker for that predicate family.

    execution_authority is a property of this exact verification run. A built-in
    evidence item is marked AUTHORITATIVELY_REPLAYED_BY_LEAN only after the
    compiled Lean authority accepts the exact package.
    """

    raw_evidence = certificate.get("evidence", [])
    evidence: Sequence[Any]
    if isinstance(raw_evidence, Sequence) and not isinstance(
        raw_evidence, (str, bytes, bytearray)
    ):
        evidence = raw_evidence
    else:
        evidence = []

    package_authority = _authority_status(
        package_authoritative=package_authoritative,
        lean_authority=lean_authority,
    )
    exact_authority = package_authority == "LEAN_AUTHORITATIVE_ACCEPT"

    rows: list[dict[str, Any]] = []
    certified_count = 0
    signed_external_count = 0

    for item in evidence:
        if not isinstance(item, Mapping):
            continue
        spec = item.get("check_spec")
        check_type = spec.get("type") if isinstance(spec, Mapping) else None
        is_certified = check_type in CERTIFIED_BUILTIN_CHECK_TYPES_V06
        is_signed_external = (
            isinstance(spec, Mapping)
            and is_signed_external_validator_spec_v06(spec)
        )
        if is_certified:
            certified_count += 1
        if is_signed_external:
            signed_external_count += 1

        if is_certified and exact_authority:
            execution_authority = "AUTHORITATIVELY_REPLAYED_BY_LEAN"
        elif is_certified:
            execution_authority = "CHECKER_TYPE_PROVED_PACKAGE_NOT_LEAN_ACCEPTED"
        else:
            execution_authority = "OUTSIDE_CERTIFIED_BUILTIN_SET"

        row = {
            "evidence_id": item.get("id"),
            "check_type": check_type,
            "checker_semantics": (
                "PROVED_IN_LEAN_FOR_THIS_CHECK_TYPE"
                if is_certified
                else "NOT_IN_CERTIFIED_BUILTIN_SET"
            ),
            "execution_authority": execution_authority,
        }
        if is_signed_external and isinstance(spec, Mapping):
            row["external_validator_contract"] = {
                "binding": "PINNED_SIGNED_RECEIPT",
                "validator": spec.get("validator"),
                "validator_public_key_fingerprint": spec.get(
                    "validator_public_key_fingerprint"
                ),
                "cryptographic_replay": (
                    "PYTHON_PRECHECK_REQUIRED"
                    if not exact_authority
                    else "PYTHON_PRECHECK_ACCEPTED_BEFORE_LEAN_TRANSCRIPT"
                ),
                "semantic_authority": "EXTERNAL_VALIDATOR_TRUST_REQUIRED",
                "lean_scientific_semantics": "NOT_PROVED_BY_PCS_LEAN_CHECKER",
            }
        rows.append(row)

    total = len(rows)
    return {
        "format": FORMAL_COVERAGE_FORMAT_V06,
        "checker_classification_scope": "CHECK_TYPE_ONLY",
        "execution_authority_scope": "EXACT_PACKAGE_VERIFICATION",
        "certified_checker_types": sorted(CERTIFIED_BUILTIN_CHECK_TYPES_V06),
        "evidence_total": total,
        "certified_type_evidence": certified_count,
        "outside_certified_type_evidence": total - certified_count,
        "signed_external_validator_evidence": signed_external_count,
        "package_authority": package_authority,
        "evidence": rows,
    }
