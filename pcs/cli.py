from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Mapping

from .jsonio import strict_json_load, StrictJSONError

from .kernel import build_certificate, verify_certificate, AssuranceError
from .hashing import sha256_file
from .impact import impact_from_artifacts
from .report import write_html
from .signing import generate_keypair, sign_certificate, verify_signature, SignatureError
from .bundle import create_reproducible_bundle, BundleSafetyError
from .bundle_verify import verify_bundle, BundleVerificationError
from .diffing import diff_certificates
from .scaffold import init_project, ScaffoldError
from .doctor import doctor
from .attest import attest, AttestationError
from .policy import load_policy, evaluate_policy_file, PolicyError
from .package import build_package_manifest, PackageError
from .environment import write_environment, diff_environment_files
from .intake import freeze_intake_file, PilotIntakeError
from .verifier_io_v06 import (
    V06VerifierIOError,
    verify_package_directory_end_to_end_v06,
    write_verification_receipt_v06,
)
from .verifier_zip_v06 import (
    V06BundleVerificationError,
    verify_package_zip_end_to_end_v06,
)
from .bundle_v06 import (
    V06BundleBuildError,
    create_verified_bundle_v06,
)
from .attest_v06 import V06AttestationError, attest_v06
from .policy_v06 import V06ReviewerPolicyError
from .benchmark_v06 import (
    V06BenchmarkError,
    run_benchmark_registry_v06,
    write_benchmark_report_v06,
)
from .receipt_signature_v06 import (
    V06ReceiptSignatureError,
    sign_verification_receipt_v06,
    verify_verification_receipt_signature_v06,
)
from .receipt_contract_v06 import audit_verification_receipt_file_v06
from .quorum_v06 import (
    V06ReviewQuorumError,
    verify_review_quorum_v06,
    write_review_quorum_result_v06,
)
from .scheduler_v06 import (
    SCHEDULER_STRATEGIES_V06,
    V06SchedulerError,
    append_telemetry_history_v06,
    load_telemetry_history_v06,
    scheduler_report_v06,
    write_scheduler_report_v06,
    write_telemetry_v06,
)
from .discover_v06 import (
    V06DiscoveryError,
    confirm_manifest_draft_v06,
    discover_project_v06,
    write_discovery_outputs_v06,
)
from .proof_translation_v06 import (
    V06ProofTranslationError,
    translate_project_v06,
    write_proof_translation_outputs_v06,
)
from .proof_repair_v06 import (
    V06ProofRepairError,
    build_proof_repair_request_v06,
    compile_proof_repair_response_v06,
    load_proof_repair_inputs_v06,
    write_compiled_repair_proposals_v06,
    write_proof_repair_request_v06,
)
from .proof_search_v06 import (
    V06ProofSearchError,
    advance_proof_search_v06,
    load_proof_search_repair_response_v06,
    load_proof_search_session_v06,
    start_proof_search_v06,
    write_current_repair_request_v06,
    write_proof_search_session_v06,
    write_proof_search_trajectory_v06,
)
from .decomposition_proposer_v06 import (
    V06DecompositionProposerError,
    build_decomposition_proposer_request_v06,
    compile_decomposition_proposer_response_v06,
    load_decomposition_proposer_request_v06,
    load_decomposition_proposer_response_v06,
    write_decomposition_proposer_request_v06,
    write_decomposition_repair_response_v06,
)
from .discovery_review_v06 import (
    V06DiscoveryReviewError,
    write_discovery_review_v06,
)
from .environment_v06 import (
    V06EnvironmentCaptureError,
    environment_replay_plan_v06,
    write_environment_replay_plan_v06,
    write_environment_replay_script_v06,
)
from .environment_replay_v06 import (
    V06EnvironmentReplayError,
    environment_from_binding_v06,
)
from .environment_workspace_v06 import (
    V06EnvironmentWorkspaceError,
    prepare_verified_environment_workspace_v06,
)
from .environment_execute_v06 import (
    V06SandboxReplayError,
    execute_prepared_replay_workspace_v06,
)
from .local_verify_v06 import (
    V06LocalVerifyError,
    verify_local_bundle_v06,
)
from .lean_authority_v06 import V06LeanAuthorityError


