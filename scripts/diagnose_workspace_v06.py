from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from pcs.attest_v06 import attest_v06
from pcs.discover_v06 import (
    confirm_manifest_draft_v06,
    discover_project_v06,
    write_discovery_outputs_v06,
)
from pcs.environment_workspace_v06 import prepare_verified_environment_workspace_v06
from pcs.scaffold import init_project
from pcs.signing import generate_keypair


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
    confirm_manifest_draft_v06(draft, manifest, project_root=project)
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
        choices=["import", "scaffold", "discover", "confirm", "attest", "prepare"],
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
