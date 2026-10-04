from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical_json import canonicalize_jcs_bytes
from .check_registry_v06 import (
    CERTIFIED_BUILTIN_CHECK_TYPES_V06,
    EXTERNAL_CHECK_KIND_BY_TYPE_V06,
    check_artifact_references_v06,
    formal_target_for_check_v06,
    predicate_from_manifest_check_v06,
)
from .discover_v06 import (
    DISCOVERY_FORMAT_V06,
    MANIFEST_DRAFT_FORMAT_V06,
    V06DiscoveryError,
    discover_project_v06,
)
from .external_validator_v06 import (
    EXTERNAL_VALIDATOR_CHECK_TYPES_V06,
    V06ExternalValidatorError,
    external_validator_adapter_missing_fields_v06,
    external_validator_artifact_ids_v06,
    normalize_external_validator_check_spec_v06,
    verify_external_validator_receipt_v06,
)
from .jsonio import StrictJSONError, strict_json_load, strict_json_loads
from .numeric_contract_v06 import V06NumericContractError
from .schema_validation import SchemaValidationError, validate_manifest_shape


PROOF_TRANSLATION_FORMAT_V06 = "pcs-proof-translation-v1"
PROOF_PROPOSALS_FORMAT_V06 = "pcs-proof-proposals-v1"
PROOF_OBLIGATION_GRAPH_FORMAT_V06 = "pcs-proof-obligation-graph-v1"
PROOF_TRANSLATION_COMPILER_V06 = "pcs-proof-translation-compiler/0.2"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class V06ProofTranslationError(ValueError):
    pass


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _safe_id(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise V06ProofTranslationError(f"unsafe or missing {label}: {value!r}")
    return value


def _confidence(value: Any, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V06ProofTranslationError(f"{label} confidence must be numeric")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise V06ProofTranslationError(f"{label} confidence must be finite in [0,1]")
    return result


def _snapshot_bytes(root: Path, item: Mapping[str, Any]) -> bytes:
    path = (root / str(item["path"])).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise V06ProofTranslationError(
            f"artifact path escapes project root: {item.get('path')!r}"
        ) from exc
    if path.is_symlink() or not path.is_file():
        raise V06ProofTranslationError(
            f"grounding artifact is missing or unsafe: {item.get('path')!r}"
        )
    raw = path.read_bytes()
    actual_hash = hashlib.sha256(raw).hexdigest()
    if actual_hash != item.get("sha256") or len(raw) != item.get("size"):
        raise V06ProofTranslationError(
            f"artifact changed during proof translation: {item.get('path')!r}"
        )
    return raw


def _strict_json_snapshot(root: Path, item: Mapping[str, Any]) -> dict[str, Any] | None:
    raw = _snapshot_bytes(root, item)
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, StrictJSONError):
        return None
    return value if isinstance(value, dict) else None


def _csv_header_snapshot(root: Path, item: Mapping[str, Any]) -> list[str] | None:
    raw = _snapshot_bytes(root, item)
    try:
        text = raw.decode("utf-8")
        row = next(csv.reader(io.StringIO(text, newline="")), None)
    except (UnicodeDecodeError, csv.Error):
        return None
    if not row:
        return None
    return [str(x).strip() for x in row]


def _restricted_pkpd_model_object(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("model_type") == "one_compartment_iv_bolus"
        and isinstance(value.get("pd"), Mapping)
        and value["pd"].get("model_type") == "direct_emax"
        and all(key in value for key in ("dose", "volume", "clearance"))
    )


def _ground_check_against_project(
    check: Mapping[str, Any],
    *,
    declared_artifact_ids: Sequence[str],
    inventory: Mapping[str, Mapping[str, Any]],
    project_root: Path,
) -> dict[str, Any]:
    check_type = check.get("type")
    checked_artifacts: list[str] = []
    facts: list[str] = []

    def item(artifact_id: str) -> Mapping[str, Any]:
        value = inventory.get(artifact_id)
        if value is None:
            raise V06ProofTranslationError(
                f"grounding references unknown artifact {artifact_id!r}"
            )
        return value

    if check_type == "reaction_balance":
        matches = []
        for artifact_id in declared_artifact_ids:
            obj = _strict_json_snapshot(project_root, item(artifact_id))
            if (
                isinstance(obj, Mapping)
                and obj.get("reactants") == check.get("reactants")
                and obj.get("products") == check.get("products")
            ):
                matches.append(artifact_id)
        if not matches:
            raise V06ProofTranslationError(
                "reaction_balance proposal is not grounded in a referenced JSON artifact with exact reactants/products"
            )
        checked_artifacts.extend(matches)
        facts.append("exact reaction arrays re-derived from project JSON")

    elif check_type == "unit_compatible":
        matches = []
        for artifact_id in declared_artifact_ids:
            obj = _strict_json_snapshot(project_root, item(artifact_id))
            if (
                isinstance(obj, Mapping)
                and obj.get("left_unit") == check.get("left_unit")
                and obj.get("right_unit") == check.get("right_unit")
            ):
                matches.append(artifact_id)
        if not matches:
            raise V06ProofTranslationError(
                "unit_compatible proposal is not grounded in a referenced JSON artifact with exact left_unit/right_unit"
            )
        checked_artifacts.extend(matches)
        facts.append("exact unit strings re-derived from project JSON")

    elif check_type == "csv_disjoint":
        left_id = str(check["left_artifact"])
        right_id = str(check["right_artifact"])
        key = check.get("key")
        left_header = _csv_header_snapshot(project_root, item(left_id))
        right_header = _csv_header_snapshot(project_root, item(right_id))
        if (
            not isinstance(key, str)
            or left_header is None
            or right_header is None
            or key not in left_header
            or key not in right_header
        ):
            raise V06ProofTranslationError(
                "csv_disjoint proposal key is not present in both referenced CSV headers"
            )
        checked_artifacts.extend([left_id, right_id])
        facts.append(f"CSV key {key!r} re-derived from both project headers")

    elif check_type == "pkpd_contract":
        model_id = str(check["model_artifact"])
        model = _strict_json_snapshot(project_root, item(model_id))
        if not _restricted_pkpd_model_object(model):
            raise V06ProofTranslationError(
                "pkpd_contract proposal does not reference a supported restricted PK/PD model artifact"
            )
        checked_artifacts.append(model_id)
        facts.append("restricted PK/PD model shape re-derived from project JSON")

    elif check_type == "pkpd_reference_match":
        model_id = str(check["model_artifact"])
        output_id = str(check["output_artifact"])
        model = _strict_json_snapshot(project_root, item(model_id))
        header = _csv_header_snapshot(project_root, item(output_id))
        required = {
            str(check.get("time_column", "time")),
            str(check.get("concentration_column", "concentration")),
            str(check.get("effect_column", "effect")),
        }
        if not _restricted_pkpd_model_object(model):
            raise V06ProofTranslationError(
                "pkpd_reference_match proposal does not reference a supported restricted PK/PD model artifact"
            )
        if header is None or not required.issubset(set(header)):
            raise V06ProofTranslationError(
                "pkpd_reference_match proposal columns are not present in the referenced output CSV"
            )
        checked_artifacts.extend([model_id, output_id])
        facts.append("restricted PK/PD model and output columns re-derived from project artifacts")

    elif check_type == "pkpd_peak_concentration_threshold":
        model_id = str(check["model_artifact"])
        output_id = str(check["output_artifact"])
        model = _strict_json_snapshot(project_root, item(model_id))
        header = _csv_header_snapshot(project_root, item(output_id))
        concentration_column = str(check.get("concentration_column", "concentration"))
        unit = check.get("unit")
        if not _restricted_pkpd_model_object(model):
            raise V06ProofTranslationError(
                "pkpd_peak_concentration_threshold proposal does not reference a supported restricted PK/PD model artifact"
            )
        if not isinstance(unit, str) or model.get("concentration_unit") != unit:
            raise V06ProofTranslationError(
                "pkpd_peak_concentration_threshold unit does not match the model-declared concentration unit"
            )
        if header is None or concentration_column not in header:
            raise V06ProofTranslationError(
                "pkpd_peak_concentration_threshold concentration column is not present in the referenced output CSV"
            )
        checked_artifacts.extend([model_id, output_id])
        facts.append(
            "restricted PK/PD model, declared concentration unit, and output concentration column re-derived from project artifacts"
        )

    else:
        raise V06ProofTranslationError(
            f"no deterministic grounding adapter for check type {check_type!r}"
        )

    return {
        "status": "GROUNDED",
        "artifact_ids": sorted(set(checked_artifacts)),
        "facts": facts,
    }


def _artifact_entry(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": item["artifact_id"],
        "path": item["path"],
        "role": item["role"],
        "media_type": item["media_type"],
        "metadata": {
            "pcs_discovery_sha256": item["sha256"],
            "pcs_discovery_size": item["size"],
        },
    }


def _proposal_assumptions(proposal: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw: list[Any] = []
    if isinstance(proposal.get("assumption"), Mapping):
        raw.append(proposal["assumption"])
    values = proposal.get("assumptions")
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes, bytearray)):
        raw.extend(values)

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, value in enumerate(raw):
        if not isinstance(value, Mapping):
            raise V06ProofTranslationError(
                f"proposal assumption {index} must be an object"
            )
        assumption = _json_clone(value)
        ident = _safe_id(assumption.get("id"), label="assumption id")
        if ident in seen:
            raise V06ProofTranslationError(f"duplicate proposal assumption id: {ident}")
        seen.add(ident)
        statement = assumption.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            raise V06ProofTranslationError(
                f"assumption {ident} requires a non-empty statement"
            )
        out.append(assumption)
    return out


