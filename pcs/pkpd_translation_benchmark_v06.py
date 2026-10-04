from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Mapping

from .discover_v06 import discover_project_v06
from .proof_repair_v06 import PROOF_REPAIR_RESPONSE_FORMAT_V06
from .proof_search_v06 import (
    advance_proof_search_v06,
    start_proof_search_v06,
    write_proof_search_session_v06,
    write_proof_search_trajectory_v06,
)
from .proof_translation_v06 import PROOF_PROPOSALS_FORMAT_V06


PKPD_TRANSLATION_BENCHMARK_FORMAT_V06 = "pcs-pkpd-translation-benchmark-v1"


class V06PkpdTranslationBenchmarkError(ValueError):
    pass


def _json_write(value: Mapping[str, Any], path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return str(path.resolve())


def _default_fixture_root() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "pkpd_translation_benchmark"
    )


def _copy_fixture(
    source: Path,
    destination: Path,
    *,
    overwrite: bool,
) -> None:
    if not source.is_dir():
        raise V06PkpdTranslationBenchmarkError(
            f"PK/PD translation benchmark fixture is missing: {source}"
        )
    if destination.exists():
        if not overwrite:
            raise V06PkpdTranslationBenchmarkError(
                f"benchmark output already exists: {destination}"
            )
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def _inventory_ids(discovery: Mapping[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in discovery.get("inventory", []):
        if not isinstance(item, Mapping):
            continue
        path = item.get("path")
        artifact_id = item.get("artifact_id")
        if isinstance(path, str) and isinstance(artifact_id, str):
            out[path] = artifact_id
    required = {
        "model.json",
        "predictions.csv",
        "observations.csv",
        "fit_summary.json",
        "study_metadata.json",
        "study_protocol.md",
        "analysis.py",
    }
    missing = sorted(required - set(out))
    if missing:
        raise V06PkpdTranslationBenchmarkError(
            f"benchmark discovery missed required fixture artifacts: {missing}"
        )
    return out


def _replay_proposal(
    ids: Mapping[str, str],
    *,
    effect_column: str,
) -> dict[str, Any]:
    assumption_id = "A_MODEL_DECLARATION"
    claim_id = "C_MODEL_PKPD_REPLAY"
    check_id = "E_MODEL_PKPD_REPLAY"
    return {
        "id": "MODEL_PKPD_REPLAY_REPAIR",
        "confidence": 0.995,
        "finding": (
            "The predictions.csv table is the model-generated output and should "
            "match the declared restricted PK/PD equations."
        ),
        "artifact_ids": [
            ids["model.json"],
            ids["predictions.csv"],
        ],
        "assumption": {
            "id": assumption_id,
            "statement": (
                "The one-compartment IV-bolus plus direct Emax equations are the "
                "declared computational model; this does not assert biological or "
                "clinical adequacy."
            ),
            "scope": [claim_id],
        },
        "claim": {
            "id": claim_id,
            "statement": (
                "The model-generated prediction table matches the declared "
                "restricted PK/PD equations within the PCS numeric tolerance."
            ),
            "kind": "computational",
            "required_evidence": [check_id],
            "assumptions": [assumption_id],
        },
        "check": {
            "id": check_id,
            "type": "pkpd_reference_match",
            "claim_ids": [claim_id],
            "model_artifact": ids["model.json"],
            "output_artifact": ids["predictions.csv"],
            "time_column": "time",
            "concentration_column": "concentration",
            "effect_column": effect_column,
            "rel_tol": 1e-9,
            "abs_tol": 1e-12,
        },
    }


def _proposal_document(
    discovery: Mapping[str, Any],
    ids: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "format": PROOF_PROPOSALS_FORMAT_V06,
        "inventory_commitment_sha256": discovery[
            "inventory_commitment_sha256"
        ],
        "proposer": {
            "kind": "external_model",
            "name": "pkpd-benchmark-grounded-proposer",
            "version": "fixture-v1",
            "model_family": "deterministic-benchmark-fixture",
        },
        "proposals": [
            _replay_proposal(ids, effect_column="response"),
            {
                "id": "MODEL_EMPIRICAL_ADEQUACY",
                "confidence": 0.99,
                "finding": (
                    "The restricted model adequately describes the synthetic "
                    "observed concentration and effect data."
                ),
                "artifact_ids": [
                    ids["model.json"],
                    ids["observations.csv"],
                    ids["fit_summary.json"],
                ],
                "claim": {
                    "id": "C_MODEL_EMPIRICAL_ADEQUACY",
                    "statement": (
                        "The restricted PK/PD model adequately describes the "
                        "synthetic observations."
                    ),
                    "kind": "empirical",
                },
                "check": {
                    "id": "E_MODEL_EMPIRICAL_ADEQUACY",
                    "type": "external_empirical_validation",
                    "claim_ids": ["C_MODEL_EMPIRICAL_ADEQUACY"],
                },
            },
            {
                "id": "MODEL_PEAK_THRESHOLD",
                "confidence": 0.995,
                "finding": (
                    "The peak predicted concentration does not exceed 12 mg/L."
                ),
                "artifact_ids": [ids["predictions.csv"]],
                "claim": {
                    "id": "C_MODEL_PEAK_THRESHOLD",
                    "statement": (
                        "The peak predicted concentration is at most 12 mg/L."
                    ),
                    "kind": "computational",
                },
                "check": {
                    "id": "E_MODEL_PEAK_THRESHOLD",
                    "type": "pkpd_peak_concentration_threshold",
                    "claim_ids": ["C_MODEL_PEAK_THRESHOLD"],
                    "output_artifact": ids["predictions.csv"],
                    "concentration_column": "concentration",
                    "upper_bound": 12.0,
                    "unit": "mg/L",
                },
            },
        ],
    }


def _candidate(
    translation: Mapping[str, Any],
    candidate_id: str,
) -> Mapping[str, Any]:
    for candidate in translation.get("candidates", []):
        if isinstance(candidate, Mapping) and candidate.get("id") == candidate_id:
            return candidate
    raise V06PkpdTranslationBenchmarkError(
        f"benchmark translation is missing candidate {candidate_id!r}"
    )


def _repair_response(
    session: Mapping[str, Any],
    corrected_proposal: Mapping[str, Any],
) -> dict[str, Any]:
    request = session.get("current_repair_request")
    if not isinstance(request, Mapping):
        raise V06PkpdTranslationBenchmarkError(
            "benchmark search lacks current repair request"
        )
    tasks = request.get("tasks")
    if not isinstance(tasks, list):
        raise V06PkpdTranslationBenchmarkError(
            "benchmark repair request lacks tasks"
        )
    task = next(
        (
            item
            for item in tasks
            if isinstance(item, Mapping)
            and item.get("proposal_id") == "MODEL_PKPD_REPLAY_REPAIR"
        ),
        None,
    )
    if not isinstance(task, Mapping):
        raise V06PkpdTranslationBenchmarkError(
            "benchmark did not expose the expected replay-grounding repair task"
        )
    return {
        "format": PROOF_REPAIR_RESPONSE_FORMAT_V06,
        "repair_request_sha256": request["repair_request_sha256"],
        "obligation_graph_sha256": request["obligation_graph_sha256"],
        "inventory_commitment_sha256": request[
            "inventory_commitment_sha256"
        ],
        "proposer": {
            "kind": "external_model",
            "name": "pkpd-benchmark-repair-proposer",
            "version": "fixture-v1",
            "model_family": "deterministic-benchmark-fixture",
        },
        "repairs": [
            {
                "obligation_id": task["obligation_id"],
                "proposal_id": task["proposal_id"],
                "action": task["allowed_action"],
                "replacement_proposal": dict(corrected_proposal),
            }
        ],
    }


def run_pkpd_translation_benchmark_v06(
    output_root: str | Path,
    *,
    fixture_root: str | Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    destination = Path(output_root).resolve()
    source = (
        Path(fixture_root).resolve()
        if fixture_root is not None
        else _default_fixture_root().resolve()
    )
    _copy_fixture(source, destination, overwrite=overwrite)

    discovery = discover_project_v06(
        destination,
        subject="synthetic-pkpd-grounded-translation-benchmark",
    )
    ids = _inventory_ids(discovery)

    deterministic_replays = [
        rec
        for rec in discovery.get("recommendations", [])
        if isinstance(rec, Mapping)
        and rec.get("detector") == "pkpd-output-columns"
    ]
    deterministic_contracts = [
        rec
        for rec in discovery.get("recommendations", [])
        if isinstance(rec, Mapping)
        and rec.get("detector") == "restricted-pkpd-model"
    ]

    control_dir = destination / ".pcs" / "pkpd-translation-benchmark"
    control_dir.mkdir(parents=True, exist_ok=True)

    proposal_document = _proposal_document(discovery, ids)
    proposal_path = control_dir / "model-proposals.json"
    _json_write(proposal_document, proposal_path)

    initial = start_proof_search_v06(
        destination,
        proposal_files=[proposal_path],
        subject="synthetic-pkpd-grounded-translation-benchmark",
        max_iterations=4,
    )
    initial_path = control_dir / "initial-search-session.json"
    write_proof_search_session_v06(initial, initial_path, overwrite=True)
    _json_write(
        initial["current_repair_request"],
        control_dir / "initial-repair-request.json",
    )

    corrected = _replay_proposal(ids, effect_column="effect")
    response = _repair_response(initial, corrected)
    response_path = control_dir / "repair-response.json"
    _json_write(response, response_path)

    final = advance_proof_search_v06(
        destination,
        initial,
        response,
        state_dir=control_dir / "search-state",
    )
    final_path = control_dir / "final-search-session.json"
    write_proof_search_session_v06(final, final_path, overwrite=True)
    trajectory_path = control_dir / "trajectory.json"
    write_proof_search_trajectory_v06(final, trajectory_path, overwrite=True)

    initial_translation = initial["current_translation"]
    final_translation = final["current_translation"]
    initial_replay = _candidate(
        initial_translation,
        "MODEL_PKPD_REPLAY_REPAIR",
    )
    final_replay = _candidate(
        final_translation,
        "MODEL_PKPD_REPLAY_REPAIR",
    )
    empirical = _candidate(
        final_translation,
        "MODEL_EMPIRICAL_ADEQUACY",
    )
    peak = _candidate(
        final_translation,
        "MODEL_PEAK_THRESHOLD",
    )

    deterministic_contract = next(
        (
            candidate
            for candidate in final_translation.get("candidates", [])
            if isinstance(candidate, Mapping)
            and isinstance(candidate.get("source"), Mapping)
            and candidate["source"].get("kind")
            == "deterministic_discovery"
            and isinstance(candidate.get("check"), Mapping)
            and candidate["check"].get("type") == "pkpd_contract"
        ),
        None,
    )

    criteria = {
        "deterministic_discovery_detected_exactly_one_pkpd_contract": (
            len(deterministic_contracts) == 1
        ),
        "deterministic_discovery_refused_ambiguous_output_role": (
            len(deterministic_replays) == 0
        ),
        "initial_model_replay_failed_closed_on_wrong_column": (
            initial_replay.get("status") == "REJECTED_UNGROUNDED"
            and any(
                isinstance(obligation, Mapping)
                and obligation.get("kind")
                == "GROUND_PREDICATE_IN_PROJECT_BYTES"
                for obligation in initial_replay.get("obligations", [])
            )
        ),
        "search_exposed_exactly_one_machine_repair": (
            initial.get("status") == "AWAITING_REPAIR"
            and initial.get("summary", {}).get("repairable_tasks") == 1
        ),
        "repaired_replay_compiled_to_lean_target": (
            final_replay.get("selected") is True
            and final_replay.get("formalizable") is True
            and final_replay.get("status")
            == "COMPILED_LEAN_BUILTIN_WITH_ASSUMPTIONS"
            and isinstance(final_replay.get("formal_target"), Mapping)
            and final_replay["formal_target"].get("real_bridge_theorem")
            == "PCSReal.PKPD.pcs_pkpd_reference_match_real"
        ),
        "deterministic_pkpd_contract_remained_selected": (
            isinstance(deterministic_contract, Mapping)
            and deterministic_contract.get("selected") is True
            and deterministic_contract.get("formalizable") is True
        ),
        "empirical_adequacy_remained_external_boundary": (
            empirical.get("selected") is False
            and empirical.get("status") == "EXTERNAL_VALIDATOR_REQUIRED"
            and any(
                isinstance(obligation, Mapping)
                and obligation.get("kind") == "PROVIDE_EXTERNAL_VALIDATOR"
                for obligation in empirical.get("obligations", [])
            )
        ),
        "unsupported_peak_threshold_remained_open": (
            peak.get("selected") is False
            and peak.get("status") == "OPEN_UNSUPPORTED_DOMAIN"
            and any(
                isinstance(obligation, Mapping)
                and obligation.get("kind")
                == "IMPLEMENT_CERTIFIED_CHECKER"
                for obligation in peak.get("obligations", [])
            )
        ),
        "search_stopped_at_non_machine_boundary": (
            final.get("status") == "BLOCKED_NO_MACHINE_REPAIR"
            and final.get("summary", {}).get("repairable_tasks") == 0
            and final.get("summary", {}).get("blocking_open_obligations") == 2
        ),
        "search_never_granted_authority": (
            final.get("authority", {}).get(
                "coordinator_trusted_to_set_authoritative"
            )
            is False
            and final.get("authority", {}).get(
                "diagnostic_reward_sets_authority"
            )
            is False
            and final.get("authority", {}).get(
                "human_confirmation_required"
            )
            is True
            and final.get("authority", {}).get(
                "replay_and_lean_authority_required"
            )
            is True
        ),
    }
    passed = all(criteria.values())

    report = {
        "format": PKPD_TRANSLATION_BENCHMARK_FORMAT_V06,
        "passed": passed,
        "subject": "synthetic-pkpd-grounded-translation-benchmark",
        "project_root": str(destination),
        "inventory_commitment_sha256": discovery[
            "inventory_commitment_sha256"
        ],
        "design": {
            "purpose": (
                "Test whether PCS can resolve an ambiguous PK/PD output role "
                "through an untrusted grounded proposer, repair a failed "
                "formalization, formally close the supported computational "
                "claims, and stop at empirical/unsupported-domain boundaries."
            ),
            "synthetic_only": True,
            "clinical_claims_permitted": False,
            "ambiguous_tables": ["predictions.csv", "observations.csv"],
        },
        "criteria": criteria,
        "discovery": {
            "summary": discovery.get("summary"),
            "unresolved": discovery.get("unresolved"),
            "deterministic_pkpd_contract_recommendations": len(
                deterministic_contracts
            ),
            "deterministic_pkpd_replay_recommendations": len(
                deterministic_replays
            ),
        },
        "initial_search": {
            "status": initial.get("status"),
            "summary": initial.get("summary"),
            "session_sha256": initial.get("session_sha256"),
            "graph_sha256": initial_translation.get(
                "obligation_graph", {}
            ).get("graph_sha256"),
            "replay_candidate_status": initial_replay.get("status"),
        },
        "final_search": {
            "status": final.get("status"),
            "summary": final.get("summary"),
            "session_sha256": final.get("session_sha256"),
            "trajectory_sha256": final.get(
                "trajectory", {}
            ).get("trajectory_sha256"),
            "graph_sha256": final_translation.get(
                "obligation_graph", {}
            ).get("graph_sha256"),
        },
        "proof_frontier": {
            "theorem_backed": [
                {
                    "candidate_id": (
                        deterministic_contract.get("id")
                        if isinstance(deterministic_contract, Mapping)
                        else None
                    ),
                    "claim": "restricted PK/PD positivity and dimensional contract",
                    "proof_level": (
                        deterministic_contract.get(
                            "formal_target", {}
                        ).get("proof_level")
                        if isinstance(deterministic_contract, Mapping)
                        else None
                    ),
                },
                {
                    "candidate_id": "MODEL_PKPD_REPLAY_REPAIR",
                    "claim": (
                        "prediction table matches the declared restricted "
                        "PK/PD equations within committed tolerance"
                    ),
                    "proof_level": final_replay.get(
                        "formal_target", {}
                    ).get("proof_level"),
                    "real_bridge_theorem": final_replay.get(
                        "formal_target", {}
                    ).get("real_bridge_theorem"),
                },
            ],
            "external_validator_required": [
                {
                    "candidate_id": "MODEL_EMPIRICAL_ADEQUACY",
                    "claim": (
                        "restricted model adequately describes synthetic "
                        "observations"
                    ),
                    "status": empirical.get("status"),
                }
            ],
            "certified_checker_missing": [
                {
                    "candidate_id": "MODEL_PEAK_THRESHOLD",
                    "claim": (
                        "peak predicted concentration is at most 12 mg/L"
                    ),
                    "status": peak.get("status"),
                }
            ],
            "not_established": [
                "biological adequacy",
                "clinical validity",
                "treatment efficacy",
                "treatment safety",
            ],
        },
        "artifacts": {
            "initial_search_session": str(initial_path.resolve()),
            "initial_repair_request": str(
                (control_dir / "initial-repair-request.json").resolve()
            ),
            "repair_response": str(response_path.resolve()),
            "final_search_session": str(final_path.resolve()),
            "trajectory": str(trajectory_path.resolve()),
        },
    }
    report_path = control_dir / "benchmark-report.json"
    _json_write(report, report_path)
    report["artifacts"]["benchmark_report"] = str(report_path.resolve())

    if not passed:
        failed = sorted(
            name
            for name, ok in criteria.items()
            if ok is not True
        )
        raise V06PkpdTranslationBenchmarkError(
            "PK/PD translation benchmark failed criteria: "
            + ", ".join(failed)
        )
    return report
