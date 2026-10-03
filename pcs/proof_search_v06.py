from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical_json import canonicalize_jcs_bytes
from .jsonio import StrictJSONError, strict_json_load
from .proof_repair_v06 import (
    PROOF_REPAIR_REQUEST_FORMAT_V06,
    V06ProofRepairError,
    build_proof_repair_request_v06,
    compile_proof_repair_response_v06,
)
from .proof_translation_v06 import (
    PROOF_PROPOSALS_FORMAT_V06,
    V06ProofTranslationError,
    translate_project_v06,
)


PROOF_SEARCH_SESSION_FORMAT_V06 = "pcs-proof-repair-search-v1"
PROOF_SEARCH_TRAJECTORY_FORMAT_V06 = "pcs-proof-repair-trajectory-v1"
PROOF_SEARCH_COORDINATOR_V06 = "pcs-proof-repair-search-coordinator/0.1"
MAX_PROOF_SEARCH_ITERATIONS_V06 = 32

_REWARD_CONTRACT_V06 = {
    "blocking_obligation_closed": 10,
    "compiled_selected_added": 4,
    "formalizable_candidate_added": 2,
    "repairable_task_closed": 1,
    "iteration_cost": -1,
    "cycle_penalty": -10,
    "authority_meaning": (
        "Diagnostic search reward only. It never sets PASS, authoritative "
        "acceptance, human confirmation, replay success, or Lean authority."
    ),
}


class V06ProofSearchError(ValueError):
    pass


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _commitment(value: Any) -> str:
    return hashlib.sha256(canonicalize_jcs_bytes(value)).hexdigest()


def _require_int(
    value: Any,
    *,
    label: str,
    minimum: int,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise V06ProofSearchError(f"{label} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        suffix = (
            f" in [{minimum},{maximum}]"
            if maximum is not None
            else f" >= {minimum}"
        )
        raise V06ProofSearchError(f"{label} must be{suffix}")
    return value


def _proposal_documents_from_files(
    paths: Sequence[str | Path],
    *,
    inventory_commitment_sha256: str,
) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path).resolve()
        try:
            value = strict_json_load(path)
        except (OSError, StrictJSONError) as exc:
            raise V06ProofSearchError(
                f"cannot load search proposal file {path}: {exc}"
            ) from exc
        if not isinstance(value, Mapping):
            raise V06ProofSearchError(
                f"search proposal file root must be an object: {path}"
            )
        if value.get("format") != PROOF_PROPOSALS_FORMAT_V06:
            raise V06ProofSearchError(
                f"unsupported search proposal format in {path}: "
                f"{value.get('format')!r}"
            )
        if value.get("inventory_commitment_sha256") != inventory_commitment_sha256:
            raise V06ProofSearchError(
                f"search proposal file is bound to a different project inventory: {path}"
            )
        proposer = value.get("proposer")
        proposals = value.get("proposals")
        if not isinstance(proposer, Mapping):
            raise V06ProofSearchError(
                f"search proposal file lacks proposer metadata: {path}"
            )
        if not isinstance(proposals, list):
            raise V06ProofSearchError(
                f"search proposal file proposals must be an array: {path}"
            )

        normalized_proposals: list[dict[str, Any]] = []
        for proposal in proposals:
            if not isinstance(proposal, Mapping):
                raise V06ProofSearchError(
                    f"search proposal entry must be an object: {path}"
                )
            proposal_id = proposal.get("id")
            if not isinstance(proposal_id, str) or not proposal_id:
                raise V06ProofSearchError(
                    f"search proposal requires a non-empty id: {path}"
                )
            if proposal_id in seen_ids:
                raise V06ProofSearchError(
                    f"duplicate search proposal id across files: {proposal_id}"
                )
            seen_ids.add(proposal_id)
            normalized_proposals.append(_json_clone(proposal))

        documents.append(
            {
                "format": PROOF_PROPOSALS_FORMAT_V06,
                "inventory_commitment_sha256": inventory_commitment_sha256,
                "proposer": _json_clone(proposer),
                "proposals": normalized_proposals,
            }
        )
    return documents


