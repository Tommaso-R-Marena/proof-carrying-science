from __future__ import annotations

import hashlib
import tempfile
import time
from datetime import datetime, timezone
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .adapters.pkpd import check_contract_file, check_output_file, strict_decimal_text
from .certificate_v06 import verify_certificate_hashes_v06
from .checks.chemistry import reaction_balanced
from .checks.splits import csv_key_disjoint
from .checks.units import units_compatible
from .decision import assess_claim
from .external_validator_v06 import (
    EXTERNAL_VALIDATOR_CHECK_TYPES_V06,
    external_validator_artifact_ids_v06,
    is_signed_external_validator_spec_v06,
    verify_external_validator_receipt_v06,
)
from .formal_coverage_v06 import CERTIFIED_BUILTIN_CHECK_TYPES_V06
from .package_v06 import MAX_PACKAGE_SINGLE_FILE_V06, MAX_PACKAGE_TOTAL_BYTES_V06
from .scheduler_v06 import (
    TELEMETRY_FORMAT_V06,
    V06SchedulerError,
    plan_evidence_v06,
)


class V06ReplayError(ValueError):
    pass


def _telemetry_evidence_id(evidence_id: str) -> str:
    return "sha256:" + hashlib.sha256(evidence_id.encode("utf-8")).hexdigest()


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


