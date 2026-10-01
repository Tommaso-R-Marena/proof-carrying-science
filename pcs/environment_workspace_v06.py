from __future__ import annotations

import hashlib
import json
import shutil
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any

from .byte_contract_v06 import parse_certificate_bytes_v06
from .canonical_json import canonicalize_jcs
from .environment_execute_v06 import (
    V06SandboxReplayError,
    build_sandbox_replay_plan_v06,
    write_sandbox_replay_plan_v06,
)
from .environment_replay_v06 import (
    V06EnvironmentReplayError,
    environment_from_binding_v06,
)
from .environment_v06 import (
    V06EnvironmentCaptureError,
    write_environment_replay_plan_v06,
    write_environment_replay_script_v06,
)
from .verifier_zip_v06 import (
    V06BundleVerificationError,
    load_package_zip_v06,
    verify_package_zip_end_to_end_v06,
)
from .lean_authority_v06 import V06LeanAuthorityError


ENVIRONMENT_WORKSPACE_FORMAT_V06 = "pcs-environment-workspace-v1"
SIGNED_CERTIFICATE_FILE_V06 = "pcs-signed-certificate.json"
_WORKSPACE_CONTROL_PATHS_V06 = {
    "pcs-environment-workspace.json",
    "pcs-environment-plan.json",
    "pcs-verification-receipt.json",
    "reconstruct-environment.sh",
    SIGNED_CERTIFICATE_FILE_V06,
    "pcs-signed-certificate-signature.json",
    "pcs-signed-environment.json",
    "pcs-execution-plan.json",
}


class V06EnvironmentWorkspaceError(ValueError):
    pass


