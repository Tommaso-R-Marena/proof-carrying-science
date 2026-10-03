from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical_json import canonicalize_jcs_bytes
from .jsonio import StrictJSONError, strict_json_load
from .proof_search_v06 import (
    PROOF_SEARCH_SESSION_FORMAT_V06,
    V06ProofSearchError,
    validate_proof_search_session_v06,
)


PROOF_SEARCH_CORPUS_FORMAT_V06 = "pcs-proof-search-corpus-v1"
PROOF_SEARCH_CORPUS_COMPILER_V06 = "pcs-proof-search-corpus-compiler/0.1"
PROOF_SEARCH_CORPUS_SPLIT_CONTRACT_V06 = "problem-group-sha256-80-10-10-v1"


class V06ProofSearchCorpusError(ValueError):
    pass


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _commitment(value: Any) -> str:
    return hashlib.sha256(canonicalize_jcs_bytes(value)).hexdigest()


def _problem_group_sha256(
    session: Mapping[str, Any],
) -> str:
    return _commitment(
        {
            "initial_plan_sha256": session.get("initial_plan_sha256"),
            "inventory_commitment_sha256": session.get(
                "inventory_commitment_sha256"
            ),
            "intent_anchors_sha256": session.get("intent_anchors_sha256"),
            "subject": session.get("subject"),
        }
    )


