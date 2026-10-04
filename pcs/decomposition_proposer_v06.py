from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .canonical_json import canonicalize_jcs_bytes
from .check_registry_v06 import (
    CERTIFIED_BUILTIN_CHECK_TYPES_V06,
    formal_target_for_check_v06,
)
from .discover_v06 import V06DiscoveryError, discover_project_v06
from .external_validator_v06 import (
    EXTERNAL_VALIDATOR_CHECK_TYPES_V06,
    EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06,
    EXTERNAL_VALIDATOR_TRUST_MODEL_V06,
)
from .jsonio import StrictJSONError, strict_json_load
from .proof_repair_v06 import (
    MAX_DECOMPOSITION_CHILDREN_PER_ACTION_V06,
    PROOF_REPAIR_RESPONSE_FORMAT_V06,
    V06ProofRepairError,
    compile_proof_repair_response_v06,
)
from .proof_search_v06 import (
    MAX_PROOF_SEARCH_DECOMPOSITION_DEPTH_V06,
    MAX_PROOF_SEARCH_PROPOSALS_V06,
    V06ProofSearchError,
    verify_proof_search_session_v06,
)


DECOMPOSITION_PROPOSER_REQUEST_FORMAT_V06 = (
    "pcs-decomposition-proposer-request-v1"
)
DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06 = (
    "pcs-decomposition-proposer-response-v1"
)
DECOMPOSITION_PROPOSER_COMPILATION_FORMAT_V06 = (
    "pcs-decomposition-proposer-compilation-v1"
)
DECOMPOSITION_PROPOSER_PROTOCOL_V06 = (
    "pcs-decomposition-proposer-protocol/0.2"
)


class V06DecompositionProposerError(ValueError):
    pass


_ALLOWED_RESPONSE_KEYS_V06 = {
    "format",
    "decomposition_request_sha256",
    "search_id",
    "inventory_commitment_sha256",
    "proposer",
    "decision",
    "children",
    "reason",
    "inspection_result_sha256",
}
_ALLOWED_PROPOSER_KEYS_V06 = {
    "kind",
    "name",
    "version",
    "model_family",
}


_CHECKER_FIELDS_V06: dict[str, dict[str, Any]] = {
    "reaction_balance": {
        "required_check_fields": ["id", "type", "claim_ids", "reactants", "products"],
        "grounding": "Exact reactant/product arrays must occur in a referenced project JSON artifact.",
    },
    "unit_compatible": {
        "required_check_fields": ["id", "type", "claim_ids", "left_unit", "right_unit"],
        "grounding": "Exact left_unit/right_unit strings must occur in a referenced project JSON artifact.",
    },
    "csv_disjoint": {
        "required_check_fields": [
            "id",
            "type",
            "claim_ids",
            "left_artifact",
            "right_artifact",
            "key",
        ],
        "grounding": "The key must exist in both referenced committed CSV headers.",
    },
    "pkpd_contract": {
        "required_check_fields": ["id", "type", "claim_ids", "model_artifact"],
        "grounding": "The referenced JSON must match the restricted one-compartment IV-bolus/direct-Emax model shape.",
    },
    "pkpd_reference_match": {
        "required_check_fields": [
            "id",
            "type",
            "claim_ids",
            "model_artifact",
            "output_artifact",
        ],
        "optional_check_fields": [
            "time_column",
            "concentration_column",
            "effect_column",
            "rel_tol",
            "abs_tol",
        ],
        "grounding": "The restricted PK/PD model and required output columns must be present in committed artifacts.",
    },
    "pkpd_peak_concentration_threshold": {
        "required_check_fields": [
            "id",
            "type",
            "claim_ids",
            "model_artifact",
            "output_artifact",
            "upper_bound",
            "unit",
        ],
        "optional_check_fields": ["concentration_column"],
        "grounding": "The unit must match the committed model concentration_unit and the concentration column must exist in the committed output CSV.",
        "scope_warning": "This checker bounds reported committed rows only; it is not continuous-time Cmax or clinical safety.",
    },
}


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _commitment(value: Any) -> str:
    return hashlib.sha256(canonicalize_jcs_bytes(value)).hexdigest()


