from __future__ import annotations

import hashlib
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .adapters.pkpd import check_contract_file, check_output_file
from .certificate_v06 import verify_certificate_hashes_v06
from .checks.chemistry import reaction_balanced
from .checks.splits import csv_key_disjoint
from .checks.units import units_compatible
from .decision import assess_claim
from .package_v06 import MAX_PACKAGE_SINGLE_FILE_V06, MAX_PACKAGE_TOTAL_BYTES_V06


class V06ReplayError(ValueError):
    pass


def _artifact_bytes(
    certificate: dict[str, Any],
    package_files: Mapping[str, bytes],
) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    total = 0
    for artifact in certificate["artifacts"]:
        path = artifact["path"]
        raw = package_files.get(path)
        if not isinstance(raw, bytes):
            raise V06ReplayError(
                f"certificate artifact {artifact['id']} is missing immutable bytes at {path!r}"
            )
        if len(raw) > MAX_PACKAGE_SINGLE_FILE_V06:
            raise V06ReplayError(f"certificate artifact {artifact['id']} exceeds byte limit")
        total += len(raw)
        if total > MAX_PACKAGE_TOTAL_BYTES_V06:
            raise V06ReplayError("certificate artifacts exceed total replay byte limit")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != artifact["sha256"]:
            raise V06ReplayError(
                f"certificate artifact hash mismatch: {artifact['id']}"
            )
        out[artifact["id"]] = raw
    return out


def _replay_one(
    evidence: dict[str, Any],
    artifact_paths: Mapping[str, Path],
) -> dict[str, Any]:
    spec = evidence["check_spec"]
    check_type = spec["type"]

    try:
        if check_type == "reaction_balance":
            ok, details = reaction_balanced(spec["reactants"], spec["products"])
            kind = "computational_test"
        elif check_type == "unit_compatible":
            ok, details = units_compatible(spec["left_unit"], spec["right_unit"])
            kind = "computational_test"
        elif check_type == "csv_disjoint":
            ok, details = csv_key_disjoint(
                artifact_paths[spec["left_artifact"]],
                artifact_paths[spec["right_artifact"]],
                spec["key"],
            )
            kind = "computational_test"
        elif check_type == "pkpd_contract":
            ok, details = check_contract_file(artifact_paths[spec["model_artifact"]])
            kind = "computational_test"
        elif check_type == "pkpd_reference_match":
            ok, details = check_output_file(
                artifact_paths[spec["model_artifact"]],
                artifact_paths[spec["output_artifact"]],
                time_column=spec["time_column"],
                concentration_column=spec["concentration_column"],
                effect_column=spec["effect_column"],
                rel_tol=float(spec["rel_tol"]),
                abs_tol=float(spec["abs_tol"]),
            )
            kind = "computational_test"
        elif check_type == "external_formal_proof":
            return {
                "id": evidence["id"],
                "kind": "formal_proof",
                "outcome": "UNVERIFIED",
                "details": {
                    "reason": "external formal proof is not established by the v0.6 built-in replay kernel",
                    "validator": spec["validator"],
                },
            }
        elif check_type == "external_empirical_validation":
            return {
                "id": evidence["id"],
                "kind": "empirical_validation",
                "outcome": "UNVERIFIED",
                "details": {
                    "reason": "external empirical validation is not established by the v0.6 built-in replay kernel",
                    "validator": spec["validator"],
                },
            }
        elif check_type == "external_statistical_validation":
            return {
                "id": evidence["id"],
                "kind": "statistical_validation",
                "outcome": "UNVERIFIED",
                "details": {
                    "reason": "external statistical validation is not established by the v0.6 built-in replay kernel",
                    "validator": spec["validator"],
                },
            }
        elif check_type == "provenance_record":
            return {
                "id": evidence["id"],
                "kind": "provenance",
                "outcome": "UNVERIFIED",
                "details": {
                    "reason": "provenance record is structurally bound but not independently established by this replay kernel",
                    "validator": spec["validator"],
                },
            }
        else:
            raise V06ReplayError(f"unsupported v0.6 replay check type: {check_type!r}")
    except Exception as exc:
        return {
            "id": evidence["id"],
            "kind": (
                "computational_test"
                if check_type in {
                    "reaction_balance",
                    "unit_compatible",
                    "csv_disjoint",
                    "pkpd_contract",
                    "pkpd_reference_match",
                }
                else evidence["kind"]
            ),
            "outcome": "FAIL",
            "details": {
                "error": type(exc).__name__,
                "message": str(exc),
                "check_type": check_type,
            },
        }

    return {
        "id": evidence["id"],
        "kind": kind,
        "outcome": "PASS" if ok else "FAIL",
        "details": details,
    }


