from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical_json import canonicalize_jcs_bytes
from .jsonio import StrictJSONError, strict_json_load
from .proof_translation_v06 import (
    PROOF_OBLIGATION_GRAPH_FORMAT_V06,
    PROOF_PROPOSALS_FORMAT_V06,
    PROOF_TRANSLATION_FORMAT_V06,
)


PROOF_REPAIR_REQUEST_FORMAT_V06 = "pcs-proof-repair-request-v1"
PROOF_REPAIR_RESPONSE_FORMAT_V06 = "pcs-proof-repair-proposals-v1"
PROOF_REPAIR_COMPILER_V06 = "pcs-proof-repair-compiler/0.1"

_ALLOWED_PROPOSAL_KEYS = {
    "id",
    "confidence",
    "finding",
    "reason",
    "artifact_ids",
    "claim",
    "check",
    "assumption",
    "assumptions",
}
_ALLOWED_CLAIM_KEYS = {
    "id",
    "statement",
    "kind",
    "required_evidence",
    "assumptions",
    "predicate",
}
_ALLOWED_CHECK_KEYS = {
    "id",
    "type",
    "claim_ids",
    "left_artifact",
    "right_artifact",
    "key",
    "reactants",
    "products",
    "left_unit",
    "right_unit",
    "model_artifact",
    "output_artifact",
    "time_column",
    "concentration_column",
    "effect_column",
    "rel_tol",
    "abs_tol",
    "upper_bound",
    "unit",
    "validator",
    "predicate",
    "receipt_format",
    "trust_model",
    "receipt_artifact",
    "validator_public_key_artifact",
    "validator_public_key_fingerprint",
    "validator_trust_policy_artifact",
    "bound_artifact_ids",
}
_ALLOWED_ASSUMPTION_KEYS = {"id", "statement", "scope"}
_REPAIRABLE_ACTORS = {"proposer", "human_or_proposer", "scientist_or_engineer"}


class V06ProofRepairError(ValueError):
    pass


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _commitment(value: Any) -> str:
    return hashlib.sha256(canonicalize_jcs_bytes(value)).hexdigest()


def _nonempty_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise V06ProofRepairError(f"{label} must be a non-empty string")
    return value