def _normalized_predicate(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    out = _json_clone(value)
    if out.get("type") == "pkpd_reference_match":
        from .numeric_contract_v06 import canonical_nonnegative_number_text_v06

        out["rel_tol"] = canonical_nonnegative_number_text_v06(
            out.get("rel_tol", 1e-9),
            label="proposal predicate rel_tol",
        )
        out["abs_tol"] = canonical_nonnegative_number_text_v06(
            out.get("abs_tol", 1e-12),
            label="proposal predicate abs_tol",
        )
    return out



_REPAIR_POLICY_BY_KIND: dict[str, dict[str, Any]] = {
    "PROVIDE_TYPED_PREDICATE": {
        "action": "propose_typed_predicate",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "CHECK_TYPE_REQUIRED": {
        "action": "revise_check_type",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "PROVIDE_EXTERNAL_VALIDATOR": {
        "action": "attach_external_validator",
        "actor": "scientist_or_engineer",
        "machine_assisted": True,
    },
    "IMPLEMENT_CERTIFIED_CHECKER": {
        "action": "implement_certified_checker",
        "actor": "pcs_engineer",
        "machine_assisted": True,
    },
    "INVALID_CHECK_SPEC": {
        "action": "repair_check_spec",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "INVALID_ARTIFACT_GROUNDING": {
        "action": "repair_artifact_grounding",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "GROUND_ARTIFACTS": {
        "action": "select_grounded_artifacts",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "GROUND_PREDICATE_IN_PROJECT_BYTES": {
        "action": "revise_predicate_from_project_bytes",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "CLAIM_REQUIRED": {
        "action": "supply_claim",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "INVALID_CLAIM": {
        "action": "repair_claim",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "CLAIM_STATEMENT_REQUIRED": {
        "action": "supply_claim_statement",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "CLAIM_EVIDENCE_LINK_MISMATCH": {
        "action": "repair_claim_evidence_links",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "ASSUMPTION_LINK_MISMATCH": {
        "action": "repair_assumption_links",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "INVALID_CLAIM_KIND": {
        "action": "choose_supported_claim_kind",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "PREDICATE_NUMERIC_CONTRACT": {
        "action": "repair_numeric_contract",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "PREDICATE_CHECK_MISMATCH": {
        "action": "accept_compiler_predicate_or_revise_check",
        "actor": "proposer",
        "machine_assisted": True,
    },
    "CONFIDENCE_BELOW_SELECTION_THRESHOLD": {
        "action": "human_review_low_confidence",
        "actor": "human",
        "machine_assisted": False,
    },
    "HUMAN_CONFIRMATION_REQUIRED": {
        "action": "human_confirm_translation",
        "actor": "human",
        "machine_assisted": False,
    },
    "ASSUMPTION_REVIEW_REQUIRED": {
        "action": "human_review_assumption",
        "actor": "human",
        "machine_assisted": False,
    },
    "EXTERNAL_VALIDATOR_TRUST_REVIEW_REQUIRED": {
        "action": "human_review_external_validator_trust",
        "actor": "human",
        "machine_assisted": False,
    },
}


def _repair_for_obligation(
    kind: str,
    *,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    policy = _REPAIR_POLICY_BY_KIND.get(kind)
    if policy is None:
        return None
    repair = _json_clone(policy)
    repair["can_set_authoritative"] = False
    if details:
        repair["context"] = _json_clone(details)
    return repair


def _obligation(
    proposal_id: str,
    kind: str,
    message: str,
    *,
    blocking: bool,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repair = _repair_for_obligation(kind, details=details)
    seed = canonicalize_jcs_bytes(
        {
            "proposal_id": proposal_id,
            "kind": kind,
            "message": message,
            "blocking": blocking,
            "details": dict(details or {}),
        }
    )
    suffix = hashlib.sha256(seed).hexdigest()[:12]
    out: dict[str, Any] = {
        "id": f"O_{proposal_id}_{suffix}",
        "proposal_id": proposal_id,
        "kind": kind,
        "blocking": blocking,
        "message": message,
    }
    if details:
        out["details"] = dict(details)
    if repair is not None:
        out["repair"] = repair
    return out


def _discovery_proposals(discovery: Mapping[str, Any]) -> list[dict[str, Any]]:
    proposals: list[dict[str, Any]] = []
    for rec in discovery.get("recommendations", []):
        if not isinstance(rec, Mapping):
            continue
        proposal = _json_clone(rec)
        proposal["proposal_source"] = {
            "kind": "deterministic_discovery",
            "name": str(rec.get("detector", "pcs-discovery")),
            "version": DISCOVERY_FORMAT_V06,
        }
        proposal["finding"] = str(rec.get("reason", ""))
        if "assumption" in proposal and "assumptions" not in proposal:
            proposal["assumptions"] = [proposal.pop("assumption")]
        proposals.append(proposal)
    return proposals


def _load_external_proposal_file(
    path: str | Path,
    *,
    expected_inventory_commitment: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    proposal_path = Path(path).resolve()
    try:
        value = strict_json_load(proposal_path)
    except (OSError, StrictJSONError) as exc:
        raise V06ProofTranslationError(
            f"cannot load proof proposal file {proposal_path}: {exc}"
        ) from exc
    if not isinstance(value, Mapping):
        raise V06ProofTranslationError("proof proposal file root must be an object")
    if value.get("format") != PROOF_PROPOSALS_FORMAT_V06:
        raise V06ProofTranslationError(
            f"unsupported proof proposal format: {value.get('format')!r}"
        )
    commitment = value.get("inventory_commitment_sha256")
    if commitment != expected_inventory_commitment:
        raise V06ProofTranslationError(
            "external proposal inventory commitment does not match the current project"
        )
    proposer = value.get("proposer")
    if not isinstance(proposer, Mapping):
        raise V06ProofTranslationError("external proposal file requires proposer metadata")
    name = proposer.get("name")
    if not isinstance(name, str) or not name.strip():
        raise V06ProofTranslationError("external proposer requires a non-empty name")

    raw_proposals = value.get("proposals")
    if not isinstance(raw_proposals, list):
        raise V06ProofTranslationError("external proposal file proposals must be an array")
    proposals: list[dict[str, Any]] = []
    for item in raw_proposals:
        if not isinstance(item, Mapping):
            raise V06ProofTranslationError("external proposal entries must be objects")
        proposal = _json_clone(item)
        proposal["proposal_source"] = {
            "kind": "external_model",
            "name": name,
            "version": proposer.get("version"),
            "model_family": proposer.get("model_family"),
        }
        proposals.append(proposal)
    return {
        "path": str(proposal_path),
        "proposer": _json_clone(proposer),
        "proposal_count": len(proposals),
    }, proposals


def _compile_external_validator_proposal(
    proposal: Mapping[str, Any],
    *,
    ident: str,
    confidence: float,
    confidence_threshold: float,
    source: Mapping[str, Any],
    claim_raw: Any,
    check: dict[str, Any],
    inventory: Mapping[str, Mapping[str, Any]],
    project_root: Path,
    result: dict[str, Any],
) -> dict[str, Any]:
    check_type = str(check.get("type"))
    missing_adapter = external_validator_adapter_missing_fields_v06(check)
    if missing_adapter:
        result["status"] = "EXTERNAL_VALIDATOR_REQUIRED"
        result["check"] = check
        result["obligations"].append(
            _obligation(
                ident,
                "PROVIDE_EXTERNAL_VALIDATOR",
                (
                    "This external validation claim needs a signed, hash-bound "
                    "validator receipt before PCS can replay it."
                ),
                blocking=True,
                details={
                    "check_type": check_type,
                    "evidence_kind": EXTERNAL_CHECK_KIND_BY_TYPE_V06[check_type],
                    "missing_adapter_fields": missing_adapter,
                },
            )
        )
        return result

    try:
        check_id = _safe_id(
            check.get("id"),
            label=f"proposal {ident} check id",
        )
        spec = normalize_external_validator_check_spec_v06(check)
        check_refs = external_validator_artifact_ids_v06(spec)
    except (V06ExternalValidatorError, V06ProofTranslationError) as exc:
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["check"] = check
        result["obligations"].append(
            _obligation(
                ident,
                "INVALID_CHECK_SPEC",
                f"The signed external-validator contract is invalid: {exc}",
                blocking=True,
            )
        )
        return result

    declared_artifacts = proposal.get("artifact_ids", [])
    if not isinstance(declared_artifacts, list) or not all(
        isinstance(x, str) for x in declared_artifacts
    ):
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["check"] = check
        result["obligations"].append(
            _obligation(
                ident,
                "INVALID_ARTIFACT_GROUNDING",
                "proposal artifact_ids must be an array of artifact IDs",
                blocking=True,
            )
        )
        return result

    artifact_ids = sorted(set(declared_artifacts) | set(check_refs))
    missing_refs = sorted(
        artifact_id
        for artifact_id in artifact_ids
        if artifact_id not in inventory
    )
    if missing_refs:
        result["status"] = "REJECTED_UNGROUNDED"
        result["check"] = check
        result["artifact_ids"] = artifact_ids
        result["obligations"].append(
            _obligation(
                ident,
                "GROUND_ARTIFACTS",
                (
                    "The signed validator contract references artifacts outside "
                    "the current discovery snapshot."
                ),
                blocking=True,
                details={"missing_artifact_ids": missing_refs},
            )
        )
        return result

    try:
        bound_bytes = {
            artifact_id: _snapshot_bytes(project_root, inventory[artifact_id])
            for artifact_id in check_refs
        }
    except V06ProofTranslationError as exc:
        result["status"] = "REJECTED_UNGROUNDED"
        result["check"] = check
        result["artifact_ids"] = artifact_ids
        result["obligations"].append(
            _obligation(
                ident,
                "PROVIDE_EXTERNAL_VALIDATOR",
                str(exc),
                blocking=True,
                details={"check_type": check_type},
            )
        )
        return result

    receipt = verify_external_validator_receipt_v06(spec, bound_bytes)
    if receipt.get("valid") is not True:
        result["status"] = "REJECTED_UNGROUNDED"
        result["check"] = check
        result["artifact_ids"] = artifact_ids
        result["grounding"] = {
            "status": "FAILED",
            "adapter": "signed_external_validator_receipt",
            "errors": list(receipt.get("errors", [])),
        }
        result["obligations"].append(
            _obligation(
                ident,
                "PROVIDE_EXTERNAL_VALIDATOR",
                (
                    "The supplied signed external-validator receipt did not "
                    "verify against the pinned key/predicate/artifact bytes."
                ),
                blocking=True,
                details={
                    "check_type": check_type,
                    "errors": list(receipt.get("errors", [])),
                },
            )
        )
        return result

    if not isinstance(claim_raw, Mapping):
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["check"] = check
        result["artifact_ids"] = artifact_ids
        result["obligations"].append(
            _obligation(
                ident,
                "CLAIM_REQUIRED",
                "A signed external validator requires a scoped claim object.",
                blocking=True,
            )
        )
        return result

    claim = _json_clone(claim_raw)
    try:
        claim_id = _safe_id(
            claim.get("id"),
            label=f"proposal {ident} claim id",
        )
        assumptions = _proposal_assumptions(proposal)
    except V06ProofTranslationError as exc:
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["check"] = check
        result["artifact_ids"] = artifact_ids
        result["obligations"].append(
            _obligation(
                ident,
                "INVALID_CLAIM",
                str(exc),
                blocking=True,
            )
        )
        return result

    statement = claim.get("statement")
    if not isinstance(statement, str) or not statement.strip():
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["obligations"].append(
            _obligation(
                ident,
                "CLAIM_STATEMENT_REQUIRED",
                "The proposed claim requires a non-empty scientific statement.",
                blocking=True,
            )
        )
        return result

    check_claim_ids = check.get("claim_ids")
    if check_claim_ids is None:
        check["claim_ids"] = [claim_id]
    elif (
        not isinstance(check_claim_ids, list)
        or not all(isinstance(x, str) for x in check_claim_ids)
        or sorted(check_claim_ids) != [claim_id]
    ):
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["obligations"].append(
            _obligation(
                ident,
                "CLAIM_EVIDENCE_LINK_MISMATCH",
                "The check claim_ids must contain exactly the proposed claim.",
                blocking=True,
            )
        )
        return result

    assumption_ids = [assumption["id"] for assumption in assumptions]
    provided_assumption_ids = claim.get("assumptions")
    if provided_assumption_ids is None:
        claim["assumptions"] = assumption_ids
    elif (
        not isinstance(provided_assumption_ids, list)
        or sorted(provided_assumption_ids) != sorted(assumption_ids)
    ):
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["obligations"].append(
            _obligation(
                ident,
                "ASSUMPTION_LINK_MISMATCH",
                (
                    "Claim assumption IDs do not exactly match the supplied "
                    "assumption objects."
                ),
                blocking=True,
            )
        )
        return result

    required = claim.get("required_evidence")
    if required is None:
        claim["required_evidence"] = [check_id]
    elif (
        not isinstance(required, list)
        or not all(isinstance(x, str) for x in required)
        or sorted(required) != [check_id]
    ):
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["obligations"].append(
            _obligation(
                ident,
                "CLAIM_EVIDENCE_LINK_MISMATCH",
                "Claim required_evidence must contain exactly the proposed check.",
                blocking=True,
            )
        )
        return result

    claim_kind = claim.get("kind", "empirical")
    if claim_kind not in {"empirical", "mixed"}:
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["obligations"].append(
            _obligation(
                ident,
                "INVALID_CLAIM_KIND",
                (
                    "Signed empirical/statistical validator evidence may support "
                    "only empirical or mixed claims."
                ),
                blocking=True,
            )
        )
        return result
    claim["kind"] = claim_kind

    predicate = _json_clone(spec["predicate"])
    provided_predicate = claim.get("predicate")
    if provided_predicate is not None and provided_predicate != predicate:
        result["status"] = "REJECTED_PREDICATE_MISMATCH"
        result["check"] = check
        result["typed_claim"] = claim
        result["artifact_ids"] = artifact_ids
        result["obligations"].append(
            _obligation(
                ident,
                "PREDICATE_CHECK_MISMATCH",
                (
                    "The model-proposed external predicate differs from the exact "
                    "predicate signed by the validator receipt."
                ),
                blocking=True,
                details={
                    "provided_predicate": _json_clone(provided_predicate),
                    "derived_predicate": predicate,
                },
            )
        )
        return result

    claim["predicate"] = predicate
    normalized_check = {
        "id": check_id,
        "claim_ids": [claim_id],
        **spec,
    }
    result["typed_claim"] = claim
    result["check"] = normalized_check
    result["artifact_ids"] = artifact_ids
    result["assumptions"] = assumptions
    result["formalizable"] = False
    result["formal_target"] = None
    result["validation_target"] = {
        "type": "SIGNED_EXTERNAL_VALIDATOR_RECEIPT",
        "validator": receipt["validator"],
        "validator_public_key_fingerprint": receipt[
            "validator_public_key_fingerprint"
        ],
        "receipt_payload_sha256": receipt["receipt_payload_sha256"],
        "reported_outcome": receipt["outcome"],
        "semantic_authority": receipt["semantic_authority"],
        "trust_contract": _json_clone(receipt["trust_contract"]),
    }
    result["grounding"] = {
        "status": "GROUNDED",
        "adapter": "signed_external_validator_receipt",
        "artifact_ids": check_refs,
        "facts": [
            "validator Ed25519 signature verified against pinned fingerprint",
            "external predicate exactly matches signed receipt",
            "all validator-bound artifact SHA-256 digests match project bytes",
            f"validator reported {receipt['outcome']}",
        ],
    }

    if confidence < confidence_threshold:
        result["status"] = "REVIEW_ONLY_LOW_CONFIDENCE"
        result["obligations"].append(
            _obligation(
                ident,
                "CONFIDENCE_BELOW_SELECTION_THRESHOLD",
                (
                    "The external validator contract compiled structurally but "
                    "the model proposal is below the selection threshold."
                ),
                blocking=True,
                details={
                    "confidence": confidence,
                    "threshold": confidence_threshold,
                },
            )
        )
        return result

    result["selected"] = True
    if receipt["outcome"] == "FAIL":
        result["status"] = "COMPILED_EXTERNAL_VALIDATOR_FAIL"
    else:
        result["status"] = (
            "COMPILED_EXTERNAL_VALIDATOR_BOUND_WITH_ASSUMPTIONS"
            if assumptions
            else "COMPILED_EXTERNAL_VALIDATOR_BOUND"
        )

    result["obligations"].append(
        _obligation(
            ident,
            "HUMAN_CONFIRMATION_REQUIRED",
            (
                "PCS authenticated and grounded the validator receipt, but a "
                "human must confirm that this externally validated predicate is "
                "the intended scientific claim before attestation."
            ),
            blocking=False,
        )
    )
    result["obligations"].append(
        _obligation(
            ident,
            "EXTERNAL_VALIDATOR_TRUST_REVIEW_REQUIRED",
            (
                "PCS verifies validator identity/signature, predicate binding, "
                "artifact hashes, and reported outcome. It does not prove the "
                "validator algorithm or scientific adequacy of its policy."
            ),
            blocking=False,
            details={
                "validator": receipt["validator"],
                "validator_public_key_fingerprint": receipt[
                    "validator_public_key_fingerprint"
                ],
                "semantic_authority": receipt["semantic_authority"],
            },
        )
    )
    if source.get("kind") == "external_model":
        result["obligations"].append(
            _obligation(
                ident,
                "MODEL_PROPOSAL_UNTRUSTED",
                (
                    "The external model remains a proposer only; it cannot set "
                    "the validator outcome or PCS authority."
                ),
                blocking=False,
            )
        )
    for assumption in assumptions:
        result["obligations"].append(
            _obligation(
                ident,
                "ASSUMPTION_REVIEW_REQUIRED",
                f"Review assumption {assumption['id']}: {assumption['statement']}",
                blocking=False,
                details={"assumption_id": assumption["id"]},
            )
        )

    normalized_translation = {
        "claim": claim,
        "check": normalized_check,
        "artifact_ids": artifact_ids,
        "assumptions": assumptions,
        "grounding": result["grounding"],
        "validation_target": result["validation_target"],
    }
    result["translation_sha256"] = hashlib.sha256(
        canonicalize_jcs_bytes(normalized_translation)
    ).hexdigest()
    return result


def _compile_proposal(
    proposal: Mapping[str, Any],
    *,
    inventory: Mapping[str, Mapping[str, Any]],
    project_root: Path,
    confidence_threshold: float,
) -> dict[str, Any]:
    ident = _safe_id(proposal.get("id"), label="proposal id")
    confidence = _confidence(
        proposal.get("confidence", 0.0),
        label=f"proposal {ident}",
    )
    source = proposal.get("proposal_source")
    if not isinstance(source, Mapping):
        source = {"kind": "unknown", "name": "unknown"}

    result: dict[str, Any] = {
        "id": ident,
        "source": _json_clone(source),
        "finding": proposal.get("finding") or proposal.get("reason"),
        "confidence": confidence,
        "confidence_threshold": confidence_threshold,
        "selected": False,
        "status": "OPEN_UNSTRUCTURED_FINDING",
        "formalizable": False,
        "formal_target": None,
        "validation_target": None,
        "typed_claim": None,
        "check": None,
        "artifact_ids": [],
        "assumptions": [],
        "grounding": None,
        "obligations": [],
    }

    claim_raw = proposal.get("claim")
    check_raw = proposal.get("check")
    if not isinstance(check_raw, Mapping):
        result["obligations"].append(
            _obligation(
                ident,
                "PROVIDE_TYPED_PREDICATE",
                "A natural-language finding cannot enter the proof boundary until a structured check/predicate is proposed.",
                blocking=True,
            )
        )
        return result

    check = _json_clone(check_raw)
    check_type = check.get("type")
    if not isinstance(check_type, str):
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["obligations"].append(
            _obligation(
                ident,
                "CHECK_TYPE_REQUIRED",
                "The proposed check does not declare a check type.",
                blocking=True,
            )
        )
        return result

    if check_type in EXTERNAL_VALIDATOR_CHECK_TYPES_V06:
        return _compile_external_validator_proposal(
            proposal,
            ident=ident,
            confidence=confidence,
            confidence_threshold=confidence_threshold,
            source=source,
            claim_raw=claim_raw,
            check=check,
            inventory=inventory,
            project_root=project_root,
            result=result,
        )

    if check_type in EXTERNAL_CHECK_KIND_BY_TYPE_V06:
        result["status"] = "EXTERNAL_VALIDATOR_REQUIRED"
        result["check"] = check
        result["obligations"].append(
            _obligation(
                ident,
                "PROVIDE_EXTERNAL_VALIDATOR",
                (
                    "PCS recognizes this external evidence family, but no signed "
                    "validator-receipt adapter is implemented for it."
                ),
                blocking=True,
                details={
                    "check_type": check_type,
                    "evidence_kind": EXTERNAL_CHECK_KIND_BY_TYPE_V06[check_type],
                },
            )
        )
        return result

    if check_type not in CERTIFIED_BUILTIN_CHECK_TYPES_V06:
        result["status"] = "OPEN_UNSUPPORTED_DOMAIN"
        result["check"] = check
        result["obligations"].append(
            _obligation(
                ident,
                "IMPLEMENT_CERTIFIED_CHECKER",
                "No certified PCS checker currently gives this proposed predicate machine-checked semantics.",
                blocking=True,
                details={"check_type": check_type},
            )
        )
        return result

    try:
        check_id = _safe_id(check.get("id"), label=f"proposal {ident} check id")
        predicate = predicate_from_manifest_check_v06(check)
        check_refs = check_artifact_references_v06(check)
    except (KeyError, ValueError, V06NumericContractError) as exc:
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["check"] = check
        result["obligations"].append(
            _obligation(
                ident,
                "INVALID_CHECK_SPEC",
                f"The proposed certified check is not structurally compilable: {exc}",
                blocking=True,
            )
        )
        return result

    missing_refs = sorted({ref for ref in check_refs if ref not in inventory})
    declared_artifacts = proposal.get("artifact_ids", [])
    if not isinstance(declared_artifacts, list) or not all(
        isinstance(x, str) for x in declared_artifacts
    ):
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["obligations"].append(
            _obligation(
                ident,
                "INVALID_ARTIFACT_GROUNDING",
                "proposal artifact_ids must be an array of artifact IDs",
                blocking=True,
            )
        )
        return result
    artifact_ids = sorted(set(declared_artifacts) | set(check_refs))
    missing_declared = sorted({ref for ref in artifact_ids if ref not in inventory})
    if missing_refs or missing_declared:
        result["status"] = "REJECTED_UNGROUNDED"
        result["check"] = check
        result["artifact_ids"] = artifact_ids
        result["obligations"].append(
            _obligation(
                ident,
                "GROUND_ARTIFACTS",
                "The proposed predicate references artifacts outside the current discovery snapshot.",
                blocking=True,
                details={"missing_artifact_ids": sorted(set(missing_refs + missing_declared))},
            )
        )
        return result

    try:
        grounding = _ground_check_against_project(
            check,
            declared_artifact_ids=artifact_ids,
            inventory=inventory,
            project_root=project_root,
        )
    except V06ProofTranslationError as exc:
        result["status"] = "REJECTED_UNGROUNDED"
        result["check"] = check
        result["artifact_ids"] = artifact_ids
        result["grounding"] = {
            "status": "FAILED",
            "error": str(exc),
        }
        result["obligations"].append(
            _obligation(
                ident,
                "GROUND_PREDICATE_IN_PROJECT_BYTES",
                str(exc),
                blocking=True,
            )
        )
        return result
    result["grounding"] = grounding

    if not isinstance(claim_raw, Mapping):
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["check"] = check
        result["artifact_ids"] = artifact_ids
        result["obligations"].append(
            _obligation(
                ident,
                "CLAIM_REQUIRED",
                "A certified check proposal requires a claim object with an id and statement.",
                blocking=True,
            )
        )
        return result

    claim = _json_clone(claim_raw)
    try:
        claim_id = _safe_id(claim.get("id"), label=f"proposal {ident} claim id")
        assumptions = _proposal_assumptions(proposal)
    except V06ProofTranslationError as exc:
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["check"] = check
        result["artifact_ids"] = artifact_ids
        result["obligations"].append(
            _obligation(
                ident,
                "INVALID_CLAIM",
                str(exc),
                blocking=True,
            )
        )
        return result

    statement = claim.get("statement")
    if not isinstance(statement, str) or not statement.strip():
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["obligations"].append(
            _obligation(
                ident,
                "CLAIM_STATEMENT_REQUIRED",
                "The proposed claim requires a non-empty scientific statement.",
                blocking=True,
            )
        )
        return result

    check_claim_ids = check.get("claim_ids")
    if check_claim_ids is None:
        check["claim_ids"] = [claim_id]
    elif (
        not isinstance(check_claim_ids, list)
        or not all(isinstance(x, str) for x in check_claim_ids)
        or sorted(check_claim_ids) != [claim_id]
    ):
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["obligations"].append(
            _obligation(
                ident,
                "CLAIM_EVIDENCE_LINK_MISMATCH",
                "The check claim_ids must contain exactly the proposed claim.",
                blocking=True,
            )
        )
        return result

    assumption_ids = [a["id"] for a in assumptions]
    provided_assumption_ids = claim.get("assumptions")
    if provided_assumption_ids is None:
        claim["assumptions"] = assumption_ids
    elif (
        not isinstance(provided_assumption_ids, list)
        or sorted(provided_assumption_ids) != sorted(assumption_ids)
    ):
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["obligations"].append(
            _obligation(
                ident,
                "ASSUMPTION_LINK_MISMATCH",
                "Claim assumption IDs do not exactly match the supplied assumption objects.",
                blocking=True,
            )
        )
        return result

    required = claim.get("required_evidence")
    if required is None:
        claim["required_evidence"] = [check_id]
    elif (
        not isinstance(required, list)
        or not all(isinstance(x, str) for x in required)
        or sorted(required) != [check_id]
    ):
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["obligations"].append(
            _obligation(
                ident,
                "CLAIM_EVIDENCE_LINK_MISMATCH",
                "Claim required_evidence must contain exactly the proposed check.",
                blocking=True,
            )
        )
        return result

    claim["kind"] = claim.get("kind", "computational")
    if claim["kind"] not in {"computational", "formal", "empirical", "mixed"}:
        result["status"] = "REJECTED_INVALID_PROPOSAL"
        result["obligations"].append(
            _obligation(
                ident,
                "INVALID_CLAIM_KIND",
                f"Unsupported claim kind {claim['kind']!r}.",
                blocking=True,
            )
        )
        return result

    provided_predicate = claim.get("predicate")
    if provided_predicate is not None:
        try:
            normalized_provided = _normalized_predicate(provided_predicate)
        except V06NumericContractError as exc:
            result["status"] = "REJECTED_INVALID_PROPOSAL"
            result["obligations"].append(
                _obligation(
                    ident,
                    "PREDICATE_NUMERIC_CONTRACT",
                    str(exc),
                    blocking=True,
                )
            )
            return result
        if normalized_provided != predicate:
            result["status"] = "REJECTED_PREDICATE_MISMATCH"
            result["check"] = check
            result["typed_claim"] = claim
            result["artifact_ids"] = artifact_ids
            result["obligations"].append(
                _obligation(
                    ident,
                    "PREDICATE_CHECK_MISMATCH",
                    "The model-proposed claim predicate differs from the predicate deterministically derived from its check specification.",
                    blocking=True,
                    details={
                        "provided_predicate": normalized_provided,
                        "derived_predicate": predicate,
                    },
                )
            )
            return result

    claim["predicate"] = predicate
    result["typed_claim"] = claim
    result["check"] = check
    result["artifact_ids"] = artifact_ids
    result["assumptions"] = assumptions
    result["formalizable"] = True
    result["formal_target"] = formal_target_for_check_v06(check_type)

    if confidence < confidence_threshold:
        result["status"] = "REVIEW_ONLY_LOW_CONFIDENCE"
        result["obligations"].append(
            _obligation(
                ident,
                "CONFIDENCE_BELOW_SELECTION_THRESHOLD",
                "The proposal compiled structurally but is below the configured selection threshold.",
                blocking=True,
                details={
                    "confidence": confidence,
                    "threshold": confidence_threshold,
                },
            )
        )
        return result

    result["selected"] = True
    result["status"] = (
        "COMPILED_LEAN_BUILTIN_WITH_ASSUMPTIONS"
        if assumptions
        else "COMPILED_LEAN_BUILTIN"
    )
    result["obligations"].append(
        _obligation(
            ident,
            "HUMAN_CONFIRMATION_REQUIRED",
            "Compilation proves that the proposal fits a theorem-backed PCS predicate; a human must still confirm that this predicate is the intended scientific claim before attestation.",
            blocking=False,
        )
    )
    if source.get("kind") == "external_model":
        result["obligations"].append(
            _obligation(
                ident,
                "MODEL_PROPOSAL_UNTRUSTED",
                "The external model is a proposer only. Its prose/confidence is not trusted; PCS trusts only the deterministic compilation and subsequent replay/proof boundary.",
                blocking=False,
            )
        )
    for assumption in assumptions:
        result["obligations"].append(
            _obligation(
                ident,
                "ASSUMPTION_REVIEW_REQUIRED",
                f"Review assumption {assumption['id']}: {assumption['statement']}",
                blocking=False,
                details={"assumption_id": assumption["id"]},
            )
        )

    normalized_translation = {
        "claim": claim,
        "check": check,
        "artifact_ids": artifact_ids,
        "assumptions": assumptions,
        "grounding": result["grounding"],
        "formal_target": result["formal_target"],
    }
    result["translation_sha256"] = hashlib.sha256(
        canonicalize_jcs_bytes(normalized_translation)
    ).hexdigest()
    return result



def _candidate_closure_state(candidate: Mapping[str, Any]) -> str:
    if any(
        isinstance(obligation, Mapping) and obligation.get("blocking") is True
        for obligation in candidate.get("obligations", [])
    ):
        return "BLOCKED"
    if candidate.get("selected") is True:
        return "COMPILED_PENDING_HUMAN_CONFIRMATION"
    if candidate.get("formalizable") is True:
        return "FORMALIZABLE_NOT_SELECTED"
    return "OPEN"


def _proof_obligation_graph(
    candidates: Sequence[Mapping[str, Any]],
    *,
    inventory: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    roots: list[str] = []
    repair_queue: list[dict[str, Any]] = []

    def add_node(node: dict[str, Any]) -> None:
        node_id = str(node["id"])
        existing = nodes.get(node_id)
        if existing is not None and existing != node:
            raise V06ProofTranslationError(
                f"proof-obligation graph node collision: {node_id}"
            )
        nodes[node_id] = node

    def add_edge(
        source: str,
        target: str,
        relation: str,
        *,
        blocking: bool = False,
    ) -> None:
        edges.append(
            {
                "from": source,
                "to": target,
                "relation": relation,
                "blocking": blocking,
            }
        )

    closure_state_counts: dict[str, int] = {}
    for candidate in sorted(candidates, key=lambda item: str(item.get("id", ""))):
        proposal_id = str(candidate["id"])
        proposal_node = f"proposal:{proposal_id}"
        closure_state = _candidate_closure_state(candidate)
        closure_state_counts[closure_state] = (
            closure_state_counts.get(closure_state, 0) + 1
        )
        roots.append(proposal_node)
        add_node(
            {
                "id": proposal_node,
                "type": "proposal",
                "status": closure_state,
                "proposal_id": proposal_id,
                "candidate_status": candidate.get("status"),
                "selected": candidate.get("selected") is True,
                "formalizable": candidate.get("formalizable") is True,
                "confidence": candidate.get("confidence"),
                "source": _json_clone(candidate.get("source")),
                "finding": candidate.get("finding"),
            }
        )

        artifact_nodes: list[str] = []
        for artifact_id in sorted(set(candidate.get("artifact_ids", []))):
            item = inventory.get(str(artifact_id))
            if item is None:
                continue
            node_id = f"artifact:{artifact_id}"
            artifact_nodes.append(node_id)
            add_node(
                {
                    "id": node_id,
                    "type": "artifact",
                    "status": "BOUND_TO_INVENTORY",
                    "artifact_id": artifact_id,
                    "path": item.get("path"),
                    "sha256": item.get("sha256"),
                    "size": item.get("size"),
                    "media_type": item.get("media_type"),
                }
            )
            add_edge(proposal_node, node_id, "references_artifact")

        grounding = candidate.get("grounding")
        grounding_nodes: list[str] = []
        if isinstance(grounding, Mapping):
            facts = grounding.get("facts", [])
            if isinstance(facts, list):
                for index, fact in enumerate(facts):
                    if not isinstance(fact, str):
                        continue
                    node_id = f"grounding:{proposal_id}:{index}"
                    grounding_nodes.append(node_id)
                    add_node(
                        {
                            "id": node_id,
                            "type": "grounding_fact",
                            "status": (
                                "CLOSED"
                                if grounding.get("status") == "GROUNDED"
                                else "FAILED"
                            ),
                            "fact": fact,
                        }
                    )
                    add_edge(proposal_node, node_id, "has_grounding_fact")
                    for artifact_node in artifact_nodes:
                        add_edge(artifact_node, node_id, "supports_grounding")

        check = candidate.get("check")
        check_node: str | None = None
        if isinstance(check, Mapping):
            check_id = str(check.get("id") or proposal_id)
            check_node = f"check:{check_id}"
            add_node(
                {
                    "id": check_node,
                    "type": "typed_check",
                    "status": (
                        "GROUNDED"
                        if isinstance(grounding, Mapping)
                        and grounding.get("status") == "GROUNDED"
                        else "PROPOSED"
                    ),
                    "check_id": check.get("id"),
                    "check_type": check.get("type"),
                    "predicate": (
                        _json_clone(candidate["typed_claim"].get("predicate"))
                        if isinstance(candidate.get("typed_claim"), Mapping)
                        else None
                    ),
                }
            )
            add_edge(proposal_node, check_node, "proposes_check")
            for grounding_node in grounding_nodes:
                add_edge(grounding_node, check_node, "grounds_check")

        claim = candidate.get("typed_claim")
        claim_node: str | None = None
        if isinstance(claim, Mapping):
            claim_id = str(claim.get("id") or proposal_id)
            claim_node = f"claim:{claim_id}"
            add_node(
                {
                    "id": claim_node,
                    "type": "typed_claim",
                    "status": (
                        "COMPILED_FORMAL"
                        if candidate.get("formalizable") is True
                        else (
                            "COMPILED_EXTERNAL"
                            if candidate.get("selected") is True
                            else "PROPOSED"
                        )
                    ),
                    "claim_id": claim.get("id"),
                    "kind": claim.get("kind"),
                    "statement": claim.get("statement"),
                    "predicate": _json_clone(claim.get("predicate")),
                }
            )
            add_edge(proposal_node, claim_node, "interprets_as_claim")
            if check_node is not None:
                add_edge(check_node, claim_node, "defines_predicate_for")

        for assumption in candidate.get("assumptions", []):
            if not isinstance(assumption, Mapping):
                continue
            assumption_id = str(assumption.get("id"))
            node_id = f"assumption:{assumption_id}"
            add_node(
                {
                    "id": node_id,
                    "type": "assumption",
                    "status": "REQUIRES_REVIEW",
                    "assumption_id": assumption.get("id"),
                    "statement": assumption.get("statement"),
                }
            )
            if claim_node is not None:
                add_edge(node_id, claim_node, "assumption_for")
            else:
                add_edge(proposal_node, node_id, "declares_assumption")

        formal_target = candidate.get("formal_target")
        if isinstance(formal_target, Mapping):
            node_id = f"formal_target:{proposal_id}"
            add_node(
                {
                    "id": node_id,
                    "type": "formal_target",
                    "status": "TARGET_RESOLVED",
                    "target": _json_clone(formal_target),
                }
            )
            if claim_node is not None:
                add_edge(claim_node, node_id, "compiled_toward")
            elif check_node is not None:
                add_edge(check_node, node_id, "compiled_toward")
            else:
                add_edge(proposal_node, node_id, "compiled_toward")

        validation_target = candidate.get("validation_target")
        if isinstance(validation_target, Mapping):
            node_id = f"external_validator_target:{proposal_id}"
            add_node(
                {
                    "id": node_id,
                    "type": "external_validator_target",
                    "status": "SIGNED_RECEIPT_BOUND",
                    "target": _json_clone(validation_target),
                }
            )
            if claim_node is not None:
                add_edge(
                    claim_node,
                    node_id,
                    "validated_under_external_trust_contract",
                )
            elif check_node is not None:
                add_edge(
                    check_node,
                    node_id,
                    "validated_under_external_trust_contract",
                )
            else:
                add_edge(
                    proposal_node,
                    node_id,
                    "validated_under_external_trust_contract",
                )

        for obligation in candidate.get("obligations", []):
            if not isinstance(obligation, Mapping):
                continue
            obligation_id = str(obligation["id"])
            node_id = f"obligation:{obligation_id}"
            blocking = obligation.get("blocking") is True
            add_node(
                {
                    "id": node_id,
                    "type": "obligation",
                    "status": "OPEN_BLOCKING" if blocking else "OPEN_REVIEW",
                    "obligation_id": obligation_id,
                    "proposal_id": proposal_id,
                    "kind": obligation.get("kind"),
                    "blocking": blocking,
                    "message": obligation.get("message"),
                    "details": _json_clone(obligation.get("details")),
                    "repair": _json_clone(obligation.get("repair")),
                }
            )
            add_edge(
                proposal_node,
                node_id,
                "has_blocking_obligation" if blocking else "has_review_obligation",
                blocking=blocking,
            )
            repair = obligation.get("repair")
            if isinstance(repair, Mapping):
                repair_queue.append(
                    {
                        "obligation_id": obligation_id,
                        "proposal_id": proposal_id,
                        "kind": obligation.get("kind"),
                        "blocking": blocking,
                        "repair": _json_clone(repair),
                    }
                )

    node_ids = set(nodes)
    for edge in edges:
        if edge["from"] not in node_ids or edge["to"] not in node_ids:
            raise V06ProofTranslationError(
                "proof-obligation graph contains a dangling edge"
            )

    ordered_nodes = [nodes[key] for key in sorted(nodes)]
    ordered_edges = sorted(
        edges,
        key=lambda edge: (
            str(edge["from"]),
            str(edge["to"]),
            str(edge["relation"]),
            bool(edge["blocking"]),
        ),
    )
    repair_queue = sorted(
        repair_queue,
        key=lambda item: (
            not bool(item["blocking"]),
            str(item["proposal_id"]),
            str(item["obligation_id"]),
        ),
    )
    type_counts: dict[str, int] = {}
    for node in ordered_nodes:
        node_type = str(node["type"])
        type_counts[node_type] = type_counts.get(node_type, 0) + 1

    graph_core = {
        "format": PROOF_OBLIGATION_GRAPH_FORMAT_V06,
        "roots": sorted(set(roots)),
        "nodes": ordered_nodes,
        "edges": ordered_edges,
        "repair_queue": repair_queue,
        "summary": {
            "nodes": len(ordered_nodes),
            "edges": len(ordered_edges),
            "blocking_obligations": sum(
                1
                for node in ordered_nodes
                if node.get("type") == "obligation"
                and node.get("blocking") is True
            ),
            "repair_actions": len(repair_queue),
            "node_type_counts": type_counts,
            "closure_state_counts": closure_state_counts,
        },
    }
    graph_sha256 = hashlib.sha256(
        canonicalize_jcs_bytes(graph_core)
    ).hexdigest()
    return {
        **graph_core,
        "graph_sha256": graph_sha256,
    }


def _merge_selected_proposals_into_manifest(
    base_manifest: Mapping[str, Any],
    *,
    candidates: Sequence[Mapping[str, Any]],
    inventory: Mapping[str, Mapping[str, Any]],
    plan_commitment: str,
    obligation_graph_commitment: str,
) -> dict[str, Any]:
    manifest = _json_clone(base_manifest)

    claims = {item["id"]: item for item in manifest.get("claims", [])}
    checks = {item["id"]: item for item in manifest.get("checks", [])}
    assumptions = {item["id"]: item for item in manifest.get("assumptions", [])}
    artifacts = {item["id"]: item for item in manifest.get("artifacts", [])}

    model_selected: list[str] = []
    translation_selected: list[str] = []

    for candidate in candidates:
        if candidate.get("selected") is not True:
            continue
        claim = candidate.get("typed_claim")
        check = candidate.get("check")
        if not isinstance(claim, Mapping) or not isinstance(check, Mapping):
            raise V06ProofTranslationError(
                f"selected candidate {candidate.get('id')} lacks compiled claim/check"
            )

        claim_id = claim["id"]
        check_id = check["id"]
        existing_claim = claims.get(claim_id)
        if existing_claim is not None and existing_claim != claim:
            raise V06ProofTranslationError(
                f"compiled claim id collision with different semantics: {claim_id}"
            )
        existing_check = checks.get(check_id)
        if existing_check is not None and existing_check != check:
            raise V06ProofTranslationError(
                f"compiled check id collision with different semantics: {check_id}"
            )
        claims[claim_id] = _json_clone(claim)
        checks[check_id] = _json_clone(check)

        for assumption in candidate.get("assumptions", []):
            assumption = _json_clone(assumption)
            assumption.setdefault("scope", [])
            if claim_id not in assumption["scope"]:
                assumption["scope"].append(claim_id)
            assumption["scope"] = sorted(set(assumption["scope"]))
            existing = assumptions.get(assumption["id"])
            if existing is not None and existing != assumption:
                raise V06ProofTranslationError(
                    f"compiled assumption id collision with different semantics: {assumption['id']}"
                )
            assumptions[assumption["id"]] = assumption

        for artifact_id in candidate.get("artifact_ids", []):
            if artifact_id not in inventory:
                raise V06ProofTranslationError(
                    f"compiled candidate references missing inventory artifact {artifact_id}"
                )
            artifacts.setdefault(artifact_id, _artifact_entry(inventory[artifact_id]))

        translation_selected.append(str(candidate["id"]))
        source = candidate.get("source")
        if isinstance(source, Mapping) and source.get("kind") == "external_model":
            model_selected.append(str(candidate["id"]))

    manifest["claims"] = [claims[key] for key in sorted(claims)]
    manifest["checks"] = [checks[key] for key in sorted(checks)]
    manifest["assumptions"] = [assumptions[key] for key in sorted(assumptions)]
    manifest["artifacts"] = [artifacts[key] for key in sorted(artifacts)]

    intake = manifest.setdefault("pcs_intake", {})
    intake["proof_translation_format"] = PROOF_TRANSLATION_FORMAT_V06
    intake["proof_translation_compiler"] = PROOF_TRANSLATION_COMPILER_V06
    intake["proof_translation_plan_sha256"] = plan_commitment
    intake["proof_obligation_graph_format"] = PROOF_OBLIGATION_GRAPH_FORMAT_V06
    intake["proof_obligation_graph_sha256"] = obligation_graph_commitment
    intake["proof_translation_selected"] = sorted(translation_selected)
    intake["proof_translation_model_selected"] = sorted(model_selected)
    intake["proof_translation_requires_confirmation"] = True
    intake["requires_confirmation"] = True
    intake["status"] = "draft"
    intake.setdefault("format", MANIFEST_DRAFT_FORMAT_V06)

    try:
        validate_manifest_shape(manifest)
    except SchemaValidationError as exc:
        raise V06ProofTranslationError(
            f"proof translation produced invalid manifest draft: {exc}"
        ) from exc
    return manifest


def translate_project_v06(
    project_root: str | Path,
    *,
    subject: str | None = None,
    proposal_files: Sequence[str | Path] | None = None,
    control_paths: Sequence[str | Path] | None = None,
    minimum_confidence: float = 0.95,
    minimum_model_confidence: float = 0.98,
    minimum_workflow_confidence: float = 0.95,
) -> dict[str, Any]:
    if not 0.0 <= minimum_confidence <= 1.0:
        raise V06ProofTranslationError("minimum_confidence must be between 0 and 1")
    if not 0.0 <= minimum_model_confidence <= 1.0:
        raise V06ProofTranslationError(
            "minimum_model_confidence must be between 0 and 1"
        )

    try:
        discovery = discover_project_v06(
            project_root,
            subject=subject,
            minimum_confidence=minimum_confidence,
            minimum_workflow_confidence=minimum_workflow_confidence,
            exclude_paths=[
                *list(proposal_files or []),
                *list(control_paths or []),
            ],
        )
    except V06DiscoveryError as exc:
        raise V06ProofTranslationError(str(exc)) from exc
    if discovery.get("format") != DISCOVERY_FORMAT_V06:
        raise V06ProofTranslationError("unexpected discovery report format")

    inventory_commitment = discovery["inventory_commitment_sha256"]
    inventory = {
        item["artifact_id"]: item
        for item in discovery.get("inventory", [])
        if isinstance(item, Mapping) and isinstance(item.get("artifact_id"), str)
    }

    proposal_sources: list[dict[str, Any]] = [
        {
            "kind": "deterministic_discovery",
            "name": "pcs-discovery-v06",
            "proposal_count": len(discovery.get("recommendations", [])),
        }
    ]
    proposals = _discovery_proposals(discovery)

    for proposal_file in proposal_files or []:
        source_meta, external = _load_external_proposal_file(
            proposal_file,
            expected_inventory_commitment=inventory_commitment,
        )
        proposal_sources.append({"kind": "external_model", **source_meta})
        proposals.extend(external)

    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for proposal in proposals:
        ident = _safe_id(proposal.get("id"), label="proposal id")
        if ident in seen:
            raise V06ProofTranslationError(f"duplicate proposal id: {ident}")
        seen.add(ident)
        source = proposal.get("proposal_source")
        is_model = isinstance(source, Mapping) and source.get("kind") == "external_model"
        threshold = minimum_model_confidence if is_model else minimum_confidence
        candidates.append(
            _compile_proposal(
                proposal,
                inventory=inventory,
                project_root=Path(project_root).resolve(),
                confidence_threshold=threshold,
            )
        )

    selected_discovery = sorted(
        candidate["id"]
        for candidate in candidates
        if candidate.get("selected") is True
        and isinstance(candidate.get("source"), Mapping)
        and candidate["source"].get("kind") == "deterministic_discovery"
    )
    expected_discovery = sorted(discovery.get("selected_recommendations", []))
    if selected_discovery != expected_discovery:
        raise V06ProofTranslationError(
            "proof compiler selection drifted from deterministic discovery selection"
        )

    obligations = [
        obligation
        for candidate in candidates
        for obligation in candidate.get("obligations", [])
    ]
    obligation_graph = _proof_obligation_graph(
        candidates,
        inventory=inventory,
    )
    plan_core = {
        "format": PROOF_TRANSLATION_FORMAT_V06,
        "compiler": PROOF_TRANSLATION_COMPILER_V06,
        "inventory_commitment_sha256": inventory_commitment,
        "proposal_sources": proposal_sources,
        "candidates": candidates,
        "obligations": obligations,
        "obligation_graph": obligation_graph,
    }
    plan_commitment = hashlib.sha256(canonicalize_jcs_bytes(plan_core)).hexdigest()

    manifest = _merge_selected_proposals_into_manifest(
        discovery["manifest_draft"],
        candidates=candidates,
        inventory=inventory,
        plan_commitment=plan_commitment,
        obligation_graph_commitment=obligation_graph["graph_sha256"],
    )

    status_counts: dict[str, int] = {}
    for candidate in candidates:
        status = str(candidate["status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    selected = [c for c in candidates if c.get("selected") is True]
    open_blocking = [o for o in obligations if o.get("blocking") is True]

    return {
        **plan_core,
        "project_root_name": discovery["project_root_name"],
        "subject": discovery["subject"],
        "plan_sha256": plan_commitment,
        "trust_model": {
            "proposers_trusted": False,
            "deterministic_compiler_trusted_for_translation_structure": True,
            "human_confirmation_required": True,
            "authoritative_scientific_acceptance_requires_existing_pcs_replay_and_lean_authority": True,
            "model_output_can_never_directly_set_pass_or_authoritative": True,
        },
        "summary": {
            "proposals_total": len(candidates),
            "compiled_selected": len(selected),
            "external_model_selected": sum(
                1
                for candidate in selected
                if isinstance(candidate.get("source"), Mapping)
                and candidate["source"].get("kind") == "external_model"
            ),
            "formalizable_candidates": sum(
                1 for candidate in candidates if candidate.get("formalizable") is True
            ),
            "blocking_open_obligations": len(open_blocking),
            "obligation_graph_nodes": obligation_graph["summary"]["nodes"],
            "obligation_graph_edges": obligation_graph["summary"]["edges"],
            "repair_actions": obligation_graph["summary"]["repair_actions"],
            "status_counts": status_counts,
            "manifest_claims": len(manifest.get("claims", [])),
            "manifest_checks": len(manifest.get("checks", [])),
        },
        "manifest_draft": manifest,
        "discovery_summary": discovery.get("summary", {}),
        "discovery_unresolved": discovery.get("unresolved", []),
    }


def write_proof_translation_outputs_v06(
    translation: Mapping[str, Any],
    *,
    plan_output: str | Path,
    manifest_output: str | Path,
    overwrite: bool = False,
) -> dict[str, str]:
    if translation.get("format") != PROOF_TRANSLATION_FORMAT_V06:
        raise V06ProofTranslationError("refusing to write non-v0.6 proof translation")

    outputs = [
        (Path(plan_output).resolve(), "proof translation plan"),
        (Path(manifest_output).resolve(), "translated manifest draft"),
    ]
    if outputs[0][0] == outputs[1][0]:
        raise V06ProofTranslationError(
            "proof translation plan and manifest draft must use different paths"
        )
    for path, label in outputs:
        if path.exists() and not overwrite:
            raise V06ProofTranslationError(
                f"refusing to overwrite existing {label}: {path}"
            )

    plan_path, manifest_path = outputs[0][0], outputs[1][0]
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    plan_path.write_text(
        json.dumps(dict(translation), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            translation["manifest_draft"],
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "proof_translation_plan": str(plan_path),
        "manifest_draft": str(manifest_path),
    }