def _nonempty(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise V06DecompositionProposerError(
            f"{label} must be a non-empty string"
        )
    return value


def _candidate_map(translation: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = translation.get("candidates")
    if not isinstance(raw, list):
        raise V06DecompositionProposerError(
            "proof translation candidates must be an array"
        )
    out: dict[str, Mapping[str, Any]] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            raise V06DecompositionProposerError(
                "proof translation candidate must be an object"
            )
        ident = _nonempty(item.get("id"), label="candidate id")
        if ident in out:
            raise V06DecompositionProposerError(
                f"duplicate proof translation candidate id {ident!r}"
            )
        out[ident] = item
    return out


def _decomposition_tasks(session: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    request = session.get("current_repair_request")
    if not isinstance(request, Mapping):
        raise V06DecompositionProposerError(
            "proof search session lacks current repair request"
        )
    raw = request.get("tasks")
    if not isinstance(raw, list):
        raise V06DecompositionProposerError(
            "proof search repair request tasks must be an array"
        )
    return [
        task
        for task in raw
        if isinstance(task, Mapping)
        and task.get("allowed_action") == "decompose_claim"
    ]


def _select_task(
    session: Mapping[str, Any],
    *,
    proposal_id: str | None,
) -> Mapping[str, Any]:
    tasks = _decomposition_tasks(session)
    if proposal_id is not None:
        matches = [
            task
            for task in tasks
            if task.get("proposal_id") == proposal_id
        ]
        if len(matches) != 1:
            raise V06DecompositionProposerError(
                f"proposal {proposal_id!r} does not have exactly one decompose_claim task"
            )
        return matches[0]
    if len(tasks) != 1:
        choices = sorted(
            str(task.get("proposal_id"))
            for task in tasks
            if isinstance(task.get("proposal_id"), str)
        )
        raise V06DecompositionProposerError(
            "decomposition proposer request requires exactly one target; "
            f"available proposal ids: {choices}"
        )
    return tasks[0]


def _inventory_metadata(discovery: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = discovery.get("inventory")
    if not isinstance(raw, list):
        raise V06DecompositionProposerError(
            "project discovery inventory must be an array"
        )
    out = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        out.append(
            {
                "artifact_id": item.get("artifact_id"),
                "path": item.get("path"),
                "sha256": item.get("sha256"),
                "size": item.get("size"),
                "media_type": item.get("media_type"),
                "role": item.get("role"),
            }
        )
    return sorted(out, key=lambda item: str(item.get("artifact_id")))


def _checker_vocabulary() -> list[dict[str, Any]]:
    certified = set(CERTIFIED_BUILTIN_CHECK_TYPES_V06)
    described = set(_CHECKER_FIELDS_V06)
    if certified != described:
        raise V06DecompositionProposerError(
            "decomposition checker vocabulary drifted from certified registry: "
            f"missing={sorted(certified - described)}, "
            f"extra={sorted(described - certified)}"
        )

    out = []
    for check_type in sorted(certified):
        target = formal_target_for_check_v06(check_type)
        if not isinstance(target, Mapping):
            raise V06DecompositionProposerError(
                f"certified checker {check_type!r} lacks a formal target"
            )
        out.append(
            {
                "type": check_type,
                **_json_clone(_CHECKER_FIELDS_V06[check_type]),
                "formal_target": target,
                "authority": "LEAN_BACKED_AFTER_DETERMINISTIC_GROUNDING_AND_REPLAY",
            }
        )
    return out


def _external_validator_vocabulary() -> list[dict[str, Any]]:
    return [
        {
            "type": check_type,
            "required_check_fields": [
                "id",
                "type",
                "claim_ids",
                "validator",
                "predicate",
                "receipt_format",
                "trust_model",
                "receipt_artifact",
                "validator_public_key_artifact",
                "validator_public_key_fingerprint",
                "validator_trust_policy_artifact",
                "bound_artifact_ids",
            ],
            "receipt_format": EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06,
            "trust_model": EXTERNAL_VALIDATOR_TRUST_MODEL_V06,
            "authority": (
                "EXTERNAL_VALIDATOR_TRUST_REQUIRED; PCS verifies signature, "
                "key pinning, predicate/artifact binding, and reported outcome, "
                "not validator algorithm correctness or scientific adequacy."
            ),
        }
        for check_type in sorted(EXTERNAL_VALIDATOR_CHECK_TYPES_V06)
    ]


def build_decomposition_proposer_request_v06(
    project_root: str | Path,
    session: Mapping[str, Any],
    *,
    proposal_id: str | None = None,
) -> dict[str, Any]:
    try:
        verify_proof_search_session_v06(session)
    except V06ProofSearchError as exc:
        raise V06DecompositionProposerError(str(exc)) from exc
    if session.get("status") != "AWAITING_REPAIR":
        raise V06DecompositionProposerError(
            "decomposition proposer requires an AWAITING_REPAIR proof-search session"
        )

    task = _select_task(session, proposal_id=proposal_id)
    target_proposal_id = _nonempty(
        task.get("proposal_id"),
        label="decomposition target proposal id",
    )
    translation = session.get("current_translation")
    if not isinstance(translation, Mapping):
        raise V06DecompositionProposerError(
            "proof search session lacks current translation"
        )
    candidate = _candidate_map(translation).get(target_proposal_id)
    if candidate is None:
        raise V06DecompositionProposerError(
            "decomposition target is absent from current translation"
        )
    if candidate.get("status") != "DECOMPOSITION_LEAF_UNRESOLVED":
        raise V06DecompositionProposerError(
            "decomposition proposer target must be an unresolved Claim IR leaf"
        )

    claim = candidate.get("typed_claim")
    if not isinstance(claim, Mapping):
        claim = candidate.get("claim_ir_claim")
    if not isinstance(claim, Mapping):
        raise V06DecompositionProposerError(
            "decomposition target lacks a Claim IR claim"
        )
    claim_id = _nonempty(claim.get("id"), label="target claim id")

    decomposition = candidate.get("decomposition")
    if not isinstance(decomposition, Mapping):
        raise V06DecompositionProposerError(
            "decomposition target lacks decomposition metadata"
        )
    depth = decomposition.get("depth")
    if isinstance(depth, bool) or not isinstance(depth, int) or depth < 0:
        raise V06DecompositionProposerError(
            "decomposition target depth is invalid"
        )
    remaining_depth = MAX_PROOF_SEARCH_DECOMPOSITION_DEPTH_V06 - depth
    if remaining_depth <= 0:
        raise V06DecompositionProposerError(
            "decomposition target has no remaining proof-search depth budget"
        )

    root = Path(project_root).resolve()
    try:
        discovery = discover_project_v06(
            root,
            subject=(
                str(session["subject"])
                if session.get("subject") is not None
                else None
            ),
        )
    except (OSError, V06DiscoveryError) as exc:
        raise V06DecompositionProposerError(
            f"cannot reconstruct committed project inventory: {exc}"
        ) from exc
    inventory_commitment = discovery.get("inventory_commitment_sha256")
    if inventory_commitment != session.get("inventory_commitment_sha256"):
        raise V06DecompositionProposerError(
            "project inventory changed since proof search began; restart search"
        )

    active_documents = session.get("active_proposal_documents")
    if not isinstance(active_documents, list):
        raise V06DecompositionProposerError(
            "proof search session lacks active proposal documents"
        )
    active_proposal_ids = sorted(
        str(proposal.get("id"))
        for document in active_documents
        if isinstance(document, Mapping)
        for proposal in document.get("proposals", [])
        if isinstance(proposal, Mapping)
        and isinstance(proposal.get("id"), str)
    )
    remaining_slots = MAX_PROOF_SEARCH_PROPOSALS_V06 - len(active_proposal_ids)
    max_children = min(
        MAX_DECOMPOSITION_CHILDREN_PER_ACTION_V06,
        remaining_slots,
    )
    if max_children <= 0:
        raise V06DecompositionProposerError(
            "decomposition target has no remaining proof-search proposal budget"
        )

    claim_ir = translation.get("claim_ir")
    if not isinstance(claim_ir, Mapping):
        raise V06DecompositionProposerError(
            "proof translation lacks Claim IR"
        )
    existing_claim_ids = sorted(
        str(item.get("claim_id"))
        for item in claim_ir.get("claims", [])
        if isinstance(item, Mapping)
        and isinstance(item.get("claim_id"), str)
    )

    request = session["current_repair_request"]
    graph = translation.get("obligation_graph")
    if not isinstance(graph, Mapping):
        raise V06DecompositionProposerError(
            "proof translation lacks proof-obligation graph"
        )

    core = {
        "format": DECOMPOSITION_PROPOSER_REQUEST_FORMAT_V06,
        "protocol": DECOMPOSITION_PROPOSER_PROTOCOL_V06,
        "search_id": session.get("search_id"),
        "session_sha256": session.get("session_sha256"),
        "inventory_commitment_sha256": inventory_commitment,
        "translation_plan_sha256": translation.get("plan_sha256"),
        "claim_ir_sha256": claim_ir.get("claim_ir_sha256"),
        "obligation_graph_sha256": graph.get("graph_sha256"),
        "repair_request_sha256": request.get("repair_request_sha256"),
        "target": {
            "proposal_id": target_proposal_id,
            "obligation_id": task.get("obligation_id"),
            "candidate_snapshot_sha256": task.get(
                "candidate_snapshot_sha256"
            ),
            "claim": _json_clone(claim),
            "candidate_status": candidate.get("status"),
            "confidence": candidate.get("confidence"),
            "decomposition": _json_clone(decomposition),
            "artifact_ids": sorted(
                str(item)
                for item in candidate.get("artifact_ids", [])
                if isinstance(item, str)
            ),
            "assumptions": _json_clone(candidate.get("assumptions", [])),
        },
        "project_inventory": _inventory_metadata(discovery),
        "existing_ids": {
            "proposal_ids": active_proposal_ids,
            "claim_ids": existing_claim_ids,
        },
        "available_authorities": {
            "certified_checkers": _checker_vocabulary(),
            "signed_external_validators": _external_validator_vocabulary(),
        },
        "allowed_strategies": [
            "certified_checker_child",
            "signed_external_validator_child",
            "further_decomposition_child",
            "required_assumption_child",
            "abstain_irreducible_or_insufficient_evidence",
        ],
        "bounds": {
            "max_children_this_action": max_children,
            "max_total_active_proposals": MAX_PROOF_SEARCH_PROPOSALS_V06,
            "remaining_proposal_slots": remaining_slots,
            "max_decomposition_depth": MAX_PROOF_SEARCH_DECOMPOSITION_DEPTH_V06,
            "parent_depth": depth,
            "remaining_depth": remaining_depth,
            "child_confidence_may_not_exceed": candidate.get("confidence"),
        },
        "inspection_contract": (
            __import__(
                "pcs.artifact_inspection_v06",
                fromlist=["artifact_inspection_contract_v06"],
            ).artifact_inspection_contract_v06()
        ),
        "response_contract": {
            "format": DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06,
            "decisions": ["decompose", "abstain"],
            "decompose_requires": [
                "1..max_children_this_action child proposals",
                f"every child decomposition.parent_claim_id == {claim_id}",
                "every child relation is non-root",
                "all child proposal and claim ids are fresh",
                "all child dependencies name existing or sibling claim ids",
                "child confidence does not exceed parent confidence",
            ],
            "abstain_requires": [
                "non-empty reason",
                "no child proposals",
            ],
        },
        "authority": {
            "proposer_trusted": False,
            "request_contains_artifact_bytes": False,
            "model_may_set_authoritative": False,
            "model_may_rewrite_parent": False,
            "children_require_deterministic_recompilation": True,
            "children_require_human_review": True,
            "replay_and_lean_authority_still_required": True,
            "abstention_is_preferred_to_fabricated_grounding": True,
        },
    }
    return {
        **core,
        "decomposition_request_sha256": _commitment(core),
    }


def verify_decomposition_proposer_request_v06(
    project_root: str | Path,
    session: Mapping[str, Any],
    request: Mapping[str, Any],
) -> None:
    target = request.get("target")
    if not isinstance(target, Mapping):
        raise V06DecompositionProposerError(
            "decomposition request lacks target object"
        )
    proposal_id = target.get("proposal_id")
    if not isinstance(proposal_id, str):
        raise V06DecompositionProposerError(
            "decomposition request lacks target proposal id"
        )
    expected = build_decomposition_proposer_request_v06(
        project_root,
        session,
        proposal_id=proposal_id,
    )
    if request != expected:
        raise V06DecompositionProposerError(
            "decomposition proposer request does not exactly match current committed search state"
        )


def compile_decomposition_proposer_response_v06(
    project_root: str | Path,
    session: Mapping[str, Any],
    request: Mapping[str, Any],
    response: Mapping[str, Any],
    *,
    inspection_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    verify_decomposition_proposer_request_v06(
        project_root,
        session,
        request,
    )
    unexpected_response = sorted(
        set(response) - _ALLOWED_RESPONSE_KEYS_V06
    )
    if unexpected_response:
        raise V06DecompositionProposerError(
            "decomposition response contains unsupported fields: "
            f"{unexpected_response}"
        )
    if response.get("format") != DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06:
        raise V06DecompositionProposerError(
            f"unsupported decomposition proposer response format: {response.get('format')!r}"
        )
    if response.get("decomposition_request_sha256") != request.get(
        "decomposition_request_sha256"
    ):
        raise V06DecompositionProposerError(
            "decomposition response is bound to a different request"
        )
    if response.get("search_id") != session.get("search_id"):
        raise V06DecompositionProposerError(
            "decomposition response is bound to a different search"
        )
    if response.get("inventory_commitment_sha256") != session.get(
        "inventory_commitment_sha256"
    ):
        raise V06DecompositionProposerError(
            "decomposition response is bound to a different project inventory"
        )

    claimed_inspection = response.get("inspection_result_sha256")
    if claimed_inspection is None and inspection_result is not None:
        raise V06DecompositionProposerError(
            "inspection result was supplied but the decomposition response does not bind it"
        )
    if claimed_inspection is not None:
        if (
            not isinstance(claimed_inspection, str)
            or len(claimed_inspection) != 64
            or any(ch not in "0123456789abcdef" for ch in claimed_inspection)
        ):
            raise V06DecompositionProposerError(
                "inspection_result_sha256 must be a lowercase SHA-256 hex string"
            )
        if inspection_result is None:
            raise V06DecompositionProposerError(
                "decomposition response binds an inspection result but none was supplied"
            )
        try:
            from .artifact_inspection_v06 import (
                V06ArtifactInspectionError,
                verify_artifact_inspection_result_v06,
            )

            verify_artifact_inspection_result_v06(
                project_root,
                session,
                request,
                inspection_result,
            )
        except V06ArtifactInspectionError as exc:
            raise V06DecompositionProposerError(
                f"bound artifact inspection result is invalid: {exc}"
            ) from exc
        if inspection_result.get("inspection_result_sha256") != claimed_inspection:
            raise V06DecompositionProposerError(
                "decomposition response binds a different artifact inspection result"
            )

    proposer = response.get("proposer")
    if not isinstance(proposer, Mapping):
        raise V06DecompositionProposerError(
            "decomposition response requires proposer metadata"
        )
    unexpected_proposer = sorted(
        set(proposer) - _ALLOWED_PROPOSER_KEYS_V06
    )
    if unexpected_proposer:
        raise V06DecompositionProposerError(
            "decomposition proposer metadata contains unsupported fields: "
            f"{unexpected_proposer}"
        )
    if proposer.get("kind") != "external_model":
        raise V06DecompositionProposerError(
            "decomposition proposer kind must be 'external_model'"
        )
    proposer_name = _nonempty(
        proposer.get("name"),
        label="decomposition proposer name",
    )
    decision = response.get("decision")
    response_sha256 = _commitment(response)

    if decision == "abstain":
        children = response.get("children", [])
        if children not in (None, []):
            raise V06DecompositionProposerError(
                "abstaining decomposition response may not include child proposals"
            )
        reason = _nonempty(
            response.get("reason"),
            label="decomposition abstention reason",
        )
        return {
            "format": DECOMPOSITION_PROPOSER_COMPILATION_FORMAT_V06,
            "protocol": DECOMPOSITION_PROPOSER_PROTOCOL_V06,
            "status": "ABSTAINED_NO_REPAIR",
            "decomposition_request_sha256": request[
                "decomposition_request_sha256"
            ],
            "decomposition_response_sha256": response_sha256,
            "search_id": session.get("search_id"),
            "inspection_result_sha256": claimed_inspection,
            "reason": reason,
            "repair_response": None,
            "authority": {
                "sets_authoritative": False,
                "changes_search_state": False,
                "human_or_other_proposer_action_required": True,
            },
        }

    if decision != "decompose":
        raise V06DecompositionProposerError(
            "decomposition response decision must be 'decompose' or 'abstain'"
        )
    children = response.get("children")
    if not isinstance(children, list):
        raise V06DecompositionProposerError(
            "decompose response children must be an array"
        )
    max_children = int(request["bounds"]["max_children_this_action"])
    if not 1 <= len(children) <= max_children:
        raise V06DecompositionProposerError(
            f"decompose response child count must be in [1,{max_children}]"
        )

    allowed_check_types = (
        set(CERTIFIED_BUILTIN_CHECK_TYPES_V06)
        | set(EXTERNAL_VALIDATOR_CHECK_TYPES_V06)
    )
    for index, child in enumerate(children):
        if not isinstance(child, Mapping):
            raise V06DecompositionProposerError(
                f"decomposition child {index} must be an object"
            )
        check = child.get("check")
        if check is None:
            continue
        if not isinstance(check, Mapping):
            raise V06DecompositionProposerError(
                f"decomposition child {index} check must be an object"
            )
        check_type = check.get("type")
        if check_type not in allowed_check_types:
            raise V06DecompositionProposerError(
                f"decomposition child {index} check type {check_type!r} is "
                "outside the advertised certified/external authority vocabulary; "
                "decompose further or abstain instead"
            )

    target = request["target"]
    repair_request = session["current_repair_request"]
    repair_response = {
        "format": PROOF_REPAIR_RESPONSE_FORMAT_V06,
        "repair_request_sha256": repair_request[
            "repair_request_sha256"
        ],
        "obligation_graph_sha256": repair_request[
            "obligation_graph_sha256"
        ],
        "inventory_commitment_sha256": repair_request[
            "inventory_commitment_sha256"
        ],
        "proposer": {
            "kind": "external_model",
            "name": proposer_name,
            "version": proposer.get("version"),
            "model_family": proposer.get("model_family"),
        },
        "repairs": [
            {
                "obligation_id": target["obligation_id"],
                "proposal_id": target["proposal_id"],
                "action": "decompose_claim",
                "child_proposals": _json_clone(children),
            }
        ],
    }

    try:
        preview = compile_proof_repair_response_v06(
            session["current_translation"],
            repair_request,
            repair_response,
        )
    except V06ProofRepairError as exc:
        raise V06DecompositionProposerError(
            f"decomposition response failed deterministic repair compilation: {exc}"
        ) from exc

    return {
        "format": DECOMPOSITION_PROPOSER_COMPILATION_FORMAT_V06,
        "protocol": DECOMPOSITION_PROPOSER_PROTOCOL_V06,
        "status": "COMPILED_REPAIR_RESPONSE",
        "decomposition_request_sha256": request[
            "decomposition_request_sha256"
        ],
        "decomposition_response_sha256": response_sha256,
        "search_id": session.get("search_id"),
        "inspection_result_sha256": claimed_inspection,
        "repair_response": repair_response,
        "preview_compiled_repair_sha256": preview.get(
            "compiled_repair_sha256"
        ),
        "introduced_proposal_ids": sorted(
            str(item.get("id"))
            for item in children
            if isinstance(item, Mapping)
            and isinstance(item.get("id"), str)
        ),
        "authority": {
            "sets_authoritative": False,
            "changes_search_state": False,
            "must_pass_advance_proof_search_v06": True,
            "human_confirmation_still_required": True,
            "replay_and_lean_authority_still_required": True,
        },
    }


def _load_json(path: str | Path, *, label: str) -> dict[str, Any]:
    resolved = Path(path).resolve()
    try:
        value = strict_json_load(resolved)
    except (OSError, StrictJSONError) as exc:
        raise V06DecompositionProposerError(
            f"cannot load {label} {resolved}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise V06DecompositionProposerError(
            f"{label} root must be an object"
        )
    return value


def load_decomposition_proposer_request_v06(
    path: str | Path,
) -> dict[str, Any]:
    value = _load_json(path, label="decomposition proposer request")
    if value.get("format") != DECOMPOSITION_PROPOSER_REQUEST_FORMAT_V06:
        raise V06DecompositionProposerError(
            "decomposition proposer request has unsupported format"
        )
    return value


def load_decomposition_proposer_response_v06(
    path: str | Path,
) -> dict[str, Any]:
    value = _load_json(path, label="decomposition proposer response")
    if value.get("format") != DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06:
        raise V06DecompositionProposerError(
            "decomposition proposer response has unsupported format"
        )
    return value


def _write_json(
    value: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool,
    label: str,
) -> str:
    output = Path(path).resolve()
    if output.exists() and not overwrite:
        raise V06DecompositionProposerError(
            f"refusing to overwrite existing {label}: {output}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            dict(value),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return str(output)


def write_decomposition_proposer_request_v06(
    request: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> str:
    if request.get("format") != DECOMPOSITION_PROPOSER_REQUEST_FORMAT_V06:
        raise V06DecompositionProposerError(
            "refusing to write invalid decomposition proposer request"
        )
    return _write_json(
        request,
        path,
        overwrite=overwrite,
        label="decomposition proposer request",
    )


def write_decomposition_repair_response_v06(
    compilation: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> str:
    if (
        compilation.get("format")
        != DECOMPOSITION_PROPOSER_COMPILATION_FORMAT_V06
        or compilation.get("status") != "COMPILED_REPAIR_RESPONSE"
        or not isinstance(compilation.get("repair_response"), Mapping)
    ):
        raise V06DecompositionProposerError(
            "decomposition compilation does not contain a repair response"
        )
    return _write_json(
        compilation["repair_response"],
        path,
        overwrite=overwrite,
        label="compiled decomposition repair response",
    )