def verify_certificate_replay_v06(
    certificate: dict[str, Any],
    package_files: Mapping[str, bytes],
) -> dict[str, Any]:
    """Replay all v0.6 built-in evidence and recompute claim decisions.

    Successful return means the certificate is structurally/hash valid and every
    recorded evidence kind/outcome plus every claim assessment agrees with fresh
    replay. It does not establish empirical adequacy beyond the implemented checks.
    """
    errors: list[str] = []
    checked = verify_certificate_hashes_v06(certificate)
    if not checked["valid"]:
        return {
            "valid": False,
            "errors": list(checked["errors"]),
            "evidence": [],
            "claim_statuses": {},
        }

    try:
        artifacts = _artifact_bytes(certificate, package_files)
    except V06ReplayError as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "evidence": [],
            "claim_statuses": {},
        }

    evidence_results: list[dict[str, Any]] = []
    replay_map: dict[str, dict[str, Any]] = {}

    with tempfile.TemporaryDirectory(prefix="pcs-v06-replay-") as tmp:
        root = Path(tmp)
        artifact_paths: dict[str, Path] = {}
        for artifact_id, raw in artifacts.items():
            path = root / hashlib.sha256(artifact_id.encode("utf-8")).hexdigest()
            path.write_bytes(raw)
            artifact_paths[artifact_id] = path

        for evidence in certificate["evidence"]:
            result = _replay_one(evidence, artifact_paths)
            evidence_results.append(result)
            replayed = deepcopy(evidence)
            replayed["kind"] = result["kind"]
            replayed["outcome"] = result["outcome"]
            replay_map[evidence["id"]] = replayed

            if evidence["kind"] != result["kind"]:
                errors.append(
                    f"evidence replay kind mismatch: {evidence['id']} "
                    f"recorded={evidence['kind']} replayed={result['kind']}"
                )
            if evidence["outcome"] != result["outcome"]:
                errors.append(
                    f"evidence replay outcome mismatch: {evidence['id']} "
                    f"recorded={evidence['outcome']} replayed={result['outcome']}"
                )
            if evidence["check_spec"]["type"] in {
                "reaction_balance",
                "unit_compatible",
                "csv_disjoint",
                "pkpd_contract",
                "pkpd_reference_match",
            } and evidence["checker"] != certificate["checker_version"]:
                errors.append(
                    f"evidence {evidence['id']} checker differs from certificate checker_version"
                )

    claim_statuses: dict[str, str] = {}
    for claim in certificate["claims"]:
        assessment = assess_claim(claim, replay_map)
        claim_statuses[claim["id"]] = assessment["status"]
        if claim["assessment"] != assessment:
            errors.append(
                f"claim replay assessment mismatch: {claim['id']} "
                f"recorded={claim['assessment']!r} replayed={assessment!r}"
            )

    return {
        "valid": not errors,
        "errors": errors,
        "certificate_semantic_hash": certificate["semantic_hash"],
        "certificate_integrity_hash": certificate["integrity_hash"],
        "evidence": evidence_results,
        "claim_statuses": claim_statuses,
    }
