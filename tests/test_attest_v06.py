from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pcs.attest_v06 import V06AttestationError, attest_v06
from pcs.scaffold import init_project
from pcs.signing import generate_keypair
from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06


ROOT = Path(__file__).resolve().parents[1]


def _keys(tmp_path: Path, stem: str = "signer") -> tuple[Path, Path, str]:
    private = tmp_path / f"{stem}-private.pem"
    public = tmp_path / f"{stem}-public.pem"
    result = generate_keypair(private, public)
    return private, public, result["fingerprint"]


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "pilot"
    init_project(root, template="pkpd", subject="v06-mvp-pilot")
    return root


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pcs.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_attest_v06_pkpd_scaffold_round_trips_to_independent_verifier(tmp_path):
    project = _project(tmp_path)
    private, public, fingerprint = _keys(tmp_path)
    bundle = tmp_path / "study.pcs.zip"

    result = attest_v06(
        project / "manifest.json",
        bundle,
        private,
        public,
        expected_fingerprint=fingerprint,
    )

    assert result["valid"] is True
    assert result["post_build_verified"] is True
    assert bundle.is_file()
    statuses = {claim["claim_id"]: claim["decision"] for claim in result["claims"]}
    assert statuses == {
        "C_PKPD_CONTRACT": "COMPUTATIONALLY_SUPPORTED",
        "C_PKPD_REPLAY": "COMPUTATIONALLY_SUPPORTED",
    }

    checked = verify_package_zip_end_to_end_v06(
        bundle,
        public,
        expected_fingerprint=fingerprint,
    )
    assert checked["valid"], checked["errors"]
    assert checked["bundle_sha256"] == result["bundle_sha256"]
    assert checked["certificate_semantic_hash"] == result[
        "certificate_semantic_hash"
    ]


def test_attest_v06_cli_is_one_command_producer(tmp_path):
    project = _project(tmp_path)
    private, public, fingerprint = _keys(tmp_path)
    bundle = tmp_path / "study.pcs.zip"

    proc = _run(
        "attest-v06",
        str(project / "manifest.json"),
        "-o",
        str(bundle),
        "--private-key",
        str(private),
        "--public-key",
        str(public),
        "--expected-signer-fingerprint",
        fingerprint,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["valid"] is True
    assert result["post_build_verified"] is True
    assert Path(result["bundle"]) == bundle.resolve()

    verify_proc = _run(
        "verify-v06-bundle",
        str(bundle),
        "--public-key",
        str(public),
        "--expected-signer-fingerprint",
        fingerprint,
    )
    assert verify_proc.returncode == 0, verify_proc.stdout + verify_proc.stderr
    verified = json.loads(verify_proc.stdout)
    assert verified["valid"] is True
    assert verified["bundle_sha256"] == result["bundle_sha256"]


def test_attest_v06_records_failed_science_honestly_instead_of_refusing_package(tmp_path):
    project = _project(tmp_path)
    private, public, fingerprint = _keys(tmp_path)
    bundle = tmp_path / "failed-claim.pcs.zip"

    # Keep valid CSV structure but make the numerical result scientifically false.
    (project / "predictions.csv").write_text(
        "time,concentration,effect\n"
        "0,999,0\n"
        "1,999,0\n",
        encoding="utf-8",
    )

    result = attest_v06(
        project / "manifest.json",
        bundle,
        private,
        public,
        expected_fingerprint=fingerprint,
    )

    assert result["valid"] is True
    statuses = {claim["claim_id"]: claim["decision"] for claim in result["claims"]}
    assert statuses["C_PKPD_CONTRACT"] == "COMPUTATIONALLY_SUPPORTED"
    assert statuses["C_PKPD_REPLAY"] == "FALSIFIED_OR_CHECK_FAILED"

    checked = verify_package_zip_end_to_end_v06(
        bundle,
        public,
        expected_fingerprint=fingerprint,
    )
    assert checked["valid"], checked["errors"]
    verified_statuses = {
        claim["claim_id"]: claim["decision"] for claim in checked["claims"]
    }
    assert verified_statuses == statuses


def test_attest_v06_rejects_mismatched_keypair_without_publishing(tmp_path):
    project = _project(tmp_path)
    private, _, _ = _keys(tmp_path, "one")
    _, wrong_public, _ = _keys(tmp_path, "two")
    bundle = tmp_path / "should-not-exist.zip"

    with pytest.raises(V06AttestationError, match="keypair mismatch"):
        attest_v06(
            project / "manifest.json",
            bundle,
            private,
            wrong_public,
        )

    assert not bundle.exists()


def test_attest_v06_rejects_artifact_path_escape_without_publishing(tmp_path):
    project = _project(tmp_path)
    private, public, _ = _keys(tmp_path)
    bundle = tmp_path / "should-not-exist.zip"

    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    manifest_path = project / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["path"] = "../outside.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(V06AttestationError, match="escapes manifest directory"):
        attest_v06(
            manifest_path,
            bundle,
            private,
            public,
        )

    assert not bundle.exists()


def test_attest_v06_rejects_claim_evidence_predicate_substitution(tmp_path):
    project = _project(tmp_path)
    private, public, _ = _keys(tmp_path)
    bundle = tmp_path / "should-not-exist.zip"

    manifest_path = project / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["claims"][1]["predicate"]["rel_tol"] = 0.5
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(V06AttestationError, match="predicate differs"):
        attest_v06(
            manifest_path,
            bundle,
            private,
            public,
        )

    assert not bundle.exists()


def test_attest_v06_refuses_existing_output_without_force(tmp_path):
    project = _project(tmp_path)
    private, public, _ = _keys(tmp_path)
    bundle = tmp_path / "existing.zip"
    bundle.write_bytes(b"existing")

    with pytest.raises(V06AttestationError, match="refusing to overwrite"):
        attest_v06(
            project / "manifest.json",
            bundle,
            private,
            public,
        )

    assert bundle.read_bytes() == b"existing"