def _verify_graph_commitment(graph: Mapping[str, Any]) -> str:
    if graph.get("format") != PROOF_OBLIGATION_GRAPH_FORMAT_V06:
        raise V06ProofRepairError(
            f"unsupported proof-obligation graph format: {graph.get('format')!r}"
        )
    claimed = graph.get("graph_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise V06ProofRepairError("proof-obligation graph lacks a valid graph_sha256")
    graph_core = {
        key: _json_clone(value)
        for key, value in graph.items()
        if key != "graph_sha256"
    }
    actual = _commitment(graph_core)
    if actual != claimed:
        raise V06ProofRepairError(
            "proof-obligation graph commitment does not match graph contents"
        )
    return actual


def _verify_translation_commitment(
    translation: Mapping[str, Any],
) -> tuple[str, Mapping[str, Any]]:
    if translation.get("format") != PROOF_TRANSLATION_FORMAT_V06:
        raise V06ProofRepairError(
            f"unsupported proof translation format: {translation.get('format')!r}"
        )
    graph = translation.get("obligation_graph")
    if not isinstance(graph, Mapping):
        raise V06ProofRepairError("proof translation lacks an obligation_graph")
    graph_sha256 = _verify_graph_commitment(graph)

    claimed_plan = translation.get("plan_sha256")
    if not isinstance(claimed_plan, str) or len(claimed_plan) != 64:
        raise V06ProofRepairError("proof translation lacks a valid plan_sha256")
    plan_core = {
        "format": translation.get("format"),
        "compiler": translation.get("compiler"),
        "inventory_commitment_sha256": translation.get(
            "inventory_commitment_sha256"
        ),
        "proposal_sources": _json_clone(translation.get("proposal_sources")),
        "candidates": _json_clone(translation.get("candidates")),
        "obligations": _json_clone(translation.get("obligations")),
        "obligation_graph": _json_clone(graph),
    }
    actual_plan = _commitment(plan_core)
    if actual_plan != claimed_plan:
        raise V06ProofRepairError(
            "proof translation plan commitment does not match translation contents"
        )
    return graph_sha256, graph


def _candidate_map(
    translation: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    raw = translation.get("candidates")
    if not isinstance(raw, list):
        raise V06ProofRepairError("proof translation candidates must be an array")
    out: dict[str, Mapping[str, Any]] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            raise V06ProofRepairError("proof translation candidate must be an object")
        ident = _nonempty_string(item.get("id"), label="candidate id")
        if ident in out:
            raise V06ProofRepairError(f"duplicate candidate id: {ident}")
        out[ident] = item
    return out


def _repairable_task(
    item: Mapping[str, Any],
    *,
    candidates: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    proposal_id = item.get("proposal_id")
    obligation_id = item.get("obligation_id")
    repair = item.get("repair")
    if (
        not isinstance(proposal_id, str)
        or not isinstance(obligation_id, str)
        or not isinstance(repair, Mapping)
    ):
        return None
    candidate = candidates.get(proposal_id)
    if candidate is None:
        raise V06ProofRepairError(
            f"repair queue references unknown proposal {proposal_id!r}"
        )
    source = candidate.get("source")
    if not isinstance(source, Mapping) or source.get("kind") != "external_model":
        return None
    if repair.get("machine_assisted") is not True:
        return None
    if repair.get("actor") not in _REPAIRABLE_ACTORS:
        return None
    if repair.get("can_set_authoritative") is not False:
        raise V06ProofRepairError(
            f"repair {obligation_id!r} violates authority-boundary contract"
        )
    action = _nonempty_string(repair.get("action"), label="repair action")
    candidate_snapshot = {
        "id": candidate.get("id"),
        "source": _json_clone(candidate.get("source")),
        "finding": candidate.get("finding"),
        "confidence": candidate.get("confidence"),
        "status": candidate.get("status"),
        "formalizable": candidate.get("formalizable"),
        "typed_claim": _json_clone(candidate.get("typed_claim")),
        "check": _json_clone(candidate.get("check")),
        "artifact_ids": _json_clone(candidate.get("artifact_ids")),
        "assumptions": _json_clone(candidate.get("assumptions")),
        "grounding": _json_clone(candidate.get("grounding")),
        "formal_target": _json_clone(candidate.get("formal_target")),
    }
    return {
        "obligation_id": obligation_id,
        "proposal_id": proposal_id,
        "kind": item.get("kind"),
        "blocking": item.get("blocking") is True,
        "allowed_action": action,
        "authority": {
            "can_set_authoritative": False,
            "must_reenter_deterministic_compiler": True,
            "human_confirmation_still_required": True,
        },
        "repair_context": _json_clone(repair.get("context")),
        "candidate_snapshot": candidate_snapshot,
        "candidate_snapshot_sha256": _commitment(candidate_snapshot),
    }


def build_proof_repair_request_v06(
    translation: Mapping[str, Any],
) -> dict[str, Any]:
    graph_sha256, graph = _verify_translation_commitment(translation)
    candidates = _candidate_map(translation)
    queue = graph.get("repair_queue")
    if not isinstance(queue, list):
        raise V06ProofRepairError("proof-obligation graph repair_queue must be an array")

    tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in queue:
        if not isinstance(item, Mapping):
            raise V06ProofRepairError("repair queue entries must be objects")
        task = _repairable_task(item, candidates=candidates)
        if task is None:
            continue
        obligation_id = task["obligation_id"]
        if obligation_id in seen:
            raise V06ProofRepairError(
                f"duplicate repairable obligation id: {obligation_id}"
            )
        seen.add(obligation_id)
        tasks.append(task)

    tasks.sort(
        key=lambda task: (
            not bool(task["blocking"]),
            str(task["proposal_id"]),
            str(task["obligation_id"]),
        )
    )
    core = {
        "format": PROOF_REPAIR_REQUEST_FORMAT_V06,
        "compiler": PROOF_REPAIR_COMPILER_V06,
        "translation_plan_sha256": translation["plan_sha256"],
        "obligation_graph_sha256": graph_sha256,
        "inventory_commitment_sha256": translation.get(
            "inventory_commitment_sha256"
        ),
        "tasks": tasks,
        "authority": {
            "proposer_trusted": False,
            "repairs_can_set_authoritative": False,
            "repairs_must_reenter_translation_compiler": True,
            "human_confirmation_required": True,
            "replay_and_lean_authority_required": True,
        },
        "summary": {
            "repairable_tasks": len(tasks),
            "blocking_repairable_tasks": sum(
                1 for task in tasks if task.get("blocking") is True
            ),
        },
    }
    return {
        **core,
        "repair_request_sha256": _commitment(core),
    }


def _verify_repair_request(
    request: Mapping[str, Any],
    *,
    translation: Mapping[str, Any],
) -> str:
    if request.get("format") != PROOF_REPAIR_REQUEST_FORMAT_V06:
        raise V06ProofRepairError(
            f"unsupported proof repair request format: {request.get('format')!r}"
        )
    claimed = request.get("repair_request_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise V06ProofRepairError("repair request lacks a valid repair_request_sha256")
    core = {
        key: _json_clone(value)
        for key, value in request.items()
        if key != "repair_request_sha256"
    }
    actual = _commitment(core)
    if actual != claimed:
        raise V06ProofRepairError(
            "repair request commitment does not match request contents"
        )
    graph_sha256, _ = _verify_translation_commitment(translation)
    if request.get("translation_plan_sha256") != translation.get("plan_sha256"):
        raise V06ProofRepairError(
            "repair request is bound to a different proof translation plan"
        )
    if request.get("obligation_graph_sha256") != graph_sha256:
        raise V06ProofRepairError(
            "repair request is bound to a different proof-obligation graph"
        )
    if request.get("inventory_commitment_sha256") != translation.get(
        "inventory_commitment_sha256"
    ):
        raise V06ProofRepairError(
            "repair request is bound to a different project inventory"
        )
    return actual


def _sanitize_assumption(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise V06ProofRepairError(f"{label} must be an object")
    unexpected = sorted(set(value) - _ALLOWED_ASSUMPTION_KEYS)
    if unexpected:
        raise V06ProofRepairError(
            f"{label} contains forbidden fields: {unexpected}"
        )
    return _json_clone(value)


def _sanitize_replacement_proposal(
    value: Any,
    *,
    expected_proposal_id: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise V06ProofRepairError("replacement_proposal must be an object")
    unexpected = sorted(set(value) - _ALLOWED_PROPOSAL_KEYS)
    if unexpected:
        raise V06ProofRepairError(
            f"replacement proposal contains forbidden fields: {unexpected}"
        )
    proposal = _json_clone(value)
    if proposal.get("id") != expected_proposal_id:
        raise V06ProofRepairError(
            "replacement proposal id must equal the obligation proposal_id"
        )

    confidence = proposal.get("confidence")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(float(confidence))
        or not 0.0 <= float(confidence) <= 1.0
    ):
        raise V06ProofRepairError(
            "replacement proposal confidence must be finite in [0,1]"
        )

    claim = proposal.get("claim")
    if claim is not None:
        if not isinstance(claim, Mapping):
            raise V06ProofRepairError("replacement claim must be an object")
        unexpected_claim = sorted(set(claim) - _ALLOWED_CLAIM_KEYS)
        if unexpected_claim:
            raise V06ProofRepairError(
                f"replacement claim contains forbidden fields: {unexpected_claim}"
            )
        proposal["claim"] = _json_clone(claim)

    check = proposal.get("check")
    if check is not None:
        if not isinstance(check, Mapping):
            raise V06ProofRepairError("replacement check must be an object")
        unexpected_check = sorted(set(check) - _ALLOWED_CHECK_KEYS)
        if unexpected_check:
            raise V06ProofRepairError(
                f"replacement check contains forbidden fields: {unexpected_check}"
            )
        proposal["check"] = _json_clone(check)

    if "assumption" in proposal:
        proposal["assumption"] = _sanitize_assumption(
            proposal["assumption"],
            label="replacement assumption",
        )
    assumptions = proposal.get("assumptions")
    if assumptions is not None:
        if not isinstance(assumptions, list):
            raise V06ProofRepairError(
                "replacement proposal assumptions must be an array"
            )
        proposal["assumptions"] = [
            _sanitize_assumption(item, label=f"replacement assumption {index}")
            for index, item in enumerate(assumptions)
        ]

    artifact_ids = proposal.get("artifact_ids")
    if artifact_ids is not None and (
        not isinstance(artifact_ids, list)
        or not all(isinstance(item, str) for item in artifact_ids)
    ):
        raise V06ProofRepairError(
            "replacement proposal artifact_ids must be an array of strings"
        )
    return proposal


def compile_proof_repair_response_v06(
    translation: Mapping[str, Any],
    request: Mapping[str, Any],
    response: Mapping[str, Any],
) -> dict[str, Any]:
    request_sha256 = _verify_repair_request(
        request,
        translation=translation,
    )
    if response.get("format") != PROOF_REPAIR_RESPONSE_FORMAT_V06:
        raise V06ProofRepairError(
            f"unsupported proof repair response format: {response.get('format')!r}"
        )
    if response.get("repair_request_sha256") != request_sha256:
        raise V06ProofRepairError(
            "repair response is bound to a different repair request"
        )
    if response.get("obligation_graph_sha256") != request.get(
        "obligation_graph_sha256"
    ):
        raise V06ProofRepairError(
            "repair response is bound to a different proof-obligation graph"
        )
    if response.get("inventory_commitment_sha256") != request.get(
        "inventory_commitment_sha256"
    ):
        raise V06ProofRepairError(
            "repair response is bound to a different project inventory"
        )

    proposer = response.get("proposer")
    if not isinstance(proposer, Mapping):
        raise V06ProofRepairError("repair response requires proposer metadata")
    proposer_name = _nonempty_string(
        proposer.get("name"),
        label="repair proposer name",
    )

    raw_tasks = request.get("tasks")
    if not isinstance(raw_tasks, list):
        raise V06ProofRepairError("repair request tasks must be an array")
    tasks: dict[str, Mapping[str, Any]] = {}
    for task in raw_tasks:
        if not isinstance(task, Mapping):
            raise V06ProofRepairError("repair request task must be an object")
        obligation_id = _nonempty_string(
            task.get("obligation_id"),
            label="repair task obligation_id",
        )
        if obligation_id in tasks:
            raise V06ProofRepairError(
                f"duplicate repair request obligation id: {obligation_id}"
            )
        tasks[obligation_id] = task

    raw_repairs = response.get("repairs")
    if not isinstance(raw_repairs, list):
        raise V06ProofRepairError("repair response repairs must be an array")

    proposals: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    seen_obligations: set[str] = set()
    seen_proposals: set[str] = set()
    for index, repair in enumerate(raw_repairs):
        if not isinstance(repair, Mapping):
            raise V06ProofRepairError(f"repair {index} must be an object")
        obligation_id = _nonempty_string(
            repair.get("obligation_id"),
            label=f"repair {index} obligation_id",
        )
        if obligation_id in seen_obligations:
            raise V06ProofRepairError(
                f"duplicate repair response obligation id: {obligation_id}"
            )
        seen_obligations.add(obligation_id)
        task = tasks.get(obligation_id)
        if task is None:
            raise V06ProofRepairError(
                f"repair response references unrequested obligation {obligation_id!r}"
            )

        proposal_id = _nonempty_string(
            repair.get("proposal_id"),
            label=f"repair {obligation_id} proposal_id",
        )
        if proposal_id != task.get("proposal_id"):
            raise V06ProofRepairError(
                f"repair {obligation_id!r} targets the wrong proposal"
            )
        action = _nonempty_string(
            repair.get("action"),
            label=f"repair {obligation_id} action",
        )
        if action != task.get("allowed_action"):
            raise V06ProofRepairError(
                f"repair {obligation_id!r} uses action {action!r}, "
                f"expected {task.get('allowed_action')!r}"
            )
        if proposal_id in seen_proposals:
            raise V06ProofRepairError(
                "one repair response may emit at most one replacement per proposal"
            )
        seen_proposals.add(proposal_id)

        replacement = _sanitize_replacement_proposal(
            repair.get("replacement_proposal"),
            expected_proposal_id=proposal_id,
        )
        proposals.append(replacement)
        provenance.append(
            {
                "obligation_id": obligation_id,
                "proposal_id": proposal_id,
                "action": action,
                "candidate_snapshot_sha256": task.get(
                    "candidate_snapshot_sha256"
                ),
                "replacement_proposal_sha256": _commitment(replacement),
            }
        )

    compiled_core = {
        "format": PROOF_PROPOSALS_FORMAT_V06,
        "inventory_commitment_sha256": translation.get(
            "inventory_commitment_sha256"
        ),
        "proposer": {
            "kind": "external_model",
            "name": proposer_name,
            "version": proposer.get("version"),
            "model_family": proposer.get("model_family"),
        },
        "proposals": proposals,
        "repair_provenance": {
            "format": PROOF_REPAIR_RESPONSE_FORMAT_V06,
            "compiler": PROOF_REPAIR_COMPILER_V06,
            "translation_plan_sha256": translation.get("plan_sha256"),
            "obligation_graph_sha256": request.get("obligation_graph_sha256"),
            "repair_request_sha256": request_sha256,
            "repairs": provenance,
        },
    }
    return {
        **compiled_core,
        "compiled_repair_sha256": _commitment(compiled_core),
    }


def load_proof_repair_inputs_v06(
    translation_path: str | Path,
    request_path: str | Path | None = None,
    response_path: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    def load(path: str | Path, *, label: str) -> dict[str, Any]:
        try:
            value = strict_json_load(Path(path).resolve())
        except (OSError, StrictJSONError) as exc:
            raise V06ProofRepairError(f"cannot load {label}: {exc}") from exc
        if not isinstance(value, dict):
            raise V06ProofRepairError(f"{label} root must be an object")
        return value

    translation = load(translation_path, label="proof translation")
    request = (
        load(request_path, label="proof repair request")
        if request_path is not None
        else None
    )
    response = (
        load(response_path, label="proof repair response")
        if response_path is not None
        else None
    )
    return translation, request, response


def _write_json(
    value: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool,
    label: str,
) -> Path:
    output = Path(path).resolve()
    if output.exists() and not overwrite:
        raise V06ProofRepairError(
            f"refusing to overwrite existing {label}: {output}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return output


def write_proof_repair_request_v06(
    request: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> str:
    if request.get("format") != PROOF_REPAIR_REQUEST_FORMAT_V06:
        raise V06ProofRepairError("refusing to write invalid proof repair request")
    return str(
        _write_json(
            request,
            path,
            overwrite=overwrite,
            label="proof repair request",
        )
    )


def write_compiled_repair_proposals_v06(
    proposals: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> str:
    if proposals.get("format") != PROOF_PROPOSALS_FORMAT_V06:
        raise V06ProofRepairError(
            "refusing to write invalid compiled repair proposals"
        )
    return str(
        _write_json(
            proposals,
            path,
            overwrite=overwrite,
            label="compiled repair proposals",
        )
    )
