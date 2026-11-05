from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.attest_v06 import V06AttestationError, build_attestation_directory_v06
from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.external_validator_v06 import (
    EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06,
    EXTERNAL_VALIDATOR_TRUST_MODEL_V06,
    EXTERNAL_VALIDATOR_TRUST_POLICY_FORMAT_V06,
    build_external_validator_receipt_payload_v06,
    sign_external_validator_receipt_v06,
)
from pcs.formal_coverage_v06 import classify_formal_coverage_v06
from pcs.jsonio import strict_json_load
from pcs.signing import generate_keypair, public_key_fingerprint


@pytest.mark.skipif(shutil.which("lake") is None, reason="Lean/Lake unavailable")
def test_signed_external_empirical_receipt_reaches_authoritative_package_without_becoming_lean_checker(
    tmp_path: Path,
):
    project = tmp_path / "project"
    project.mkdir()
    data = b"time,value\n0,1\n1,2\n"
    policy = b'{"format":"fixture-policy-v1","max_error":"0.5"}\n'
    (project / "data.csv").write_bytes(data)
    (project / "policy.json").write_bytes(policy)

    validator_private = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    validator_public = validator_private.public_key()
    validator_der = validator_public.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    (project / "validator_public_key.der").write_bytes(validator_der)

    predicate = {
        "type": "external",
        "namespace": "pcs-test-empirical-validator/v1",
        "proposition": (
            "The bound synthetic dataset passes the exact bound fixture policy."
        ),
    }
    bound = {
        "A_DATA": data,
        "A_POLICY": policy,
    }
    payload = build_external_validator_receipt_payload_v06(
        check_type="external_empirical_validation",
        validator="fixture-empirical-validator/1",
        predicate=predicate,
        bound_artifact_ids=list(bound),
        artifact_bytes=bound,
        outcome="PASS",
    )
    receipt = sign_external_validator_receipt_v06(
        payload,
        validator_private,
    )
    (project / "validator_receipt.json").write_bytes(
        canonicalize_jcs_bytes(receipt)
    )

    validator_fingerprint = public_key_fingerprint(validator_public)
    trust_policy = {
        "format": EXTERNAL_VALIDATOR_TRUST_POLICY_FORMAT_V06,
        "validator": "fixture-empirical-validator/1",
        "validator_public_key_fingerprint": validator_fingerprint,
        "allowed_check_types": ["external_empirical_validation"],
        "allowed_predicate_namespaces": [predicate["namespace"]],
    }
    trust_policy_bytes = canonicalize_jcs_bytes(trust_policy)
    (project / "validator_trust_policy.json").write_bytes(trust_policy_bytes)

    # Re-sign with the project trust policy itself included in the validator-bound
    # bytes. The private validator key is never packaged.
    bound_with_trust = {
        **bound,
        "A_TRUST": trust_policy_bytes,
    }
    payload = build_external_validator_receipt_payload_v06(
        check_type="external_empirical_validation",
        validator="fixture-empirical-validator/1",
        predicate=predicate,
        bound_artifact_ids=list(bound_with_trust),
        artifact_bytes=bound_with_trust,
        outcome="PASS",
    )
    receipt = sign_external_validator_receipt_v06(
        payload,
        validator_private,
    )
    (project / "validator_receipt.json").write_bytes(
        canonicalize_jcs_bytes(receipt)
    )

    manifest = {
        "subject": "signed-external-validator-integration",
        "assumptions": [],
        "claims": [
            {
                "id": "C_EMPIRICAL",
                "statement": (
                    "The synthetic dataset passes the prespecified fixture policy."
                ),
                "kind": "empirical",
                "required_evidence": ["E_EMPIRICAL"],
                "assumptions": [],
                "predicate": predicate,
            }
        ],
        "artifacts": [
            {
                "id": "A_DATA",
                "path": "data.csv",
                "role": "synthetic-observations",
                "media_type": "text/csv",
            },
            {
                "id": "A_POLICY",
                "path": "policy.json",
                "role": "validation-policy",
                "media_type": "application/json",
            },
            {
                "id": "A_RECEIPT",
                "path": "validator_receipt.json",
                "role": "signed-external-validator-receipt",
                "media_type": "application/json",
            },
            {
                "id": "A_KEY",
                "path": "validator_public_key.der",
                "role": "external-validator-public-key",
                "media_type": "application/octet-stream",
            },
            {
                "id": "A_TRUST",
                "path": "validator_trust_policy.json",
                "role": "external-validator-trust-policy",
                "media_type": "application/json",
            },
        ],
        "checks": [
            {
                "id": "E_EMPIRICAL",
                "type": "external_empirical_validation",
                "claim_ids": ["C_EMPIRICAL"],
                "validator": "fixture-empirical-validator/1",
                "predicate": predicate,
                "receipt_format": EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06,
                "trust_model": EXTERNAL_VALIDATOR_TRUST_MODEL_V06,
                "receipt_artifact": "A_RECEIPT",
                "validator_public_key_artifact": "A_KEY",
                "validator_public_key_fingerprint": validator_fingerprint,
                "validator_trust_policy_artifact": "A_TRUST",
                "bound_artifact_ids": ["A_DATA", "A_POLICY", "A_TRUST"],
            }
        ],
        "workflow": {"nodes": []},
    }
    manifest_path = project / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    pcs_private = tmp_path / "pcs-private.pem"
    pcs_public = tmp_path / "pcs-public.pem"
    generate_keypair(pcs_private, pcs_public)

    package = tmp_path / "package"
    with pytest.raises(V06AttestationError, match="lean_authority"):
        build_attestation_directory_v06(
            manifest_path,
            package,
            pcs_private,
            pcs_public,
            generated_at="2026-10-04T00:00:00+00:00",
        )

    # External validator receipts remain parseable evidence for non-kernel review,
    # but a PASS from a checker outside the certified Lean registry must not produce
    # a Lean-authoritative package acceptance.
    certificate = strict_json_load(package / "certificate.json")
    evidence = certificate["evidence"][0]
    assert evidence["outcome"] == "PASS"
    assert evidence["kind"] == "empirical_validation"
    assert evidence["checker"] == "fixture-empirical-validator/1"

    coverage = classify_formal_coverage_v06(
        certificate,
        package_authoritative=False,
        lean_authority={"accepted": False, "verdict": "REJECT"},
    )
    row = coverage["evidence"][0]
    assert coverage["package_authority"] != "LEAN_AUTHORITATIVE_ACCEPT"
    assert row["checker_semantics"] == "NOT_IN_CERTIFIED_BUILTIN_SET"
    assert row["execution_authority"] == "OUTSIDE_CERTIFIED_BUILTIN_SET"
    assert row["external_validator_contract"]["semantic_authority"] == (
        "EXTERNAL_VALIDATOR_TRUST_REQUIRED"
    )
    assert row["external_validator_contract"]["lean_scientific_semantics"] == (
        "NOT_PROVED_BY_PCS_LEAN_CHECKER"
    )
