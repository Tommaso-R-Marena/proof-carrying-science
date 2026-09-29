from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from pcs.policy_v06 import apply_reviewer_policy_v06
from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))
MEMBERS = [
    "certificate.json",
    "certificate_signature.json",
    "package_manifest.json",
    "package_signature.json",
    "artifacts/fixture.bin",
    "normalized/index.json",
    META["normalized_wire_path"],
]


def _write_public_key(path: Path) -> None:
    key = Ed25519PublicKey.from_public_bytes(
        base64.b64decode(META["public_key_raw_base64"], validate=True)
    )
    path.write_bytes(
        key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def _golden_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
        for rel in MEMBERS:
            info = zipfile.ZipInfo(rel, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            zf.writestr(info, (GOLDEN / rel).read_bytes())


def _policy(path: Path, allowed: list[str], *, fingerprint: str | None = None) -> bytes:
    value = {
        "policy_version": "pcs-acceptance-policy-v1",
        "require_signature": True,
        "required_claims": {"C1": allowed},
    }
    if fingerprint is not None:
        value["expected_signer_fingerprint"] = fingerprint
    raw = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    path.write_bytes(raw)
    return raw


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pcs.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_no_policy_preserves_verification_validity_as_acceptance():
    verification = {
        "valid": True,
        "failed_stage": None,
        "public_key_fingerprint": "a" * 64,
        "claims": [
            {
                "claim_id": "C1",
                "decision": "COMPUTATIONALLY_SUPPORTED",
            }
        ],
    }

    result = apply_reviewer_policy_v06(verification, None)

    assert result["valid"] is True
    assert result["accepted"] is True
    assert result["reviewer_policy"] == {
        "applied": False,
        "pass": None,
        "policy_sha256": None,
        "failures": [],
    }


def test_valid_package_can_fail_reviewer_policy_without_becoming_invalid(tmp_path):
    bundle = tmp_path / "golden.zip"
    public_key = tmp_path / "public.pem"
    policy = tmp_path / "strict-policy.json"
    _golden_zip(bundle)
    _write_public_key(public_key)
    raw_policy = _policy(
        policy,
        ["FORMALLY_VERIFIED_UNDER_ASSUMPTIONS"],
        fingerprint=META["public_key_fingerprint"],
    )

    result = verify_package_zip_end_to_end_v06(
        bundle,
        public_key,
        expected_fingerprint=META["public_key_fingerprint"],
        policy_path=policy,
    )

    assert result["valid"] is True
    assert result["accepted"] is False
    assert result["reviewer_policy"]["applied"] is True
    assert result["reviewer_policy"]["pass"] is False
    assert result["reviewer_policy"]["policy_sha256"] == hashlib.sha256(
        raw_policy
    ).hexdigest()
    assert result["reviewer_policy"]["failures"] == [
        {
            "type": "claim_status",
            "claim_id": "C1",
            "actual": "COMPUTATIONALLY_SUPPORTED",
            "allowed": ["FORMALLY_VERIFIED_UNDER_ASSUMPTIONS"],
        }
    ]


def test_valid_package_passes_matching_reviewer_policy(tmp_path):
    bundle = tmp_path / "golden.zip"
    public_key = tmp_path / "public.pem"
    policy = tmp_path / "policy.json"
    _golden_zip(bundle)
    _write_public_key(public_key)
    raw_policy = _policy(
        policy,
        ["COMPUTATIONALLY_SUPPORTED"],
        fingerprint=META["public_key_fingerprint"],
    )

    result = verify_package_zip_end_to_end_v06(
        bundle,
        public_key,
        expected_fingerprint=META["public_key_fingerprint"],
        policy_path=policy,
    )

    assert result["valid"] is True
    assert result["accepted"] is True
    assert result["reviewer_policy"]["pass"] is True
    assert result["reviewer_policy"]["failures"] == []
    assert result["reviewer_policy"]["policy_sha256"] == hashlib.sha256(
        raw_policy
    ).hexdigest()


def test_reviewer_policy_can_pin_signer_independently_of_cli_pin(tmp_path):
    bundle = tmp_path / "golden.zip"
    public_key = tmp_path / "public.pem"
    policy = tmp_path / "wrong-signer-policy.json"
    _golden_zip(bundle)
    _write_public_key(public_key)
    _policy(
        policy,
        ["COMPUTATIONALLY_SUPPORTED"],
        fingerprint="0" * 64,
    )

    result = verify_package_zip_end_to_end_v06(
        bundle,
        public_key,
        policy_path=policy,
    )

    assert result["valid"] is True
    assert result["accepted"] is False
    failures = result["reviewer_policy"]["failures"]
    assert len(failures) == 1
    assert failures[0]["type"] == "signer"
    assert failures[0]["actual"] == META["public_key_fingerprint"]


def test_zip_cli_exit_code_and_receipt_follow_policy_acceptance(tmp_path):
    bundle = tmp_path / "golden.zip"
    public_key = tmp_path / "public.pem"
    pass_policy = tmp_path / "pass.json"
    fail_policy = tmp_path / "fail.json"
    receipt = tmp_path / "receipt.json"
    _golden_zip(bundle)
    _write_public_key(public_key)
    pass_raw = _policy(
        pass_policy,
        ["COMPUTATIONALLY_SUPPORTED"],
        fingerprint=META["public_key_fingerprint"],
    )
    _policy(
        fail_policy,
        ["FORMALLY_VERIFIED_UNDER_ASSUMPTIONS"],
        fingerprint=META["public_key_fingerprint"],
    )

    passed = _run(
        "verify-v06-bundle",
        str(bundle),
        "--public-key",
        str(public_key),
        "--policy",
        str(pass_policy),
        "--receipt",
        str(receipt),
    )
    assert passed.returncode == 0, passed.stdout + passed.stderr
    passed_result = json.loads(passed.stdout)
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    assert passed_result["valid"] is True
    assert passed_result["accepted"] is True
    assert saved["reviewer_policy"]["policy_sha256"] == hashlib.sha256(
        pass_raw
    ).hexdigest()

    failed = _run(
        "verify-v06-bundle",
        str(bundle),
        "--public-key",
        str(public_key),
        "--policy",
        str(fail_policy),
    )
    assert failed.returncode == 1, failed.stdout + failed.stderr
    failed_result = json.loads(failed.stdout)
    assert failed_result["valid"] is True
    assert failed_result["accepted"] is False
    assert failed_result["reviewer_policy"]["failures"][0]["type"] == "claim_status"
