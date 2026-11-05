from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.attest_v06 import V06AttestationError, attest_v06
from pcs.provenance_v06 import (
    IN_TOTO_PAYLOAD_TYPE,
    IN_TOTO_STATEMENT_V1,
    dsse_pae_v06,
    write_cyclonedx_sbom_v06,
)
from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.signing import public_key_fingerprint
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


def _build_provenance_fixture(
    tmp_path: Path,
    subject_sha256: str,
) -> tuple[Path, Path, str]:
    private = Ed25519PrivateKey.generate()
    payload = canonicalize_jcs_bytes(
        {
            "_type": IN_TOTO_STATEMENT_V1,
            "subject": [
                {
                    "name": "pcs-build-subject",
                    "digest": {"sha256": subject_sha256},
                }
            ],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {
                "buildDefinition": {
                    "buildType": "https://example.invalid/pcs-test-build/v1"
                },
                "runDetails": {},
            },
        }
    )
    signature = private.sign(dsse_pae_v06(IN_TOTO_PAYLOAD_TYPE, payload))
    envelope = {
        "payloadType": IN_TOTO_PAYLOAD_TYPE,
        "payload": base64.b64encode(payload).decode("ascii"),
        "signatures": [
            {
                "keyid": "pcs-test-builder",
                "sig": base64.b64encode(signature).decode("ascii"),
            }
        ],
    }
    envelope_path = tmp_path / "build.dsse.json"
    public_path = tmp_path / "builder-public.pem"
    envelope_path.write_bytes(canonicalize_jcs_bytes(envelope))
    public_path.write_bytes(
        private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return envelope_path, public_path, public_key_fingerprint(private.public_key())


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


def test_attest_v06_binds_sbom_and_reports_verified_provenance(tmp_path):
    project = _project(tmp_path)
    private, public, fingerprint = _keys(tmp_path)
    bundle = tmp_path / "study-with-provenance.pcs.zip"
    sbom = tmp_path / "runtime.cdx.json"
    write_cyclonedx_sbom_v06(sbom)

    result = attest_v06(
        project / "manifest.json",
        bundle,
        private,
        public,
        expected_fingerprint=fingerprint,
        sbom_path=sbom,
    )

    assert result["valid"] is True
    assert result["provenance"]["mode"] == "bound"
    assert result["provenance"]["entries"][0]["kind"] == "sbom"

    checked = verify_package_zip_end_to_end_v06(
        bundle,
        public,
        expected_fingerprint=fingerprint,
    )
    assert checked["valid"], checked["errors"]
    assert checked["provenance"]["mode"] == "bound"
    assert any(
        entry["kind"] == "sbom"
        for entry in checked["provenance"]["entries"]
    )
    assert "provenance/index.json" in checked["verified_members"]
    assert "provenance/sbom.json" in checked["verified_members"]


def test_attest_v06_build_provenance_survives_authoritative_zip_verification(
    tmp_path,
):
    project = _project(tmp_path)
    private, public, fingerprint = _keys(tmp_path)
    bundle = tmp_path / "study-with-build-provenance.pcs.zip"
    subject_sha256 = hashlib.sha256(
        (project / "model.json").read_bytes()
    ).hexdigest()
    provenance, builder_public, builder_fingerprint = (
        _build_provenance_fixture(tmp_path, subject_sha256)
    )

    produced = attest_v06(
        project / "manifest.json",
        bundle,
        private,
        public,
        expected_fingerprint=fingerprint,
        build_provenance_path=provenance,
        build_provenance_public_key_path=builder_public,
        expected_build_provenance_fingerprint=builder_fingerprint,
        expected_build_subject_sha256=[subject_sha256],
    )

    assert produced["valid"] is True
    assert produced["provenance"]["mode"] == "bound"
    assert produced["provenance"]["reviewer_expectations"]["applied"] is True
    assert produced["provenance"]["reviewer_expectations"][
        "build_provenance_fingerprint"
    ] == builder_fingerprint
    assert produced["provenance"]["reviewer_expectations"][
        "subject_sha256"
    ] == [subject_sha256]

    checked = verify_package_zip_end_to_end_v06(
        bundle,
        public,
        expected_fingerprint=fingerprint,
        expected_build_provenance_fingerprint=builder_fingerprint,
        expected_build_subject_sha256=[subject_sha256],
    )
    assert checked["valid"], checked["errors"]
    assert checked["provenance"]["reviewer_expectations"]["applied"] is True
    assert checked["provenance"]["reviewer_expectations"][
        "build_provenance_fingerprint"
    ] == builder_fingerprint

    wrong_signer = verify_package_zip_end_to_end_v06(
        bundle,
        public,
        expected_fingerprint=fingerprint,
        expected_build_provenance_fingerprint="a" * 64,
        expected_build_subject_sha256=[subject_sha256],
    )
    assert wrong_signer["valid"] is False
    assert wrong_signer["failed_stage"] == "provenance"

    stale_subject = verify_package_zip_end_to_end_v06(
        bundle,
        public,
        expected_fingerprint=fingerprint,
        expected_build_provenance_fingerprint=builder_fingerprint,
        expected_build_subject_sha256=["b" * 64],
    )
    assert stale_subject["valid"] is False
    assert stale_subject["failed_stage"] == "provenance"


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
