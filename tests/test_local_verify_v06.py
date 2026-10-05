from __future__ import annotations

import json

import pytest

from pcs.local_verify_v06 import (
    V06LocalVerifyError,
    load_trust_profile_v06,
    verify_local_bundle_v06,
)
from scripts.run_golden_examples_v06 import build_golden_examples


def test_trust_profile_reduces_bundle_verification_to_one_call(tmp_path):
    report = build_golden_examples(tmp_path / "golden")
    case = next(c for c in report["cases"] if c["name"] == "pkpd-supported")
    project = tmp_path / "golden" / "pkpd-supported"
    public = tmp_path / "golden" / "demo-public.pem"
    trust = tmp_path / "trust.json"
    # The deterministic demo key fingerprint is recovered from a successful result.
    bundle = tmp_path / "golden" / case["bundle"]
    from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06
    first = verify_package_zip_end_to_end_v06(bundle, public)
    trust.write_text(json.dumps({
        "format": "pcs-verifier-trust-v1",
        "public_key": str(public),
        "expected_signer_fingerprint": first["public_key_fingerprint"],
    }), encoding="utf-8")
    result = verify_local_bundle_v06(bundle, trust, receipt=tmp_path / "receipt.json")
    assert result["valid"] is True
    assert result["claims"][0]["decision"] in {"COMPUTATIONALLY_SUPPORTED", "FALSIFIED_OR_CHECK_FAILED"}
    assert (tmp_path / "receipt.json").is_file()


    trust.write_text(
        json.dumps(
            {
                "format": "pcs-verifier-trust-v1",
                "public_key": str(public),
                "expected_signer_fingerprint": first["public_key_fingerprint"],
                "expected_build_provenance_fingerprint": "a" * 64,
                "expected_build_subject_sha256": ["b" * 64],
            }
        ),
        encoding="utf-8",
    )
    required_build = verify_local_bundle_v06(bundle, trust)
    assert required_build["valid"] is False
    assert required_build["failed_stage"] == "provenance"
    assert any(
        "requires external build provenance" in error
        for error in required_build["errors"]
    )



def test_trust_profile_rejects_partial_build_provenance_pin(tmp_path):
    public = tmp_path / "producer.pem"
    public.write_text("placeholder", encoding="utf-8")
    base = {
        "format": "pcs-verifier-trust-v1",
        "public_key": "producer.pem",
        "expected_signer_fingerprint": "a" * 64,
    }

    fingerprint_only = tmp_path / "fingerprint-only.json"
    fingerprint_only.write_text(
        json.dumps({
            **base,
            "expected_build_provenance_fingerprint": "b" * 64,
        }),
        encoding="utf-8",
    )
    with pytest.raises(V06LocalVerifyError, match="requires both"):
        load_trust_profile_v06(fingerprint_only)

    subject_only = tmp_path / "subject-only.json"
    subject_only.write_text(
        json.dumps({
            **base,
            "expected_build_subject_sha256": ["c" * 64],
        }),
        encoding="utf-8",
    )
    with pytest.raises(V06LocalVerifyError, match="requires both"):
        load_trust_profile_v06(subject_only)
