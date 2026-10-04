from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .discover_v06 import discover_project_v06
from .external_validator_v06 import (
    EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06,
    EXTERNAL_VALIDATOR_TRUST_MODEL_V06,
    EXTERNAL_VALIDATOR_TRUST_POLICY_FORMAT_V06,
    build_external_validator_receipt_payload_v06,
    sign_external_validator_receipt_v06,
)
from .proof_repair_v06 import PROOF_REPAIR_RESPONSE_FORMAT_V06
from .proof_search_v06 import (
    advance_proof_search_v06,
    start_proof_search_v06,
    write_proof_search_session_v06,
    write_proof_search_trajectory_v06,
)
from .proof_translation_v06 import PROOF_PROPOSALS_FORMAT_V06
from .reference_validators.pkpd_rmse_v06 import (
    PKPD_RMSE_VALIDATOR_ID_V06,
    evaluate_pkpd_rmse_policy_v06,
)
from .signing import public_key_fingerprint


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
        "validation_policy.json",
        "validator_trust_policy.json",
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


def _empirical_predicate() -> dict[str, str]:
    return {
        "type": "external",
        "namespace": "pcs-reference-pkpd-rmse-policy/v1",
        "proposition": (
            "The bound model prediction and synthetic observation tables satisfy "
            "the exact bound pcs-pkpd-rmse-policy-v1 thresholds under exact time "
            "alignment. This proposition is a scoped validation-policy result, "
            "not biological or clinical truth."
        ),
    }


def _empirical_proposal(
    ids: Mapping[str, str],
    *,
    validator_fingerprint: str | None = None,
) -> dict[str, Any]:
    artifact_ids = [
        ids["model.json"],
        ids["predictions.csv"],
        ids["observations.csv"],
        ids["validation_policy.json"],
        ids["validator_trust_policy.json"],
    ]
    check: dict[str, Any] = {
        "id": "E_MODEL_EMPIRICAL_ADEQUACY",
        "type": "external_empirical_validation",
        "claim_ids": ["C_MODEL_EMPIRICAL_ADEQUACY"],
        "validator": PKPD_RMSE_VALIDATOR_ID_V06,
        "predicate": _empirical_predicate(),
    }
    if validator_fingerprint is not None:
        artifact_ids.extend(
            [
                ids["validator_receipt.json"],
                ids["validator_public_key.der"],
            ]
        )
        check.update(
            {
                "receipt_format": EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06,
                "trust_model": EXTERNAL_VALIDATOR_TRUST_MODEL_V06,
                "receipt_artifact": ids["validator_receipt.json"],
                "validator_public_key_artifact": ids[
                    "validator_public_key.der"
                ],
                "validator_public_key_fingerprint": validator_fingerprint,
                "validator_trust_policy_artifact": ids[
                    "validator_trust_policy.json"
                ],
                "bound_artifact_ids": sorted(
                    [
                        ids["model.json"],
                        ids["predictions.csv"],
                        ids["observations.csv"],
                        ids["validation_policy.json"],
                        ids["validator_trust_policy.json"],
                    ]
                ),
            }
        )

    return {
        "id": "MODEL_EMPIRICAL_ADEQUACY",
        "confidence": 0.99,
        "finding": (
            "The restricted model satisfies the prespecified synthetic RMSE "
            "validation policy on the observed concentration and effect data."
        ),
        "artifact_ids": sorted(artifact_ids),
        "claim": {
            "id": "C_MODEL_EMPIRICAL_ADEQUACY",
            "statement": (
                "The restricted PK/PD model satisfies the prespecified synthetic "
                "RMSE validation policy on the bound observations."
            ),
            "kind": "empirical",
            "predicate": _empirical_predicate(),
        },
        "check": check,
    }


