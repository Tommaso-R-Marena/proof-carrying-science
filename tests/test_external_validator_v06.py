from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.crypto_domains_v06 import CERTIFICATE_SIGNATURE_DOMAIN
from pcs.external_validator_v06 import (
    EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06,
    EXTERNAL_VALIDATOR_TRUST_MODEL_V06,
    EXTERNAL_VALIDATOR_TRUST_POLICY_FORMAT_V06,
    V06ExternalValidatorError,
    build_external_validator_receipt_payload_v06,
    external_validator_artifact_ids_v06,
    normalize_external_validator_check_spec_v06,
    sign_external_validator_receipt_v06,
    verify_external_validator_receipt_v06,
)
from pcs.formal_coverage_v06 import classify_formal_coverage_v06
from pcs.reference_validators.pkpd_rmse_v06 import (
    evaluate_pkpd_rmse_policy_v06,
)
from pcs.replay_v06 import replay_evidence_item_v06
from pcs.signing import public_key_fingerprint
from pcs.signing_v06 import sign_jcs_payload


PREDICATE = {
    "type": "external",
    "namespace": "pcs-test-validator/v1",
    "proposition": "The bound synthetic data satisfy the bound test policy.",
}


def _key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes(range(32)))


def _fixture() -> tuple[dict, dict[str, bytes], dict]:
    key = _key()
    public = key.public_key()
    public_der = public.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    fingerprint = public_key_fingerprint(public)
    trust_policy = canonicalize_jcs_bytes(
        {
            "format": EXTERNAL_VALIDATOR_TRUST_POLICY_FORMAT_V06,
            "validator": "fixture-validator/1",
            "validator_public_key_fingerprint": fingerprint,
            "allowed_check_types": ["external_empirical_validation"],
            "allowed_predicate_namespaces": [PREDICATE["namespace"]],
        }
    )
    bound = {
        "A_MODEL": b'{"model":"fixture"}\n',
        "A_DATA": b"time,value\n0,1\n1,2\n",
        "A_POLICY": b'{"threshold":"fixture"}\n',
        "A_TRUST": trust_policy,
    }
    payload = build_external_validator_receipt_payload_v06(
        check_type="external_empirical_validation",
        validator="fixture-validator/1",
        predicate=PREDICATE,
        bound_artifact_ids=list(bound),
        artifact_bytes=bound,
        outcome="PASS",
    )
    receipt = sign_external_validator_receipt_v06(payload, key)
    spec = {
        "type": "external_empirical_validation",
        "validator": "fixture-validator/1",
        "predicate": PREDICATE,
        "receipt_format": EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06,
        "trust_model": EXTERNAL_VALIDATOR_TRUST_MODEL_V06,
        "receipt_artifact": "A_RECEIPT",
        "validator_public_key_artifact": "A_KEY",
        "validator_public_key_fingerprint": fingerprint,
        "validator_trust_policy_artifact": "A_TRUST",
        "bound_artifact_ids": sorted(bound),
    }
    all_bytes = {
        **bound,
        "A_RECEIPT": canonicalize_jcs_bytes(receipt),
        "A_KEY": public_der,
    }
    return spec, all_bytes, receipt


def test_signed_external_validator_receipt_binds_identity_predicate_and_bytes():
    spec, artifact_bytes, _ = _fixture()

    checked = verify_external_validator_receipt_v06(
        spec,
        artifact_bytes,
    )

    assert checked["valid"] is True
    assert checked["outcome"] == "PASS"
    assert checked["kind"] == "empirical_validation"
    assert checked["semantic_authority"] == "EXTERNAL_VALIDATOR_TRUST_REQUIRED"
    assert checked["trust_contract"]["pcs_does_not_verify"] == [
        "validator_algorithm_correctness",
        "validator_policy_scientific_adequacy",
        "biological_or_clinical_truth",
    ]


def test_signed_validator_receipt_rejects_proposer_selected_untrusted_key():
    spec, artifact_bytes, _ = _fixture()
    forged_key = Ed25519PrivateKey.generate().public_key()
    forged_der = forged_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    artifact_bytes["A_KEY"] = forged_der
    spec["validator_public_key_fingerprint"] = public_key_fingerprint(forged_key)

    checked = verify_external_validator_receipt_v06(
        spec,
        artifact_bytes,
    )

    assert checked["valid"] is False
    assert any("trust policy" in error for error in checked["errors"])


def test_signed_validator_receipt_fails_closed_if_bound_data_changes():
    spec, artifact_bytes, _ = _fixture()
    artifact_bytes["A_DATA"] = b"time,value\n0,1\n1,999\n"

    checked = verify_external_validator_receipt_v06(
        spec,
        artifact_bytes,
    )

    assert checked["valid"] is False
    assert checked["outcome"] == "FAIL"
    assert any("artifact bindings" in error for error in checked["errors"])