def _validate_active_documents(
    documents: Any,
    *,
    inventory_commitment_sha256: str,
) -> list[dict[str, Any]]:
    if not isinstance(documents, list):
        raise V06ProofSearchError(
            "proof search active_proposal_documents must be an array"
        )
    out: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, document in enumerate(documents):
        if not isinstance(document, Mapping):
            raise V06ProofSearchError(
                f"active proposal document {index} must be an object"
            )
        if document.get("format") != PROOF_PROPOSALS_FORMAT_V06:
            raise V06ProofSearchError(
                f"active proposal document {index} has unsupported format"
            )
        if (
            document.get("inventory_commitment_sha256")
            != inventory_commitment_sha256
        ):
            raise V06ProofSearchError(
                f"active proposal document {index} is bound to a different inventory"
            )
        proposer = document.get("proposer")
        proposals = document.get("proposals")
        if not isinstance(proposer, Mapping) or not isinstance(proposals, list):
            raise V06ProofSearchError(
                f"active proposal document {index} is malformed"
            )
        normalized = {
            "format": PROOF_PROPOSALS_FORMAT_V06,
            "inventory_commitment_sha256": inventory_commitment_sha256,
            "proposer": _json_clone(proposer),
            "proposals": [],
        }
        for proposal in proposals:
            if not isinstance(proposal, Mapping):
                raise V06ProofSearchError(
                    f"active proposal document {index} contains non-object proposal"
                )
            proposal_id = proposal.get("id")
            if not isinstance(proposal_id, str) or not proposal_id:
                raise V06ProofSearchError(
                    f"active proposal document {index} contains proposal without id"
                )
            if proposal_id in seen_ids:
                raise V06ProofSearchError(
                    f"duplicate active proposal id: {proposal_id}"
                )
            seen_ids.add(proposal_id)
            normalized["proposals"].append(_json_clone(proposal))
        if normalized["proposals"]:
            out.append(normalized)
    return out


