from pcs_next_v1.trust.policy import pin_policy
from pcs_next_v1.trust.signed_receipt import (
    detect_signature_faults,
    mint_demo_signer,
    sign_package_hashes,
    verify_signed_package,
)


def _policy_with_pin(fp: str):
    raw = {
        "format": "pcs-next-acceptance-policy-v1",
        "policy_id": "t",
        "policy_version": "1.0.0",
        "protocol_version": "pcs-next-v1",
        "required_checks": ["hash_integrity"],
        "allowed_claim_statuses": ["COMPUTATIONALLY_TESTED"],
        "max_artifact_bytes": 1000,
        "fail_closed_unknown_versions": True,
        "pinned_signer_fingerprints": [fp],
    }
    return pin_policy(raw)


def test_sign_and_verify():
    s = mint_demo_signer()
    pol = _policy_with_pin(s["fingerprint"])
    sig = sign_package_hashes(lock_hash="aa", bundle_hash="bb", private_der=s["private_der"])
    assert verify_signed_package(lock_hash="aa", bundle_hash="bb", public_der=s["public_der"], signature=sig, policy=pol)["ok"]
    assert detect_signature_faults(lock_hash="aa", bundle_hash="bb", public_der=s["public_der"], signature=bytes([sig[0] ^ 1]) + sig[1:], policy=pol) == "signature_invalid"
    other = mint_demo_signer()
    assert detect_signature_faults(lock_hash="aa", bundle_hash="bb", public_der=other["public_der"], signature=sig, policy=pol) == "signer_not_pinned"