def test_validator_receipt_signature_domain_cannot_be_substituted():
    spec, artifact_bytes, receipt = _fixture()
    payload = receipt["payload"]["payload"]
    wrong_domain = sign_jcs_payload(
        CERTIFICATE_SIGNATURE_DOMAIN,
        payload,
        _key(),
    )
    artifact_bytes["A_RECEIPT"] = canonicalize_jcs_bytes(wrong_domain)

    checked = verify_external_validator_receipt_v06(
        spec,
        artifact_bytes,
    )

    assert checked["valid"] is False
    assert any("signature" in error.lower() for error in checked["errors"])


def test_external_validator_check_rejects_authority_smuggling():
    spec, _, _ = _fixture()
    spec["outcome"] = "PASS"

    with pytest.raises(
        V06ExternalValidatorError,
        match="forbidden fields",
    ):
        normalize_external_validator_check_spec_v06(spec)


def test_replay_accepts_signed_receipt_but_formal_coverage_stays_external(
    tmp_path: Path,
):
    spec, artifact_bytes, _ = _fixture()
    paths: dict[str, Path] = {}
    for artifact_id, raw in artifact_bytes.items():
        path = tmp_path / artifact_id
        path.write_bytes(raw)
        paths[artifact_id] = path

    evidence = {
        "id": "E_EXTERNAL",
        "kind": "empirical_validation",
        "claim_ids": ["C_EXTERNAL"],
        "outcome": "UNVERIFIED",
        "checker": spec["validator"],
        "predicate": PREDICATE,
        "artifact_ids": external_validator_artifact_ids_v06(spec),
        "check_spec": spec,
    }
    replayed = replay_evidence_item_v06(evidence, paths)

    assert replayed["outcome"] == "PASS"
    assert replayed["kind"] == "empirical_validation"
    assert replayed["details"]["semantic_authority"] == (
        "EXTERNAL_VALIDATOR_TRUST_REQUIRED"
    )

    certificate = {"evidence": [evidence]}
    coverage = classify_formal_coverage_v06(
        certificate,
        package_authoritative=True,
        lean_authority={"accepted": True},
    )
    row = coverage["evidence"][0]
    assert coverage["signed_external_validator_evidence"] == 1
    assert row["checker_semantics"] == "NOT_IN_CERTIFIED_BUILTIN_SET"
    assert row["execution_authority"] == "OUTSIDE_CERTIFIED_BUILTIN_SET"
    assert row["external_validator_contract"]["lean_scientific_semantics"] == (
        "NOT_PROVED_BY_PCS_LEAN_CHECKER"
    )


def test_replay_fails_if_receipt_bound_artifact_is_tampered(tmp_path: Path):
    spec, artifact_bytes, _ = _fixture()
    artifact_bytes["A_DATA"] = b"time,value\n0,1\n1,999\n"
    paths: dict[str, Path] = {}
    for artifact_id, raw in artifact_bytes.items():
        path = tmp_path / artifact_id
        path.write_bytes(raw)
        paths[artifact_id] = path

    evidence = {
        "id": "E_EXTERNAL",
        "kind": "empirical_validation",
        "claim_ids": ["C_EXTERNAL"],
        "outcome": "PASS",
        "checker": spec["validator"],
        "predicate": PREDICATE,
        "artifact_ids": external_validator_artifact_ids_v06(spec),
        "check_spec": spec,
    }
    replayed = replay_evidence_item_v06(evidence, paths)

    assert replayed["outcome"] == "FAIL"
    assert replayed["details"]["semantic_authority"] == (
        "EXTERNAL_VALIDATOR_TRUST_REQUIRED"
    )


def test_reference_pkpd_rmse_validator_obeys_prespecified_thresholds():
    predictions = (
        b"time,concentration,effect\n"
        b"0,10,80\n"
        b"1,9,75\n"
    )
    observations = (
        b"time,concentration,effect\n"
        b"0,10.1,80.5\n"
        b"1,8.9,74.5\n"
    )
    passing_policy = json.dumps(
        {
            "format": "pcs-pkpd-rmse-policy-v1",
            "time_column": "time",
            "concentration_column": "concentration",
            "effect_column": "effect",
            "concentration_rmse_max": "0.2",
            "effect_rmse_max": "0.6",
            "require_exact_time_alignment": True,
        },
        sort_keys=True,
    ).encode()
    failing_policy = passing_policy.replace(b'"0.6"', b'"0.4"')

    passed = evaluate_pkpd_rmse_policy_v06(
        predictions_bytes=predictions,
        observations_bytes=observations,
        policy_bytes=passing_policy,
    )
    failed = evaluate_pkpd_rmse_policy_v06(
        predictions_bytes=predictions,
        observations_bytes=observations,
        policy_bytes=failing_policy,
    )

    assert passed["outcome"] == "PASS"
    assert failed["outcome"] == "FAIL"
