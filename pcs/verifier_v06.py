from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .byte_contract_v06 import (
    V06ByteContractError,
    parse_certificate_bytes_v06,
    parse_package_manifest_bytes_v06,
    parse_signature_record_bytes_v06,
    verify_package_file_map_v06,
)
from .normalized_set_v06 import verify_normalized_set_after_replay_v06
from .replay_v06 import verify_certificate_replay_v06
from .signing_v06 import verify_certificate_signature_v06
from .workflow_replay_v06 import verify_static_workflow_replay_v06
from .environment_replay_v06 import verify_environment_replay_v06


VERIFIER_FORMAT_V06 = "pcs-end-to-end-verifier-v06-v1"


def _failed(
    stage: str,
    errors: list[str],
    *,
    stages: dict[str, bool],
) -> dict[str, Any]:
    return {
        "format": VERIFIER_FORMAT_V06,
        "authority_required": True,
        "authoritative": False,
        "valid": False,
        "failed_stage": stage,
        "errors": errors,
        "stages": stages,
        "claims": [],
    }


def verify_end_to_end_v06(
    *,
    certificate_bytes: bytes,
    certificate_signature_bytes: bytes,
    package_manifest_bytes: bytes,
    package_signature_bytes: bytes,
    package_files: Mapping[str, bytes],
    public_key: Ed25519PublicKey,
    expected_fingerprint: str | None = None,
    scheduler_strategy: str = "manifest",
    scheduler_history: list[dict[str, Any]] | None = None,
    bandit_alpha: float = 1.0,
    shadow_bandit: bool = False,
    telemetry_sink: dict[str, Any] | None = None,
    authority_context_sink: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the Python v0.6 precheck over one complete package.

    Public production verification is authoritative only after
    `enforce_lean_authority_v06` conjoins this precheck with the Lean v0.6/v2
    acceptance result. This function remains separately callable for testing and
    external-oracle execution, but its successful result is explicitly marked
    `authoritative: false`.

    Acceptance requires, in order:

    1. exact canonical JCS bytes for certificate, both signature records and manifest;
    2. certificate hash/schema validity and its Ed25519 signature;
    3. exact signed package member set, byte sizes/hashes, certificate binding and
       package-manifest Ed25519 signature;
    4. fresh regeneration of any human-confirmed reproducibility-environment contract;
    5. fresh static replay of any human-confirmed workflow dependency claims;
    6. fresh replay of every certificate evidence item;
    7. exact equality of the delivered normalized set with the set derived from
       that *same* replay result.

    This is the production executable composition point. It does not turn an
    unsupported external replay adapter into verified evidence: the replay layer
    still marks such evidence UNVERIFIED and therefore prevents acceptance of a
    falsely recorded PASS.
    """
    stages = {
        "canonical_inputs": False,
        "certificate_signature": False,
        "package_binding": False,
        "environment_replay": False,
        "workflow_replay": False,
        "replay": False,
        "normalized_set": False,
    }

    if not isinstance(package_files, Mapping):
        return _failed(
            "canonical_inputs",
            ["v0.6 package file map must be a mapping"],
            stages=stages,
        )

    try:
        certificate = parse_certificate_bytes_v06(certificate_bytes)
        certificate_signature = parse_signature_record_bytes_v06(
            certificate_signature_bytes
        )
        # Parse these here as a strict canonical-input gate even though the
        # package verifier will independently parse and verify them again.
        parse_package_manifest_bytes_v06(package_manifest_bytes)
        parse_signature_record_bytes_v06(package_signature_bytes)
    except V06ByteContractError as exc:
        return _failed("canonical_inputs", [str(exc)], stages=stages)
    stages["canonical_inputs"] = True

    certificate_auth = verify_certificate_signature_v06(
        certificate,
        certificate_signature,
        public_key,
        expected_fingerprint=expected_fingerprint,
    )
    if not certificate_auth["valid"]:
        return _failed(
            "certificate_signature",
            list(certificate_auth["errors"]),
            stages=stages,
        )
    stages["certificate_signature"] = True

    package_check = verify_package_file_map_v06(
        package_manifest_bytes,
        certificate_bytes,
        package_signature_bytes,
        package_files,
        public_key,
        expected_fingerprint=expected_fingerprint,
    )
    if not package_check["valid"]:
        return _failed(
            "package_binding",
            list(package_check["errors"]),
            stages=stages,
        )
    stages["package_binding"] = True

    environment_replay = verify_environment_replay_v06(
        certificate,
        package_files,
    )
    if not environment_replay["valid"]:
        return _failed(
            "environment_replay",
            list(environment_replay["errors"]),
            stages=stages,
        )
    stages["environment_replay"] = True

    workflow_replay = verify_static_workflow_replay_v06(
        certificate,
        package_files,
    )
    if not workflow_replay["valid"]:
        return _failed(
            "workflow_replay",
            list(workflow_replay["errors"]),
            stages=stages,
        )
    stages["workflow_replay"] = True

    replay = verify_certificate_replay_v06(
        certificate,
        package_files,
        scheduler_strategy=scheduler_strategy,
        scheduler_history=scheduler_history,
        bandit_alpha=bandit_alpha,
        shadow_bandit=shadow_bandit,
        telemetry_sink=telemetry_sink,
    )
    if not replay["valid"]:
        return _failed("replay", list(replay["errors"]), stages=stages)
    stages["replay"] = True

    normalized = verify_normalized_set_after_replay_v06(
        certificate,
        package_files,
        replay,
    )
    if not normalized["valid"]:
        return _failed(
            "normalized_set",
            list(normalized["errors"]),
            stages=stages,
        )
    stages["normalized_set"] = True

    entries_by_claim = {
        entry["claim_id"]: entry for entry in normalized["entries"]
    }
    claims: list[dict[str, Any]] = []
    for claim in certificate["claims"]:
        claim_id = claim["id"]
        entry = entries_by_claim[claim_id]
        claims.append(
            {
                "claim_id": claim_id,
                "kind": claim["kind"],
                "decision": replay["claim_statuses"][claim_id],
                "predicate": claim["predicate"],
                "normalized_path": entry["path"],
                "wire_semantic_hash": entry["wire_semantic_hash"],
            }
        )

    if authority_context_sink is not None:
        authority_context_sink.clear()
        authority_context_sink.update(
            {
                "certificate": certificate,
                "environment_replay": environment_replay,
                "workflow_replay": workflow_replay,
                "replay": replay,
            }
        )

    result = {
        "format": VERIFIER_FORMAT_V06,
        "authority_required": True,
        "authoritative": False,
        "valid": True,
        "failed_stage": None,
        "errors": [],
        "stages": stages,
        "certificate_semantic_hash": certificate["semantic_hash"],
        "certificate_integrity_hash": certificate["integrity_hash"],
        "public_key_fingerprint": package_check["public_key_fingerprint"],
        "normalized_index_semantic_hash": normalized["index_semantic_hash"],
        "verified_members": package_check["verified_members"],
        "environment_replay": {
            "mode": environment_replay["mode"],
            "hermeticity": environment_replay["hermeticity"],
            "source_files_checked": environment_replay["source_files_checked"],
            "dependency_records": environment_replay.get("dependency_records", 0),
            "unresolved_items": environment_replay.get("unresolved_items", 0),
            "replay_plan": environment_replay.get("replay_plan"),
        },
        "workflow_replay": {
            "nodes_checked": workflow_replay["nodes_checked"],
            "mode": workflow_replay["mode"],
        },
        "claims": claims,
    }
    if (
        scheduler_strategy != "manifest"
        or shadow_bandit
        or bool(scheduler_history)
    ):
        result["replay_scheduler"] = replay["scheduler"]
    return result
