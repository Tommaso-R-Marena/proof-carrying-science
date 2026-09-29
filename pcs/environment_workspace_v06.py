from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath
from typing import Any

from .byte_contract_v06 import parse_certificate_bytes_v06
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


ENVIRONMENT_WORKSPACE_FORMAT_V06 = "pcs-environment-workspace-v1"


class V06EnvironmentWorkspaceError(ValueError):
    pass


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
    return path


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
    except (V06BundleVerificationError, OSError, ValueError) as exc:
        raise V06EnvironmentWorkspaceError(str(exc)) from exc

    if not verified.get("valid"):
        raise V06EnvironmentWorkspaceError(
            "refusing to prepare environment workspace from a bundle that failed "
            f"verification at {verified.get('failed_stage')!r}: "
            + "; ".join(str(x) for x in verified.get("errors", []))
        )

    try:
        loaded = load_package_zip_v06(bundle)
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
        for artifact in certificate.get("artifacts", []):
            if not isinstance(artifact, dict):
                continue
            source_path = artifact.get("source_path")
            if not isinstance(source_path, str):
                continue
            _safe_source_path(source_path)
            if source_path in seen_paths:
                raise V06EnvironmentWorkspaceError(
                    f"duplicate source_path in certificate: {source_path!r}"
                )
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

        metadata = {
            "format": ENVIRONMENT_WORKSPACE_FORMAT_V06,
            "bundle_sha256": loaded["bundle_sha256"],
            "certificate_semantic_hash": certificate["semantic_hash"],
            "certificate_integrity_hash": certificate["integrity_hash"],
            "environment_hermeticity": environment.get("hermeticity"),
            "environment_semantic_sha256": environment.get("semantic_sha256"),
            "environment_source_artifact_ids": list(
                binding.get("source_artifact_ids", [])
            ),
            "materialized_artifacts": materialized,
            "replay_plan": plan_path.name,
            "review_before_run_script": script_path.name,
            "automatic_execution_permitted_by_pcs": False,
            "warning": (
                "Review reconstruct-environment.sh before execution. Environment "
                "installation/build commands may access the network and execute "
                "project or dependency build/install code. PCS did not execute them."
            ),
        }
        (staging / "pcs-environment-workspace.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
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
        "environment_hermeticity": environment.get("hermeticity"),
        "materialized_artifact_count": len(materialized),
        "environment_source_count": len(binding.get("source_artifact_ids", [])),
        "replay_plan": str(destination / "pcs-environment-plan.json"),
        "review_before_run_script": str(
            destination / "reconstruct-environment.sh"
        ),
        "automatic_execution_permitted_by_pcs": False,
    }
