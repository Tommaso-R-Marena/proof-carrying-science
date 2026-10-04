from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_inspection_v06 import (
    ARTIFACT_INSPECTION_QUERY_FORMAT_V06,
    ARTIFACT_INSPECTION_RESULT_FORMAT_V06,
    V06ArtifactInspectionError,
    inspect_artifacts_v06,
    verify_artifact_inspection_result_v06,
)
from .canonical_json import canonicalize_jcs_bytes
from .decomposition_proposer_v06 import (
    DECOMPOSITION_PROPOSER_REQUEST_FORMAT_V06,
    DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06,
    V06DecompositionProposerError,
    compile_decomposition_proposer_response_v06,
    verify_decomposition_proposer_request_v06,
)
from .jsonio import StrictJSONError, strict_json_load
from .proof_search_v06 import (
    PROOF_SEARCH_SESSION_FORMAT_V06,
    V06ProofSearchError,
    verify_proof_search_session_v06,
)


PROOF_SEARCH_DATA_USE_POLICY_FORMAT_V06 = "pcs-proof-search-data-use-policy-v1"
PROOF_SEARCH_RECORD_FORMAT_V06 = "pcs-proof-search-record-v1"
PROOF_SEARCH_CORPUS_FORMAT_V06 = "pcs-proof-search-corpus-v2"
PROOF_SEARCH_CORPUS_COMPILER_V06 = "pcs-proof-search-corpus-compiler/0.2"
PROOF_SEARCH_SPLIT_CONTRACT_V06 = "problem-group-sha256-80-10-10-v2"

_SOURCE_CLASSES = {
    "synthetic",
    "public",
    "partner_authorized",
    "internal_authorized",
}
_POLICY_KEYS = {
    "format",
    "source_class",
    "purpose",
    "content_export_allowed",
    "evaluation_allowed",
    "training_allowed",
    "authorization_reference",
}
_INTERACTION_FORMATS = {
    DECOMPOSITION_PROPOSER_REQUEST_FORMAT_V06,
    DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06,
    ARTIFACT_INSPECTION_QUERY_FORMAT_V06,
    ARTIFACT_INSPECTION_RESULT_FORMAT_V06,
}


class V06ProofSearchCorpusError(ValueError):
    pass


