from __future__ import annotations

from copy import deepcopy

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.semantic_confirmation_v1 import (RECEIPT_FORMAT, signing_payload,
                                           check_translation_with_confirmation)
from pcs.semantic_translation_v1 import interpretation_digest, sha256
from tests.test_semantic_translation_v1 import fixture


FIXED_NOW = 1_900_000_000


def payload():
    registry, human, candidate = fixture()
    signer = Ed25519PrivateKey.generate()
    keyhex = signer.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw).hex()
    unsigned = {
        "format": RECEIPT_FORMAT, "claim_id": human["claim_id"],
        "interpretation_sha256": interpretation_digest(human),
        "registry_sha256": sha256(registry), "claim_ir_sha256": None,
        "approver": "PCS-reviewer-test", "issued_at": FIXED_NOW-100,
        "expires_at": FIXED_NOW+100, "nonce": "0123456789abcdef0123456789abcdef",
    }
    receipt = dict(unsigned, signature_hex=signer.sign(signing_payload(unsigned)).hex())
    return registry, human, candidate, signer, keyhex, receipt


def check(modify=None, *, signer_key=None, now=FIXED_NOW):
    registry, human, candidate, signer, keyhex, receipt = payload()
    if modify:
        modify(registry, human, candidate, receipt)
    return check_translation_with_confirmation(registry, human, candidate,
        approved_registry_sha256=sha256(registry), confirmation_receipt=receipt,
        approved_signer_public_key_hex=signer_key or keyhex, now_epoch=now)


def test_genuine_signed_receipt_is_authentication_not_lean_authority():
    out = check()
    assert out["decision"] == "STRUCTURALLY_CONFORMANT_NONAUTHORITATIVE"
    assert out["confirmation_authenticated"] is True
    assert len(out["confirmation_receipt_sha256"]) == 64
    assert out["authoritative"] is False
    assert "PROOF_NOT_VERIFIED" in out["unverified_authority_bridges"]


@pytest.mark.parametrize("tamper", [
    lambda r,h,c,x: x.__setitem__("approver", "imposter"),
    lambda r,h,c,x: x.__setitem__("nonce", "0"*32),
    lambda r,h,c,x: x.__setitem__("interpretation_sha256", "0"*64),
    lambda r,h,c,x: x.__setitem__("registry_sha256", "f"*64),
    lambda r,h,c,x: x.__setitem__("claim_id", "C_WRONG"),
    lambda r,h,c,x: x.__setitem__("signature_hex", "0"*128),
    lambda r,h,c,x: x.__setitem__("issued_at", FIXED_NOW-99),
    lambda r,h,c,x: x.__setitem__("claim_ir_sha256", "f"*64),
])
def test_any_unapproved_signed_receipt_mutation_fails_closed(tamper):
    out = check(tamper)
    assert out["decision"] == "REJECTED"
    assert out["confirmation_authenticated"] is False
    assert out["authoritative"] is False
    assert any(z["code"].startswith("CONFIRMATION_") for z in out["diagnostics"])


def test_wrong_approved_signer_key_rejected():
    other = Ed25519PrivateKey.generate()
    key = other.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw).hex()
    out = check(signer_key=key)
    assert "CONFIRMATION_SIGNATURE_INVALID" in {z["code"] for z in out["diagnostics"]}
    assert out["decision"] == "REJECTED"


@pytest.mark.parametrize("now", [FIXED_NOW-500, FIXED_NOW+500])
def test_expired_or_not_yet_valid_receipts_reject(now):
    out = check(now=now)
    assert out["decision"] == "REJECTED"
    assert "CONFIRMATION_RECEIPT_EXPIRED" in {z["code"] for z in out["diagnostics"]}


def test_changed_interpretation_invalidates_signed_receipt():
    out = check(lambda r,h,c,x: h.__setitem__("statement", "A different request"))
    assert out["decision"] == "REJECTED"
    assert out["confirmation_authenticated"] is False


def test_signed_approval_does_not_override_semantic_rejection():
    out = check(lambda r,h,c,x: c["formula"].__setitem__("op", "exists"))
    assert out["confirmation_authenticated"] is True
    assert out["decision"] == "REJECTED"
    assert out["authoritative"] is False
    assert "QUANTIFIER_MISMATCH" in {z["code"] for z in out["diagnostics"]}


def test_malformed_receipt_fails_closed_and_never_promotes_untrusted_signer():
    out = check(lambda r,h,c,x: x.__setitem__("signature_hex", []))
    assert out["decision"] == "REJECTED"
    assert not out["confirmation_authenticated"]


def test_signed_confirmation_standalone_cli(tmp_path):
    import json
    import time
    from scripts.run_semantic_translation_v1 import main
    reg, human, cand, signer, public_key, receipt = payload()
    now = int(time.time())
    receipt["issued_at"] = now - 30
    receipt["expires_at"] = now + 30
    receipt["signature_hex"] = signer.sign(signing_payload({k: v for k, v in receipt.items() if k != "signature_hex"})).hex()
    paths = {}
    for name, value in [("registry",reg),("interpretation",human),("candidate",cand),("confirmation-receipt",receipt)]:
        p = tmp_path / (name + ".json")
        p.write_text(json.dumps(value))
        paths[name] = p
    output = tmp_path / "decision.json"
    args = ["--registry",str(paths["registry"]),"--interpretation",str(paths["interpretation"]),
            "--candidate",str(paths["candidate"]),"--approved-registry-sha256",sha256(reg),
            "--confirmation-receipt",str(paths["confirmation-receipt"]),
            "--approved-confirmation-public-key-hex",public_key,"--output",str(output)]
    assert main(args) == 0
    saved = json.loads(output.read_text())
    assert saved["confirmation_authenticated"] is True
    assert saved["authoritative"] is False
    receipt["nonce"] = "0"*32
    paths["confirmation-receipt"].write_text(json.dumps(receipt))
    assert main(args) == 1
    assert json.loads(output.read_text())["confirmation_authenticated"] is False
