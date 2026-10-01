from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from pcs.attest_v06 import attest_v06
from pcs.byte_contract_v06 import parse_certificate_bytes_v06
from pcs.discover_v06 import (
    confirm_manifest_draft_v06,
    discover_project_v06,
    write_discovery_outputs_v06,
)
from pcs.environment_execute_v06 import build_sandbox_replay_plan_v06
from pcs.environment_replay_v06 import environment_from_binding_v06
from pcs.environment_v06 import (
    write_environment_replay_plan_v06,
    write_environment_replay_script_v06,
)
from pcs.environment_workspace_v06 import prepare_verified_environment_workspace_v06
from pcs.scaffold import init_project
from pcs.signing import generate_keypair
from pcs.verifier_zip_v06 import (
    load_package_zip_v06,
    verify_package_zip_end_to_end_v06,
)


def scaffold(root: Path) -> Path:
    project = root / "study"
    init_project(project, template="pkpd", subject="environment-workspace-diagnostic")
    (project / "requirements.txt").write_text(
        "numpy==1.26.4 --hash=sha256:" + "a" * 64 + "\n",
        encoding="utf-8",
    )
    (project / ".python-version").write_text("3.12.2\n", encoding="utf-8")
    (project / "Dockerfile").write_text(
        "FROM python:3.12-slim@sha256:" + "b" * 64 + "\n"
        "WORKDIR /app\n"
        "COPY . .\n",
        encoding="utf-8",
    )
    return project


def discover(project: Path) -> Path:
    report = discover_project_v06(project)
    draft = project / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(
        report,
        manifest_output=draft,
        report_output=project / "pcs-discovery.json",
    )
    return draft


def confirm(project: Path, draft: Path) -> Path:
    manifest = project / "manifest.json"
    confirm_manifest_draft_v06(
        draft,
        manifest,
        project_root=project,
        overwrite=True,
    )
    return manifest


def attest(root: Path, manifest: Path) -> tuple[Path, Path, str]:
    private = root / "private.pem"
    public = root / "public.pem"
    fingerprint = generate_keypair(private, public)["fingerprint"]
    bundle = root / "study.pcs.zip"
    result = attest_v06(
        manifest,
        bundle,
        private,
        public,
        expected_fingerprint=fingerprint,
    )
    if result.get("valid") is not True:
        raise RuntimeError(f"attestation failed: {result}")
    return bundle, public, fingerprint


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=[
            "import", "scaffold", "discover", "confirm", "attest",
            "verify", "load", "environment", "replay-plan",
            "sandbox-plan", "prepare",
        ],
    )
    args = parser.parse_args()

    if args.stage == "import":
        print(json.dumps({"stage": "import", "ok": True}))
        return 0

    with tempfile.TemporaryDirectory(prefix="pcs-workspace-diagnostic-") as tmp:
        root = Path(tmp)
        project = scaffold(root)
        if args.stage == "scaffold":
            print(json.dumps({"stage": "scaffold", "ok": project.is_dir()}))
            return 0

        draft = discover(project)
        if args.stage == "discover":
            print(json.dumps({"stage": "discover", "ok": draft.is_file()}))
            return 0

        manifest = confirm(project, draft)
        if args.stage == "confirm":
            print(json.dumps({"stage": "confirm", "ok": manifest.is_file()}))
            return 0

        bundle, public, fingerprint = attest(root, manifest)
        if args.stage == "attest":
            print(json.dumps({"stage": "attest", "ok": bundle.is_file()}))
            return 0

        verified = verify_package_zip_end_to_end_v06(
            bundle,
            public,
            expected_fingerprint=fingerprint,
        )
        if verified.get("valid") is not True:
            raise RuntimeError(f"zip verification failed: {verified}")
        if args.stage == "verify":
            print(json.dumps({"stage": "verify", "ok": True}))
            return 0

        loaded = load_package_zip_v06(bundle)
        if loaded.get("bundle_sha256") != verified.get("bundle_sha256"):
            raise RuntimeError("bundle hash changed after verification")
        if args.stage == "load":
            print(json.dumps({"stage": "load", "ok": True}))
            return 0

        certificate = parse_certificate_bytes_v06(loaded["certificate_bytes"])
        binding = certificate.get("environment")
        if not isinstance(binding, dict):
            raise RuntimeError("signed certificate lacks environment binding")
        environment = environment_from_binding_v06(binding)
        if args.stage == "environment":
            print(json.dumps({
                "stage": "environment",
                "ok": True,
                "hermeticity": environment.get("hermeticity"),
            }))
            return 0

        plan_path = write_environment_replay_plan_v06(
            environment,
            root / "pcs-environment-plan.json",
        )
        script_path = write_environment_replay_script_v06(
            environment,
            root / "reconstruct-environment.sh",
        )
        if args.stage == "replay-plan":
            print(json.dumps({
                "stage": "replay-plan",
                "ok": plan_path.is_file() and script_path.is_file(),
            }))
            return 0

        sandbox_plan = build_sandbox_replay_plan_v06(certificate, environment)
        if args.stage == "sandbox-plan":
            print(json.dumps({
                "stage": "sandbox-plan",
                "ok": True,
                "available": sandbox_plan is not None,
                "sha256": (
                    hashlib.sha256(
                        json.dumps(sandbox_plan, sort_keys=True).encode("utf-8")
                    ).hexdigest()
                    if sandbox_plan is not None else None
                ),
            }))
            return 0

        result = prepare_verified_environment_workspace_v06(
            bundle,
            root / "workspace",
            public,
            expected_fingerprint=fingerprint,
        )
        if result.get("valid") is not True:
            raise RuntimeError(f"workspace preparation failed: {result}")
        print(json.dumps({
            "stage": "prepare",
            "ok": True,
            "sandbox_execution_available": result.get("sandbox_execution_available"),
        }))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
