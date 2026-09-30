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


def build_fixture(root: Path) -> tuple[Path, Path, str, Path]:
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

    report = discover_project_v06(project)
    draft = project / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(
        report,
        manifest_output=draft,
        report_output=project / "pcs-discovery.json",
    )
    manifest = project / "manifest.json"
    confirm_manifest_draft_v06(draft, manifest, project_root=project)

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
    return bundle, public, fingerprint, project


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["import", "bundle", "prepare"])
    args = parser.parse_args()

    if args.stage == "import":
        print(json.dumps({"stage": "import", "ok": True}))
        return 0

    with tempfile.TemporaryDirectory(prefix="pcs-workspace-diagnostic-") as tmp:
        root = Path(tmp)
        bundle, public, fingerprint, project = build_fixture(root)
        if args.stage == "bundle":
            print(json.dumps({
                "stage": "bundle",
                "ok": True,
                "bundle_exists": bundle.is_file(),
                "project_exists": project.is_dir(),
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
