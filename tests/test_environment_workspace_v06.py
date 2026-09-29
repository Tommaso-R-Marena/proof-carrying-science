from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pcs.attest_v06 import attest_v06
from pcs.discover_v06 import (
    confirm_manifest_draft_v06,
    discover_project_v06,
    write_discovery_outputs_v06,
)
from pcs.environment_workspace_v06 import (
    ENVIRONMENT_WORKSPACE_FORMAT_V06,
    V06EnvironmentWorkspaceError,
    prepare_verified_environment_workspace_v06,
)
from pcs.scaffold import init_project
from pcs.signing import generate_keypair


ROOT = Path(__file__).resolve().parents[1]


def _keys(tmp_path: Path, prefix: str = "") -> tuple[Path, Path, str]:
    private = tmp_path / f"{prefix}private.pem"
    public = tmp_path / f"{prefix}public.pem"
    result = generate_keypair(private, public)
    return private, public, result["fingerprint"]


def _bundle(tmp_path: Path) -> tuple[Path, Path, str, Path]:
    project = tmp_path / "study"
    init_project(project, template="pkpd", subject="environment-workspace")
    (project / "requirements.txt").write_text(
        "numpy==1.26.4 --hash=sha256:" + "a" * 64 + "\n",
        encoding="utf-8",
    )
    (project / ".python-version").write_text("3.12.2\n", encoding="utf-8")
    (project / "Dockerfile").write_text(
        "FROM python:3.12-slim@sha256:" + "b" * 64 + "\n"
        "WORKDIR /app\n"
        "COPY . .\n"
        "RUN python -c \"from pathlib import Path; "
        "Path('SHOULD_NOT_EXIST').write_text('executed')\"\n",
        encoding="utf-8",
    )

    report = discover_project_v06(project)
    draft = project / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(
        report,
        manifest_output=draft,
        report_output=project / "pcs-discovery.json",
    )
    manifest = project / "manifest.json"
    confirm_manifest_draft_v06(draft, manifest, project_root=project)

    private, public, fingerprint = _keys(tmp_path)
    bundle = tmp_path / "study.pcs.zip"
    result = attest_v06(
        manifest,
        bundle,
        private,
        public,
        expected_fingerprint=fingerprint,
    )
    assert result["valid"] is True
    return bundle, public, fingerprint, project


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pcs.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_prepare_verified_environment_workspace_materializes_signed_project_without_execution(tmp_path):
    bundle, public, fingerprint, project = _bundle(tmp_path)
    workspace = tmp_path / "replay-workspace"

    result = prepare_verified_environment_workspace_v06(
        bundle,
        workspace,
        public,
        expected_fingerprint=fingerprint,
    )

    assert result["valid"] is True
    assert result["format"] == ENVIRONMENT_WORKSPACE_FORMAT_V06
    assert result["automatic_execution_permitted_by_pcs"] is False
    assert (workspace / "model.json").read_bytes() == (project / "model.json").read_bytes()
    assert (workspace / "predictions.csv").read_bytes() == (
        project / "predictions.csv"
    ).read_bytes()
    assert (workspace / "requirements.txt").read_bytes() == (
        project / "requirements.txt"
    ).read_bytes()
    assert (workspace / ".python-version").read_bytes() == (
        project / ".python-version"
    ).read_bytes()
    assert (workspace / "Dockerfile").read_bytes() == (
        project / "Dockerfile"
    ).read_bytes()
    assert not (workspace / "SHOULD_NOT_EXIST").exists()

    metadata = json.loads(
        (workspace / "pcs-environment-workspace.json").read_text(encoding="utf-8")
    )
    assert metadata["format"] == ENVIRONMENT_WORKSPACE_FORMAT_V06
    assert metadata["bundle_sha256"] == result["bundle_sha256"]
    assert metadata["certificate_semantic_hash"] == result[
        "certificate_semantic_hash"
    ]
    assert metadata["certificate_integrity_hash"] == result[
        "certificate_integrity_hash"
    ]
    assert metadata["normalized_index_semantic_hash"] == result[
        "normalized_index_semantic_hash"
    ]
    assert metadata["public_key_fingerprint"] == result[
        "public_key_fingerprint"
    ]
    assert metadata["automatic_execution_permitted_by_pcs"] is False
    assert metadata["materialized_artifacts"]
    assert (workspace / metadata["verification_receipt"]).exists()
    assert len(metadata["replay_plan_sha256"]) == 64
    assert len(metadata["review_before_run_script_sha256"]) == 64
    assert len(metadata["verification_receipt_sha256"]) == 64

    plan = json.loads(
        (workspace / "pcs-environment-plan.json").read_text(encoding="utf-8")
    )
    assert plan["steps"][0]["kind"] == "container_build"
    script = (workspace / "reconstruct-environment.sh").read_text(encoding="utf-8")
    assert "REVIEW BEFORE EXECUTION" in script
    assert "docker build" in script


def test_prepare_environment_workspace_refuses_existing_destination(tmp_path):
    bundle, public, fingerprint, _ = _bundle(tmp_path)
    workspace = tmp_path / "replay-workspace"
    workspace.mkdir()

    with pytest.raises(V06EnvironmentWorkspaceError, match="already exists"):
        prepare_verified_environment_workspace_v06(
            bundle,
            workspace,
            public,
            expected_fingerprint=fingerprint,
        )


def test_prepare_environment_workspace_refuses_wrong_producer_key(tmp_path):
    bundle, _public, fingerprint, _ = _bundle(tmp_path)
    _wrong_private, wrong_public, _wrong_fp = _keys(tmp_path, "wrong-")

    with pytest.raises(
        V06EnvironmentWorkspaceError,
        match="failed verification",
    ):
        prepare_verified_environment_workspace_v06(
            bundle,
            tmp_path / "wrong-key-workspace",
            wrong_public,
            expected_fingerprint=fingerprint,
        )


def test_prepare_environment_cli_creates_verified_nonexecuted_workspace(tmp_path):
    bundle, public, fingerprint, _ = _bundle(tmp_path)
    workspace = tmp_path / "cli-workspace"

    proc = _run(
        "prepare-environment-v06",
        str(bundle),
        "-o",
        str(workspace),
        "--public-key",
        str(public),
        "--expected-signer-fingerprint",
        fingerprint,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["valid"] is True
    assert result["automatic_execution_permitted_by_pcs"] is False
    assert Path(result["workspace"]) == workspace.resolve()
    assert (workspace / "pcs-environment-workspace.json").exists()
    assert not (workspace / "SHOULD_NOT_EXIST").exists()



def test_prepare_environment_workspace_rejects_bundle_swap_after_verification(
    tmp_path,
    monkeypatch,
):
    import pcs.environment_workspace_v06 as workspace_mod

    bundle, public, fingerprint, _ = _bundle(tmp_path)
    original = workspace_mod.load_package_zip_v06

    def swapped(path):
        loaded = dict(original(path))
        loaded["bundle_sha256"] = "0" * 64
        return loaded

    monkeypatch.setattr(workspace_mod, "load_package_zip_v06", swapped)

    with pytest.raises(
        V06EnvironmentWorkspaceError,
        match="changed after verification",
    ):
        prepare_verified_environment_workspace_v06(
            bundle,
            tmp_path / "swapped-workspace",
            public,
            expected_fingerprint=fingerprint,
        )