def _split_for_problem_group(problem_group_sha256: str) -> str:
    bucket = int(
        hashlib.sha256(
            canonicalize_jcs_bytes(
                {
                    "contract": PROOF_SEARCH_CORPUS_SPLIT_CONTRACT_V06,
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


def _source_record(session: Mapping[str, Any]) -> dict[str, Any]:
    problem_group_sha256 = _problem_group_sha256(session)
    return {
        "session_sha256": session["session_sha256"],
        "search_id": session["search_id"],
        "problem_group_sha256": problem_group_sha256,
        "trajectory_sha256": session["trajectory"]["trajectory_sha256"],
        "inventory_commitment_sha256": session[
            "inventory_commitment_sha256"
        ],
        "initial_plan_sha256": session["initial_plan_sha256"],
        "iteration": session["iteration"],
        "status": session["status"],
        "split": _split_for_problem_group(problem_group_sha256),
        "summary": _json_clone(session["summary"]),
    }


def _metric_delta(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    key: str,
) -> int:
    return int(after.get(key, 0)) - int(before.get(key, 0))


def _example_from_repair_record(
    *,
    session: Mapping[str, Any],
    step: Mapping[str, Any],
    record: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    search_id = str(session["search_id"])
    problem_group_sha256 = _problem_group_sha256(session)
    task = record.get("task")
    replacement = record.get("replacement_proposal")
    if not isinstance(task, Mapping) or not isinstance(replacement, Mapping):
        raise V06ProofSearchCorpusError(
            "trajectory repair record is missing task/replacement proposal"
        )
    before = step.get("metrics_before")
    after = step.get("metrics_after")
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        raise V06ProofSearchCorpusError(
            "trajectory step is missing before/after metrics"
        )

    outcome = str(step.get("outcome"))
    if outcome not in {
        "OBJECTIVE_PROGRESS",
        "CYCLE_DETECTED",
        "NOVEL_STATE_NO_OBJECTIVE_PROGRESS",
    }:
        raise V06ProofSearchCorpusError(
            f"unsupported proof-search trajectory outcome: {outcome!r}"
        )

    core = {
        "search_id": search_id,
        "problem_group_sha256": problem_group_sha256,
        "split": _split_for_problem_group(problem_group_sha256),
        "iteration": int(step["iteration"]),
        "proposal_id": record.get("proposal_id"),
        "obligation_id": record.get("obligation_id"),
        "allowed_action": record.get("action"),
        "state": {
            "before_state_sha256": step.get("before_state_sha256"),
            "before_plan_sha256": step.get("before_plan_sha256"),
            "before_graph_sha256": step.get("before_graph_sha256"),
            "repair_request_sha256": step.get("repair_request_sha256"),
            "task": _json_clone(task),
        },
        "target_action": {
            "replacement_proposal": _json_clone(replacement),
            "replacement_proposal_sha256": record.get(
                "replacement_proposal_sha256"
            ),
        },
        "observed_transition": {
            "after_state_sha256": step.get("after_state_sha256"),
            "after_plan_sha256": step.get("after_plan_sha256"),
            "after_graph_sha256": step.get("after_graph_sha256"),
            "compiled_repair_sha256": step.get("compiled_repair_sha256"),
            "metrics_before": _json_clone(before),
            "metrics_after": _json_clone(after),
        },
        "labels": {
            "outcome": outcome,
            "objective_progress": outcome == "OBJECTIVE_PROGRESS",
            "cycle_detected": outcome == "CYCLE_DETECTED",
            "no_objective_progress": (
                outcome == "NOVEL_STATE_NO_OBJECTIVE_PROGRESS"
            ),
            "blocking_obligation_delta": _metric_delta(
                before, after, "blocking_open_obligations"
            ),
            "blocking_obligations_closed": (
                int(before.get("blocking_open_obligations", 0))
                - int(after.get("blocking_open_obligations", 0))
            ),
            "compiled_selected_delta": _metric_delta(
                before, after, "compiled_selected"
            ),
            "compiled_selected_added": (
                int(after.get("compiled_selected", 0))
                - int(before.get("compiled_selected", 0))
            ),
            "formalizable_candidate_delta": _metric_delta(
                before, after, "formalizable_candidates"
            ),
            "formalizable_candidates_added": (
                int(after.get("formalizable_candidates", 0))
                - int(before.get("formalizable_candidates", 0))
            ),
            "repairable_task_delta": _metric_delta(
                before, after, "repairable_tasks"
            ),
            "repairable_tasks_closed": (
                int(before.get("repairable_tasks", 0))
                - int(after.get("repairable_tasks", 0))
            ),
            "diagnostic_reward": int(step.get("diagnostic_reward", 0)),
            "label_scope": "SEARCH_BEHAVIOR_ONLY",
            "has_scientific_truth_label": False,
            "has_proof_authority_label": False,
            "credit_assignment": "STEP_LEVEL_SHARED",
        },
        "authority": {
            "training_record_is_authoritative": False,
            "diagnostic_reward_sets_authority": False,
            "human_confirmation_required": True,
            "replay_and_lean_authority_required": True,
        },
    }
    return _commitment(core), core


def build_proof_search_corpus_v06(
    sessions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    sources: dict[str, dict[str, Any]] = {}
    examples: dict[str, dict[str, Any]] = {}

    for index, session in enumerate(sessions):
        if not isinstance(session, Mapping):
            raise V06ProofSearchCorpusError(
                f"proof-search corpus session {index} must be an object"
            )
        if session.get("format") != PROOF_SEARCH_SESSION_FORMAT_V06:
            raise V06ProofSearchCorpusError(
                f"unsupported proof-search session format at index {index}: "
                f"{session.get('format')!r}"
            )
        try:
            validate_proof_search_session_v06(session)
        except V06ProofSearchError as exc:
            raise V06ProofSearchCorpusError(
                f"invalid proof-search session at index {index}: {exc}"
            ) from exc

        source = _source_record(session)
        session_sha256 = str(source["session_sha256"])
        existing_source = sources.get(session_sha256)
        if existing_source is not None and existing_source != source:
            raise V06ProofSearchCorpusError(
                "proof-search session hash collision with different metadata"
            )
        sources[session_sha256] = source

        trajectory = session.get("trajectory")
        steps = trajectory.get("steps") if isinstance(trajectory, Mapping) else None
        if not isinstance(steps, list):
            raise V06ProofSearchCorpusError(
                "validated proof-search session lacks trajectory steps"
            )
        for step in steps:
            if not isinstance(step, Mapping):
                continue
            records = step.get("repair_records", [])
            if not isinstance(records, list):
                raise V06ProofSearchCorpusError(
                    "trajectory repair_records must be an array"
                )
            for record in records:
                if not isinstance(record, Mapping):
                    raise V06ProofSearchCorpusError(
                        "trajectory repair record must be an object"
                    )
                example_id, core = _example_from_repair_record(
                    session=session,
                    step=step,
                    record=record,
                )
                existing = examples.get(example_id)
                if existing is None:
                    examples[example_id] = {
                        "example_id": example_id,
                        **core,
                        "source_session_sha256s": [session_sha256],
                    }
                else:
                    comparable = {
                        key: value
                        for key, value in existing.items()
                        if key not in {"example_id", "source_session_sha256s"}
                    }
                    if comparable != core:
                        raise V06ProofSearchCorpusError(
                            "proof-search example hash collision with different content"
                        )
                    existing["source_session_sha256s"] = sorted(
                        set(existing["source_session_sha256s"])
                        | {session_sha256}
                    )

    ordered_sources = [
        sources[key]
        for key in sorted(sources)
    ]
    ordered_examples = [
        examples[key]
        for key in sorted(examples)
    ]

    split_counts = {"train": 0, "validation": 0, "test": 0}
    outcome_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    search_ids: set[str] = set()
    problem_groups: set[str] = set()
    for example in ordered_examples:
        split_counts[str(example["split"])] += 1
        outcome = str(example["labels"]["outcome"])
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        search_ids.add(str(example["search_id"]))
        problem_groups.add(str(example["problem_group_sha256"]))
    for source in ordered_sources:
        status = str(source["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
        search_ids.add(str(source["search_id"]))
        problem_groups.add(str(source["problem_group_sha256"]))

    core = {
        "format": PROOF_SEARCH_CORPUS_FORMAT_V06,
        "compiler": PROOF_SEARCH_CORPUS_COMPILER_V06,
        "split_contract": {
            "id": PROOF_SEARCH_CORPUS_SPLIT_CONTRACT_V06,
            "train_percent": 80,
            "validation_percent": 10,
            "test_percent": 10,
            "grouping_key": "problem_group_sha256",
            "purpose": (
                "Keep all trajectories derived from the same underlying proof "
                "problem in one split even when run configuration such as the "
                "iteration budget changes."
            ),
        },
        "trust_model": {
            "corpus_is_proof_authority": False,
            "diagnostic_reward_is_scientific_truth": False,
            "examples_come_from_validated_pcs_search_sessions": True,
            "labels_describe_search_behavior_not_scientific_correctness": True,
            "human_confirmation_replay_and_lean_remain_authoritative": True,
        },
        "sources": ordered_sources,
        "examples": ordered_examples,
        "summary": {
            "source_sessions": len(ordered_sources),
            "search_ids": len(search_ids),
            "problem_groups": len(problem_groups),
            "examples": len(ordered_examples),
            "split_counts": split_counts,
            "outcome_counts": {
                key: outcome_counts[key]
                for key in sorted(outcome_counts)
            },
            "source_status_counts": {
                key: status_counts[key]
                for key in sorted(status_counts)
            },
            "examples_with_positive_diagnostic_reward": sum(
                1
                for example in ordered_examples
                if int(example["labels"]["diagnostic_reward"]) > 0
            ),
            "examples_with_nonpositive_diagnostic_reward": sum(
                1
                for example in ordered_examples
                if int(example["labels"]["diagnostic_reward"]) <= 0
            ),
        },
    }
    return {
        **core,
        "corpus_sha256": _commitment(core),
    }


def load_proof_search_sessions_v06(
    paths: Sequence[str | Path],
) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    for raw_path in paths:
        path = Path(raw_path).resolve()
        try:
            value = strict_json_load(path)
        except (OSError, StrictJSONError) as exc:
            raise V06ProofSearchCorpusError(
                f"cannot load proof-search session {path}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise V06ProofSearchCorpusError(
                f"proof-search session root must be an object: {path}"
            )
        sessions.append(value)
    return sessions


def build_proof_search_corpus_from_files_v06(
    paths: Sequence[str | Path],
) -> dict[str, Any]:
    return build_proof_search_corpus_v06(
        load_proof_search_sessions_v06(paths)
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
    claimed = corpus.get("corpus_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise V06ProofSearchCorpusError(
            "proof-search corpus lacks a valid corpus_sha256"
        )
    core = {
        key: _json_clone(value)
        for key, value in corpus.items()
        if key != "corpus_sha256"
    }
    if _commitment(core) != claimed:
        raise V06ProofSearchCorpusError(
            "proof-search corpus commitment does not match corpus contents"
        )

    output = Path(path).resolve()
    if output.exists() and not overwrite:
        raise V06ProofSearchCorpusError(
            f"refusing to overwrite existing proof-search corpus: {output}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            dict(corpus),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return str(output)