def _strict_tolerance(value: Any) -> float:
    """A PK/PD tolerance: an integer or a strict decimal string (as in the Lean authority's
    `PCS.V2.PKPDCheck.tolOf`). Strings such as ' 1e-9', '1_0', 'inf' or 'nan', which
    `float()` would accept, fail closed."""
    if isinstance(value, bool):
        raise ValueError("tolerance must not be a boolean")
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        # direct-API callers; certificates always carry the canonical decimal text
        return value
    if isinstance(value, str):
        return float(strict_decimal_text(value))
    raise ValueError("tolerance must be a number or a decimal string")


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
                rel_tol=_strict_tolerance(spec["rel_tol"]),
                abs_tol=_strict_tolerance(spec["abs_tol"]),
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
        elif check_type in EXTERNAL_VALIDATOR_CHECK_TYPES_V06:
            if not is_signed_external_validator_spec_v06(spec):
                kind = (
                    "empirical_validation"
                    if check_type == "external_empirical_validation"
                    else "statistical_validation"
                )
                return {
                    "id": evidence["id"],
                    "kind": kind,
                    "outcome": "UNVERIFIED",
                    "details": {
                        "reason": (
                            "external validation lacks a complete signed-receipt "
                            "adapter contract"
                        ),
                        "validator": spec["validator"],
                        "semantic_authority": "EXTERNAL_VALIDATOR_TRUST_REQUIRED",
                    },
                }

            validator_artifacts = {
                artifact_id: artifact_paths[artifact_id].read_bytes()
                for artifact_id in external_validator_artifact_ids_v06(spec)
            }
            receipt = verify_external_validator_receipt_v06(
                spec,
                validator_artifacts,
            )
            if receipt.get("valid") is not True:
                return {
                    "id": evidence["id"],
                    "kind": receipt["kind"],
                    "outcome": "FAIL",
                    "details": {
                        "reason": "signed external validator receipt failed verification",
                        "validator": spec["validator"],
                        "errors": list(receipt.get("errors", [])),
                        "semantic_authority": "EXTERNAL_VALIDATOR_TRUST_REQUIRED",
                    },
                }
            return {
                "id": evidence["id"],
                "kind": receipt["kind"],
                "outcome": receipt["outcome"],
                "details": {
                    "reason": (
                        "PCS verified the pinned validator signature, predicate, "
                        "and exact artifact bindings; validator methodology remains "
                        "an explicit external trust assumption"
                    ),
                    "validator": receipt["validator"],
                    "validator_public_key_fingerprint": receipt[
                        "validator_public_key_fingerprint"
                    ],
                    "receipt_payload_sha256": receipt[
                        "receipt_payload_sha256"
                    ],
                    "artifact_bindings": receipt["artifact_bindings"],
                    "trust_contract": receipt["trust_contract"],
                    "semantic_authority": receipt["semantic_authority"],
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
                if check_type in CERTIFIED_BUILTIN_CHECK_TYPES_V06
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



def replay_evidence_item_v06(
    evidence: dict[str, Any],
    artifact_paths: Mapping[str, Path],
) -> dict[str, Any]:
    """Replay one typed v0.6 evidence item against exact packaged artifact paths."""
    return _replay_one(evidence, artifact_paths)


def verify_certificate_replay_v06(
    certificate: dict[str, Any],
    package_files: Mapping[str, bytes],
    *,
    scheduler_strategy: str = "manifest",
    scheduler_history: list[dict[str, Any]] | None = None,
    bandit_alpha: float = 1.0,
    shadow_bandit: bool = False,
    telemetry_sink: dict[str, Any] | None = None,
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
    result_by_id: dict[str, dict[str, Any]] = {}

    artifact_sizes = {
        artifact_id: len(raw)
        for artifact_id, raw in artifacts.items()
    }
    try:
        schedule = plan_evidence_v06(
            certificate["evidence"],
            artifact_sizes,
            strategy=scheduler_strategy,
            history=scheduler_history or [],
            bandit_alpha=bandit_alpha,
            shadow_bandit=shadow_bandit,
        )
    except V06SchedulerError as exc:
        return {
            "valid": False,
            "errors": [f"replay scheduler configuration invalid: {exc}"],
            "evidence": [],
            "claim_statuses": {},
        }

    evidence_by_id = {
        evidence["id"]: evidence
        for evidence in certificate["evidence"]
    }
    telemetry_checks: list[dict[str, Any]] = []
    cumulative_ms = 0.0
    first_failure: dict[str, Any] | None = None

    with tempfile.TemporaryDirectory(prefix="pcs-v06-replay-") as tmp:
        root = Path(tmp)
        artifact_paths: dict[str, Path] = {}
        for artifact_id, raw in artifacts.items():
            path = root / hashlib.sha256(artifact_id.encode("utf-8")).hexdigest()
            path.write_bytes(raw)
            artifact_paths[artifact_id] = path

        candidate_by_id = {
            candidate["evidence_id"]: candidate
            for candidate in schedule["candidates"]
        }

        for execution_index, evidence_id in enumerate(schedule["execution_order"]):
            evidence = evidence_by_id[evidence_id]
            candidate = candidate_by_id[evidence_id]
            wall_start = time.perf_counter_ns()
            cpu_start = time.process_time_ns()
            result = _replay_one(evidence, artifact_paths)
            cpu_ns = time.process_time_ns() - cpu_start
            wall_ns = time.perf_counter_ns() - wall_start
            duration_ms = wall_ns / 1_000_000.0
            cumulative_ms += duration_ms

            result_by_id[evidence_id] = result
            replayed = deepcopy(evidence)
            replayed["kind"] = result["kind"]
            replayed["outcome"] = result["outcome"]
            replay_map[evidence_id] = replayed

            if result["outcome"] == "PASS":
                failure_class = None
            elif result["outcome"] == "UNVERIFIED":
                failure_class = "unsupported_external"
            elif isinstance(result.get("details"), dict) and result["details"].get("error"):
                failure_class = f"exception:{result['details']['error']}"
            else:
                failure_class = "predicate_false"

            telemetry_checks.append(
                {
                    "evidence_id": _telemetry_evidence_id(evidence_id),
                    "check_type": evidence["check_spec"]["type"],
                    "original_index": candidate["original_index"],
                    "execution_index": execution_index,
                    "artifact_count": candidate["artifact_count"],
                    "input_bytes": candidate["input_bytes"],
                    "outcome": result["outcome"],
                    "failure_class": failure_class,
                    "duration_ms": duration_ms,
                    "cpu_ms": cpu_ns / 1_000_000.0,
                }
            )
            if first_failure is None and result["outcome"] == "FAIL":
                first_failure = {
                    "evidence_id": _telemetry_evidence_id(evidence_id),
                    "execution_index": execution_index,
                    "time_to_first_failure_ms": cumulative_ms,
                }

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
            if (
                evidence["check_spec"]["type"] in CERTIFIED_BUILTIN_CHECK_TYPES_V06
                and evidence["checker"] != certificate["checker_version"]
            ):
                errors.append(
                    f"evidence {evidence['id']} checker differs from certificate checker_version"
                )

    # Preserve certificate order for all semantic consumers regardless of execution order.
    evidence_results = [
        result_by_id[evidence["id"]]
        for evidence in certificate["evidence"]
    ]

    telemetry = {
        "format": TELEMETRY_FORMAT_V06,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "certificate_semantic_hash": certificate["semantic_hash"],
        "checker_version": certificate["checker_version"],
        "scheduler": {
            "format": schedule["format"],
            "requested_strategy": schedule["requested_strategy"],
            "strategy": schedule["strategy"],
            "fallback_reason": schedule["fallback_reason"],
            "history_runs": schedule["history_runs"],
            "bandit_alpha": schedule["bandit_alpha"],
            "bandit_readiness": schedule["bandit_readiness"],
            "all_mandatory_checks_execute": schedule["all_mandatory_checks_execute"],
            "scientific_verdict_uses_scheduler": schedule[
                "scientific_verdict_uses_scheduler"
            ],
            "execution_order": [
                _telemetry_evidence_id(x)
                for x in schedule["execution_order"]
            ],
            "shadow_bandit_order": (
                [
                    _telemetry_evidence_id(x)
                    for x in schedule["shadow_bandit_order"]
                ]
                if schedule["shadow_bandit_order"] is not None
                else None
            ),
        },
        "checks": telemetry_checks,
        "summary": {
            "check_count": len(telemetry_checks),
            "fail_count": sum(1 for x in telemetry_checks if x["outcome"] == "FAIL"),
            "unverified_count": sum(
                1 for x in telemetry_checks if x["outcome"] == "UNVERIFIED"
            ),
            "total_duration_ms": sum(x["duration_ms"] for x in telemetry_checks),
            "total_cpu_ms": sum(x["cpu_ms"] for x in telemetry_checks),
            "first_failure": first_failure,
        },
    }
    if telemetry_sink is not None:
        telemetry_sink.clear()
        telemetry_sink.update(telemetry)

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
        "scheduler": {
            "format": schedule["format"],
            "requested_strategy": schedule["requested_strategy"],
            "strategy": schedule["strategy"],
            "fallback_reason": schedule["fallback_reason"],
            "history_runs": schedule["history_runs"],
            "bandit_alpha": schedule["bandit_alpha"],
            "bandit_readiness": schedule["bandit_readiness"],
            "all_mandatory_checks_execute": schedule["all_mandatory_checks_execute"],
            "scientific_verdict_uses_scheduler": schedule[
                "scientific_verdict_uses_scheduler"
            ],
            "execution_order": schedule["execution_order"],
            "shadow_bandit_order": schedule["shadow_bandit_order"],
        },
    }