def _clone(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _commitment(value: Any) -> str:
    return hashlib.sha256(canonicalize_jcs_bytes(value)).hexdigest()


def _id_hash(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return _commitment({"id": value})


def _require_bool(value: Any, *, label: str) -> bool:
    if not isinstance(value, bool):
        raise V06ProofSearchCorpusError(f"{label} must be boolean")
    return value


def _default_policy() -> dict[str, Any]:
    core = {
        "explicit_policy": False,
        "source_class": "unspecified",
        "purpose": "operational_audit_only",
        "content_export_allowed": False,
        "evaluation_allowed": False,
        "training_allowed": False,
        "authorization_reference_sha256": None,
    }
    return {
        **core,
        "policy_sha256": _commitment(core),
    }


def validate_data_use_policy_v06(
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    unexpected = sorted(set(policy) - _POLICY_KEYS)
    if unexpected:
        raise V06ProofSearchCorpusError(
            f"data-use policy contains unsupported fields: {unexpected}"
        )
    if policy.get("format") != PROOF_SEARCH_DATA_USE_POLICY_FORMAT_V06:
        raise V06ProofSearchCorpusError(
            "data-use policy has unsupported format"
        )
    source_class = policy.get("source_class")
    if source_class not in _SOURCE_CLASSES:
        raise V06ProofSearchCorpusError(
            f"data-use source_class must be one of {sorted(_SOURCE_CLASSES)}"
        )
    purpose = policy.get("purpose")
    if not isinstance(purpose, str) or not purpose.strip():
        raise V06ProofSearchCorpusError(
            "data-use policy purpose must be non-empty"
        )
    content_export_allowed = _require_bool(
        policy.get("content_export_allowed"),
        label="content_export_allowed",
    )
    evaluation_allowed = _require_bool(
        policy.get("evaluation_allowed"),
        label="evaluation_allowed",
    )
    training_allowed = _require_bool(
        policy.get("training_allowed"),
        label="training_allowed",
    )
    authorization_reference = policy.get("authorization_reference")
    if authorization_reference is not None and (
        not isinstance(authorization_reference, str)
        or not authorization_reference.strip()
    ):
        raise V06ProofSearchCorpusError(
            "authorization_reference must be null or a non-empty string"
        )
    if training_allowed and not evaluation_allowed:
        raise V06ProofSearchCorpusError(
            "training_allowed requires evaluation_allowed"
        )
    if training_allowed and not content_export_allowed:
        raise V06ProofSearchCorpusError(
            "training_allowed requires content_export_allowed"
        )
    if (
        source_class in {"partner_authorized", "internal_authorized"}
        and (content_export_allowed or evaluation_allowed or training_allowed)
        and authorization_reference is None
    ):
        raise V06ProofSearchCorpusError(
            f"{source_class} data reuse requires authorization_reference"
        )

    normalized_core = {
        "explicit_policy": True,
        "source_class": source_class,
        "purpose": purpose.strip(),
        "content_export_allowed": content_export_allowed,
        "evaluation_allowed": evaluation_allowed,
        "training_allowed": training_allowed,
        "authorization_reference_sha256": (
            _commitment({"authorization_reference": authorization_reference})
            if authorization_reference is not None
            else None
        ),
    }
    return {
        **normalized_core,
        "policy_sha256": _commitment(
            {
                key: value
                for key, value in policy.items()
            }
        ),
    }


def load_data_use_policy_v06(
    path: str | Path,
) -> dict[str, Any]:
    resolved = Path(path).resolve()
    try:
        value = strict_json_load(resolved)
    except (OSError, StrictJSONError) as exc:
        raise V06ProofSearchCorpusError(
            f"cannot load proof-search data-use policy {resolved}: {exc}"
        ) from exc
    if not isinstance(value, Mapping):
        raise V06ProofSearchCorpusError(
            "proof-search data-use policy root must be an object"
        )
    validate_data_use_policy_v06(value)
    return dict(value)


def _problem_group_sha256(session: Mapping[str, Any]) -> str:
    return _commitment(
        {
            "initial_plan_sha256": session.get("initial_plan_sha256"),
            "inventory_commitment_sha256": session.get(
                "inventory_commitment_sha256"
            ),
            "initial_intent_anchors_sha256": session.get(
                "initial_intent_anchors_sha256"
            ),
        }
    )


def _split_for_problem_group(
    problem_group_sha256: str,
    policy: Mapping[str, Any],
) -> str:
    if policy.get("training_allowed") is True:
        bucket = int(
            hashlib.sha256(
                canonicalize_jcs_bytes(
                    {
                        "contract": PROOF_SEARCH_SPLIT_CONTRACT_V06,
                        "problem_group_sha256": problem_group_sha256,
                    }
                )
            ).hexdigest()[:8],
            16,
        ) % 100
        if bucket < 80:
            return "train"
        if bucket < 90:
            return "validation"
        return "test"
    if policy.get("evaluation_allowed") is True:
        return "evaluation"
    return "restricted"


def _load_interaction_documents(
    paths: Sequence[str | Path],
) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for raw_path in paths:
        path = Path(raw_path).resolve()
        try:
            value = strict_json_load(path)
        except (OSError, StrictJSONError) as exc:
            raise V06ProofSearchCorpusError(
                f"cannot load proof-search interaction {path}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise V06ProofSearchCorpusError(
                f"proof-search interaction root must be an object: {path}"
            )
        if value.get("format") not in _INTERACTION_FORMATS:
            raise V06ProofSearchCorpusError(
                f"unsupported proof-search interaction format in {path}: "
                f"{value.get('format')!r}"
            )
        documents.append(value)
    return documents


def _validated_session_index(
    final_session: Mapping[str, Any],
    historical_sessions: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    sessions: dict[str, Mapping[str, Any]] = {}
    final_search_id = final_session.get("search_id")
    final_inventory = final_session.get("inventory_commitment_sha256")
    for index, candidate in enumerate(
        [final_session, *historical_sessions]
    ):
        if not isinstance(candidate, Mapping):
            raise V06ProofSearchCorpusError(
                f"proof-search historical session {index} must be an object"
            )
        try:
            verify_proof_search_session_v06(candidate)
        except V06ProofSearchError as exc:
            raise V06ProofSearchCorpusError(
                f"invalid proof-search historical session {index}: {exc}"
            ) from exc
        if candidate.get("search_id") != final_search_id:
            raise V06ProofSearchCorpusError(
                "historical session belongs to a different proof search"
            )
        if candidate.get("inventory_commitment_sha256") != final_inventory:
            raise V06ProofSearchCorpusError(
                "historical session is bound to a different project inventory"
            )
        session_sha = candidate.get("session_sha256")
        if not isinstance(session_sha, str):
            raise V06ProofSearchCorpusError(
                "historical session lacks session_sha256"
            )
        existing = sessions.get(session_sha)
        if existing is not None and existing != candidate:
            raise V06ProofSearchCorpusError(
                "conflicting historical sessions share one session_sha256"
            )
        sessions[session_sha] = candidate
    return sessions


def _interaction_indexes(
    project_root: str | Path,
    final_session: Mapping[str, Any],
    session_index: Mapping[str, Mapping[str, Any]],
    documents: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, list[str]]]:
    root = Path(project_root).resolve()
    requests: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    inspection_results: dict[str, Mapping[str, Any]] = {}
    inspections_by_request: dict[str, list[str]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    payloads: dict[str, dict[str, Any]] = {}
    repair_to_interactions: dict[str, list[str]] = {}

    for document in documents:
        fmt = document.get("format")
        doc_sha = _commitment(document)
        payloads[doc_sha] = _clone(document)
        if fmt == DECOMPOSITION_PROPOSER_REQUEST_FORMAT_V06:
            bound_session_sha = document.get("session_sha256")
            bound_session = session_index.get(str(bound_session_sha))
            if bound_session is None:
                raise V06ProofSearchCorpusError(
                    "decomposition request requires its exact historical "
                    "proof-search session; supply that snapshot"
                )
            try:
                verify_decomposition_proposer_request_v06(
                    root,
                    bound_session,
                    document,
                )
            except V06DecompositionProposerError as exc:
                raise V06ProofSearchCorpusError(
                    f"invalid decomposition request interaction: {exc}"
                ) from exc
            request_sha = document.get("decomposition_request_sha256")
            if not isinstance(request_sha, str):
                raise V06ProofSearchCorpusError(
                    "decomposition request lacks request commitment"
                )
            existing = requests.get(request_sha)
            if existing is not None and existing[0] != document:
                raise V06ProofSearchCorpusError(
                    "conflicting decomposition requests share one commitment"
                )
            requests[request_sha] = (document, bound_session)
            target = document.get("target")
            summaries[doc_sha] = {
                "document_sha256": doc_sha,
                "format": fmt,
                "decomposition_request_sha256": request_sha,
                "source_session_sha256": bound_session_sha,
                "target_proposal_id_sha256": _id_hash(
                    target.get("proposal_id")
                    if isinstance(target, Mapping)
                    else None
                ),
                "target_claim_id_sha256": _id_hash(
                    target.get("claim", {}).get("id")
                    if isinstance(target, Mapping)
                    and isinstance(target.get("claim"), Mapping)
                    else None
                ),
                "kind": "DECOMPOSITION_REQUEST",
            }

    for document in documents:
        fmt = document.get("format")
        doc_sha = _commitment(document)
        if fmt == ARTIFACT_INSPECTION_QUERY_FORMAT_V06:
            request_sha = document.get("decomposition_request_sha256")
            request_binding = requests.get(str(request_sha))
            if request_binding is None:
                raise V06ProofSearchCorpusError(
                    "inspection query lacks matching verified decomposition request"
                )
            request, bound_session = request_binding
            try:
                expected_result = inspect_artifacts_v06(
                    root,
                    bound_session,
                    request,
                    document,
                )
            except V06ArtifactInspectionError as exc:
                raise V06ProofSearchCorpusError(
                    f"invalid artifact inspection query interaction: {exc}"
                ) from exc
            operations = document.get("operations")
            summaries[doc_sha] = {
                "document_sha256": doc_sha,
                "format": fmt,
                "decomposition_request_sha256": request_sha,
                "kind": "INSPECTION_QUERY",
                "operation_count": (
                    len(operations) if isinstance(operations, list) else 0
                ),
                "views": sorted(
                    str(item.get("view"))
                    for item in operations
                    if isinstance(item, Mapping)
                ) if isinstance(operations, list) else [],
                "expected_inspection_result_sha256": expected_result.get(
                    "inspection_result_sha256"
                ),
            }
        elif fmt == ARTIFACT_INSPECTION_RESULT_FORMAT_V06:
            request_sha = document.get("decomposition_request_sha256")
            request_binding = requests.get(str(request_sha))
            if request_binding is None:
                raise V06ProofSearchCorpusError(
                    "inspection result lacks matching verified decomposition request"
                )
            request, bound_session = request_binding
            try:
                verify_artifact_inspection_result_v06(
                    root,
                    bound_session,
                    request,
                    document,
                )
            except V06ArtifactInspectionError as exc:
                raise V06ProofSearchCorpusError(
                    f"invalid artifact inspection result interaction: {exc}"
                ) from exc
            result_sha = document.get("inspection_result_sha256")
            if not isinstance(result_sha, str):
                raise V06ProofSearchCorpusError(
                    "inspection result lacks result commitment"
                )
            existing = inspection_results.get(result_sha)
            if existing is not None and existing != document:
                raise V06ProofSearchCorpusError(
                    "conflicting inspection results share one commitment"
                )
            inspection_results[result_sha] = document
            inspections_by_request.setdefault(str(request_sha), []).append(
                result_sha
            )
            observations = document.get("observations")
            summaries[doc_sha] = {
                "document_sha256": doc_sha,
                "format": fmt,
                "decomposition_request_sha256": request_sha,
                "inspection_result_sha256": result_sha,
                "kind": "INSPECTION_RESULT",
                "observation_count": (
                    len(observations)
                    if isinstance(observations, list)
                    else 0
                ),
                "views": sorted(
                    {
                        str(item.get("view"))
                        for item in observations
                        if isinstance(item, Mapping)
                    }
                ) if isinstance(observations, list) else [],
            }

    for document in documents:
        if document.get("format") != DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06:
            continue
        doc_sha = _commitment(document)
        request_sha = document.get("decomposition_request_sha256")
        request_binding = requests.get(str(request_sha))
        if request_binding is None:
            raise V06ProofSearchCorpusError(
                "decomposition response lacks matching verified request"
            )
        request, bound_session = request_binding
        inspection_sha = document.get("inspection_result_sha256")
        inspection = (
            inspection_results.get(str(inspection_sha))
            if inspection_sha is not None
            else None
        )
        try:
            compilation = compile_decomposition_proposer_response_v06(
                root,
                bound_session,
                request,
                document,
                inspection_result=inspection,
            )
        except V06DecompositionProposerError as exc:
            raise V06ProofSearchCorpusError(
                f"invalid decomposition response interaction: {exc}"
            ) from exc
        repair_response = compilation.get("repair_response")
        repair_sha = (
            _commitment(repair_response)
            if isinstance(repair_response, Mapping)
            else None
        )
        refs = [doc_sha]
        request_doc_sha = _commitment(request)
        refs.append(request_doc_sha)
        if inspection is not None:
            refs.append(_commitment(inspection))
            query = inspection.get("artifact_inspection_query")
            if isinstance(query, Mapping):
                refs.append(_commitment(query))
        if repair_sha is not None:
            repair_to_interactions.setdefault(repair_sha, []).extend(refs)
        children = document.get("children")
        summaries[doc_sha] = {
            "document_sha256": doc_sha,
            "format": document.get("format"),
            "decomposition_request_sha256": request_sha,
            "inspection_result_sha256": inspection_sha,
            "kind": "DECOMPOSITION_RESPONSE",
            "decision": document.get("decision"),
            "child_count": (
                len(children) if isinstance(children, list) else 0
            ),
            "repair_response_sha256": repair_sha,
            "changes_search_state": repair_sha is not None,
        }

    ordered = [
        summaries[key]
        for key in sorted(summaries)
    ]
    return (
        ordered,
        payloads,
        {
            key: sorted(set(value))
            for key, value in sorted(repair_to_interactions.items())
        },
    )


def _metadata_action_projection(
    action: Mapping[str, Any],
) -> dict[str, Any]:
    emitted_hashes = action.get("emitted_proposal_sha256")
    return {
        "action_record_sha256": action.get("action_record_sha256"),
        "action": action.get("action"),
        "mode": action.get("mode"),
        "obligation_id_sha256": _id_hash(action.get("obligation_id")),
        "proposal_id_sha256": _id_hash(action.get("proposal_id")),
        "candidate_snapshot_sha256": (
            action.get("task", {}).get("candidate_snapshot_sha256")
            if isinstance(action.get("task"), Mapping)
            else None
        ),
        "emitted_proposal_count": (
            len(emitted_hashes)
            if isinstance(emitted_hashes, Mapping)
            else 0
        ),
        "emitted_proposal_sha256": (
            sorted(str(value) for value in emitted_hashes.values())
            if isinstance(emitted_hashes, Mapping)
            else []
        ),
    }


def _step_examples(
    session: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    include_content: bool,
    repair_to_interactions: Mapping[str, Sequence[str]],
) -> list[dict[str, Any]]:
    problem_group = _problem_group_sha256(session)
    split = _split_for_problem_group(problem_group, policy)
    trajectory = session.get("trajectory")
    steps = (
        trajectory.get("steps")
        if isinstance(trajectory, Mapping)
        else None
    )
    if not isinstance(steps, list):
        raise V06ProofSearchCorpusError(
            "validated proof-search session lacks trajectory steps"
        )

    examples: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        before = step.get("metrics_before")
        after = step.get("metrics_after")
        if not isinstance(before, Mapping) or not isinstance(after, Mapping):
            raise V06ProofSearchCorpusError(
                "proof-search step lacks before/after metrics"
            )
        actions = step.get("action_records")
        normalized_actions = (
            [item for item in actions if isinstance(item, Mapping)]
            if isinstance(actions, list)
            else []
        )
        if not normalized_actions:
            normalized_actions = [
                {
                    "action_record_sha256": None,
                    "action": "LEGACY_HASH_ONLY",
                    "mode": "legacy",
                    "obligation_id": None,
                    "proposal_id": None,
                    "task": None,
                    "emitted_proposals": [],
                    "emitted_proposal_sha256": {},
                }
            ]

        repair_sha = step.get("repair_response_sha256")
        interaction_refs = (
            list(repair_to_interactions.get(str(repair_sha), []))
            if isinstance(repair_sha, str)
            else []
        )
        for action in normalized_actions:
            metadata_action = _metadata_action_projection(action)
            identity_core = {
                "problem_group_sha256": problem_group,
                "iteration": int(step.get("iteration", 0)),
                "action": metadata_action,
                "state": {
                    "before_state_sha256": step.get("before_state_sha256"),
                    "before_plan_sha256": step.get("before_plan_sha256"),
                    "before_graph_sha256": step.get("before_graph_sha256"),
                    "repair_request_sha256": step.get(
                        "repair_request_sha256"
                    ),
                    "repair_response_sha256": repair_sha,
                },
                "transition": {
                    "after_state_sha256": step.get("after_state_sha256"),
                    "after_plan_sha256": step.get("after_plan_sha256"),
                    "after_graph_sha256": step.get("after_graph_sha256"),
                    "compiled_repair_sha256": step.get(
                        "compiled_repair_sha256"
                    ),
                    "metrics_before": _clone(before),
                    "metrics_after": _clone(after),
                },
                "labels": {
                    "outcome": step.get("outcome"),
                    "objective_progress": (
                        step.get("outcome") == "OBJECTIVE_PROGRESS"
                    ),
                    "cycle_detected": (
                        step.get("outcome") == "CYCLE_DETECTED"
                    ),
                    "diagnostic_reward": int(
                        step.get("diagnostic_reward", 0)
                    ),
                    "label_scope": "SEARCH_BEHAVIOR_ONLY",
                    "scientific_truth_label": False,
                    "proof_authority_label": False,
                    "credit_assignment": "STEP_LEVEL_SHARED",
                },
                "interaction_refs": sorted(set(interaction_refs)),
                "content_available": (
                    action.get("action") != "LEGACY_HASH_ONLY"
                ),
                "authority": {
                    "record_is_authoritative": False,
                    "diagnostic_reward_sets_authority": False,
                    "human_confirmation_required": True,
                    "replay_and_lean_authority_required": True,
                },
            }
            example = {
                "example_id": _commitment(identity_core),
                **identity_core,
                "split": split,
                "content_included": bool(
                    include_content
                    and action.get("action") != "LEGACY_HASH_ONLY"
                ),
            }
            if example["content_included"]:
                example["content"] = {
                    "task": _clone(action.get("task")),
                    "emitted_proposals": _clone(
                        action.get("emitted_proposals", [])
                    ),
                }
            examples.append(example)
    return sorted(examples, key=lambda item: item["example_id"])


def build_proof_search_record_v06(
    project_root: str | Path,
    session: Mapping[str, Any],
    *,
    interaction_documents: Sequence[Mapping[str, Any]] = (),
    historical_sessions: Sequence[Mapping[str, Any]] = (),
    data_use_policy: Mapping[str, Any] | None = None,
    include_content: bool = False,
) -> dict[str, Any]:
    if session.get("format") != PROOF_SEARCH_SESSION_FORMAT_V06:
        raise V06ProofSearchCorpusError(
            "proof-search record requires a v0.6 proof-search session"
        )
    try:
        verify_proof_search_session_v06(session)
    except V06ProofSearchError as exc:
        raise V06ProofSearchCorpusError(
            f"invalid proof-search session: {exc}"
        ) from exc

    policy = (
        validate_data_use_policy_v06(data_use_policy)
        if data_use_policy is not None
        else _default_policy()
    )
    if include_content and policy.get("content_export_allowed") is not True:
        raise V06ProofSearchCorpusError(
            "content-bearing proof-search export requires an explicit "
            "data-use policy with content_export_allowed=true"
        )

    session_index = _validated_session_index(
        session,
        historical_sessions,
    )
    interactions, payloads, repair_to_interactions = _interaction_indexes(
        project_root,
        session,
        session_index,
        interaction_documents,
    )
    examples = _step_examples(
        session,
        policy=policy,
        include_content=include_content,
        repair_to_interactions=repair_to_interactions,
    )
    if include_content:
        for example in examples:
            if example.get("content_included") is not True:
                continue
            content = example.get("content")
            if not isinstance(content, dict):
                raise V06ProofSearchCorpusError(
                    "content-bearing example lacks content object"
                )
            content["interaction_payloads"] = {
                ref: _clone(payloads[ref])
                for ref in example.get("interaction_refs", [])
                if ref in payloads
            }

    problem_group = _problem_group_sha256(session)
    split = _split_for_problem_group(problem_group, policy)
    core: dict[str, Any] = {
        "format": PROOF_SEARCH_RECORD_FORMAT_V06,
        "compiler": PROOF_SEARCH_CORPUS_COMPILER_V06,
        "source_session": {
            "session_sha256": session.get("session_sha256"),
            "search_id_sha256": _id_hash(session.get("search_id")),
            "problem_group_sha256": problem_group,
            "trajectory_sha256": session.get(
                "trajectory", {}
            ).get("trajectory_sha256"),
            "inventory_commitment_sha256": session.get(
                "inventory_commitment_sha256"
            ),
            "initial_plan_sha256": session.get("initial_plan_sha256"),
            "final_status": session.get("status"),
            "iteration": session.get("iteration"),
        },
        "data_use": _clone(policy),
        "split": split,
        "interaction_summaries": interactions,
        "examples": examples,
        "summary": {
            "trajectory_steps": session.get(
                "summary", {}
            ).get("trajectory_steps", 0),
            "examples": len(examples),
            "interactions": len(interactions),
            "content_included": include_content,
            "evaluation_allowed": policy.get("evaluation_allowed") is True,
            "training_allowed": policy.get("training_allowed") is True,
            "legacy_hash_only_examples": sum(
                1
                for example in examples
                if example["action"]["action"] == "LEGACY_HASH_ONLY"
            ),
        },
        "trust_model": {
            "record_is_proof_authority": False,
            "labels_are_scientific_truth": False,
            "labels_are_search_behavior_only": True,
            "training_eligibility_comes_only_from_data_use_policy": True,
            "human_confirmation_replay_and_lean_remain_authoritative": True,
        },
    }
    return {
        **core,
        "record_sha256": _commitment(core),
    }


def build_proof_search_record_from_files_v06(
    project_root: str | Path,
    session_path: str | Path,
    *,
    interaction_paths: Sequence[str | Path] = (),
    historical_session_paths: Sequence[str | Path] = (),
    data_use_policy_path: str | Path | None = None,
    include_content: bool = False,
) -> dict[str, Any]:
    try:
        session = strict_json_load(Path(session_path).resolve())
    except (OSError, StrictJSONError) as exc:
        raise V06ProofSearchCorpusError(
            f"cannot load proof-search session: {exc}"
        ) from exc
    if not isinstance(session, Mapping):
        raise V06ProofSearchCorpusError(
            "proof-search session root must be an object"
        )
    policy = (
        load_data_use_policy_v06(data_use_policy_path)
        if data_use_policy_path is not None
        else None
    )
    interactions = _load_interaction_documents(interaction_paths)
    historical_sessions: list[Mapping[str, Any]] = []
    for raw_path in historical_session_paths:
        resolved = Path(raw_path).resolve()
        try:
            value = strict_json_load(resolved)
        except (OSError, StrictJSONError) as exc:
            raise V06ProofSearchCorpusError(
                f"cannot load historical proof-search session {resolved}: {exc}"
            ) from exc
        if not isinstance(value, Mapping):
            raise V06ProofSearchCorpusError(
                f"historical proof-search session root must be an object: {resolved}"
            )
        historical_sessions.append(value)
    return build_proof_search_record_v06(
        project_root,
        session,
        interaction_documents=interactions,
        historical_sessions=historical_sessions,
        data_use_policy=policy,
        include_content=include_content,
    )


def _verify_record(record: Mapping[str, Any]) -> None:
    if record.get("format") != PROOF_SEARCH_RECORD_FORMAT_V06:
        raise V06ProofSearchCorpusError(
            "proof-search record has unsupported format"
        )
    claimed = record.get("record_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise V06ProofSearchCorpusError(
            "proof-search record lacks a valid record_sha256"
        )
    core = {
        key: _clone(value)
        for key, value in record.items()
        if key != "record_sha256"
    }
    if _commitment(core) != claimed:
        raise V06ProofSearchCorpusError(
            "proof-search record commitment does not match contents"
        )
    data_use = record.get("data_use")
    if not isinstance(data_use, Mapping):
        raise V06ProofSearchCorpusError(
            "proof-search record lacks data-use metadata"
        )
    if record.get("summary", {}).get("content_included") is True and (
        data_use.get("content_export_allowed") is not True
    ):
        raise V06ProofSearchCorpusError(
            "proof-search record includes content without data-use authorization"
        )
    examples = record.get("examples")
    if not isinstance(examples, list):
        raise V06ProofSearchCorpusError(
            "proof-search record examples must be an array"
        )
    for example in examples:
        if not isinstance(example, Mapping):
            raise V06ProofSearchCorpusError(
                "proof-search record example must be an object"
            )
        identity_core = {
            key: _clone(value)
            for key, value in example.items()
            if key not in {
                "example_id",
                "split",
                "content_included",
                "content",
            }
        }
        if (
            not isinstance(example.get("example_id"), str)
            or _commitment(identity_core) != example.get("example_id")
        ):
            raise V06ProofSearchCorpusError(
                "proof-search example identity commitment is invalid"
            )
        if example.get("content_included") is True:
            if data_use.get("content_export_allowed") is not True:
                raise V06ProofSearchCorpusError(
                    "proof-search example content violates data-use policy"
                )
            if not isinstance(example.get("content"), Mapping):
                raise V06ProofSearchCorpusError(
                    "content-bearing proof-search example lacks content"
                )
        elif "content" in example:
            raise V06ProofSearchCorpusError(
                "metadata-only proof-search example unexpectedly contains content"
            )


def build_proof_search_corpus_v06(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    unique: dict[str, dict[str, Any]] = {}
    examples: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise V06ProofSearchCorpusError(
                f"proof-search corpus record {index} must be an object"
            )
        _verify_record(record)
        record_sha = str(record["record_sha256"])
        existing = unique.get(record_sha)
        if existing is not None and existing != record:
            raise V06ProofSearchCorpusError(
                "proof-search record hash collision with different contents"
            )
        unique[record_sha] = _clone(record)

        source = record.get("source_session")
        if not isinstance(source, Mapping):
            raise V06ProofSearchCorpusError(
                "proof-search record lacks source-session metadata"
            )
        for example in record.get("examples", []):
            if not isinstance(example, Mapping):
                continue
            example_id = example.get("example_id")
            if not isinstance(example_id, str):
                raise V06ProofSearchCorpusError(
                    "proof-search example lacks example_id"
                )
            existing_example = examples.get(example_id)
            policy = record["data_use"]
            projected = {
                **_clone(example),
                "source_record_sha256s": [record_sha],
                "data_use": {
                    "content_export_allowed": (
                        policy.get("content_export_allowed") is True
                    ),
                    "evaluation_allowed": (
                        policy.get("evaluation_allowed") is True
                    ),
                    "training_allowed": (
                        policy.get("training_allowed") is True
                    ),
                    "source_policy_sha256s": [
                        str(policy.get("policy_sha256"))
                    ],
                    "aggregation_rule": "MOST_RESTRICTIVE",
                },
            }
            if existing_example is None:
                examples[example_id] = projected
            else:
                identity_keys_excluded = {
                    "source_record_sha256s",
                    "data_use",
                    "split",
                    "content_included",
                    "content",
                }
                comparable = {
                    key: value
                    for key, value in existing_example.items()
                    if key not in identity_keys_excluded
                }
                incoming = {
                    key: value
                    for key, value in projected.items()
                    if key not in identity_keys_excluded
                }
                if comparable != incoming:
                    raise V06ProofSearchCorpusError(
                        "proof-search example hash collision with different identity content"
                    )

                existing_content = existing_example.get("content")
                incoming_content = projected.get("content")
                if (
                    existing_content is not None
                    and incoming_content is not None
                    and existing_content != incoming_content
                ):
                    raise V06ProofSearchCorpusError(
                        "proof-search example identity maps to conflicting authorized content"
                    )

                existing_example["source_record_sha256s"] = sorted(
                    set(existing_example["source_record_sha256s"])
                    | {record_sha}
                )
                existing_policy = existing_example["data_use"]
                aggregated = {
                    "content_export_allowed": (
                        existing_policy.get("content_export_allowed") is True
                        and policy.get("content_export_allowed") is True
                    ),
                    "evaluation_allowed": (
                        existing_policy.get("evaluation_allowed") is True
                        and policy.get("evaluation_allowed") is True
                    ),
                    "training_allowed": (
                        existing_policy.get("training_allowed") is True
                        and policy.get("training_allowed") is True
                    ),
                    "source_policy_sha256s": sorted(
                        set(existing_policy.get("source_policy_sha256s", []))
                        | {str(policy.get("policy_sha256"))}
                    ),
                    "aggregation_rule": "MOST_RESTRICTIVE",
                }
                existing_example["data_use"] = aggregated
                existing_example["split"] = _split_for_problem_group(
                    str(existing_example["problem_group_sha256"]),
                    aggregated,
                )

                all_sources_include_content = (
                    existing_example.get("content_included") is True
                    and projected.get("content_included") is True
                    and aggregated["content_export_allowed"] is True
                )
                if all_sources_include_content:
                    existing_example["content_included"] = True
                    if existing_content is None and incoming_content is not None:
                        existing_example["content"] = _clone(incoming_content)
                else:
                    existing_example["content_included"] = False
                    existing_example.pop("content", None)

    ordered_records = []
    for key in sorted(unique):
        record = unique[key]
        ordered_records.append(
            {
                "record_sha256": record["record_sha256"],
                "source_session": _clone(record["source_session"]),
                "data_use": _clone(record["data_use"]),
                "split": record.get("split"),
                "summary": _clone(record.get("summary", {})),
                "trust_model": _clone(record.get("trust_model", {})),
            }
        )
    ordered_examples = [
        examples[key]
        for key in sorted(examples)
    ]
    split_counts: dict[str, int] = {}
    outcome_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    for example in ordered_examples:
        split = str(example.get("split"))
        split_counts[split] = split_counts.get(split, 0) + 1
        outcome = str(example.get("labels", {}).get("outcome"))
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        action = str(example.get("action", {}).get("action"))
        action_counts[action] = action_counts.get(action, 0) + 1

    core = {
        "format": PROOF_SEARCH_CORPUS_FORMAT_V06,
        "compiler": PROOF_SEARCH_CORPUS_COMPILER_V06,
        "split_contract": {
            "id": PROOF_SEARCH_SPLIT_CONTRACT_V06,
            "training_split": {
                "train_percent": 80,
                "validation_percent": 10,
                "test_percent": 10,
            },
            "evaluation_only_split": "evaluation",
            "unauthorized_split": "restricted",
            "grouping_key": "problem_group_sha256",
        },
        "records": ordered_records,
        "examples": ordered_examples,
        "summary": {
            "records": len(ordered_records),
            "examples": len(ordered_examples),
            "split_counts": {
                key: split_counts[key]
                for key in sorted(split_counts)
            },
            "outcome_counts": {
                key: outcome_counts[key]
                for key in sorted(outcome_counts)
            },
            "action_counts": {
                key: action_counts[key]
                for key in sorted(action_counts)
            },
            "training_eligible_examples": sum(
                1
                for example in ordered_examples
                if example.get("data_use", {}).get(
                    "training_allowed"
                ) is True
            ),
            "evaluation_eligible_examples": sum(
                1
                for example in ordered_examples
                if example.get("data_use", {}).get(
                    "evaluation_allowed"
                ) is True
            ),
            "content_bearing_examples": sum(
                1
                for example in ordered_examples
                if example.get("content_included") is True
            ),
        },
        "trust_model": {
            "corpus_is_proof_authority": False,
            "diagnostic_reward_is_scientific_truth": False,
            "training_eligibility_is_policy_gated": True,
            "most_restrictive_policy_wins_on_deduplication": True,
            "human_confirmation_replay_and_lean_remain_authoritative": True,
        },
    }
    return {
        **core,
        "corpus_sha256": _commitment(core),
    }


def load_proof_search_records_v06(
    paths: Sequence[str | Path],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_path in paths:
        path = Path(raw_path).resolve()
        try:
            value = strict_json_load(path)
        except (OSError, StrictJSONError) as exc:
            raise V06ProofSearchCorpusError(
                f"cannot load proof-search record {path}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise V06ProofSearchCorpusError(
                f"proof-search record root must be an object: {path}"
            )
        records.append(value)
    return records


def build_proof_search_corpus_from_files_v06(
    paths: Sequence[str | Path],
) -> dict[str, Any]:
    return build_proof_search_corpus_v06(
        load_proof_search_records_v06(paths)
    )


def _write_committed_json(
    value: Mapping[str, Any],
    path: str | Path,
    *,
    hash_field: str,
    overwrite: bool,
    label: str,
) -> str:
    claimed = value.get(hash_field)
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise V06ProofSearchCorpusError(
            f"{label} lacks a valid {hash_field}"
        )
    core = {
        key: _clone(item)
        for key, item in value.items()
        if key != hash_field
    }
    if _commitment(core) != claimed:
        raise V06ProofSearchCorpusError(
            f"{label} commitment does not match contents"
        )
    output = Path(path).resolve()
    if output.exists() and not overwrite:
        raise V06ProofSearchCorpusError(
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


def write_proof_search_record_v06(
    record: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> str:
    _verify_record(record)
    return _write_committed_json(
        record,
        path,
        hash_field="record_sha256",
        overwrite=overwrite,
        label="proof-search record",
    )


def write_proof_search_corpus_v06(
    corpus: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> str:
    if corpus.get("format") != PROOF_SEARCH_CORPUS_FORMAT_V06:
        raise V06ProofSearchCorpusError(
            "refusing to write invalid proof-search corpus"
        )
    return _write_committed_json(
        corpus,
        path,
        hash_field="corpus_sha256",
        overwrite=overwrite,
        label="proof-search corpus",
    )
