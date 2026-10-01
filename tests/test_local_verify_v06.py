from __future__ import annotations

import json

from pcs.local_verify_v06 import verify_local_bundle_v06
from scripts.run_golden_examples_v06 import build_golden_examples


def test_trust_profile_reduces_bundle_verification_to_one_call(tmp_path):
    report = build_golden_examples(tmp_path / "golden")
    case = next(c for c in report["cases"] if c["name"] == "pkpd-supported")
    project = tmp_path / "golden" / "pkpd-supported"
    public = project / "demo-public.pem"
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
