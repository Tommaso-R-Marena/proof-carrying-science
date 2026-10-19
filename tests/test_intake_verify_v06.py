"""Reviewer-side intake-lock enforcement and malicious-producer substitutions."""

from __future__ import annotations

import hashlib
import copy
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.attest_v06 import attest_v06
from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.canonical_zip_v06 import canonical_zip_bytes_v06
from pcs.discover_v06 import confirm_manifest_draft_v06, discover_project_v06, write_discovery_outputs_v06
from pcs.independent_pilot_v1 import _align_draft_to_intake, stage_external_lab_project
from pcs.intake import INTAKE_LOCK_PACKAGE_MEMBER_V06, freeze_intake, freeze_intake_file
from pcs.intake_verify_v06 import verify_package_intake_lock_v06
from pcs.lean_authority_v06 import V06LeanAuthorityError, resolve_lean_authority_v06
from pcs.package_v06 import build_package_manifest_v06, sign_package_manifest_v06
from pcs.signing import public_key_fingerprint
from pcs.verifier_zip_v06 import load_package_zip_v06, verify_package_zip_end_to_end_v06
from pcs.verifier_io_v06 import (
    V06VerifierIOError,
    verify_package_directory_end_to_end_v06,
    write_verification_receipt_v06,
)
from pcs.receipt_contract_v06 import audit_verification_receipt_v06
from pcs.receipt_signature_v06 import (
    sign_verification_receipt_v06,
    verify_verification_receipt_signature_v06,
)


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "formal" / ".lake" / "build" / "bin" / "pcs-lean-authority"


def _actual_authority_path() -> Path:
    """Use the receiver's actual binary, including isolated cleanroom builds."""
    if AUTHORITY.is_file() and os.access(AUTHORITY, os.X_OK):
        return AUTHORITY
    resolved = resolve_lean_authority_v06(None)
    path = resolved.get("path")
    if path is None:
        raise V06LeanAuthorityError("a compiled real authority binary is required")
    candidate = Path(path)
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        raise V06LeanAuthorityError("resolved authority is not an executable file")
    return candidate


def _authority_available() -> bool:
    if AUTHORITY.is_file() and os.access(AUTHORITY, os.X_OK):
        return True
    try:
        resolved = resolve_lean_authority_v06(None)
    except V06LeanAuthorityError:
        return False
    path = resolved.get("path")
    # repository-build without a compiled binary is not sufficient for high-assurance tests.
    if path is None:
        return False
    candidate = Path(path)
    return candidate.is_file() and os.access(candidate, os.X_OK)


def _require_authority() -> None:
    if _authority_available():
        return
    if os.environ.get("PCS_REQUIRE_LEAN_AUTHORITY") == "1":
        pytest.fail(
            "pcs-lean-authority unavailable; required by PCS_REQUIRE_LEAN_AUTHORITY=1. "
            "Build with: cd formal && lake build pcs-lean-authority"
        )
    pytest.skip(
        "pcs-lean-authority unavailable; build with: cd formal && lake build pcs-lean-authority"
    )


@pytest.fixture(autouse=True)
def _authority_gate():
    _require_authority()


