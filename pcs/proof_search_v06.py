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


def _proposal_intent_anchor(
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    proposal_id = proposal.get("id")
    if not isinstance(proposal_id, str) or not proposal_id:
        raise V06ProofSearchError(
            "proof search proposal requires a non-empty id for intent binding"
        )
    finding = proposal.get("finding")
    if not isinstance(finding, str) or not finding.strip():
        reason = proposal.get("reason")
        finding = reason if isinstance(reason, str) and reason.strip() else None

    claim = proposal.get("claim")
    statement = None
    kind = None
    if isinstance(claim, Mapping):
        raw_statement = claim.get("statement")
        if isinstance(raw_statement, str) and raw_statement.strip():
            statement = raw_statement
        raw_kind = claim.get("kind", "computational")
        if isinstance(raw_kind, str):
            kind = raw_kind

    if finding is None and statement is None:
        raise V06ProofSearchError(
            f"proposal {proposal_id!r} lacks a natural-language intent anchor; "
            "proof search requires finding/reason or claim.statement"
        )
    confidence = proposal.get("confidence")
    check = proposal.get("check")
    check_type = (
        check.get("type")
        if isinstance(check, Mapping) and isinstance(check.get("type"), str)
        else None
    )
    return {
        "proposal_id": proposal_id,
        "finding": finding,
        "claim_statement": statement,
        "claim_kind": kind,
        "proposal_confidence": confidence,
        "check_type": check_type,
    }


def _intent_anchors_from_documents(
    documents: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    anchors: dict[str, dict[str, Any]] = {}
    for document in documents:
        for proposal in document.get("proposals", []):
            if not isinstance(proposal, Mapping):
                continue
            anchor = _proposal_intent_anchor(proposal)
            proposal_id = anchor["proposal_id"]
            if proposal_id in anchors:
                raise V06ProofSearchError(
                    f"duplicate intent anchor proposal id: {proposal_id}"
                )
            anchors[proposal_id] = anchor
    return {
        key: anchors[key]
        for key in sorted(anchors)
    }


def _assert_proposal_preserves_intent(
    proposal: Mapping[str, Any],
    anchor: Mapping[str, Any],
) -> None:
    proposal_id = proposal.get("id")
    if proposal_id != anchor.get("proposal_id"):
        raise V06ProofSearchError(
            "repair proposal does not match its immutable intent anchor"
        )

    anchored_finding = anchor.get("finding")
    if anchored_finding is not None:
        current_finding = proposal.get("finding")
        if not isinstance(current_finding, str) or not current_finding.strip():
            reason = proposal.get("reason")
            current_finding = (
                reason
                if isinstance(reason, str) and reason.strip()
                else None
            )
        if current_finding != anchored_finding:
            raise V06ProofSearchError(
                f"repair for proposal {proposal_id!r} changes the immutable "
                "scientific finding; create a new human-reviewed proposal instead"
            )

    anchored_statement = anchor.get("claim_statement")
    anchored_kind = anchor.get("claim_kind")
    claim = proposal.get("claim")
    if anchored_statement is not None:
        if not isinstance(claim, Mapping) or claim.get("statement") != anchored_statement:
            raise V06ProofSearchError(
                f"repair for proposal {proposal_id!r} changes the immutable "
                "claim statement; create a new human-reviewed proposal instead"
            )
    if anchored_kind is not None:
        if not isinstance(claim, Mapping) or claim.get("kind", "computational") != anchored_kind:
            raise V06ProofSearchError(
                f"repair for proposal {proposal_id!r} changes the immutable "
                "claim kind; create a new human-reviewed proposal instead"
            )

    if proposal.get("confidence") != anchor.get("proposal_confidence"):
        raise V06ProofSearchError(
            f"repair for proposal {proposal_id!r} changes model confidence; "
            "confidence promotion requires a new human-reviewed proposal"
        )

    anchored_check_type = anchor.get("check_type")
    if anchored_check_type is not None:
        check = proposal.get("check")
        if (
            not isinstance(check, Mapping)
            or check.get("type") != anchored_check_type
        ):
            raise V06ProofSearchError(
                f"repair for proposal {proposal_id!r} changes the checker family; "
                "checker-family reproposal requires human review"
            )


def _semantic_state_projection(
    translation: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = translation.get("candidates")
    if not isinstance(candidates, list):
        raise V06ProofSearchError(
            "proof translation candidates must be an array"
        )

    def semantic_mapping(
        value: Any,
        *,
        ignored_keys: set[str],
    ) -> Any:
        if not isinstance(value, Mapping):
            return _json_clone(value)
        return {
            str(key): _json_clone(item)
            for key, item in value.items()
            if key not in ignored_keys
        }

    def semantic_assumptions(value: Any) -> list[Any]:
        if not isinstance(value, list):
            return []
        normalized = [
            semantic_mapping(
                item,
                ignored_keys={"id", "scope"},
            )
            for item in value
            if isinstance(item, Mapping)
        ]
        return sorted(normalized, key=_commitment)

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

        projected_obligations: list[dict[str, Any]] = []
        for obligation in obligations:
            if not isinstance(obligation, Mapping):
                continue
            repair = obligation.get("repair")
            details = obligation.get("details")
            normalized_details = (
                {
                    str(key): _json_clone(item)
                    for key, item in details.items()
                    if key not in {"assumption_id"}
                }
                if isinstance(details, Mapping)
                else _json_clone(details)
            )
            projected_obligations.append(
                {
                    "kind": obligation.get("kind"),
                    "blocking": obligation.get("blocking") is True,
                    "details": normalized_details,
                    "repair_action": (
                        repair.get("action")
                        if isinstance(repair, Mapping)
                        else None
                    ),
                }
            )

        projected.append(
            {
                # Proposal IDs remain stable under the repair contract and
                # distinguish independent search roots.
                "id": candidate.get("id"),
                "status": candidate.get("status"),
                "selected": candidate.get("selected") is True,
                "formalizable": candidate.get("formalizable") is True,
                # Ignore internal claim/check link IDs so renaming them cannot
                # masquerade as semantic search progress.
                "typed_claim": semantic_mapping(
                    candidate.get("typed_claim"),
                    ignored_keys={"id", "required_evidence", "assumptions"},
                ),
                "check": semantic_mapping(
                    candidate.get("check"),
                    ignored_keys={"id", "claim_ids"},
                ),
                "artifact_ids": sorted(
                    str(item)
                    for item in candidate.get("artifact_ids", [])
                    if isinstance(item, str)
                ),
                "assumptions": semantic_assumptions(
                    candidate.get("assumptions")
                ),
                "grounding": _json_clone(candidate.get("grounding")),
                "formal_target": _json_clone(candidate.get("formal_target")),
                "obligations": sorted(
                    projected_obligations,
                    key=_commitment,
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
    if session.get("coordinator") != PROOF_SEARCH_COORDINATOR_V06:
        raise V06ProofSearchError(
            "proof search session coordinator version is unsupported"
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

    translation = session.get("current_translation")
    request = session.get("current_repair_request")
    if not isinstance(translation, Mapping) or not isinstance(request, Mapping):
        raise V06ProofSearchError(
            "proof search session lacks current translation/repair request"
        )
    try:
        expected_request = build_proof_repair_request_v06(translation)
    except V06ProofRepairError as exc:
        raise V06ProofSearchError(
            f"proof search current translation is invalid: {exc}"
        ) from exc
    if request != expected_request:
        raise V06ProofSearchError(
            "proof search current repair request does not exactly match "
            "the deterministic request for its translation"
        )

    inventory = translation.get("inventory_commitment_sha256")
    if not isinstance(inventory, str):
        raise V06ProofSearchError(
            "proof search translation lacks inventory commitment"
        )
    if session.get("inventory_commitment_sha256") != inventory:
        raise V06ProofSearchError(
            "proof search session inventory binding does not match translation"
        )
    if session.get("subject") != translation.get("subject"):
        raise V06ProofSearchError(
            "proof search subject does not match current translation"
        )

    active_documents = _validate_active_documents(
        session.get("active_proposal_documents"),
        inventory_commitment_sha256=inventory,
    )
    if active_documents != session.get("active_proposal_documents"):
        raise V06ProofSearchError(
            "proof search active proposal documents are not normalized"
        )

    intent_anchors = session.get("intent_anchors")
    if not isinstance(intent_anchors, Mapping):
        raise V06ProofSearchError(
            "proof search session lacks intent anchors"
        )
    claimed_intent_hash = session.get("intent_anchors_sha256")
    if (
        not isinstance(claimed_intent_hash, str)
        or len(claimed_intent_hash) != 64
        or _commitment(intent_anchors) != claimed_intent_hash
    ):
        raise V06ProofSearchError(
            "proof search intent-anchor commitment is invalid"
        )
    active_ids: set[str] = set()
    for document in active_documents:
        for proposal in document.get("proposals", []):
            if not isinstance(proposal, Mapping):
                continue
            proposal_id = str(proposal.get("id"))
            active_ids.add(proposal_id)
            anchor = intent_anchors.get(proposal_id)
            if not isinstance(anchor, Mapping):
                raise V06ProofSearchError(
                    f"active proposal {proposal_id!r} lacks an intent anchor"
                )
            _assert_proposal_preserves_intent(proposal, anchor)
    if active_ids != set(intent_anchors):
        raise V06ProofSearchError(
            "proof search intent anchors do not exactly cover active proposals"
        )

    expected_authority = {
        "coordinator_trusted_to_set_authoritative": False,
        "repair_model_trusted": False,
        "diagnostic_reward_sets_authority": False,
        "scientific_intent_reproposal_requires_human": True,
        "human_confirmation_required": True,
        "replay_and_lean_authority_required": True,
    }
    if session.get("authority") != expected_authority:
        raise V06ProofSearchError(
            "proof search authority boundary metadata is invalid"
        )

    expected_search_id = _commitment(
        {
            "initial_plan_sha256": session.get("initial_plan_sha256"),
            "inventory_commitment_sha256": inventory,
            "intent_anchors_sha256": claimed_intent_hash,
            "max_iterations": max_iterations,
        }
    )[:20]
    if session.get("search_id") != expected_search_id:
        raise V06ProofSearchError(
            "proof search id does not match its initial bindings"
        )

    seen_states = session.get("seen_state_sha256")
    if not isinstance(seen_states, list) or not all(
        isinstance(value, str) and len(value) == 64
        for value in seen_states
    ):
        raise V06ProofSearchError(
            "proof search seen_state_sha256 must be an array of SHA-256 strings"
        )
    if len(seen_states) != iteration + 1:
        raise V06ProofSearchError(
            "proof search semantic-state history length does not match iteration"
        )
    current_state = _semantic_state_sha256(translation)
    if seen_states[-1] != current_state:
        raise V06ProofSearchError(
            "proof search current semantic state is not the last seen state"
        )

    trajectory = session.get("trajectory")
    if not isinstance(trajectory, Mapping):
        raise V06ProofSearchError(
            "proof search session lacks trajectory"
        )
    if trajectory.get("format") != PROOF_SEARCH_TRAJECTORY_FORMAT_V06:
        raise V06ProofSearchError(
            "proof search trajectory format is invalid"
        )
    if trajectory.get("reward_contract") != _REWARD_CONTRACT_V06:
        raise V06ProofSearchError(
            "proof search trajectory reward contract is invalid"
        )
    steps = trajectory.get("steps")
    if not isinstance(steps, list) or not all(
        isinstance(step, Mapping) for step in steps
    ):
        raise V06ProofSearchError(
            "proof search trajectory steps must be an array of objects"
        )
    if len(steps) != iteration:
        raise V06ProofSearchError(
            "proof search trajectory length does not match iteration"
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

    for index, step in enumerate(steps, start=1):
        if int(step.get("iteration", -1)) != index:
            raise V06ProofSearchError(
                "proof search trajectory iteration sequence is invalid"
            )
        if step.get("before_state_sha256") != seen_states[index - 1]:
            raise V06ProofSearchError(
                "proof search trajectory before-state chain is invalid"
            )
        if step.get("after_state_sha256") != seen_states[index]:
            raise V06ProofSearchError(
                "proof search trajectory after-state chain is invalid"
            )
        authority = step.get("authority")
        if not isinstance(authority, Mapping) or (
            authority.get("sets_authoritative") is not False
            or authority.get("human_confirmation_still_required") is not True
            or authority.get("replay_and_lean_authority_still_required") is not True
        ):
            raise V06ProofSearchError(
                "proof search trajectory step violates authority-boundary metadata"
            )

    cycle_detected = (
        iteration > 0 and current_state in seen_states[:-1]
    )
    expected_status = _search_status(
        translation=translation,
        repair_request=request,
        iteration=iteration,
        max_iterations=max_iterations,
        cycle_detected=cycle_detected,
    )
    if session.get("status") != expected_status:
        raise V06ProofSearchError(
            "proof search status does not match deterministic search state"
        )

    metrics = _translation_metrics(translation, request)
    reward_total = sum(
        int(step.get("diagnostic_reward", 0))
        for step in steps
    )
    expected_summary = {
        **metrics,
        "semantic_state_sha256": current_state,
        "trajectory_steps": len(steps),
        "diagnostic_reward_total": reward_total,
    }
    if steps:
        expected_summary["last_outcome"] = steps[-1].get("outcome")
    if session.get("summary") != expected_summary:
        raise V06ProofSearchError(
            "proof search summary does not match deterministic session state"
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
    intent_anchors: Mapping[str, Mapping[str, Any]],
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

    for proposal in proposals:
        if not isinstance(proposal, Mapping):
            raise V06ProofSearchError(
                "compiled repair proposal must be an object"
            )
        proposal_id = proposal.get("id")
        anchor = intent_anchors.get(str(proposal_id))
        if not isinstance(anchor, Mapping):
            raise V06ProofSearchError(
                f"compiled repair proposal {proposal_id!r} lacks an intent anchor"
            )
        _assert_proposal_preserves_intent(proposal, anchor)

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
    intent_anchors = _intent_anchors_from_documents(documents)
    intent_anchors_sha256 = _commitment(intent_anchors)
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
            "intent_anchors_sha256": intent_anchors_sha256,
            "max_iterations": max_iterations,
        }
    )[:20]

    core = {
        "format": PROOF_SEARCH_SESSION_FORMAT_V06,
        "coordinator": PROOF_SEARCH_COORDINATOR_V06,
        "search_id": search_id,
        "project_root_name": root.name,
        "subject": translation.get("subject"),
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
            "scientific_intent_reproposal_requires_human": True,
            "human_confirmation_required": True,
            "replay_and_lean_authority_required": True,
        },
        "intent_anchors": intent_anchors,
        "intent_anchors_sha256": intent_anchors_sha256,
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
    intent_anchors = session.get("intent_anchors")
    if not isinstance(intent_anchors, Mapping):
        raise V06ProofSearchError(
            "proof search session lacks intent anchors"
        )
    merged_documents = _merge_repaired_proposals(
        active_documents,
        compiled,
        inventory_commitment_sha256=inventory,
        intent_anchors=intent_anchors,
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
            subject=(
                str(session["subject"])
                if session.get("subject") is not None
                else None
            ),
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
