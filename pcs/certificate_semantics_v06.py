from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from .decision import assess_claim
from .check_registry_v06 import (
    CERTIFIED_BUILTIN_CHECK_TYPES_V06,
    EXTERNAL_CHECK_KIND_BY_TYPE_V06,
)
from .external_validator_v06 import (
    external_validator_artifact_ids_v06,
    is_signed_external_validator_spec_v06,
    normalize_external_validator_check_spec_v06,
)
from .schema_validation import SchemaValidationError, validate_v06_certificate_shape
from .numeric_contract_v06 import (
    V06NumericContractError,
    canonical_nonnegative_number_text_v06,
)


class V06CertificateSemanticsError(ValueError):
    pass


_BUILTIN_CHECK_TYPES = set(CERTIFIED_BUILTIN_CHECK_TYPES_V06)
_EXTERNAL_KIND_BY_TYPE = dict(EXTERNAL_CHECK_KIND_BY_TYPE_V06)


def _unique_id_map(items: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        ident = item["id"]
        if ident in out:
            raise V06CertificateSemanticsError(f"duplicate {label} id: {ident}")
        out[ident] = item
    return out


def _safe_relative_path(value: str, *, label: str) -> None:
    if "\\" in value:
        raise V06CertificateSemanticsError(f"{label} uses backslash: {value!r}")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or value.endswith("/")
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise V06CertificateSemanticsError(f"{label} is not a canonical relative path: {value!r}")


def _validate_predicate_numeric_contract_v06(
    predicate: dict[str, Any],
    *,
    label: str,
) -> None:
    predicate_type = predicate.get("type")
    if predicate_type == "pkpd_peak_concentration_threshold":
        keys = ("upper_bound",)
    elif predicate_type == "pkpd_reference_match":
        keys = ("rel_tol", "abs_tol")
    else:
        return
    for key in keys:
        value = predicate.get(key)
        try:
            canonical = canonical_nonnegative_number_text_v06(
                value,
                label=f"{label}.{key}",
            )
        except V06NumericContractError as exc:
            raise V06CertificateSemanticsError(str(exc)) from exc
        if canonical != value:
            raise V06CertificateSemanticsError(
                f"{label}.{key} must use canonical numeric text {canonical!r}"
            )


def predicate_from_check_spec(check_spec: dict[str, Any]) -> dict[str, Any]:
    check_type = check_spec["type"]
    if check_type in _BUILTIN_CHECK_TYPES:
        return dict(check_spec)
    if check_type in _EXTERNAL_KIND_BY_TYPE:
        return dict(check_spec["predicate"])
    raise V06CertificateSemanticsError(f"unsupported v0.6 check type: {check_type!r}")


def artifact_ids_from_predicate(predicate: dict[str, Any]) -> list[str]:
    predicate_type = predicate["type"]
    if predicate_type == "csv_disjoint":
        return [predicate["left_artifact"], predicate["right_artifact"]]
    if predicate_type == "pkpd_contract":
        return [predicate["model_artifact"]]
    if predicate_type in {"pkpd_reference_match", "pkpd_peak_concentration_threshold"}:
        return [predicate["model_artifact"], predicate["output_artifact"]]
    return []


def _validate_evidence_kind(evidence: dict[str, Any]) -> None:
    check_type = evidence["check_spec"]["type"]
    if check_type in _BUILTIN_CHECK_TYPES:
        expected_kind = "computational_test"
    else:
        expected_kind = _EXTERNAL_KIND_BY_TYPE.get(check_type)
    if expected_kind is None:
        raise V06CertificateSemanticsError(
            f"evidence {evidence['id']} has unsupported check type {check_type!r}"
        )
    if evidence["kind"] != expected_kind:
        raise V06CertificateSemanticsError(
            f"evidence {evidence['id']} kind {evidence['kind']!r} "
            f"does not match check type {check_type!r} ({expected_kind!r})"
        )


def workflow_summary_v06(
    workflow: dict[str, Any],
    artifact_ids: set[str],
) -> dict[str, Any]:
    nodes = workflow["nodes"]
    node_map = _unique_id_map(nodes, "workflow node")
    producers: dict[str, str] = {}
    consumers: dict[str, list[str]] = {}
    edges: dict[str, set[str]] = {node_id: set() for node_id in node_map}

    for node in nodes:
        for artifact_id in node["inputs"] + node["outputs"]:
            if artifact_id not in artifact_ids:
                raise V06CertificateSemanticsError(
                    f"workflow node {node['id']} references unknown artifact {artifact_id}"
                )
        for artifact_id in node["outputs"]:
            other = producers.get(artifact_id)
            if other is not None:
                raise V06CertificateSemanticsError(
                    f"artifact {artifact_id} has multiple workflow producers: "
                    f"{other}, {node['id']}"
                )
            producers[artifact_id] = node["id"]
        for artifact_id in node["inputs"]:
            consumers.setdefault(artifact_id, []).append(node["id"])

    for artifact_id, producer in producers.items():
        for consumer in consumers.get(artifact_id, []):
            if consumer != producer:
                edges[producer].add(consumer)

    temporary: set[str] = set()
    permanent: set[str] = set()
    order: list[str] = []

    def visit(node_id: str) -> None:
        if node_id in permanent:
            return
        if node_id in temporary:
            raise V06CertificateSemanticsError(
                f"workflow cycle detected at node {node_id}"
            )
        temporary.add(node_id)
        for successor in sorted(edges[node_id]):
            visit(successor)
        temporary.remove(node_id)
        permanent.add(node_id)
        order.append(node_id)

    for node_id in sorted(node_map):
        visit(node_id)
    order.reverse()
    return {"node_count": len(nodes), "topological_order": order}


def validate_certificate_semantics_v06(certificate: dict[str, Any]) -> None:
    """Validate cross-object semantic invariants after JSON Schema validation.

    This function checks structure-to-structure consistency only. It does not
    establish that recorded evidence outcomes are scientifically true; domain
    replay remains a separate verifier boundary.
    """
    try:
        validate_v06_certificate_shape(certificate)
    except SchemaValidationError as exc:
        raise V06CertificateSemanticsError(str(exc)) from exc

    assumptions = certificate["assumptions"]
    claims = certificate["claims"]
    artifacts = certificate["artifacts"]
    evidence = certificate["evidence"]

    assumption_map = _unique_id_map(assumptions, "assumption")
    claim_map = _unique_id_map(claims, "claim")
    artifact_map = _unique_id_map(artifacts, "artifact")
    evidence_map = _unique_id_map(evidence, "evidence")

    for artifact in artifacts:
        _safe_relative_path(artifact["path"], label=f"artifact {artifact['id']} path")
        if "source_path" in artifact:
            _safe_relative_path(
                artifact["source_path"],
                label=f"artifact {artifact['id']} source_path",
            )

    for assumption in assumptions:
        for claim_id in assumption["scope"]:
            claim = claim_map.get(claim_id)
            if claim is None:
                raise V06CertificateSemanticsError(
                    f"assumption {assumption['id']} scopes unknown claim {claim_id}"
                )
            if assumption["id"] not in claim["assumptions"]:
                raise V06CertificateSemanticsError(
                    f"assumption {assumption['id']} scopes claim {claim_id}, "
                    "but the claim does not reference the assumption"
                )

    for evidence_item in evidence:
        _validate_evidence_kind(evidence_item)
        derived_predicate = predicate_from_check_spec(evidence_item["check_spec"])
        _validate_predicate_numeric_contract_v06(
            derived_predicate,
            label=f"evidence {evidence_item['id']} predicate",
        )
        if evidence_item["predicate"] != derived_predicate:
            raise V06CertificateSemanticsError(
                f"evidence {evidence_item['id']} predicate differs from its check specification"
            )

        expected_artifact_ids = artifact_ids_from_predicate(derived_predicate)
        check_spec = evidence_item["check_spec"]
        check_type = check_spec["type"]
        if check_type in _BUILTIN_CHECK_TYPES:
            if evidence_item["artifact_ids"] != expected_artifact_ids:
                raise V06CertificateSemanticsError(
                    f"evidence {evidence_item['id']} artifact_ids differ from its built-in predicate"
                )
        elif is_signed_external_validator_spec_v06(check_spec):
            try:
                normalized_external = normalize_external_validator_check_spec_v06(
                    check_spec
                )
                external_artifacts = external_validator_artifact_ids_v06(
                    normalized_external
                )
            except ValueError as exc:
                raise V06CertificateSemanticsError(
                    f"evidence {evidence_item['id']} has invalid signed-validator contract: {exc}"
                ) from exc
            if evidence_item["artifact_ids"] != external_artifacts:
                raise V06CertificateSemanticsError(
                    f"evidence {evidence_item['id']} artifact_ids differ from its signed-validator contract"
                )
            if evidence_item["checker"] != normalized_external["validator"]:
                raise V06CertificateSemanticsError(
                    f"evidence {evidence_item['id']} checker differs from its external validator identity"
                )

        for artifact_id in evidence_item["artifact_ids"]:
            if artifact_id not in artifact_map:
                raise V06CertificateSemanticsError(
                    f"evidence {evidence_item['id']} references unknown artifact {artifact_id}"
                )

        for claim_id in evidence_item["claim_ids"]:
            claim = claim_map.get(claim_id)
            if claim is None:
                raise V06CertificateSemanticsError(
                    f"evidence {evidence_item['id']} references unknown claim {claim_id}"
                )
            if evidence_item["id"] not in claim["required_evidence"]:
                raise V06CertificateSemanticsError(
                    f"evidence {evidence_item['id']} declares support for claim {claim_id}, "
                    "but the claim does not require that evidence"
                )

    for claim in claims:
        _validate_predicate_numeric_contract_v06(
            claim["predicate"],
            label=f"claim {claim['id']} predicate",
        )
        for assumption_id in claim["assumptions"]:
            assumption = assumption_map.get(assumption_id)
            if assumption is None:
                raise V06CertificateSemanticsError(
                    f"claim {claim['id']} references unknown assumption {assumption_id}"
                )
            if claim["id"] not in assumption["scope"]:
                raise V06CertificateSemanticsError(
                    f"claim {claim['id']} references assumption {assumption_id}, "
                    "but the assumption scope does not include the claim"
                )

        for evidence_id in claim["required_evidence"]:
            required = evidence_map.get(evidence_id)
            if required is None:
                raise V06CertificateSemanticsError(
                    f"claim {claim['id']} references unknown evidence {evidence_id}"
                )
            if claim["id"] not in required["claim_ids"]:
                raise V06CertificateSemanticsError(
                    f"claim {claim['id']} requires evidence {evidence_id}, "
                    "but the evidence does not declare support for the claim"
                )
            if required["predicate"] != claim["predicate"]:
                raise V06CertificateSemanticsError(
                    f"claim {claim['id']} and required evidence {evidence_id} "
                    "do not carry the exact same predicate"
                )

        expected_assessment = assess_claim(claim, evidence_map)
        if claim["assessment"] != expected_assessment:
            raise V06CertificateSemanticsError(
                f"claim {claim['id']} assessment mismatch: "
                f"recorded={claim['assessment']!r} expected={expected_assessment!r}"
            )

        for artifact_id in artifact_ids_from_predicate(claim["predicate"]):
            if artifact_id not in artifact_map:
                raise V06CertificateSemanticsError(
                    f"claim {claim['id']} predicate references unknown artifact {artifact_id}"
                )

    environment = certificate.get("environment")
    if environment is not None:
        for artifact_id in environment["source_artifact_ids"]:
            if artifact_id not in artifact_map:
                raise V06CertificateSemanticsError(
                    f"environment references unknown artifact {artifact_id}"
                )

    expected_workflow_summary = workflow_summary_v06(
        certificate["workflow"],
        set(artifact_map),
    )
    if certificate["workflow_summary"] != expected_workflow_summary:
        raise V06CertificateSemanticsError(
            "workflow_summary does not equal the recomputed workflow DAG summary"
        )