def cmd_certify(args):
    try:
        out = Path(args.output).resolve()
        if out.exists() and any(out.iterdir()):
            raise AssuranceError(
                f"certification output directory must be empty to prevent stale evidence contamination: {out}"
            )
        cert = build_certificate(args.manifest, out)
    except (AssuranceError, OSError, json.JSONDecodeError) as e:
        print(f"REJECT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(f"WROTE {Path(args.output) / 'certificate.json'}")
    print(f"SEMANTIC_HASH {cert.get('semantic_hash')}")
    for c in cert["claims"]:
        print(f"{c['id']}: {c['assessment']['status']}")
    return 0


def cmd_verify(args):
    try:
        result = verify_certificate(args.certificate)
    except (AssuranceError, OSError, json.JSONDecodeError) as e:
        print(f"REJECT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1



def _scheduler_context_from_args(args):
    history = load_telemetry_history_v06(
        getattr(args, "scheduler_history", None)
    )
    telemetry_sink = {}
    return {
        "scheduler_strategy": getattr(args, "scheduler", "manifest"),
        "scheduler_history": history,
        "bandit_alpha": getattr(args, "bandit_alpha", 1.0),
        "shadow_bandit": getattr(args, "shadow_bandit", False),
        "telemetry_sink": telemetry_sink,
    }, telemetry_sink


def _persist_scheduler_telemetry_from_args(args, telemetry):
    written = None
    appended = None
    if not telemetry:
        return written, appended
    output = getattr(args, "scheduler_telemetry_out", None)
    if output:
        written = write_telemetry_v06(
            telemetry,
            output,
            overwrite=getattr(args, "force_scheduler_telemetry", False),
        )
    append_path = getattr(args, "scheduler_telemetry_append", None)
    if append_path:
        appended = append_telemetry_history_v06(
            telemetry,
            append_path,
        )
    return written, appended


def _sign_reviewer_receipt_from_args(args, receipt_path):
    reviewer_private_key = getattr(args, "reviewer_private_key", None)
    if not reviewer_private_key:
        return None
    if receipt_path is None:
        raise V06ReceiptSignatureError(
            "--reviewer-private-key requires --receipt so exact receipt bytes can be signed"
        )
    signature_output = getattr(args, "receipt_signature", None)
    if not signature_output:
        signature_output = str(receipt_path) + ".sig.json"
    sign_verification_receipt_v06(
        receipt_path,
        reviewer_private_key,
        signature_output,
        overwrite=getattr(args, "force_receipt_signature", False),
    )
    return Path(signature_output).resolve()


def cmd_verify_v06(args):
    try:
        scheduler_kwargs, telemetry_sink = _scheduler_context_from_args(args)
        result = verify_package_directory_end_to_end_v06(
            args.package,
            args.public_key,
            expected_fingerprint=args.expected_signer_fingerprint,
            policy_path=args.policy,
            lean_authority_path=args.lean_authority,
            **scheduler_kwargs,
        )
        telemetry_path, telemetry_history_path = _persist_scheduler_telemetry_from_args(
            args,
            telemetry_sink,
        )
        receipt_path = None
        receipt_signature_path = None
        if args.receipt:
            receipt_path = write_verification_receipt_v06(
                result,
                args.receipt,
                overwrite=args.force_receipt,
            )
        receipt_signature_path = _sign_reviewer_receipt_from_args(
            args,
            receipt_path,
        )
    except (
        OSError,
        V06VerifierIOError,
        V06ReviewerPolicyError,
        V06ReceiptSignatureError,
        V06SchedulerError,
        V06LeanAuthorityError,
    ) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    output = dict(result)
    if receipt_path is not None:
        output["receipt_written"] = str(receipt_path)
    if receipt_signature_path is not None:
        output["receipt_signature_written"] = str(receipt_signature_path)
    if telemetry_path is not None:
        output["scheduler_telemetry_written"] = str(telemetry_path)
    if telemetry_history_path is not None:
        output["scheduler_history_appended"] = str(telemetry_history_path)
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("accepted", result["valid"]) else 1


def cmd_verify_v06_bundle(args):
    try:
        scheduler_kwargs, telemetry_sink = _scheduler_context_from_args(args)
        result = verify_package_zip_end_to_end_v06(
            args.bundle,
            args.public_key,
            expected_fingerprint=args.expected_signer_fingerprint,
            policy_path=args.policy,
            lean_authority_path=args.lean_authority,
            **scheduler_kwargs,
        )
        telemetry_path, telemetry_history_path = _persist_scheduler_telemetry_from_args(
            args,
            telemetry_sink,
        )
        receipt_path = None
        receipt_signature_path = None
        if args.receipt:
            receipt_path = write_verification_receipt_v06(
                result,
                args.receipt,
                overwrite=args.force_receipt,
            )
        receipt_signature_path = _sign_reviewer_receipt_from_args(
            args,
            receipt_path,
        )
    except (
        OSError,
        V06VerifierIOError,
        V06BundleVerificationError,
        V06ReviewerPolicyError,
        V06ReceiptSignatureError,
        V06SchedulerError,
        V06LeanAuthorityError,
    ) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    output = dict(result)
    if receipt_path is not None:
        output["receipt_written"] = str(receipt_path)
    if receipt_signature_path is not None:
        output["receipt_signature_written"] = str(receipt_signature_path)
    if telemetry_path is not None:
        output["scheduler_telemetry_written"] = str(telemetry_path)
    if telemetry_history_path is not None:
        output["scheduler_history_appended"] = str(telemetry_history_path)
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("accepted", result["valid"]) else 1


def cmd_verify_local_v06(args):
    try:
        result = verify_local_bundle_v06(
            args.bundle,
            args.trust,
            receipt=args.receipt,
            overwrite_receipt=args.force_receipt,
            lean_authority_path=args.lean_authority,
        )
    except (OSError, StrictJSONError, V06LocalVerifyError, V06BundleVerificationError, V06ReviewerPolicyError, V06LeanAuthorityError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("accepted", result["valid"]) else 1


def cmd_audit_receipt_v06(args):
    result = audit_verification_receipt_file_v06(
        args.receipt,
        bundle_path=args.bundle,
        producer_public_key_path=args.producer_public_key,
        authority_path=args.lean_authority,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["valid"] else 1


def cmd_verify_receipt_v06(args):
    result = verify_verification_receipt_signature_v06(
        args.receipt,
        args.signature,
        args.reviewer_public_key,
        expected_reviewer_fingerprint=args.expected_reviewer_fingerprint,
        bundle_path=args.bundle,
        producer_public_key_path=args.producer_public_key,
        authority_path=args.lean_authority,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["valid"] else 1



def cmd_verify_quorum_v06(args):
    try:
        result = verify_review_quorum_v06(
            args.quorum_policy,
            args.review_set,
        )
        if args.output:
            written = write_review_quorum_result_v06(
                result,
                args.output,
                overwrite=args.force,
            )
            result = dict(result)
            result["result_written"] = str(written)
    except (OSError, V06ReviewQuorumError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["pass"] else 1


def cmd_bundle_v06(args):
    try:
        result = create_verified_bundle_v06(
            args.package,
            args.output,
            args.public_key,
            expected_fingerprint=args.expected_signer_fingerprint,
            overwrite=args.force,
            lean_authority_path=args.lean_authority,
        )
    except (OSError, V06BundleBuildError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_attest_v06(args):
    try:
        result = attest_v06(
            args.manifest,
            args.output,
            args.private_key,
            args.public_key,
            expected_fingerprint=args.expected_signer_fingerprint,
            overwrite=args.force,
            lean_authority_path=args.lean_authority,
        )
    except (OSError, V06AttestationError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_translate_project_v06(args):
    try:
        root = Path(args.project).resolve()
        plan_output = (
            Path(args.output).resolve()
            if args.output
            else root / "pcs-proof-translation.json"
        )
        manifest_output = (
            Path(args.manifest_draft).resolve()
            if args.manifest_draft
            else root / "pcs-manifest.draft.json"
        )
        result = translate_project_v06(
            root,
            subject=args.subject,
            proposal_files=args.proposals,
            control_paths=[plan_output, manifest_output],
            minimum_confidence=args.minimum_confidence,
            minimum_model_confidence=args.minimum_model_confidence,
            minimum_workflow_confidence=args.minimum_workflow_confidence,
        )
        written = write_proof_translation_outputs_v06(
            result,
            plan_output=plan_output,
            manifest_output=manifest_output,
            overwrite=args.force,
        )
        project_root_flag = (
            f" --project-root {root}"
            if manifest_output.parent != root
            else ""
        )
        response = {
            "format": result["format"],
            "project": str(root),
            "plan_sha256": result["plan_sha256"],
            "claim_ir_sha256": result["claim_ir"]["claim_ir_sha256"],
            "claim_ir_summary": result["claim_ir"]["summary"],
            "obligation_graph_sha256": result["obligation_graph"]["graph_sha256"],
            "obligation_graph_summary": result["obligation_graph"]["summary"],
            "summary": result["summary"],
            "blocking_obligations": [
                obligation
                for obligation in result["obligations"]
                if obligation.get("blocking") is True
            ],
            **written,
            "next": (
                f"Review {written['proof_translation_plan']} and "
                f"{written['manifest_draft']}, then run "
                f"pcs confirm-v06 {written['manifest_draft']}"
                f"{project_root_flag} -o {root / 'manifest.json'}"
            ),
        }
    except (OSError, V06ProofTranslationError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(response, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_prepare_proof_repairs_v06(args):
    try:
        translation, _, _ = load_proof_repair_inputs_v06(args.translation)
        request = build_proof_repair_request_v06(translation)
        output = write_proof_repair_request_v06(
            request,
            args.output,
            overwrite=args.force,
        )
        response = {
            "format": request["format"],
            "translation_plan_sha256": request["translation_plan_sha256"],
            "claim_ir_sha256": request["claim_ir_sha256"],
            "obligation_graph_sha256": request["obligation_graph_sha256"],
            "repair_request_sha256": request["repair_request_sha256"],
            "summary": request["summary"],
            "proof_repair_request": output,
            "next": (
                "Give the repair request to an external proposer that returns "
                "pcs-proof-repair-proposals-v1, then compile that response with "
                "pcs compile-repairs-v06."
            ),
        }
    except (OSError, V06ProofRepairError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(response, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_compile_proof_repairs_v06(args):
    try:
        translation, request, repair_response = load_proof_repair_inputs_v06(
            args.translation,
            args.request,
            args.response,
        )
        if request is None or repair_response is None:
            raise V06ProofRepairError(
                "compile-repairs-v06 requires translation, request, and response inputs"
            )
        compiled = compile_proof_repair_response_v06(
            translation,
            request,
            repair_response,
        )
        output = write_compiled_repair_proposals_v06(
            compiled,
            args.output,
            overwrite=args.force,
        )
        has_decomposition = any(
            isinstance(item, Mapping) and item.get("mode") == "decompose"
            for item in compiled.get("repair_provenance", {}).get(
                "repairs", []
            )
        )
        response = {
            "format": compiled["format"],
            "compiled_repair_sha256": compiled["compiled_repair_sha256"],
            "proposal_count": len(compiled["proposals"]),
            "compiled_proposals": output,
            "contains_decomposition_additions": has_decomposition,
            "next": (
                (
                    "Apply this response with continue-proof-search-v06, or merge "
                    "the emitted child proposals with the original parent proposal "
                    "documents before retranslation. Do not translate the child-only "
                    "file by itself."
                )
                if has_decomposition
                else (
                    "Rerun pcs translate-project-v06 on the unchanged project with "
                    f"--proposals {output}. The repaired proposal must pass grounding, "
                    "predicate compilation, confidence gating, human confirmation, replay, "
                    "and Lean authority exactly like any other untrusted proposal."
                )
            ),
        }
    except (OSError, V06ProofRepairError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(response, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_start_proof_search_v06(args):
    try:
        root = Path(args.project).resolve()
        session_output = Path(args.output).resolve()
        request_output = (
            Path(args.repair_request).resolve()
            if args.repair_request
            else session_output.with_name(session_output.stem + ".request.json")
        )
        if request_output == session_output:
            raise V06ProofSearchError(
                "proof search session and repair request must use different paths"
            )
        session = start_proof_search_v06(
            root,
            proposal_files=args.proposals,
            subject=args.subject,
            max_iterations=args.max_iterations,
            minimum_confidence=args.minimum_confidence,
            minimum_model_confidence=args.minimum_model_confidence,
            minimum_workflow_confidence=args.minimum_workflow_confidence,
        )
        session_path = write_proof_search_session_v06(
            session,
            session_output,
            overwrite=args.force,
        )
        request_path = write_current_repair_request_v06(
            session,
            request_output,
            overwrite=args.force,
        )
        response = {
            "format": session["format"],
            "search_id": session["search_id"],
            "status": session["status"],
            "iteration": session["iteration"],
            "max_iterations": session["max_iterations"],
            "summary": session["summary"],
            "session_sha256": session["session_sha256"],
            "proof_search_session": session_path,
            "proof_repair_request": request_path,
            "next": (
                "Give the repair request to an external proposer and then run "
                "pcs advance-proof-search-v06 with the returned repair response."
                if session["status"] == "AWAITING_REPAIR"
                else "The search has no machine-repair step to run in its current state."
            ),
        }
    except (OSError, V06ProofSearchError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(response, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_advance_proof_search_v06(args):
    try:
        root = Path(args.project).resolve()
        session = load_proof_search_session_v06(args.session)
        repair_response = load_proof_search_repair_response_v06(args.response)
        updated = advance_proof_search_v06(
            root,
            session,
            repair_response,
            state_dir=args.state_dir,
        )
        session_path = write_proof_search_session_v06(
            updated,
            args.output,
            overwrite=args.force,
        )

        request_path = None
        if args.repair_request:
            request_path = write_current_repair_request_v06(
                updated,
                args.repair_request,
                overwrite=args.force,
            )

        trajectory_path = None
        if args.trajectory:
            trajectory_path = write_proof_search_trajectory_v06(
                updated,
                args.trajectory,
                overwrite=args.force,
            )

        response = {
            "format": updated["format"],
            "search_id": updated["search_id"],
            "status": updated["status"],
            "iteration": updated["iteration"],
            "max_iterations": updated["max_iterations"],
            "summary": updated["summary"],
            "session_sha256": updated["session_sha256"],
            "trajectory_sha256": updated["trajectory"]["trajectory_sha256"],
            "proof_search_session": session_path,
            "proof_repair_request": request_path,
            "proof_search_trajectory": trajectory_path,
            "next": (
                "Submit another graph-bound repair response."
                if updated["status"] == "AWAITING_REPAIR"
                else (
                    "Search reached a theorem-backed translation; human confirmation, "
                    "replay, and Lean authority are still required."
                    if updated["status"] == "READY_FOR_HUMAN_CONFIRMATION"
                    else f"Search stopped with status {updated['status']}."
                )
            ),
        }
    except (OSError, V06ProofSearchError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(response, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_prepare_decomposition_v06(args):
    try:
        root = Path(args.project).resolve()
        session = load_proof_search_session_v06(args.session)
        request = build_decomposition_proposer_request_v06(
            root,
            session,
            proposal_id=args.proposal,
        )
        output = write_decomposition_proposer_request_v06(
            request,
            args.output,
            overwrite=args.force,
        )
        response = {
            "format": request["format"],
            "protocol": request["protocol"],
            "search_id": request["search_id"],
            "proposal_id": request["target"]["proposal_id"],
            "claim_id": request["target"]["claim"]["id"],
            "decomposition_request_sha256": request[
                "decomposition_request_sha256"
            ],
            "bounds": request["bounds"],
            "decomposition_request": output,
            "next": (
                "Give this metadata-only, graph-bound request to an external "
                "proposer. It must return pcs-decomposition-proposer-response-v1 "
                "with decision 'decompose' or 'abstain', then run "
                "pcs compile-decomposition-v06."
            ),
        }
    except (
        OSError,
        V06ProofSearchError,
        V06DecompositionProposerError,
    ) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(response, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_compile_decomposition_v06(args):
    try:
        root = Path(args.project).resolve()
        session = load_proof_search_session_v06(args.session)
        request = load_decomposition_proposer_request_v06(args.request)
        proposer_response = load_decomposition_proposer_response_v06(
            args.response
        )
        compilation = compile_decomposition_proposer_response_v06(
            root,
            session,
            request,
            proposer_response,
        )

        repair_output = None
        if compilation["status"] == "COMPILED_REPAIR_RESPONSE":
            output = (
                Path(args.output).resolve()
                if args.output
                else Path(args.response).resolve().with_name(
                    Path(args.response).stem + ".repair.json"
                )
            )
            repair_output = write_decomposition_repair_response_v06(
                compilation,
                output,
                overwrite=args.force,
            )

        response = {
            "format": compilation["format"],
            "protocol": compilation["protocol"],
            "status": compilation["status"],
            "search_id": compilation["search_id"],
            "decomposition_request_sha256": compilation[
                "decomposition_request_sha256"
            ],
            "decomposition_response_sha256": compilation[
                "decomposition_response_sha256"
            ],
            "repair_response": repair_output,
            "authority": compilation["authority"],
            "next": (
                (
                    f"Run pcs advance-proof-search-v06 {root} "
                    f"{Path(args.session).resolve()} {repair_output} "
                    "with a new output session path. PCS will deterministically "
                    "retranslate every introduced child."
                )
                if repair_output is not None
                else (
                    "The proposer abstained. No PCS search state changed; route "
                    "the unresolved claim to a human or another untrusted proposer."
                )
            ),
        }
    except (
        OSError,
        V06ProofSearchError,
        V06DecompositionProposerError,
    ) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(response, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_discover_v06(args):
    try:
        root = Path(args.project).resolve()
        manifest_output = (
            Path(args.output).resolve()
            if args.output
            else root / "pcs-manifest.draft.json"
        )
        report_output = (
            Path(args.report).resolve()
            if args.report
            else root / "pcs-discovery.json"
        )
        review_output = (
            Path(args.review).resolve()
            if args.review
            else root / "pcs-discovery-review.md"
        )
        environment_plan_output = (
            Path(args.environment_plan).resolve()
            if args.environment_plan
            else root / "pcs-environment-plan.json"
        )
        result = discover_project_v06(
            root,
            subject=args.subject,
            minimum_confidence=args.minimum_confidence,
            minimum_workflow_confidence=args.minimum_workflow_confidence,
        )
        written = write_discovery_outputs_v06(
            result,
            manifest_output=manifest_output,
            report_output=report_output,
            overwrite=args.force,
        )
        review_path = write_discovery_review_v06(
            result,
            review_output,
            overwrite=args.force,
        )
        written["discovery_review"] = str(review_path)
        environment_plan_path = write_environment_replay_plan_v06(
            result["environment_capture"],
            environment_plan_output,
            overwrite=args.force,
        )
        written["environment_plan"] = str(environment_plan_path)
        draft_path = Path(written["manifest_draft"]).resolve()
        project_root_flag = (
            f" --project-root {root}"
            if draft_path.parent != root
            else ""
        )
        response = {
            "format": result["format"],
            "project": str(root),
            "summary": result["summary"],
            "unresolved": result["unresolved"],
            **written,
            "next": (
                f"Review {written['manifest_draft']}, then run "
                f"pcs confirm-v06 {written['manifest_draft']}"
                f"{project_root_flag} -o {root / 'manifest.json'}"
            ),
        }
    except (
        OSError,
        V06DiscoveryError,
        V06DiscoveryReviewError,
        V06EnvironmentCaptureError,
    ) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(response, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def _environment_from_document_v06(path: str | Path) -> dict:
    value = strict_json_load(path)
    if not isinstance(value, dict):
        raise V06EnvironmentCaptureError("environment input root must be an object")
    if isinstance(value.get("environment_capture"), dict):
        return value["environment_capture"]
    environment = value.get("environment")
    if isinstance(environment, dict):
        if environment.get("format") == "pcs-environment-capture-v1":
            return environment
        if environment.get("format") == "pcs-environment-binding-v1":
            try:
                return environment_from_binding_v06(environment)
            except V06EnvironmentReplayError as exc:
                raise V06EnvironmentCaptureError(str(exc)) from exc
    if value.get("format") == "pcs-environment-capture-v1":
        return value
    raise V06EnvironmentCaptureError(
        "input does not contain a PCS v0.6 environment capture or binding"
    )


def cmd_prepare_environment_v06(args):
    try:
        result = prepare_verified_environment_workspace_v06(
            args.bundle,
            args.output,
            args.public_key,
            expected_fingerprint=args.expected_signer_fingerprint,
        )
    except (OSError, V06EnvironmentWorkspaceError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_execute_environment_v06(args):
    try:
        result = execute_prepared_replay_workspace_v06(
            args.workspace,
            args.output,
            args.public_key,
            expected_fingerprint=args.expected_signer_fingerprint,
            runtime=args.runtime,
            image=args.image,
            timeout_seconds=args.timeout_seconds,
            memory=args.memory,
            cpus=args.cpus,
            determinism_runs=args.runs,
        )
    except (OSError, ValueError, V06VerifierIOError, V06SandboxReplayError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["valid"] else 1


def cmd_environment_plan_v06(args):
    try:
        environment = _environment_from_document_v06(args.input)
        plan = environment_replay_plan_v06(environment)
        result = {
            "format": plan["format"],
            "hermeticity": plan["hermeticity"],
            "required_tools": plan["required_tools"],
            "steps": plan["steps"],
            "automatic_execution_permitted_by_pcs": plan[
                "automatic_execution_permitted_by_pcs"
            ],
            "reason": plan["reason"],
        }
        if args.output:
            path = write_environment_replay_plan_v06(
                environment,
                args.output,
                overwrite=args.force,
            )
            result["plan_written"] = str(path)
        if args.script:
            script = write_environment_replay_script_v06(
                environment,
                args.script,
                overwrite=args.force,
            )
            result["review_before_run_script_written"] = str(script)
    except (
        OSError,
        StrictJSONError,
        V06EnvironmentCaptureError,
    ) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_confirm_v06(args):
    try:
        draft = Path(args.draft).resolve()
        root = (
            Path(args.project_root).resolve()
            if args.project_root
            else draft.parent
        )
        output = (
            Path(args.output).resolve()
            if args.output
            else root / "manifest.json"
        )
        result = confirm_manifest_draft_v06(
            draft,
            output,
            project_root=root,
            overwrite=args.force,
            allow_empty=args.allow_empty,
        )
        result["next"] = (
            f"pcs attest-v06 {result['manifest']} -o study.pcs.zip "
            "--private-key <private.pem> --public-key <public.pem>"
        )
    except (OSError, V06DiscoveryError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_benchmark_v06(args):
    try:
        report = run_benchmark_registry_v06(args.registry)
        if args.output:
            out = write_benchmark_report_v06(
                report,
                args.output,
                overwrite=args.force,
            )
            report = dict(report)
            report["report_written"] = str(out)
    except (OSError, V06BenchmarkError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["summary"]["unexpected"] == 0 else 1


def cmd_scheduler_report_v06(args):
    try:
        history = load_telemetry_history_v06(args.history)
        report = scheduler_report_v06(
            history,
            bandit_alpha=args.bandit_alpha,
        )
        if args.output:
            written = write_scheduler_report_v06(
                report,
                args.output,
                overwrite=args.force,
            )
            report = dict(report)
            report["report_written"] = str(written)
    except (OSError, V06SchedulerError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_inspect(args):
    cert = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
    print(f"Subject: {cert.get('subject')}")
    print(f"Semantic: {cert.get('semantic_hash')}")
    print(f"Integrity: {cert.get('integrity_hash')}")
    print("Claims:")
    for c in cert.get("claims", []):
        a = c.get("assessment", {})
        assumptions = ",".join(c.get("assumptions", [])) or "none"
        print(f"  {c.get('id')}: {a.get('status')} | assumptions={assumptions} | {c.get('statement')}")
    return 0


def cmd_hash(args):
    print(sha256_file(args.file))
    return 0


def cmd_impact(args):
    cert = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
    result = impact_from_artifacts(cert, set(args.artifact))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_report(args):
    cert = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
    out = write_html(cert, args.output)
    print(f"WROTE {out}")
    return 0


def cmd_gate(args):
    cert = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
    statuses = {c.get("id"): c.get("assessment", {}).get("status") for c in cert.get("claims", [])}
    acceptable = set(args.accept or ["COMPUTATIONALLY_SUPPORTED", "FORMALLY_VERIFIED_UNDER_ASSUMPTIONS", "EMPIRICALLY_VALIDATED_WITHIN_SCOPE", "MIXED_SUPPORT_UNDER_ASSUMPTIONS"])
    required = args.claim or sorted(statuses)
    failures = {cid: statuses.get(cid, "MISSING") for cid in required if statuses.get(cid) not in acceptable}
    print(json.dumps({"pass": not failures, "required": required, "acceptable_statuses": sorted(acceptable), "failures": failures}, indent=2, sort_keys=True))
    return 0 if not failures else 1


def cmd_keygen(args):
    try:
        result = generate_keypair(args.private_key, args.public_key, overwrite=args.force)
    except (OSError, SignatureError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_sign(args):
    try:
        integrity = verify_certificate(args.certificate)
        if not integrity["valid"]:
            print(json.dumps(integrity, indent=2, sort_keys=True), file=sys.stderr)
            print("REJECT: refusing to sign an invalid certificate", file=sys.stderr)
            return 2
        record = sign_certificate(args.certificate, args.private_key, args.output)
    except (OSError, json.JSONDecodeError, SignatureError, AssuranceError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps({"wrote": str(args.output), "public_key_fingerprint": record["public_key_fingerprint"]}, indent=2, sort_keys=True))
    return 0


def cmd_verify_signature(args):
    try:
        integrity = verify_certificate(args.certificate)
        sig = verify_signature(args.certificate, args.signature, args.public_key)
        result = {"valid": bool(integrity["valid"] and sig["valid"]), "certificate_integrity": integrity, "signature": sig}
    except (OSError, json.JSONDecodeError, SignatureError, AssuranceError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


def cmd_bundle(args):
    try:
        integrity = verify_certificate(args.certificate)
        if not integrity["valid"]:
            print(json.dumps(integrity, indent=2, sort_keys=True), file=sys.stderr)
            print("REJECT: refusing to bundle an invalid certificate", file=sys.stderr)
            return 2
        build_package_manifest(Path(args.certificate).resolve().parent)
        result = create_reproducible_bundle(args.certificate, args.output)
    except (OSError, json.JSONDecodeError, AssuranceError, PackageError, BundleSafetyError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_verify_bundle(args):
    try:
        result = verify_bundle(
            args.bundle,
            public_key=args.public_key,
            require_signature=args.require_signature,
            expected_signer_fingerprint=args.expected_signer_fingerprint,
            policy=args.policy,
        )
    except (OSError, json.JSONDecodeError, AssuranceError, SignatureError, BundleVerificationError, PolicyError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    receipt_path = getattr(args, "receipt", None)
    if receipt_path:
        receipt = dict(result)
        out = Path(receipt_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = dict(result)
        result["receipt_written"] = str(out.resolve())

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


def cmd_diff(args):
    try:
        result = diff_certificates(args.left, args.right)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_init(args):
    try:
        result = init_project(args.destination, template=args.template, subject=args.subject, force=args.force)
    except (OSError, ScaffoldError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_doctor(args):
    result = doctor()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["healthy"] else 1


def cmd_attest(args):
    try:
        result = attest(
            args.manifest,
            args.output,
            private_key=args.private_key,
            public_key=args.public_key,
            bundle_path=args.bundle,
            intake_lock=args.intake_lock,
        )
    except (OSError, json.JSONDecodeError, AssuranceError, SignatureError, AttestationError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_freeze_intake(args):
    try:
        result = freeze_intake_file(args.input, args.output, overwrite=args.force)
    except (OSError, json.JSONDecodeError, PilotIntakeError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps({
        "wrote": str(Path(args.output).resolve()),
        "pilot_id": result["intake"]["pilot_id"],
        "intake_semantic_hash": result["intake_semantic_hash"],
        "frozen_at": result["frozen_at"],
    }, indent=2, sort_keys=True))
    return 0


def cmd_snapshot_env(args):
    try:
        result = write_environment(args.output)
    except OSError as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps({"wrote": str(args.output), "semantic_hash": result["semantic_hash"], "packages": len(result["packages"])}, indent=2, sort_keys=True))
    return 0


def cmd_env_diff(args):
    try:
        result = diff_environment_files(args.left, args.right)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="pcs", description="Proof-Carrying Science reference CLI")
    sub = p.add_subparsers(required=True)

    c = sub.add_parser("certify", help="run manifest checks and emit self-contained evidence package")
    c.add_argument("manifest")
    c.add_argument("-o", "--output", required=True)
    c.set_defaults(func=cmd_certify)

    v = sub.add_parser("verify", help="independently verify an evidence certificate/package")
    v.add_argument("certificate")
    v.set_defaults(func=cmd_verify)

    tp6 = sub.add_parser(
        "translate-project-v06",
        help="analyze a project and compile supported findings into theorem-backed PCS claims",
    )
    tp6.add_argument("project", help="scientific project directory to analyze locally")
    tp6.add_argument(
        "-o",
        "--output",
        help="proof-translation plan JSON; defaults inside the project",
    )
    tp6.add_argument(
        "--manifest-draft",
        help="translated PCS manifest draft; defaults inside the project",
    )
    tp6.add_argument(
        "--proposals",
        action="append",
        default=[],
        help=(
            "optional pcs-proof-proposals-v1 JSON from an external model/proposer; "
            "repeatable and bound to the current project inventory commitment"
        ),
    )
    tp6.add_argument("--subject", help="override the discovered project subject")
    tp6.add_argument(
        "--minimum-confidence",
        type=float,
        default=0.95,
        help="minimum deterministic-discovery confidence selected into the draft",
    )
    tp6.add_argument(
        "--minimum-model-confidence",
        type=float,
        default=0.98,
        help="minimum external-model confidence selected into the draft",
    )
    tp6.add_argument(
        "--minimum-workflow-confidence",
        type=float,
        default=0.95,
        help="minimum confidence for static Python/notebook workflow nodes",
    )
    tp6.add_argument(
        "--force",
        action="store_true",
        help="explicitly replace existing translation outputs",
    )
    tp6.set_defaults(func=cmd_translate_project_v06)

    pr6 = sub.add_parser(
        "prepare-repairs-v06",
        help="derive machine-repairable proof obligations from a committed translation graph",
    )
    pr6.add_argument(
        "translation",
        help="pcs-proof-translation-v1 JSON produced by translate-project-v06",
    )
    pr6.add_argument(
        "-o",
        "--output",
        required=True,
        help="pcs-proof-repair-request-v1 JSON for an external proposer",
    )
    pr6.add_argument(
        "--force",
        action="store_true",
        help="explicitly replace an existing repair request",
    )
    pr6.set_defaults(func=cmd_prepare_proof_repairs_v06)

    cr6 = sub.add_parser(
        "compile-repairs-v06",
        help="validate graph-bound model repairs and emit ordinary untrusted PCS proposals",
    )
    cr6.add_argument("translation", help="original pcs-proof-translation-v1 JSON")
    cr6.add_argument("request", help="committed pcs-proof-repair-request-v1 JSON")
    cr6.add_argument("response", help="external pcs-proof-repair-proposals-v1 JSON")
    cr6.add_argument(
        "-o",
        "--output",
        required=True,
        help="compiled pcs-proof-proposals-v1 JSON to feed back into translation",
    )
    cr6.add_argument(
        "--force",
        action="store_true",
        help="explicitly replace existing compiled repair proposals",
    )
    cr6.set_defaults(func=cmd_compile_proof_repairs_v06)

    sps6 = sub.add_parser(
        "start-proof-search-v06",
        help="start a bounded graph-driven proof-repair search session",
    )
    sps6.add_argument("project", help="scientific project directory")
    sps6.add_argument(
        "--proposals",
        action="append",
        required=True,
        help="initial pcs-proof-proposals-v1 JSON; repeatable",
    )
    sps6.add_argument(
        "-o",
        "--output",
        required=True,
        help="write committed pcs-proof-repair-search-v1 session JSON",
    )
    sps6.add_argument(
        "--repair-request",
        help="write current repair request; defaults beside the session output",
    )
    sps6.add_argument("--subject", help="override discovered project subject")
    sps6.add_argument(
        "--max-iterations",
        type=int,
        default=4,
        help="hard repair-search budget; maximum 32",
    )
    sps6.add_argument("--minimum-confidence", type=float, default=0.95)
    sps6.add_argument("--minimum-model-confidence", type=float, default=0.98)
    sps6.add_argument("--minimum-workflow-confidence", type=float, default=0.95)
    sps6.add_argument("--force", action="store_true")
    sps6.set_defaults(func=cmd_start_proof_search_v06)

    aps6 = sub.add_parser(
        "advance-proof-search-v06",
        help="apply one graph-bound repair and deterministically recompile the search state",
    )
    aps6.add_argument("project", help="unchanged scientific project directory")
    aps6.add_argument("session", help="committed pcs-proof-repair-search-v1 JSON")
    aps6.add_argument("response", help="external pcs-proof-repair-proposals-v1 JSON")
    aps6.add_argument(
        "-o",
        "--output",
        required=True,
        help="write the next committed proof-search session",
    )
    aps6.add_argument(
        "--repair-request",
        help="optionally write the next repair request",
    )
    aps6.add_argument(
        "--trajectory",
        help="optionally write the committed repair trajectory separately",
    )
    aps6.add_argument(
        "--state-dir",
        help="proposal staging directory; defaults under PROJECT/.pcs/proof-search",
    )
    aps6.add_argument("--force", action="store_true")
    aps6.set_defaults(func=cmd_advance_proof_search_v06)

    pd6 = sub.add_parser(
        "prepare-decomposition-v06",
        help="build one metadata-only, graph-bound request for an unresolved Claim IR leaf",
    )
    pd6.add_argument("project", help="unchanged scientific project directory")
    pd6.add_argument("session", help="committed pcs-proof-repair-search-v1 JSON")
    pd6.add_argument(
        "-o",
        "--output",
        required=True,
        help="write pcs-decomposition-proposer-request-v1 JSON",
    )
    pd6.add_argument(
        "--proposal",
        help="target proposal id when multiple decompose_claim tasks are available",
    )
    pd6.add_argument("--force", action="store_true")
    pd6.set_defaults(func=cmd_prepare_decomposition_v06)

    cd6 = sub.add_parser(
        "compile-decomposition-v06",
        help="compile one external decomposition proposal into an ordinary PCS repair response",
    )
    cd6.add_argument("project", help="unchanged scientific project directory")
    cd6.add_argument("session", help="committed pcs-proof-repair-search-v1 JSON")
    cd6.add_argument("request", help="pcs-decomposition-proposer-request-v1 JSON")
    cd6.add_argument("response", help="pcs-decomposition-proposer-response-v1 JSON")
    cd6.add_argument(
        "-o",
        "--output",
        help="write standard pcs-proof-repair-proposals-v1 response; defaults beside response",
    )
    cd6.add_argument("--force", action="store_true")
    cd6.set_defaults(func=cmd_compile_decomposition_v06)

    d6 = sub.add_parser(
        "discover-v06",
        help="scan a scientific project and draft a reviewable PCS v0.6 manifest",
    )
    d6.add_argument("project", help="scientific project directory to inspect locally")
    d6.add_argument("-o", "--output", help="manifest draft path; defaults inside project")
    d6.add_argument("--report", help="discovery report path; defaults inside project")
    d6.add_argument(
        "--review",
        help="human-readable discovery review Markdown; defaults inside project",
    )
    d6.add_argument(
        "--environment-plan",
        help="environment replay-plan JSON; defaults inside project",
    )
    d6.add_argument("--subject", help="override the discovered project subject")
    d6.add_argument(
        "--minimum-confidence",
        type=float,
        default=0.95,
        help="minimum recommendation confidence auto-selected into the draft",
    )
    d6.add_argument(
        "--minimum-workflow-confidence",
        type=float,
        default=0.95,
        help="minimum confidence for static Python/notebook workflow nodes",
    )
    d6.add_argument(
        "--force",
        action="store_true",
        help="explicitly replace existing discovery outputs",
    )
    d6.set_defaults(func=cmd_discover_v06)

    pew6 = sub.add_parser(
        "prepare-environment-v06",
        help="verify a v0.6 bundle and materialize a non-executed replay workspace",
    )
    pew6.add_argument("bundle", help="verified-delivery candidate .pcs.zip")
    pew6.add_argument("-o", "--output", required=True, help="new replay workspace directory")
    pew6.add_argument("--public-key", required=True, help="trusted producer Ed25519 public key PEM")
    pew6.add_argument(
        "--expected-signer-fingerprint",
        help="pin the accepted producer public-key fingerprint",
    )
    pew6.set_defaults(func=cmd_prepare_environment_v06)

    sew6 = sub.add_parser(
        "execute-environment-v06",
        help="sandbox-execute a prepared replay workspace and capture realized environment/output state",
    )
    sew6.add_argument("workspace", help="workspace created by prepare-environment-v06")
    sew6.add_argument("-o", "--output", required=True, help="new realized replay result directory")
    sew6.add_argument("--public-key", required=True, help="trusted producer Ed25519 public key PEM")
    sew6.add_argument("--expected-signer-fingerprint", help="pin the accepted producer public-key fingerprint")
    sew6.add_argument("--runtime", choices=["auto", "docker", "podman"], default="auto")
    sew6.add_argument("--image", help="existing local OCI image; required when no signed digest-pinned container can be rebuilt offline")
    sew6.add_argument("--timeout-seconds", type=int, default=300)
    sew6.add_argument("--memory", default="2g")
    sew6.add_argument("--cpus", type=float, default=1.0)
    sew6.add_argument(
        "--runs",
        type=int,
        default=2,
        help=(
            "independent fresh replay runs used to test deterministic outputs "
            "and realized environment; must be 2-5"
        ),
    )
    sew6.set_defaults(func=cmd_execute_environment_v06)

    ep6 = sub.add_parser(
        "environment-plan-v06",
        help="inspect or materialize a v0.6 reproducibility-environment reconstruction plan",
    )
    ep6.add_argument(
        "input",
        help="pcs-discovery.json, manifest.json, certificate.json, or environment capture JSON",
    )
    ep6.add_argument("-o", "--output", help="write replay-plan JSON")
    ep6.add_argument(
        "--script",
        help="write a review-before-run shell script; PCS never executes it automatically",
    )
    ep6.add_argument(
        "--force",
        action="store_true",
        help="explicitly replace existing plan/script outputs",
    )
    ep6.set_defaults(func=cmd_environment_plan_v06)

    c6 = sub.add_parser(
        "confirm-v06",
        help="confirm a reviewed PCS discovery draft and freeze its artifact snapshot",
    )
    c6.add_argument("draft", help="pcs-manifest.draft.json generated by discover-v06")
    c6.add_argument("-o", "--output", help="confirmed manifest; defaults to project/manifest.json")
    c6.add_argument(
        "--project-root",
        help="project root when the draft is stored elsewhere",
    )
    c6.add_argument(
        "--allow-empty",
        action="store_true",
        help="explicitly confirm a draft with no supported claims/checks",
    )
    c6.add_argument(
        "--force",
        action="store_true",
        help="explicitly replace an existing confirmed manifest",
    )
    c6.set_defaults(func=cmd_confirm_v06)

    v6 = sub.add_parser(
        "verify-v06",
        help="end-to-end verify a PCS v0.6 package directory",
    )
    v6.add_argument("package", help="directory containing the delivered v0.6 package")
    v6.add_argument("--public-key", required=True, help="trusted Ed25519 public key PEM")
    v6.add_argument(
        "--expected-signer-fingerprint",
        help="pin the accepted Ed25519 raw-public-key SHA-256 fingerprint",
    )
    v6.add_argument(
        "--lean-authority",
        help="receiver-owned pcs-lean-authority executable; defaults to embedded/repository authority",
    )
    v6.add_argument(
        "--policy",
        help="external reviewer acceptance-policy JSON; does not change PCS validity",
    )
    v6.add_argument("--receipt", help="write deterministic JSON verification receipt")
    v6.add_argument(
        "--force-receipt",
        action="store_true",
        help="explicitly replace an existing receipt",
    )
    v6.add_argument(
        "--reviewer-private-key",
        help="Ed25519 private key used to sign the exact verification receipt bytes",
    )
    v6.add_argument(
        "--receipt-signature",
        help="reviewer signature output; default is <receipt>.sig.json",
    )
    v6.add_argument(
        "--force-receipt-signature",
        action="store_true",
        help="explicitly replace an existing reviewer receipt signature",
    )
    v6.add_argument(
        "--scheduler",
        choices=SCHEDULER_STRATEGIES_V06,
        default="manifest",
        help="mandatory-check execution order; never changes scientific semantics",
    )
    v6.add_argument(
        "--scheduler-history",
        help="prior replay telemetry JSONL used only for scheduling",
    )
    v6.add_argument(
        "--scheduler-telemetry-out",
        help="write this run's observational replay telemetry JSON",
    )
    v6.add_argument(
        "--scheduler-telemetry-append",
        help="append this run's telemetry as one JSONL history record",
    )
    v6.add_argument(
        "--force-scheduler-telemetry",
        action="store_true",
        help="explicitly replace an existing telemetry output file",
    )
    v6.add_argument(
        "--shadow-bandit",
        action="store_true",
        help="record contextual-bandit recommendation without using it for execution order",
    )
    v6.add_argument(
        "--bandit-alpha",
        type=float,
        default=1.0,
        help="nonnegative LinUCB exploration coefficient",
    )
    v6.set_defaults(func=cmd_verify_v06)

    v6b = sub.add_parser(
        "verify-v06-bundle",
        help="safely verify a PCS v0.6 ZIP bundle without extracting it",
    )
    v6b.add_argument("bundle", help="delivered PCS v0.6 ZIP archive")
    v6b.add_argument("--public-key", required=True, help="trusted Ed25519 public key PEM")
    v6b.add_argument(
        "--expected-signer-fingerprint",
        help="pin the accepted Ed25519 raw-public-key SHA-256 fingerprint",
    )
    v6b.add_argument(
        "--lean-authority",
        help="receiver-owned pcs-lean-authority executable; defaults to embedded/repository authority",
    )
    v6b.add_argument(
        "--policy",
        help="external reviewer acceptance-policy JSON; does not change PCS validity",
    )
    v6b.add_argument("--receipt", help="write deterministic JSON verification receipt")
    v6b.add_argument(
        "--force-receipt",
        action="store_true",
        help="explicitly replace an existing receipt",
    )
    v6b.add_argument(
        "--reviewer-private-key",
        help="Ed25519 private key used to sign the exact verification receipt bytes",
    )
    v6b.add_argument(
        "--receipt-signature",
        help="reviewer signature output; default is <receipt>.sig.json",
    )
    v6b.add_argument(
        "--force-receipt-signature",
        action="store_true",
        help="explicitly replace an existing reviewer receipt signature",
    )
    v6b.add_argument(
        "--scheduler",
        choices=SCHEDULER_STRATEGIES_V06,
        default="manifest",
        help="mandatory-check execution order; never changes scientific semantics",
    )
    v6b.add_argument(
        "--scheduler-history",
        help="prior replay telemetry JSONL used only for scheduling",
    )
    v6b.add_argument(
        "--scheduler-telemetry-out",
        help="write this run's observational replay telemetry JSON",
    )
    v6b.add_argument(
        "--scheduler-telemetry-append",
        help="append this run's telemetry as one JSONL history record",
    )
    v6b.add_argument(
        "--force-scheduler-telemetry",
        action="store_true",
        help="explicitly replace an existing telemetry output file",
    )
    v6b.add_argument(
        "--shadow-bandit",
        action="store_true",
        help="record contextual-bandit recommendation without using it for execution order",
    )
    v6b.add_argument(
        "--bandit-alpha",
        type=float,
        default=1.0,
        help="nonnegative LinUCB exploration coefficient",
    )
    v6b.set_defaults(func=cmd_verify_v06_bundle)

    vl6 = sub.add_parser(
        "verify-local-v06",
        help="one-command v0.6 bundle verification using a pinned trust-profile JSON",
    )
    vl6.add_argument("bundle", help="delivered PCS v0.6 ZIP archive")
    vl6.add_argument("--trust", required=True, help="pcs-verifier-trust-v1 JSON; paths are relative to the profile")
    vl6.add_argument(
        "--lean-authority",
        help="receiver-owned pcs-lean-authority executable; overrides trust-profile path",
    )
    vl6.add_argument("--receipt", help="write deterministic verification receipt JSON")
    vl6.add_argument("--force-receipt", action="store_true")
    vl6.set_defaults(func=cmd_verify_local_v06)

    ar6 = sub.add_parser(
        "audit-receipt-v06",
        help="audit internal v0.6 receipt invariants and optional external bindings",
    )
    ar6.add_argument("receipt", help="verification receipt JSON")
    ar6.add_argument(
        "--bundle",
        help="optional delivered bundle whose exact SHA-256 must match the receipt",
    )
    ar6.add_argument(
        "--producer-public-key",
        help="optional trusted producer Ed25519 public key whose fingerprint must match",
    )
    ar6.add_argument(
        "--lean-authority",
        help="optional pcs-lean-authority executable whose SHA-256 must match the receipt",
    )
    ar6.set_defaults(func=cmd_audit_receipt_v06)

    vr6 = sub.add_parser(
        "verify-receipt-v06",
        help="verify reviewer signature plus the semantic v0.6 receipt contract",
    )
    vr6.add_argument("receipt", help="verification receipt JSON")
    vr6.add_argument("--signature", required=True, help="reviewer receipt signature JSON")
    vr6.add_argument(
        "--reviewer-public-key",
        required=True,
        help="trusted reviewer Ed25519 public key PEM",
    )
    vr6.add_argument(
        "--expected-reviewer-fingerprint",
        help="pin the accepted reviewer public-key SHA-256 fingerprint",
    )
    vr6.add_argument(
        "--bundle",
        help="optional delivered bundle whose exact SHA-256 must match the receipt",
    )
    vr6.add_argument(
        "--producer-public-key",
        help="optional trusted producer Ed25519 public key whose fingerprint must match",
    )
    vr6.add_argument(
        "--lean-authority",
        help="optional pcs-lean-authority executable whose SHA-256 must match the receipt",
    )
    vr6.set_defaults(func=cmd_verify_receipt_v06)

    vq6 = sub.add_parser(
        "verify-quorum-v06",
        help="verify role-aware multi-reviewer quorum over signed v0.6 receipts",
    )
    vq6.add_argument("--quorum-policy", required=True, help="review quorum policy JSON")
    vq6.add_argument("--review-set", required=True, help="portable review-set JSON")
    vq6.add_argument("-o", "--output", help="write deterministic quorum result JSON")
    vq6.add_argument(
        "--force",
        action="store_true",
        help="explicitly replace an existing quorum result",
    )
    vq6.set_defaults(func=cmd_verify_quorum_v06)

    b6 = sub.add_parser(
        "bundle-v06",
        help="create a deterministic verified PCS v0.6 ZIP bundle",
    )
    b6.add_argument("package", help="complete PCS v0.6 package directory")
    b6.add_argument("-o", "--output", required=True, help="output ZIP path")
    b6.add_argument("--public-key", required=True, help="trusted Ed25519 public key PEM")
    b6.add_argument(
        "--expected-signer-fingerprint",
        help="pin the accepted Ed25519 raw-public-key SHA-256 fingerprint",
    )
    b6.add_argument(
        "--lean-authority",
        help="receiver/producer-owned pcs-lean-authority executable; defaults to embedded/repository authority",
    )
    b6.add_argument(
        "--force",
        action="store_true",
        help="explicitly replace an existing output ZIP",
    )
    b6.set_defaults(func=cmd_bundle_v06)

    a6 = sub.add_parser(
        "attest-v06",
        help="produce a complete signed, replayed, self-verified PCS v0.6 bundle",
    )
    a6.add_argument("manifest", help="PCS project manifest JSON")
    a6.add_argument("-o", "--output", required=True, help="output v0.6 delivery ZIP")
    a6.add_argument("--private-key", required=True, help="Ed25519 private signing key PEM")
    a6.add_argument("--public-key", required=True, help="matching trusted Ed25519 public key PEM")
    a6.add_argument(
        "--expected-signer-fingerprint",
        help="optionally pin the expected raw-public-key SHA-256 fingerprint",
    )
    a6.add_argument(
        "--lean-authority",
        help="receiver/producer-owned pcs-lean-authority executable; defaults to embedded/repository authority",
    )
    a6.add_argument(
        "--force",
        action="store_true",
        help="explicitly replace an existing output ZIP after the replacement self-verifies",
    )
    a6.set_defaults(func=cmd_attest_v06)

    bm6 = sub.add_parser(
        "benchmark-v06",
        help="run a provenance-bound PCS v0.6 real-world benchmark registry",
    )
    bm6.add_argument("registry", help="benchmark registry JSON")
    bm6.add_argument("-o", "--output", help="write deterministic benchmark report JSON")
    bm6.add_argument(
        "--force",
        action="store_true",
        help="explicitly replace an existing benchmark report",
    )
    bm6.set_defaults(func=cmd_benchmark_v06)

    sr6 = sub.add_parser(
        "scheduler-report-v06",
        help="analyze chronological replay telemetry and compare scheduling strategies",
    )
    sr6.add_argument("history", help="replay telemetry JSONL history")
    sr6.add_argument("-o", "--output", help="write scheduler analysis JSON")
    sr6.add_argument("--bandit-alpha", type=float, default=1.0)
    sr6.add_argument(
        "--force",
        action="store_true",
        help="explicitly replace an existing scheduler report",
    )
    sr6.set_defaults(func=cmd_scheduler_report_v06)

    i = sub.add_parser("inspect", help="human-readable certificate summary")
    i.add_argument("certificate")
    i.set_defaults(func=cmd_inspect)

    h = sub.add_parser("hash", help="SHA-256 an artifact")
    h.add_argument("file")
    h.set_defaults(func=cmd_hash)

    im = sub.add_parser("impact", help="show claims/evidence invalidated if an artifact changes")
    im.add_argument("certificate")
    im.add_argument("--artifact", action="append", required=True, help="changed artifact id; repeatable")
    im.set_defaults(func=cmd_impact)

    r = sub.add_parser("report", help="render a human-readable HTML assurance report")
    r.add_argument("certificate")
    r.add_argument("-o", "--output", required=True)
    r.set_defaults(func=cmd_report)

    g = sub.add_parser("gate", help="CI gate: fail unless required claims have acceptable status")
    g.add_argument("certificate")
    g.add_argument("--claim", action="append", help="required claim id; default is all claims")
    g.add_argument("--accept", action="append", help="acceptable status; repeatable")
    g.set_defaults(func=cmd_gate)

    kg = sub.add_parser("keygen", help="generate an Ed25519 certificate-signing keypair")
    kg.add_argument("--private-key", required=True)
    kg.add_argument("--public-key", required=True)
    kg.add_argument("--force", action="store_true", help="explicitly replace existing key files")
    kg.set_defaults(func=cmd_keygen)

    s = sub.add_parser("sign", help="sign a valid certificate without modifying it")
    s.add_argument("certificate")
    s.add_argument("--private-key", required=True)
    s.add_argument("-o", "--output", required=True)
    s.set_defaults(func=cmd_sign)

    vs = sub.add_parser("verify-signature", help="verify certificate integrity and an Ed25519 signature record")
    vs.add_argument("certificate")
    vs.add_argument("--signature", required=True)
    vs.add_argument("--public-key", required=True)
    vs.set_defaults(func=cmd_verify_signature)

    b = sub.add_parser("bundle", help="create a deterministic ZIP of a valid evidence package")
    b.add_argument("certificate")
    b.add_argument("-o", "--output", required=True)
    b.set_defaults(func=cmd_bundle)

    vb = sub.add_parser("verify-bundle", help="safely unpack and independently verify a PCS evidence ZIP")
    vb.add_argument("bundle")
    vb.add_argument("--public-key", help="Ed25519 public key for signature verification")
    vb.add_argument("--require-signature", action="store_true", help="reject unsigned bundles")
    vb.add_argument("--expected-signer-fingerprint", help="pin the accepted Ed25519 public-key SHA-256 fingerprint")
    vb.add_argument("--policy", help="external reviewer acceptance-policy JSON")
    vb.add_argument("--receipt", help="write a JSON verification receipt for this exact bundle/policy invocation")
    vb.set_defaults(func=cmd_verify_bundle)

    d = sub.add_parser("diff", help="compare the scientific content of two certificates")
    d.add_argument("left")
    d.add_argument("right")
    d.set_defaults(func=cmd_diff)

    ini = sub.add_parser("init", help="create a bounded starter PCS project")
    ini.add_argument("destination")
    ini.add_argument("--template", default="pkpd", choices=["pkpd"])
    ini.add_argument("--subject")
    ini.add_argument("--force", action="store_true")
    ini.set_defaults(func=cmd_init)

    doc = sub.add_parser("doctor", help="check the local PCS runtime and reference adapter")
    doc.set_defaults(func=cmd_doctor)

    att = sub.add_parser("attest", help="certify, replay-verify, report, optionally sign, and bundle a manifest")
    att.add_argument("manifest")
    att.add_argument("-o", "--output", required=True, help="evidence output directory")
    att.add_argument("--private-key")
    att.add_argument("--public-key")
    att.add_argument("--bundle", help="output ZIP path; defaults to <output>.zip")
    att.add_argument("--intake-lock", help="frozen pilot intake lock; claim/assumption IDs must exactly match the certificate")
    att.set_defaults(func=cmd_attest)

    fi = sub.add_parser("freeze-intake", help="freeze a pre-result pilot claim/assumption inventory by semantic hash")
    fi.add_argument("input", help="pilot intake JSON")
    fi.add_argument("-o", "--output", required=True, help="write the timestamped intake lock JSON")
    fi.add_argument("--force", action="store_true", help="explicitly replace an existing intake lock")
    fi.set_defaults(func=cmd_freeze_intake)

    se = sub.add_parser("snapshot-env", help="write a deterministic, secrets-free runtime provenance snapshot")
    se.add_argument("-o", "--output", required=True)
    se.set_defaults(func=cmd_snapshot_env)

    ed = sub.add_parser("env-diff", help="compare two PCS runtime provenance snapshots")
    ed.add_argument("left")
    ed.add_argument("right")
    ed.set_defaults(func=cmd_env_diff)

    return p


def main():
    args = build_parser().parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
