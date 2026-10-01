from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from pcs.attest_v06 import V06AttestationError, attest_v06
from pcs.discover_v06 import (
    V06DiscoveryError,
    confirm_manifest_draft_v06,
    discover_project_v06,
    write_discovery_outputs_v06,
)
from pcs.discovery_review_v06 import render_discovery_review_v06
from pcs.scaffold import init_project
from pcs.signing import generate_keypair
from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06


ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pcs.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _keys(tmp_path: Path) -> tuple[Path, Path, str]:
    private = tmp_path / "private.pem"
    public = tmp_path / "public.pem"
    result = generate_keypair(private, public)
    return private, public, result["fingerprint"]


def test_discover_pkpd_project_drafts_two_high_confidence_checks(tmp_path):
    project = tmp_path / "pkpd"
    init_project(project, template="pkpd", subject="guided-pkpd")

    report = discover_project_v06(project)

    assert report["format"] == "pcs-project-discovery-v1"
    assert report["summary"]["claims_drafted"] == 2
    assert report["summary"]["checks_drafted"] == 2
    assert report["manifest_draft"]["pcs_intake"]["status"] == "draft"
    assert report["manifest_draft"]["pcs_intake"]["requires_confirmation"] is True
    check_types = {x["type"] for x in report["manifest_draft"]["checks"]}
    assert check_types == {"pkpd_contract", "pkpd_reference_match"}
    artifact_paths = {x["path"] for x in report["manifest_draft"]["artifacts"]}
    assert artifact_paths == {"model.json", "predictions.csv"}
    assert all(
        "pcs_discovery_sha256" in x["metadata"]
        for x in report["manifest_draft"]["artifacts"]
    )


def test_unconfirmed_discovery_draft_cannot_be_attested(tmp_path):
    project = tmp_path / "pkpd"
    init_project(project, template="pkpd", subject="guided-pkpd")
    report = discover_project_v06(project)
    draft = project / "pcs-manifest.draft.json"
    discovery = project / "pcs-discovery.json"
    write_discovery_outputs_v06(
        report,
        manifest_output=draft,
        report_output=discovery,
    )

    with pytest.raises(V06AttestationError, match="unconfirmed PCS discovery draft"):
        attest_v06(
            draft,
            tmp_path / "should-not-exist.zip",
            tmp_path / "missing-private.pem",
            tmp_path / "missing-public.pem",
        )


def test_discover_confirm_attest_is_complete_product_onboarding_path(tmp_path):
    project = tmp_path / "pkpd"
    init_project(project, template="pkpd", subject="guided-pkpd")
    report = discover_project_v06(project)
    draft = project / "pcs-manifest.draft.json"
    discovery = project / "pcs-discovery.json"
    write_discovery_outputs_v06(
        report,
        manifest_output=draft,
        report_output=discovery,
    )
    manifest = project / "manifest.json"
    confirmed = confirm_manifest_draft_v06(
        draft,
        manifest,
        project_root=project,
    )

    assert confirmed["valid"] is True
    assert confirmed["snapshot_verified"] == 2
    confirmed_obj = json.loads(manifest.read_text(encoding="utf-8"))
    assert confirmed_obj["pcs_intake"]["status"] == "confirmed"
    assert confirmed_obj["pcs_intake"]["requires_confirmation"] is False
    assert all(
        artifact["metadata"]["pcs_discovery_confirmed"] is True
        for artifact in confirmed_obj["artifacts"]
    )

    private, public, fingerprint = _keys(tmp_path)
    bundle = tmp_path / "guided-study.pcs.zip"
    result = attest_v06(
        manifest,
        bundle,
        private,
        public,
        expected_fingerprint=fingerprint,
    )

    assert result["valid"] is True
    assert result["post_build_verified"] is True
    checked = verify_package_zip_end_to_end_v06(
        bundle,
        public,
        expected_fingerprint=fingerprint,
    )
    assert checked["valid"], checked["errors"]
    statuses = {x["claim_id"]: x["decision"] for x in checked["claims"]}
    assert set(statuses.values()) == {"COMPUTATIONALLY_SUPPORTED"}

    with zipfile.ZipFile(bundle, "r") as zf:
        certificate = json.loads(zf.read("certificate.json").decode("utf-8"))
    assert all(
        artifact.get("metadata", {}).get("pcs_discovery_confirmed") is True
        for artifact in certificate["artifacts"]
    )
    assert all(
        isinstance(
            artifact.get("metadata", {}).get(
                "pcs_discovery_inventory_commitment_sha256"
            ),
            str,
        )
        for artifact in certificate["artifacts"]
    )


def test_artifact_change_after_confirmation_is_rejected_at_attestation(tmp_path):
    project = tmp_path / "pkpd"
    init_project(project, template="pkpd", subject="guided-pkpd")
    report = discover_project_v06(project)
    draft = project / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(
        report,
        manifest_output=draft,
        report_output=project / "pcs-discovery.json",
    )
    manifest = project / "manifest.json"
    confirm_manifest_draft_v06(
        draft,
        manifest,
        project_root=project,
    )

    (project / "predictions.csv").write_text(
        "time,concentration,effect\n0,999,0\n",
        encoding="utf-8",
    )
    private, public, _ = _keys(tmp_path)

    with pytest.raises(V06AttestationError, match="changed after PCS discovery/confirmation"):
        attest_v06(
            manifest,
            tmp_path / "should-not-exist.zip",
            private,
            public,
        )