_WINDOWS_FORBIDDEN = set('<>:"|?*')
_WINDOWS_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def _safe_source_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise V06EnvironmentWorkspaceError(
            f"unsafe project-relative source path: {value!r}"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or value.endswith("/")
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise V06EnvironmentWorkspaceError(
            f"unsafe project-relative source path: {value!r}"
        )
    for segment in path.parts:
        if unicodedata.normalize("NFC", segment) != segment:
            raise V06EnvironmentWorkspaceError(
                f"non-NFC project-relative source path: {value!r}"
            )
        if any(
            ord(ch) < 32
            or ord(ch) == 127
            or ch in _WINDOWS_FORBIDDEN
            for ch in segment
        ):
            raise V06EnvironmentWorkspaceError(
                f"non-portable project-relative source path: {value!r}"
            )
        if segment.endswith((" ", ".")):
            raise V06EnvironmentWorkspaceError(
                f"non-portable project-relative source path: {value!r}"
            )
        stem = segment.split(".", 1)[0].rstrip(" .").casefold()
        if stem in _WINDOWS_RESERVED:
            raise V06EnvironmentWorkspaceError(
                f"Windows-reserved project-relative source path: {value!r}"
            )
    return path


def _portable_key(value: str) -> str:
    return "/".join(
        unicodedata.normalize("NFC", part).casefold()
        for part in PurePosixPath(value).parts
    )


def _write_workspace_file(root: Path, relative: str, raw: bytes) -> None:
    posix = _safe_source_path(relative)
    target = root.joinpath(*posix.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise V06EnvironmentWorkspaceError(
            f"workspace path collision while materializing: {relative!r}"
        )
    target.write_bytes(raw)


def prepare_verified_environment_workspace_v06(
    bundle: str | Path,
    output: str | Path,
    public_key_path: str | Path,
    *,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Prepare a verified local replay workspace without executing it.

    The bundle is fully verified first. Only after verification succeeds are signed
    project artifacts materialized at their certificate source_path locations.

    No package manager, container builder, installer, notebook, script, or user code
    is executed by this function.
    """
    destination = Path(output).resolve()
    if destination.exists():
        raise V06EnvironmentWorkspaceError(
            f"environment workspace output already exists: {destination}"
        )
    if destination.is_symlink():
        raise V06EnvironmentWorkspaceError(
            f"refusing symlinked environment workspace output: {destination}"
        )

    try:
        verified = verify_package_zip_end_to_end_v06(
            bundle,
            public_key_path,
            expected_fingerprint=expected_fingerprint,
        )
    except (V06BundleVerificationError, V06LeanAuthorityError, OSError, ValueError) as exc:
        raise V06EnvironmentWorkspaceError(str(exc)) from exc

    if not verified.get("valid"):
        raise V06EnvironmentWorkspaceError(
            "refusing to prepare environment workspace from a bundle that failed "
            f"verification at {verified.get('failed_stage')!r}: "
            + "; ".join(str(x) for x in verified.get("errors", []))
        )

    try:
        loaded = load_package_zip_v06(bundle)
        if loaded.get("bundle_sha256") != verified.get("bundle_sha256"):
            raise V06EnvironmentWorkspaceError(
                "bundle bytes changed after verification and before workspace "
                "materialization"
            )
        certificate = parse_certificate_bytes_v06(loaded["certificate_bytes"])
    except (V06BundleVerificationError, OSError, ValueError) as exc:
        raise V06EnvironmentWorkspaceError(str(exc)) from exc

    binding = certificate.get("environment")
    if not isinstance(binding, dict):
        raise V06EnvironmentWorkspaceError(
            "verified bundle does not contain a reproducibility-environment contract"
        )
    try:
        environment = environment_from_binding_v06(binding)
    except V06EnvironmentReplayError as exc:
        raise V06EnvironmentWorkspaceError(str(exc)) from exc

    artifact_by_id = {
        artifact["id"]: artifact
        for artifact in certificate.get("artifacts", [])
        if isinstance(artifact, dict) and isinstance(artifact.get("id"), str)
    }

    # Build in a sibling staging directory so a failed materialization never leaves
    # a partially prepared workspace at the requested destination.
    staging = destination.with_name(destination.name + ".pcs-staging")
    if staging.exists():
        raise V06EnvironmentWorkspaceError(
            f"environment workspace staging path already exists: {staging}"
        )
    staging.mkdir(parents=True, exist_ok=False)

    materialized: list[dict[str, Any]] = []
    try:
        # Materialize all signed project artifacts with source_path metadata. This
        # preserves Docker build contexts and gives the reviewer the same relative
        # layout used by workflow/environment replay.
        seen_paths: set[str] = set()
        portable_paths: dict[str, str] = {}
        for artifact in certificate.get("artifacts", []):
            if not isinstance(artifact, dict):
                continue
            source_path = artifact.get("source_path")
            if not isinstance(source_path, str):
                continue
            _safe_source_path(source_path)
            if source_path in _WORKSPACE_CONTROL_PATHS_V06:
                raise V06EnvironmentWorkspaceError(
                    f"project source_path collides with reserved PCS workspace control file: {source_path!r}"
                )
            if source_path in seen_paths:
                raise V06EnvironmentWorkspaceError(
                    f"duplicate source_path in certificate: {source_path!r}"
                )
            portable_key = _portable_key(source_path)
            other = portable_paths.get(portable_key)
            if other is not None and other != source_path:
                raise V06EnvironmentWorkspaceError(
                    f"cross-platform source_path collision: "
                    f"{other!r} vs {source_path!r}"
                )
            portable_paths[portable_key] = source_path
            seen_paths.add(source_path)

            package_path = artifact.get("path")
            raw = loaded["package_files"].get(package_path)
            if not isinstance(raw, bytes):
                raise V06EnvironmentWorkspaceError(
                    f"signed artifact bytes missing for {artifact.get('id')!r}"
                )
            digest = hashlib.sha256(raw).hexdigest()
            if digest != artifact.get("sha256"):
                raise V06EnvironmentWorkspaceError(
                    f"artifact hash mismatch while preparing workspace: "
                    f"{artifact.get('id')!r}"
                )
            _write_workspace_file(staging, source_path, raw)
            materialized.append(
                {
                    "artifact_id": artifact["id"],
                    "source_path": source_path,
                    "sha256": digest,
                    "size": len(raw),
                    "environment_source": artifact["id"]
                    in set(binding.get("source_artifact_ids", [])),
                }
            )

        try:
            plan_path = write_environment_replay_plan_v06(
                environment,
                staging / "pcs-environment-plan.json",
            )
            script_path = write_environment_replay_script_v06(
                environment,
                staging / "reconstruct-environment.sh",
            )
        except (V06EnvironmentCaptureError, OSError) as exc:
            raise V06EnvironmentWorkspaceError(str(exc)) from exc

        try:
            signed_certificate_path = staging / "pcs-signed-certificate.json"
            signed_certificate_path.write_bytes(loaded["certificate_bytes"])
            signed_certificate_signature_path = (
                staging / "pcs-signed-certificate-signature.json"
            )
            signed_certificate_signature_path.write_bytes(
                loaded["certificate_signature_bytes"]
            )
            signed_environment_path = staging / "pcs-signed-environment.json"
            signed_environment_path.write_text(
                canonicalize_jcs(environment) + "\n",
                encoding="utf-8",
            )
            sandbox_execution_plan = build_sandbox_replay_plan_v06(
                certificate,
                environment,
            )
            sandbox_execution_plan_path = None
            if sandbox_execution_plan is not None:
                sandbox_execution_plan_path = write_sandbox_replay_plan_v06(
                    sandbox_execution_plan,
                    staging / "pcs-execution-plan.json",
                )
        except (OSError, V06SandboxReplayError) as exc:
            raise V06EnvironmentWorkspaceError(str(exc)) from exc

        receipt_path = staging / "pcs-verification-receipt.json"
        receipt_path.write_text(
            json.dumps(verified, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        metadata = {
            "format": ENVIRONMENT_WORKSPACE_FORMAT_V06,
            "bundle_sha256": loaded["bundle_sha256"],
            "certificate_semantic_hash": certificate["semantic_hash"],
            "certificate_integrity_hash": certificate["integrity_hash"],
            "normalized_index_semantic_hash": verified.get(
                "normalized_index_semantic_hash"
            ),
            "public_key_fingerprint": verified.get("public_key_fingerprint"),
            "environment_hermeticity": environment.get("hermeticity"),
            "environment_semantic_sha256": environment.get("semantic_sha256"),
            "signed_certificate": signed_certificate_path.name,
            "signed_certificate_sha256": hashlib.sha256(
                signed_certificate_path.read_bytes()
            ).hexdigest(),
            "signed_certificate_signature": signed_certificate_signature_path.name,
            "signed_certificate_signature_sha256": hashlib.sha256(
                signed_certificate_signature_path.read_bytes()
            ).hexdigest(),
            "signed_environment_contract": signed_environment_path.name,
            "signed_environment_contract_sha256": hashlib.sha256(
                signed_environment_path.read_bytes()
            ).hexdigest(),
            "sandbox_execution_available": sandbox_execution_plan_path is not None,
            "sandbox_execution_plan": (
                sandbox_execution_plan_path.name
                if sandbox_execution_plan_path is not None
                else None
            ),
            "sandbox_execution_plan_sha256": (
                hashlib.sha256(sandbox_execution_plan_path.read_bytes()).hexdigest()
                if sandbox_execution_plan_path is not None
                else None
            ),
            "environment_source_artifact_ids": list(
                binding.get("source_artifact_ids", [])
            ),
            "materialized_artifacts": materialized,
            "replay_plan": plan_path.name,
            "review_before_run_script": script_path.name,
            "verification_receipt": receipt_path.name,
            "replay_plan_sha256": hashlib.sha256(
                plan_path.read_bytes()
            ).hexdigest(),
            "review_before_run_script_sha256": hashlib.sha256(
                script_path.read_bytes()
            ).hexdigest(),
            "verification_receipt_sha256": hashlib.sha256(
                receipt_path.read_bytes()
            ).hexdigest(),
            "automatic_execution_permitted_by_pcs": False,
            "warning": (
                "Review reconstruct-environment.sh before execution. Environment "
                "installation/build commands may access the network and execute "
                "project or dependency build/install code. PCS did not execute them. "
                "Use pcs execute-environment-v06 explicitly to run the prepared workflow "
                "inside the fail-closed OCI sandbox."
            ),
        }
        (staging / "pcs-environment-workspace.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

        if load_package_zip_v06(bundle).get("bundle_sha256") != verified.get(
            "bundle_sha256"
        ):
            raise V06EnvironmentWorkspaceError(
                "bundle bytes changed during workspace staging"
            )

        staging.replace(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return {
        "valid": True,
        "format": ENVIRONMENT_WORKSPACE_FORMAT_V06,
        "workspace": str(destination),
        "bundle_sha256": loaded["bundle_sha256"],
        "certificate_semantic_hash": certificate["semantic_hash"],
        "certificate_integrity_hash": certificate["integrity_hash"],
        "normalized_index_semantic_hash": verified.get(
            "normalized_index_semantic_hash"
        ),
        "public_key_fingerprint": verified.get("public_key_fingerprint"),
        "environment_hermeticity": environment.get("hermeticity"),
        "sandbox_execution_available": sandbox_execution_plan_path is not None,
        "sandbox_execution_plan": (
            str(destination / sandbox_execution_plan_path.name)
            if sandbox_execution_plan_path is not None
            else None
        ),
        "materialized_artifact_count": len(materialized),
        "environment_source_count": len(binding.get("source_artifact_ids", [])),
        "replay_plan": str(destination / "pcs-environment-plan.json"),
        "review_before_run_script": str(
            destination / "reconstruct-environment.sh"
        ),
        "automatic_execution_permitted_by_pcs": False,
        "signed_certificate": str(destination / SIGNED_CERTIFICATE_FILE_V06),
    }