def _keys(tmp: Path) -> tuple[Ed25519PrivateKey, Path, Path, str]:
    tmp.mkdir(parents=True, exist_ok=True)
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    priv = tmp / "private.pem"
    pub = tmp / "public.pem"
    priv.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    pub.write_bytes(
        public.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private, priv, pub, public_key_fingerprint(public)


def _confirmed_manifest_and_lock(lab: Path) -> tuple[Path, Path, dict]:
    lock = freeze_intake_file(lab / "pilot_intake.json", lab / "pilot.lock.json", overwrite=True)
    discovered = discover_project_v06(lab)
    draft = lab / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(
        discovered,
        manifest_output=draft,
        report_output=lab / "pcs-discovery.json",
        overwrite=True,
    )
    aligned = _align_draft_to_intake(json.loads(draft.read_text(encoding="utf-8")), lock["intake"])
    draft.write_text(json.dumps(aligned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = lab / "manifest.json"
    confirm_manifest_draft_v06(draft, manifest, project_root=lab, overwrite=True)
    return manifest, lab / "pilot.lock.json", lock


def _attest_honest_bundle(tmp_path: Path, *, include_lock: bool = True) -> tuple[Path, Path, str, dict, Ed25519PrivateKey]:
    lab = tmp_path / "lab"
    stage_external_lab_project(lab)
    manifest, lock_path, lock = _confirmed_manifest_and_lock(lab)
    private, priv_path, pub_path, fingerprint = _keys(tmp_path / "keys")
    bundle = tmp_path / "honest.pcs.zip"
    attest_v06(
        manifest,
        bundle,
        priv_path,
        pub_path,
        expected_fingerprint=fingerprint,
        intake_lock=lock_path if include_lock else None,
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        overwrite=True,
        generated_at="2026-10-17T00:00:00+00:00",
    )
    return bundle, pub_path, fingerprint, lock, private


def _malicious_resign_with_substituted_lock(
    honest_bundle: Path,
    *,
    private_key: Ed25519PrivateKey,
    substituted_lock: dict,
    out: Path,
) -> Path:
    """Produce an internally signed package whose intake lock does not match the certificate.

    Mimics a malicious producer that bypasses producer-side intake checks by
    substituting ``pilot-intake-lock.json`` after attestation and resigning the
    package manifest with the producer key. Certificate signatures remain valid.
    """
    loaded = load_package_zip_v06(honest_bundle)
    package_files = dict(loaded["package_files"])
    lock_bytes = canonicalize_jcs_bytes(substituted_lock)
    package_files[INTAKE_LOCK_PACKAGE_MEMBER_V06] = lock_bytes

    certificate = json.loads(package_files["certificate.json"].decode("utf-8"))
    inventory = {
        name: {"sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}
        for name, raw in package_files.items()
    }
    package_manifest = build_package_manifest_v06(certificate, inventory)
    package_manifest_bytes = canonicalize_jcs_bytes(package_manifest)
    package_signature = sign_package_manifest_v06(package_manifest, private_key)
    package_signature_bytes = canonicalize_jcs_bytes(package_signature)

    members = {
        **package_files,
        "certificate_signature.json": loaded["certificate_signature_bytes"],
        "package_manifest.json": package_manifest_bytes,
        "package_signature.json": package_signature_bytes,
    }
    out.write_bytes(canonical_zip_bytes_v06(members))
    return out


def test_reviewer_accepts_matching_signed_intake_lock(tmp_path):
    bundle, pub, fingerprint, lock, _private = _attest_honest_bundle(tmp_path)
    result = verify_package_zip_end_to_end_v06(
        bundle,
        pub,
        expected_fingerprint=fingerprint,
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        require_canonical_archive=True,
        require_intake_lock=True,
        expected_intake_semantic_hash=lock["intake_semantic_hash"],
    )
    assert result["valid"] is True
    assert result["authoritative"] is True
    intake = result["intake_lock"]
    assert intake["valid"] is True
    assert intake["present"] is True
    assert intake["stages"]["certificate_consistent"] is True
    assert intake["preregistration_evidence"] == (
        "reviewer_owned_expected_intake_semantic_hash"
    )
    assert intake["frozen_at"]
    assert "not preregistration" in " ".join(intake["notes"]).lower()


def test_malicious_substituted_intake_lock_is_rejected_by_independent_verifier(tmp_path):
    bundle, pub, fingerprint, lock, private = _attest_honest_bundle(tmp_path)
    mutated_intake = json.loads(json.dumps(lock["intake"]))
    mutated_intake["claims"][0]["statement"] = (
        "Malicious post-hoc weakened claim substituted into signed lock."
    )
    bad_lock = freeze_intake(mutated_intake, frozen_at="2026-10-17T00:00:00+00:00")
    assert bad_lock["intake_semantic_hash"] != lock["intake_semantic_hash"]

    evil = _malicious_resign_with_substituted_lock(
        bundle,
        private_key=private,
        substituted_lock=bad_lock,
        out=tmp_path / "malicious-substituted-lock.pcs.zip",
    )

    result = verify_package_zip_end_to_end_v06(
        evil,
        pub,
        expected_fingerprint=fingerprint,
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        require_canonical_archive=True,
        require_intake_lock=True,
    )
    assert result["valid"] is not True
    assert result.get("failed_stage") == "intake_lock" or any(
        "intake" in str(err).lower() for err in (result.get("errors") or [])
    )
    intake = result.get("intake_lock") or {}
    assert intake.get("valid") is not True
    assert intake.get("stages", {}).get("certificate_consistent") is not True


def test_malicious_mismatched_expected_hash_is_rejected(tmp_path):
    bundle, pub, fingerprint, lock, _private = _attest_honest_bundle(tmp_path)
    wrong_expected = "ab" * 32
    assert wrong_expected != lock["intake_semantic_hash"]
    result = verify_package_zip_end_to_end_v06(
        bundle,
        pub,
        expected_fingerprint=fingerprint,
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        require_canonical_archive=True,
        require_intake_lock=True,
        expected_intake_semantic_hash=wrong_expected,
    )
    assert result["valid"] is not True
    intake = result.get("intake_lock") or {}
    assert intake.get("valid") is not True
    assert intake.get("stages", {}).get("expected_hash_bound") is False
    assert intake.get("preregistration_evidence") == "none"


def test_present_but_mismatched_lock_fails_closed_even_when_not_required(tmp_path):
    bundle, pub, fingerprint, lock, private = _attest_honest_bundle(tmp_path)
    mutated_intake = json.loads(json.dumps(lock["intake"]))
    mutated_intake["assumptions"][0]["statement"] = "Substituted assumption text."
    bad_lock = freeze_intake(mutated_intake, frozen_at=lock["frozen_at"])
    evil = _malicious_resign_with_substituted_lock(
        bundle,
        private_key=private,
        substituted_lock=bad_lock,
        out=tmp_path / "present-mismatched.pcs.zip",
    )
    result = verify_package_zip_end_to_end_v06(
        evil,
        pub,
        expected_fingerprint=fingerprint,
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        require_canonical_archive=True,
        require_intake_lock=False,
    )
    assert result["valid"] is not True
    assert (result.get("intake_lock") or {}).get("valid") is not True


def test_require_intake_lock_rejects_missing_member(tmp_path):
    lab = tmp_path / "lab"
    stage_external_lab_project(lab)
    manifest, _lock_path, _lock = _confirmed_manifest_and_lock(lab)
    _private, priv_path, pub_path, fingerprint = _keys(tmp_path / "keys")
    bundle = tmp_path / "no-lock.pcs.zip"
    attest_v06(
        manifest,
        bundle,
        priv_path,
        pub_path,
        expected_fingerprint=fingerprint,
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        overwrite=True,
        generated_at="2026-10-17T00:00:00+00:00",
    )
    with zipfile.ZipFile(bundle, "r") as zf:
        assert INTAKE_LOCK_PACKAGE_MEMBER_V06 not in zf.namelist()
    result = verify_package_zip_end_to_end_v06(
        bundle,
        pub_path,
        expected_fingerprint=fingerprint,
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        require_canonical_archive=True,
        require_intake_lock=True,
    )
    assert result["valid"] is not True
    assert (result.get("intake_lock") or {}).get("present") is False


def test_frozen_at_is_not_preregistration_evidence():
    example = ROOT / "examples" / "pkpd_one_compartment" / "pilot_intake.json"
    intake = json.loads(example.read_text(encoding="utf-8"))
    lock = freeze_intake(intake, frozen_at="2099-01-01T00:00:00+00:00")
    cert = {
        "claims": [
            {
                "id": c["id"],
                "statement": c["statement"],
                "kind": c["desired_assurance"],
            }
            for c in lock["intake"]["claims"]
        ],
        "assumptions": [
            {"id": a["id"], "statement": a["statement"]}
            for a in lock["intake"]["assumptions"]
        ],
    }
    package_files = {
        INTAKE_LOCK_PACKAGE_MEMBER_V06: canonicalize_jcs_bytes(lock),
    }
    checked = verify_package_intake_lock_v06(
        certificate=cert,
        package_files=package_files,
        require_intake_lock=True,
    )
    assert checked["valid"] is True
    assert checked["frozen_at"] == "2099-01-01T00:00:00+00:00"
    assert checked["preregistration_evidence"] == "none"


def _received_path(bundle: Path, transport: str, tmp_path: Path) -> Path:
    if transport == "zip":
        return bundle
    directory = tmp_path / "received"
    directory.mkdir()
    # Test-generated canonical archive, not arbitrary untrusted extraction.
    with zipfile.ZipFile(bundle) as archive:
        archive.extractall(directory)
    return directory


@pytest.mark.parametrize("transport", ["zip", "directory"])
@pytest.mark.parametrize("failure", ["expected_hash", "missing", "invalid_lock", "certificate_mismatch"])
def test_real_lean_accept_with_intake_veto_persists_signed_negative_receipt(tmp_path, transport, failure):
    bundle, pub, fingerprint, lock, private = _attest_honest_bundle(
        tmp_path, include_lock=failure != "missing"
    )
    if failure in {"invalid_lock", "certificate_mismatch"}:
        if failure == "invalid_lock":
            substituted = {"format": "invalid-intake"}
        else:
            changed = copy.deepcopy(lock["intake"])
            changed["claims"][0]["statement"] = "Substituted statement."
            substituted = freeze_intake(changed, frozen_at=lock["frozen_at"])
        bundle = _malicious_resign_with_substituted_lock(
            bundle, private_key=private, substituted_lock=substituted,
            out=tmp_path / "substituted.pcs.zip",
        )
    received = _received_path(bundle, transport, tmp_path)
    verify = (verify_package_zip_end_to_end_v06 if transport == "zip"
              else verify_package_directory_end_to_end_v06)
    kwargs = {"require_intake_lock": True}
    if failure == "expected_hash":
        kwargs["expected_intake_semantic_hash"] = "ab" * 32
    result = verify(received, pub, expected_fingerprint=fingerprint,
                    lean_authority_path=_actual_authority_path(), **kwargs)
    assert result["lean_authority"]["accepted"] is True
    assert result["lean_authority"]["verdict"] == "ACCEPT"
    assert result["stages"]["lean_authority"] is True
    assert result["formal_coverage"]["package_authority"] == "LEAN_AUTHORITATIVE_ACCEPT"
    assert all(result[name] is False for name in ("valid", "accepted", "authoritative"))
    assert result["failed_stage"] == "intake_lock"
    assert audit_verification_receipt_v06(result)["valid"] is True
    receipt = write_verification_receipt_v06(result, tmp_path / "negative.json")
    _reviewer, reviewer_private, reviewer_public, reviewer_fp = _keys(tmp_path / "reviewer")
    signature = tmp_path / "negative.sig.json"
    sign_verification_receipt_v06(receipt, reviewer_private, signature)
    replay = verify_verification_receipt_signature_v06(
        receipt, signature, reviewer_public,
        expected_reviewer_fingerprint=reviewer_fp,
        bundle_path=bundle if transport == "zip" else None,
        producer_public_key_path=pub, authority_path=_actual_authority_path(),
    )
    assert replay["valid"] is True
    assert replay["pcs_valid"] is False
    assert replay["reviewer_accepted"] is False

    # Signing a rejection cannot authenticate subsequent changes to its veto.
    changed = copy.deepcopy(result)
    changed["intake_lock"]["errors"].append("Altered after signing")
    receipt.write_text(json.dumps(changed), encoding="utf-8")
    assert verify_verification_receipt_signature_v06(
        receipt, signature, reviewer_public
    )["valid"] is False


@pytest.mark.parametrize("transport", ["zip", "directory"])
def test_cli_writes_and_signs_real_lean_intake_rejection(tmp_path, transport):
    bundle, pub, fingerprint, _lock, _private = _attest_honest_bundle(tmp_path)
    received = _received_path(bundle, transport, tmp_path)
    _reviewer, reviewer_private, reviewer_public, _reviewer_fp = _keys(tmp_path / "reviewer")
    receipt = tmp_path / "cli-negative.json"
    command = "verify-v06-bundle" if transport == "zip" else "verify-v06"
    run = subprocess.run([
        sys.executable, "-m", "pcs.cli", command, str(received),
        "--public-key", str(pub), "--expected-signer-fingerprint", fingerprint,
        "--lean-authority", str(_actual_authority_path()), "--require-intake-lock",
        "--expected-intake-semantic-hash", "ab" * 32,
        "--receipt", str(receipt), "--reviewer-private-key", str(reviewer_private),
    ], capture_output=True, text=True, cwd=ROOT, timeout=60)
    assert run.returncode == 1, run.stderr
    output = json.loads(run.stdout)
    assert output["accepted"] is False
    assert output["lean_authority"]["accepted"] is True
    assert Path(output["receipt_written"]) == receipt
    assert verify_verification_receipt_signature_v06(
        receipt, output["receipt_signature_written"], reviewer_public
    )["valid"] is True


@pytest.mark.parametrize("mutation", [
    "erase_veto", "valid_veto", "wrong_stage", "erase_errors", "all_stages_pass",
    "wrong_expected_hash", "invalid_member_hash", "accept_package", "erase_lean_accept",
])
def test_intake_veto_cannot_launder_contradictory_receipt(tmp_path, mutation):
    bundle, pub, fingerprint, lock, _private = _attest_honest_bundle(tmp_path)
    result = verify_package_zip_end_to_end_v06(
        bundle, pub, expected_fingerprint=fingerprint, lean_authority_path=_actual_authority_path(),
        require_intake_lock=True, expected_intake_semantic_hash="ab" * 32,
    )
    assert result["lean_authority"]["accepted"] is True
    if mutation == "erase_veto":
        del result["intake_lock"]
    elif mutation == "valid_veto":
        result["intake_lock"]["valid"] = True
    elif mutation == "wrong_stage":
        result["failed_stage"] = "arbitrary-host-failure"
    elif mutation == "erase_errors":
        result["errors"] = []
    elif mutation == "all_stages_pass":
        result["intake_lock"]["stages"]["expected_hash_bound"] = True
    elif mutation == "wrong_expected_hash":
        result["intake_lock"]["expected_intake_semantic_hash"] = lock["intake_semantic_hash"]
    elif mutation == "invalid_member_hash":
        result["intake_lock"]["member_sha256"] = "invalid"
    elif mutation == "accept_package":
        for name in ("valid", "authoritative", "accepted"):
            result[name] = True
    elif mutation == "erase_lean_accept":
        result["lean_authority"]["accepted"] = False
        result["lean_authority"]["verdict"] = "REJECT"
    assert audit_verification_receipt_v06(result)["valid"] is False
    with pytest.raises(V06VerifierIOError, match="receipt contract failed"):
        write_verification_receipt_v06(result, tmp_path / "must-not-persist.json")


@pytest.mark.parametrize("transport", ["zip", "directory"])
def test_isolated_authority_from_environment_writes_signed_negative_receipt(tmp_path, monkeypatch, transport):
    """Actual binary outside the checkout, selected only by receiver environment.

    Redirecting the test's absent-path sentinel does not replace verification.
    The copied real Lean executable runs during attestation and the actual CLI.
    """
    isolated = tmp_path / "receiver-owned" / "pcs-lean-authority"
    isolated.parent.mkdir()
    source = _actual_authority_path()
    shutil.copy2(source, isolated)
    digest = hashlib.sha256(isolated.read_bytes()).hexdigest()
    assert digest == hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setenv("PCS_LEAN_AUTHORITY_BIN", str(isolated))
    monkeypatch.setattr(sys.modules[__name__], "AUTHORITY", tmp_path / "absent-checkout" / "pcs-lean-authority")
    assert _actual_authority_path() == isolated.resolve()
    bundle, pub, fingerprint, _lock, _private = _attest_honest_bundle(tmp_path)
    received = _received_path(bundle, transport, tmp_path)
    _reviewer, reviewer_private, reviewer_public, _reviewer_fp = _keys(tmp_path / "reviewer")
    receipt_path = tmp_path / "isolated-negative.json"
    command = "verify-v06-bundle" if transport == "zip" else "verify-v06"
    # Intentionally omit --lean-authority: this reproduces the public CI layout.
    run = subprocess.run([
        sys.executable, "-m", "pcs.cli", command, str(received),
        "--public-key", str(pub), "--expected-signer-fingerprint", fingerprint,
        "--require-intake-lock", "--expected-intake-semantic-hash", "ab" * 32,
        "--receipt", str(receipt_path), "--reviewer-private-key", str(reviewer_private),
    ], capture_output=True, text=True, cwd=ROOT, timeout=60)
    assert run.returncode == 1, run.stderr
    result = json.loads(run.stdout)
    assert result["lean_authority"]["accepted"] is True
    assert result["lean_authority"]["authority_sha256"] == digest
    assert all(result[name] is False for name in ("valid", "accepted", "authoritative"))
    replay = verify_verification_receipt_signature_v06(
        receipt_path, result["receipt_signature_written"], reviewer_public,
        bundle_path=bundle if transport == "zip" else None,
        producer_public_key_path=pub, authority_path=_actual_authority_path(),
    )
    assert replay["valid"] is True
    assert replay["pcs_valid"] is False and replay["reviewer_accepted"] is False