def test_discover_named_csv_splits_and_high_priority_key(tmp_path):
    project = tmp_path / "splits"
    project.mkdir()
    (project / "train.csv").write_text(
        "subject_id,value\nS1,1\nS2,2\n",
        encoding="utf-8",
    )
    (project / "test.csv").write_text(
        "subject_id,value\nS3,3\nS4,4\n",
        encoding="utf-8",
    )

    report = discover_project_v06(project)

    checks = report["manifest_draft"]["checks"]
    assert len(checks) == 1
    assert checks[0]["type"] == "csv_disjoint"
    assert checks[0]["key"] == "subject_id"
    assert report["recommendations"][0]["confidence"] >= 0.95


def test_discover_reaction_and_unit_json_keeps_source_files_in_artifacts(tmp_path):
    project = tmp_path / "chem"
    project.mkdir()
    (project / "reaction.json").write_text(
        json.dumps(
            {
                "reactants": [
                    {"formula": "N2", "coefficient": 1},
                    {"formula": "H2", "coefficient": 3},
                ],
                "products": [{"formula": "NH3", "coefficient": 2}],
            }
        ),
        encoding="utf-8",
    )
    (project / "units.json").write_text(
        json.dumps({"left_unit": "mg/L", "right_unit": "g/m^3"}),
        encoding="utf-8",
    )

    report = discover_project_v06(project)

    assert {x["type"] for x in report["manifest_draft"]["checks"]} == {
        "reaction_balance",
        "unit_compatible",
    }
    assert {x["path"] for x in report["manifest_draft"]["artifacts"]} == {
        "reaction.json",
        "units.json",
    }


def test_discovery_excludes_key_material_and_does_not_package_it(tmp_path):
    project = tmp_path / "keys"
    project.mkdir()
    (project / "train.csv").write_text("id,x\n1,1\n", encoding="utf-8")
    (project / "test.csv").write_text("id,x\n2,2\n", encoding="utf-8")
    (project / "secret.pem").write_text(
        "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n",
        encoding="utf-8",
    )

    report = discover_project_v06(project)

    assert "secret.pem" not in {x["path"] for x in report["inventory"]}
    assert {"path": "secret.pem", "reason": "key-material-excluded"} in report["skipped"]
    assert "secret.pem" not in {x["path"] for x in report["manifest_draft"]["artifacts"]}


def test_confirm_refuses_no_supported_claims_without_explicit_override(tmp_path):
    project = tmp_path / "unsupported"
    project.mkdir()
    (project / "notes.txt").write_text("scientific notes\n", encoding="utf-8")
    report = discover_project_v06(project)
    draft = project / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(
        report,
        manifest_output=draft,
        report_output=project / "pcs-discovery.json",
    )

    assert report["summary"]["claims_drafted"] == 0
    assert report["unresolved"][0]["type"] == "no-supported-checks-detected"
    with pytest.raises(V06DiscoveryError, match="no claims"):
        confirm_manifest_draft_v06(
            draft,
            project / "manifest.json",
            project_root=project,
        )


def test_confirm_refuses_artifact_changed_between_discovery_and_confirmation(tmp_path):
    project = tmp_path / "splits"
    project.mkdir()
    (project / "train.csv").write_text("id,x\n1,1\n", encoding="utf-8")
    (project / "test.csv").write_text("id,x\n2,2\n", encoding="utf-8")
    report = discover_project_v06(project)
    draft = project / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(
        report,
        manifest_output=draft,
        report_output=project / "pcs-discovery.json",
    )

    (project / "test.csv").write_text("id,x\n1,999\n", encoding="utf-8")

    with pytest.raises(V06DiscoveryError, match="changed since discovery"):
        confirm_manifest_draft_v06(
            draft,
            project / "manifest.json",
            project_root=project,
        )


def test_discover_and_confirm_cli_use_project_local_defaults(tmp_path):
    project = tmp_path / "cli-project"
    project.mkdir()
    (project / "train.csv").write_text("id,x\n1,1\n", encoding="utf-8")
    (project / "test.csv").write_text("id,x\n2,2\n", encoding="utf-8")

    discover = _run("discover-v06", str(project))
    assert discover.returncode == 0, discover.stdout + discover.stderr
    discovered = json.loads(discover.stdout)
    assert Path(discovered["manifest_draft"]) == (
        project / "pcs-manifest.draft.json"
    ).resolve()
    assert Path(discovered["discovery_report"]) == (
        project / "pcs-discovery.json"
    ).resolve()
    assert Path(discovered["discovery_review"]) == (
        project / "pcs-discovery-review.md"
    ).resolve()
    review_text = (project / "pcs-discovery-review.md").read_text(
        encoding="utf-8"
    )
    assert "# PCS guided discovery review" in review_text
    assert "## Scientific-check recommendations" in review_text
    assert "pcs confirm-v06" in review_text

    confirm = _run(
        "confirm-v06",
        str(project / "pcs-manifest.draft.json"),
    )
    assert confirm.returncode == 0, confirm.stdout + confirm.stderr
    confirmed = json.loads(confirm.stdout)
    assert Path(confirmed["manifest"]) == (project / "manifest.json").resolve()
    assert confirmed["snapshot_verified"] == 2



def test_discovery_review_matches_selected_workflow_and_unresolved_items(tmp_path):
    project = tmp_path / "review-project"
    project.mkdir()
    (project / "train.csv").write_text("id,x\n1,1\n", encoding="utf-8")
    (project / "test.csv").write_text("id,x\n2,2\n", encoding="utf-8")
    (project / "analysis.py").write_text(
        "import pandas as pd\n"
        "df = pd.read_csv('train.csv')\n"
        "df.to_csv('test.csv', index=False)\n",
        encoding="utf-8",
    )

    report = discover_project_v06(project)
    review = render_discovery_review_v06(report)

    assert "## Static workflow inferences" in review
    assert "analysis.py" in review
    assert "train.csv" in review
    assert "test.csv" in review
    assert "graph LR" in review
    assert "user code was not" in review.lower()
    assert "pcs confirm-v06" in review