def _semantic_state_projection(
    translation: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = translation.get("candidates")
    if not isinstance(candidates, list):
        raise V06ProofSearchError(
            "proof translation candidates must be an array"
        )
    projected: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise V06ProofSearchError(
                "proof translation candidate must be an object"
            )
        obligations = candidate.get("obligations", [])
        if not isinstance(obligations, list):
            raise V06ProofSearchError(
                "proof translation candidate obligations must be an array"
            )
        projected_obligations = []
        for obligation in obligations:
            if not isinstance(obligation, Mapping):
                continue
            repair = obligation.get("repair")
            projected_obligations.append(
                {
                    "kind": obligation.get("kind"),
                    "blocking": obligation.get("blocking") is True,
                    "message": obligation.get("message"),
                    "details": _json_clone(obligation.get("details")),
                    "repair_action": (
                        repair.get("action")
                        if isinstance(repair, Mapping)
                        else None
                    ),
                }
            )
        projected.append(
            {
                "id": candidate.get("id"),
                "status": candidate.get("status"),
                "selected": candidate.get("selected") is True,
                "formalizable": candidate.get("formalizable") is True,
                "typed_claim": _json_clone(candidate.get("typed_claim")),
                "check": _json_clone(candidate.get("check")),
                "artifact_ids": _json_clone(candidate.get("artifact_ids")),
                "assumptions": _json_clone(candidate.get("assumptions")),
                "grounding": _json_clone(candidate.get("grounding")),
                "formal_target": _json_clone(candidate.get("formal_target")),
                "obligations": sorted(
                    projected_obligations,
                    key=lambda item: (
                        str(item.get("kind")),
                        bool(item.get("blocking")),
                        str(item.get("message")),
                    ),
                ),
            }
        )
    projected.sort(key=lambda item: str(item.get("id")))
    return {
        "inventory_commitment_sha256": translation.get(
            "inventory_commitment_sha256"
        ),
        "candidates": projected,
    }


def _semantic_state_sha256(translation: Mapping[str, Any]) -> str:
    return _commitment(_semantic_state_projection(translation))


def _translation_metrics(
    translation: Mapping[str, Any],
    repair_request: Mapping[str, Any],
) -> dict[str, int]:
    summary = translation.get("summary")
    request_summary = repair_request.get("summary")
    if not isinstance(summary, Mapping) or not isinstance(
        request_summary, Mapping
    ):
        raise V06ProofSearchError(
            "translation/repair request summaries are missing"
        )
    return {
        "blocking_open_obligations": int(
            summary.get("blocking_open_obligations", 0)
        ),
        "compiled_selected": int(summary.get("compiled_selected", 0)),
        "formalizable_candidates": int(
            summary.get("formalizable_candidates", 0)
        ),
        "repairable_tasks": int(
            request_summary.get("repairable_tasks", 0)
        ),
        "blocking_repairable_tasks": int(
            request_summary.get("blocking_repairable_tasks", 0)
        ),
    }


def _diagnostic_reward(
    before: Mapping[str, int],
    after: Mapping[str, int],
    *,
    cycle: bool,
) -> int:
    reward = int(_REWARD_CONTRACT_V06["iteration_cost"])
    reward += int(_REWARD_CONTRACT_V06["blocking_obligation_closed"]) * (
        int(before["blocking_open_obligations"])
        - int(after["blocking_open_obligations"])
    )
    reward += int(_REWARD_CONTRACT_V06["compiled_selected_added"]) * (
        int(after["compiled_selected"])
        - int(before["compiled_selected"])
    )
    reward += int(_REWARD_CONTRACT_V06["formalizable_candidate_added"]) * (
        int(after["formalizable_candidates"])
        - int(before["formalizable_candidates"])
    )
    reward += int(_REWARD_CONTRACT_V06["repairable_task_closed"]) * (
        int(before["repairable_tasks"])
        - int(after["repairable_tasks"])
    )
    if cycle:
        reward += int(_REWARD_CONTRACT_V06["cycle_penalty"])
    return reward


def _search_status(
    *,
    translation: Mapping[str, Any],
    repair_request: Mapping[str, Any],
    iteration: int,
    max_iterations: int,
    cycle_detected: bool = False,
) -> str:
    if cycle_detected:
        return "CYCLE_DETECTED"
    metrics = _translation_metrics(translation, repair_request)
    if metrics["blocking_open_obligations"] == 0:
        return "READY_FOR_HUMAN_CONFIRMATION"
    if metrics["repairable_tasks"] == 0:
        return "BLOCKED_NO_MACHINE_REPAIR"
    if iteration >= max_iterations:
        return "MAX_ITERATIONS_REACHED"
    return "AWAITING_REPAIR"


def _trajectory_with_hash(
    steps: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    core = {
        "format": PROOF_SEARCH_TRAJECTORY_FORMAT_V06,
        "reward_contract": _json_clone(_REWARD_CONTRACT_V06),
        "steps": [_json_clone(step) for step in steps],
    }
    return {
        **core,
        "trajectory_sha256": _commitment(core),
    }


def _session_with_hash(core: Mapping[str, Any]) -> dict[str, Any]:
    session_core = _json_clone(core)
    session_core.pop("session_sha256", None)
    return {
        **session_core,
        "session_sha256": _commitment(session_core),
    }


def _verify_session(
    session: Mapping[str, Any],
) -> None:
    if session.get("format") != PROOF_SEARCH_SESSION_FORMAT_V06:
        raise V06ProofSearchError(
            f"unsupported proof search session format: {session.get('format')!r}"
        )
    claimed = session.get("session_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise V06ProofSearchError(
            "proof search session lacks a valid session_sha256"
        )
    core = {
        key: _json_clone(value)
        for key, value in session.items()
        if key != "session_sha256"
    }
    if _commitment(core) != claimed:
        raise V06ProofSearchError(
            "proof search session commitment does not match session contents"
        )

    max_iterations = _require_int(
        session.get("max_iterations"),
        label="proof search max_iterations",
        minimum=1,
        maximum=MAX_PROOF_SEARCH_ITERATIONS_V06,
    )
    iteration = _require_int(
        session.get("iteration"),
        label="proof search iteration",
        minimum=0,
        maximum=max_iterations,
    )
    if iteration > max_iterations:
        raise V06ProofSearchError(
            "proof search iteration exceeds max_iterations"
        )

    translation = session.get("current_translation")
    request = session.get("current_repair_request")
    if not isinstance(translation, Mapping) or not isinstance(request, Mapping):
        raise V06ProofSearchError(
            "proof search session lacks current translation/repair request"
        )
    if request.get("format") != PROOF_REPAIR_REQUEST_FORMAT_V06:
        raise V06ProofSearchError(
            "proof search session current repair request has wrong format"
        )
    if request.get("translation_plan_sha256") != translation.get(
        "plan_sha256"
    ):
        raise V06ProofSearchError(
            "proof search current repair request is stale for its translation"
        )
    if request.get("obligation_graph_sha256") != translation.get(
        "obligation_graph", {}
    ).get("graph_sha256"):
        raise V06ProofSearchError(
            "proof search current repair request is stale for its graph"
        )

    inventory = translation.get("inventory_commitment_sha256")
    if not isinstance(inventory, str):
        raise V06ProofSearchError(
            "proof search translation lacks inventory commitment"
        )
    _validate_active_documents(
        session.get("active_proposal_documents"),
        inventory_commitment_sha256=inventory,
    )

    seen_states = session.get("seen_state_sha256")
    if not isinstance(seen_states, list) or not all(
        isinstance(value, str) and len(value) == 64
        for value in seen_states
    ):
        raise V06ProofSearchError(
            "proof search seen_state_sha256 must be an array of SHA-256 strings"
        )
    current_state = _semantic_state_sha256(translation)
    if not seen_states or seen_states[-1] != current_state:
        raise V06ProofSearchError(
            "proof search current semantic state is not the last seen state"
        )

    trajectory = session.get("trajectory")
    if not isinstance(trajectory, Mapping):
        raise V06ProofSearchError(
            "proof search session lacks trajectory"
        )
    trajectory_claimed = trajectory.get("trajectory_sha256")
    trajectory_core = {
        key: _json_clone(value)
        for key, value in trajectory.items()
        if key != "trajectory_sha256"
    }
    if (
        not isinstance(trajectory_claimed, str)
        or len(trajectory_claimed) != 64
        or _commitment(trajectory_core) != trajectory_claimed
    ):
        raise V06ProofSearchError(
            "proof search trajectory commitment is invalid"
        )


def _write_staged_proposal_documents(
    documents: Sequence[Mapping[str, Any]],
    *,
    project_root: Path,
    state_dir: str | Path | None,
    search_id: str,
    iteration: int,
) -> list[Path]:
    base = (
        Path(state_dir).resolve()
        if state_dir is not None
        else project_root / ".pcs" / "proof-search" / search_id
    )
    stage = base / f"iteration-{iteration:03d}"
    stage.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    for index, document in enumerate(documents):
        path = stage / f"proposals-{index:03d}.json"
        path.write_text(
            json.dumps(
                dict(document),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        paths.append(path)
    return paths


def _merge_repaired_proposals(
    active_documents: Sequence[Mapping[str, Any]],
    compiled_repairs: Mapping[str, Any],
    *,
    inventory_commitment_sha256: str,
) -> list[dict[str, Any]]:
    proposals = compiled_repairs.get("proposals")
    proposer = compiled_repairs.get("proposer")
    if not isinstance(proposals, list) or not isinstance(proposer, Mapping):
        raise V06ProofSearchError(
            "compiled repair output lacks proposals/proposer"
        )
    replacement_ids = {
        proposal.get("id")
        for proposal in proposals
        if isinstance(proposal, Mapping)
        and isinstance(proposal.get("id"), str)
    }
    if len(replacement_ids) != len(proposals):
        raise V06ProofSearchError(
            "compiled repairs contain invalid or duplicate proposal ids"
        )

    known_ids = {
        proposal.get("id")
        for document in active_documents
        for proposal in document.get("proposals", [])
        if isinstance(proposal, Mapping)
    }
    unknown = sorted(replacement_ids - known_ids)
    if unknown:
        raise V06ProofSearchError(
            f"compiled repairs replace unknown active proposal ids: {unknown}"
        )

    merged: list[dict[str, Any]] = []
    for document in active_documents:
        kept = [
            _json_clone(proposal)
            for proposal in document.get("proposals", [])
            if isinstance(proposal, Mapping)
            and proposal.get("id") not in replacement_ids
        ]
        if kept:
            merged.append(
                {
                    "format": PROOF_PROPOSALS_FORMAT_V06,
                    "inventory_commitment_sha256": inventory_commitment_sha256,
                    "proposer": _json_clone(document["proposer"]),
                    "proposals": kept,
                }
            )

    if proposals:
        merged.append(
            {
                "format": PROOF_PROPOSALS_FORMAT_V06,
                "inventory_commitment_sha256": inventory_commitment_sha256,
                "proposer": _json_clone(proposer),
                "proposals": [_json_clone(item) for item in proposals],
            }
        )

    return _validate_active_documents(
        merged,
        inventory_commitment_sha256=inventory_commitment_sha256,
    )


def start_proof_search_v06(
    project_root: str | Path,
    *,
    proposal_files: Sequence[str | Path],
    subject: str | None = None,
    max_iterations: int = 4,
    minimum_confidence: float = 0.95,
    minimum_model_confidence: float = 0.98,
    minimum_workflow_confidence: float = 0.95,
) -> dict[str, Any]:
    max_iterations = _require_int(
        max_iterations,
        label="proof search max_iterations",
        minimum=1,
        maximum=MAX_PROOF_SEARCH_ITERATIONS_V06,
    )
    if not proposal_files:
        raise V06ProofSearchError(
            "proof search requires at least one external proposal file"
        )
    root = Path(project_root).resolve()

    try:
        translation = translate_project_v06(
            root,
            subject=subject,
            proposal_files=proposal_files,
            minimum_confidence=minimum_confidence,
            minimum_model_confidence=minimum_model_confidence,
            minimum_workflow_confidence=minimum_workflow_confidence,
        )
        request = build_proof_repair_request_v06(translation)
    except (V06ProofTranslationError, V06ProofRepairError) as exc:
        raise V06ProofSearchError(str(exc)) from exc

    inventory = translation.get("inventory_commitment_sha256")
    if not isinstance(inventory, str):
        raise V06ProofSearchError(
            "translation lacks project inventory commitment"
        )
    documents = _proposal_documents_from_files(
        proposal_files,
        inventory_commitment_sha256=inventory,
    )
    state_sha256 = _semantic_state_sha256(translation)
    metrics = _translation_metrics(translation, request)
    status = _search_status(
        translation=translation,
        repair_request=request,
        iteration=0,
        max_iterations=max_iterations,
    )
    search_id = _commitment(
        {
            "initial_plan_sha256": translation.get("plan_sha256"),
            "inventory_commitment_sha256": inventory,
            "max_iterations": max_iterations,
        }
    )[:20]

    core = {
        "format": PROOF_SEARCH_SESSION_FORMAT_V06,
        "coordinator": PROOF_SEARCH_COORDINATOR_V06,
        "search_id": search_id,
        "project_root_name": root.name,
        "inventory_commitment_sha256": inventory,
        "initial_plan_sha256": translation.get("plan_sha256"),
        "max_iterations": max_iterations,
        "iteration": 0,
        "status": status,
        "thresholds": {
            "minimum_confidence": minimum_confidence,
            "minimum_model_confidence": minimum_model_confidence,
            "minimum_workflow_confidence": minimum_workflow_confidence,
        },
        "authority": {
            "coordinator_trusted_to_set_authoritative": False,
            "repair_model_trusted": False,
            "diagnostic_reward_sets_authority": False,
            "human_confirmation_required": True,
            "replay_and_lean_authority_required": True,
        },
        "active_proposal_documents": documents,
        "current_translation": translation,
        "current_repair_request": request,
        "seen_state_sha256": [state_sha256],
        "trajectory": _trajectory_with_hash([]),
        "summary": {
            **metrics,
            "semantic_state_sha256": state_sha256,
            "trajectory_steps": 0,
            "diagnostic_reward_total": 0,
        },
    }
    return _session_with_hash(core)


def advance_proof_search_v06(
    project_root: str | Path,
    session: Mapping[str, Any],
    repair_response: Mapping[str, Any],
    *,
    state_dir: str | Path | None = None,
) -> dict[str, Any]:
    _verify_session(session)
    if session.get("status") != "AWAITING_REPAIR":
        raise V06ProofSearchError(
            f"proof search cannot advance from terminal/non-repair state "
            f"{session.get('status')!r}"
        )

    root = Path(project_root).resolve()
    max_iterations = int(session["max_iterations"])
    next_iteration = int(session["iteration"]) + 1
    if next_iteration > max_iterations:
        raise V06ProofSearchError(
            "proof search iteration budget is exhausted"
        )

    before_translation = session["current_translation"]
    before_request = session["current_repair_request"]
    before_state = _semantic_state_sha256(before_translation)
    before_metrics = _translation_metrics(
        before_translation,
        before_request,
    )

    try:
        compiled = compile_proof_repair_response_v06(
            before_translation,
            before_request,
            repair_response,
        )
    except V06ProofRepairError as exc:
        raise V06ProofSearchError(str(exc)) from exc

    inventory = session["inventory_commitment_sha256"]
    active_documents = _validate_active_documents(
        session["active_proposal_documents"],
        inventory_commitment_sha256=inventory,
    )
    merged_documents = _merge_repaired_proposals(
        active_documents,
        compiled,
        inventory_commitment_sha256=inventory,
    )
    staged = _write_staged_proposal_documents(
        merged_documents,
        project_root=root,
        state_dir=state_dir,
        search_id=str(session["search_id"]),
        iteration=next_iteration,
    )

    thresholds = session.get("thresholds")
    if not isinstance(thresholds, Mapping):
        raise V06ProofSearchError(
            "proof search session lacks thresholds"
        )
    try:
        after_translation = translate_project_v06(
            root,
            proposal_files=staged,
            minimum_confidence=float(thresholds["minimum_confidence"]),
            minimum_model_confidence=float(
                thresholds["minimum_model_confidence"]
            ),
            minimum_workflow_confidence=float(
                thresholds["minimum_workflow_confidence"]
            ),
        )
        after_request = build_proof_repair_request_v06(after_translation)
    except (
        KeyError,
        ValueError,
        V06ProofTranslationError,
        V06ProofRepairError,
    ) as exc:
        raise V06ProofSearchError(
            f"repaired proposal failed deterministic retranslation: {exc}"
        ) from exc

    if after_translation.get("inventory_commitment_sha256") != inventory:
        raise V06ProofSearchError(
            "project inventory changed during proof search; restart from a new translation"
        )

    after_state = _semantic_state_sha256(after_translation)
    seen_states = list(session["seen_state_sha256"])
    cycle = after_state in seen_states
    after_metrics = _translation_metrics(
        after_translation,
        after_request,
    )
    reward = _diagnostic_reward(
        before_metrics,
        after_metrics,
        cycle=cycle,
    )

    if cycle:
        outcome = "CYCLE_DETECTED"
    elif (
        after_metrics["blocking_open_obligations"]
        < before_metrics["blocking_open_obligations"]
        or after_metrics["compiled_selected"]
        > before_metrics["compiled_selected"]
        or after_metrics["formalizable_candidates"]
        > before_metrics["formalizable_candidates"]
        or after_metrics["repairable_tasks"]
        < before_metrics["repairable_tasks"]
    ):
        outcome = "OBJECTIVE_PROGRESS"
    else:
        outcome = "NOVEL_STATE_NO_OBJECTIVE_PROGRESS"

    response_sha256 = _commitment(repair_response)
    step = {
        "iteration": next_iteration,
        "before_plan_sha256": before_translation.get("plan_sha256"),
        "before_graph_sha256": before_translation.get(
            "obligation_graph", {}
        ).get("graph_sha256"),
        "before_state_sha256": before_state,
        "repair_request_sha256": before_request.get(
            "repair_request_sha256"
        ),
        "repair_response_sha256": response_sha256,
        "compiled_repair_sha256": compiled.get(
            "compiled_repair_sha256"
        ),
        "repaired_proposal_ids": sorted(
            str(item.get("id"))
            for item in compiled.get("proposals", [])
            if isinstance(item, Mapping)
        ),
        "after_plan_sha256": after_translation.get("plan_sha256"),
        "after_graph_sha256": after_translation.get(
            "obligation_graph", {}
        ).get("graph_sha256"),
        "after_state_sha256": after_state,
        "metrics_before": before_metrics,
        "metrics_after": after_metrics,
        "diagnostic_reward": reward,
        "outcome": outcome,
        "authority": {
            "sets_authoritative": False,
            "human_confirmation_still_required": True,
            "replay_and_lean_authority_still_required": True,
        },
    }

    trajectory = session["trajectory"]
    steps = [
        _json_clone(item)
        for item in trajectory.get("steps", [])
        if isinstance(item, Mapping)
    ]
    steps.append(step)
    next_trajectory = _trajectory_with_hash(steps)

    next_seen = seen_states + [after_state]
    status = _search_status(
        translation=after_translation,
        repair_request=after_request,
        iteration=next_iteration,
        max_iterations=max_iterations,
        cycle_detected=cycle,
    )
    reward_total = sum(
        int(item.get("diagnostic_reward", 0))
        for item in steps
    )

    core = {
        key: _json_clone(value)
        for key, value in session.items()
        if key
        not in {
            "session_sha256",
            "iteration",
            "status",
            "active_proposal_documents",
            "current_translation",
            "current_repair_request",
            "seen_state_sha256",
            "trajectory",
            "summary",
        }
    }
    core.update(
        {
            "iteration": next_iteration,
            "status": status,
            "active_proposal_documents": merged_documents,
            "current_translation": after_translation,
            "current_repair_request": after_request,
            "seen_state_sha256": next_seen,
            "trajectory": next_trajectory,
            "summary": {
                **after_metrics,
                "semantic_state_sha256": after_state,
                "trajectory_steps": len(steps),
                "diagnostic_reward_total": reward_total,
                "last_outcome": outcome,
            },
        }
    )
    return _session_with_hash(core)


def load_proof_search_session_v06(
    path: str | Path,
) -> dict[str, Any]:
    resolved = Path(path).resolve()
    try:
        value = strict_json_load(resolved)
    except (OSError, StrictJSONError) as exc:
        raise V06ProofSearchError(
            f"cannot load proof search session {resolved}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise V06ProofSearchError(
            "proof search session root must be an object"
        )
    _verify_session(value)
    return value


def load_proof_search_repair_response_v06(
    path: str | Path,
) -> dict[str, Any]:
    resolved = Path(path).resolve()
    try:
        value = strict_json_load(resolved)
    except (OSError, StrictJSONError) as exc:
        raise V06ProofSearchError(
            f"cannot load proof search repair response {resolved}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise V06ProofSearchError(
            "proof search repair response root must be an object"
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
        raise V06ProofSearchError(
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


def write_proof_search_session_v06(
    session: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> str:
    _verify_session(session)
    return _write_json(
        session,
        path,
        overwrite=overwrite,
        label="proof search session",
    )


def write_current_repair_request_v06(
    session: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> str:
    _verify_session(session)
    request = session["current_repair_request"]
    return _write_json(
        request,
        path,
        overwrite=overwrite,
        label="proof search repair request",
    )


def write_proof_search_trajectory_v06(
    session: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> str:
    _verify_session(session)
    return _write_json(
        session["trajectory"],
        path,
        overwrite=overwrite,
        label="proof search trajectory",
    )