def _benchmark_validator_private_key() -> Ed25519PrivateKey:
    seed = hashlib.sha256(
        b"PCS synthetic PKPD validator benchmark key v1"
    ).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def _prepare_validator_receipt(
    destination: Path,
) -> tuple[dict[str, Any], str]:
    private_key = _benchmark_validator_private_key()
    public_key = private_key.public_key()
    public_der = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    (destination / "validator_public_key.der").write_bytes(public_der)
    validator_fingerprint = public_key_fingerprint(public_key)
    _json_write(
        {
            "format": EXTERNAL_VALIDATOR_TRUST_POLICY_FORMAT_V06,
            "validator": PKPD_RMSE_VALIDATOR_ID_V06,
            "validator_public_key_fingerprint": validator_fingerprint,
            "allowed_check_types": ["external_empirical_validation"],
            "allowed_predicate_namespaces": [
                _empirical_predicate()["namespace"]
            ],
        },
        destination / "validator_trust_policy.json",
    )

    preliminary = discover_project_v06(
        destination,
        subject="synthetic-pkpd-grounded-translation-benchmark",
    )
    ids = _inventory_ids(preliminary)
    bound_paths = (
        "model.json",
        "predictions.csv",
        "observations.csv",
        "validation_policy.json",
        "validator_trust_policy.json",
    )
    artifact_bytes = {
        ids[path]: (destination / path).read_bytes()
        for path in bound_paths
    }

    validation = evaluate_pkpd_rmse_policy_v06(
        predictions_bytes=(destination / "predictions.csv").read_bytes(),
        observations_bytes=(destination / "observations.csv").read_bytes(),
        policy_bytes=(destination / "validation_policy.json").read_bytes(),
    )
    payload = build_external_validator_receipt_payload_v06(
        check_type="external_empirical_validation",
        validator=PKPD_RMSE_VALIDATOR_ID_V06,
        predicate=_empirical_predicate(),
        bound_artifact_ids=[ids[path] for path in bound_paths],
        artifact_bytes=artifact_bytes,
        outcome=validation["outcome"],
    )
    receipt = sign_external_validator_receipt_v06(
        payload,
        private_key,
    )
    _json_write(receipt, destination / "validator_receipt.json")
    return validation, validator_fingerprint


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
            _empirical_proposal(ids),
            {
                "id": "MODEL_PEAK_THRESHOLD",
                "confidence": 0.995,
                "finding": (
                    "The peak predicted concentration does not exceed 12 mg/L."
                ),
                "artifact_ids": [ids["model.json"], ids["predictions.csv"]],
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
                    "model_artifact": ids["model.json"],
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
    corrected_proposals: Sequence[Mapping[str, Any]],
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
    by_proposal = {
        str(item.get("proposal_id")): item
        for item in tasks
        if isinstance(item, Mapping)
        and isinstance(item.get("proposal_id"), str)
    }
    repairs: list[dict[str, Any]] = []
    for proposal in corrected_proposals:
        proposal_id = proposal.get("id")
        task = by_proposal.get(str(proposal_id))
        if not isinstance(task, Mapping):
            raise V06PkpdTranslationBenchmarkError(
                f"benchmark did not expose a repair task for {proposal_id!r}"
            )
        repairs.append(
            {
                "obligation_id": task["obligation_id"],
                "proposal_id": task["proposal_id"],
                "action": task["allowed_action"],
                "replacement_proposal": dict(proposal),
            }
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
            "version": "fixture-v2",
            "model_family": "deterministic-benchmark-fixture",
        },
        "repairs": repairs,
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

    validation_result, validator_fingerprint = _prepare_validator_receipt(
        destination
    )
    if validation_result.get("outcome") != "PASS":
        raise V06PkpdTranslationBenchmarkError(
            "reference PK/PD validation policy unexpectedly failed"
        )

    discovery = discover_project_v06(
        destination,
        subject="synthetic-pkpd-grounded-translation-benchmark",
    )
    ids = _inventory_ids(discovery)
    for required_dynamic in (
        "validator_public_key.der",
        "validator_receipt.json",
    ):
        if required_dynamic not in ids:
            raise V06PkpdTranslationBenchmarkError(
                f"benchmark discovery missed {required_dynamic}"
            )

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

    corrected_replay = _replay_proposal(ids, effect_column="effect")
    corrected_empirical = _empirical_proposal(
        ids,
        validator_fingerprint=validator_fingerprint,
    )
    response = _repair_response(
        initial,
        [corrected_replay, corrected_empirical],
    )
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
        "search_exposed_replay_and_validator_repairs": (
            initial.get("status") == "AWAITING_REPAIR"
            and initial.get("summary", {}).get("repairable_tasks") == 2
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
        "empirical_policy_result_bound_to_signed_external_validator": (
            empirical.get("selected") is True
            and empirical.get("formalizable") is False
            and empirical.get("status") == "COMPILED_EXTERNAL_VALIDATOR_BOUND"
            and isinstance(empirical.get("validation_target"), Mapping)
            and empirical["validation_target"].get("reported_outcome") == "PASS"
            and empirical["validation_target"].get("semantic_authority")
            == "EXTERNAL_VALIDATOR_TRUST_REQUIRED"
            and any(
                isinstance(obligation, Mapping)
                and obligation.get("kind")
                == "EXTERNAL_VALIDATOR_TRUST_REVIEW_REQUIRED"
                and obligation.get("blocking") is False
                for obligation in empirical.get("obligations", [])
            )
        ),
        "peak_threshold_promoted_to_certified_lean_checker": (
            peak.get("selected") is True
            and peak.get("formalizable") is True
            and peak.get("status") == "COMPILED_LEAN_BUILTIN"
            and isinstance(peak.get("formal_target"), Mapping)
            and peak["formal_target"].get("soundness_theorem")
            == "PCS.V2.PKPDCheck.pkpdPeakRun_sound"
            and peak["typed_claim"].get("predicate", {}).get("upper_bound")
            == "12"
        ),
        "search_closed_all_machine_blockers": (
            final.get("status") == "READY_FOR_HUMAN_CONFIRMATION"
            and final.get("summary", {}).get("repairable_tasks") == 0
            and final.get("summary", {}).get("blocking_open_obligations") == 0
            and final.get("summary", {}).get("compiled_selected") == 4
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
                "claims, bind one empirical policy result to a signed external "
                "validator receipt, and demonstrate promotion of the previously "
                "unsupported peak-table threshold into the certified Lean checker set."
            ),
            "synthetic_only": True,
            "clinical_claims_permitted": False,
            "ambiguous_tables": ["predictions.csv", "observations.csv"],
            "external_validator": {
                "validator": PKPD_RMSE_VALIDATOR_ID_V06,
                "public_key_fingerprint": validator_fingerprint,
                "receipt_format": EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06,
                "trust_model": EXTERNAL_VALIDATOR_TRUST_MODEL_V06,
                "reference_validation_result": validation_result,
                "semantic_authority": "EXTERNAL_VALIDATOR_TRUST_REQUIRED",
            },
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
                {
                    "candidate_id": "MODEL_PEAK_THRESHOLD",
                    "claim": (
                        "maximum reported concentration in the committed prediction "
                        "table is at most 12 mg/L"
                    ),
                    "proof_level": peak.get(
                        "formal_target", {}
                    ).get("proof_level"),
                    "soundness_theorem": peak.get(
                        "formal_target", {}
                    ).get("soundness_theorem"),
                },
            ],
            "externally_validated_under_trust_contract": [
                {
                    "candidate_id": "MODEL_EMPIRICAL_ADEQUACY",
                    "claim": (
                        "restricted model satisfies the prespecified synthetic "
                        "RMSE policy on the bound observations"
                    ),
                    "status": empirical.get("status"),
                    "reported_outcome": empirical.get(
                        "validation_target", {}
                    ).get("reported_outcome"),
                    "semantic_authority": empirical.get(
                        "validation_target", {}
                    ).get("semantic_authority"),
                    "validator": empirical.get(
                        "validation_target", {}
                    ).get("validator"),
                    "validator_public_key_fingerprint": empirical.get(
                        "validation_target", {}
                    ).get("validator_public_key_fingerprint"),
                }
            ],
            "certified_checker_missing": [],
            "not_established": [
                "validator methodology correctness beyond the signed receipt",
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
