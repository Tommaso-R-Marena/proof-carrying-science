from __future__ import annotations

import base64
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from pcs.byte_contract_v06 import parse_certificate_bytes_v06
from pcs.canonical_json import canonicalize_jcs, canonicalize_jcs_bytes
from pcs.certificate_v06 import finalize_certificate_hashes_v06
from pcs.certificate_semantics_v06 import workflow_summary_v06
from pcs.environment_replay_v06 import environment_binding_v06
from pcs.normalized_set_v06 import (
    INDEX_PATH_V06,
    index_semantic_hash_v06,
)
from pcs.normalized_wire_v06 import wire_semantic_hash_v06
from pcs.package_v06 import build_package_manifest_v06, sign_package_manifest_v06
from pcs.signing_v06 import sign_certificate_v06
from pcs.verifier_v06 import verify_end_to_end_v06


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))
TEST_PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))


def _raw(rel: str) -> bytes:
    return (GOLDEN / rel).read_bytes()


def _public_key() -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(
        base64.b64decode(META["public_key_raw_base64"], validate=True)
    )


def _golden_files() -> dict[str, bytes]:
    return {
        "certificate.json": _raw("certificate.json"),
        "artifacts/fixture.bin": _raw("artifacts/fixture.bin"),
        META["normalized_wire_path"]: _raw(META["normalized_wire_path"]),
        INDEX_PATH_V06: _raw(INDEX_PATH_V06),
    }


def _signed_inputs(
    certificate: dict,
    files: dict[str, bytes],
) -> tuple[bytes, bytes, bytes, bytes]:
    certificate_bytes = canonicalize_jcs_bytes(certificate)
    files = dict(files)
    files["certificate.json"] = certificate_bytes
    inventory = {
        name: {"sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}
        for name, raw in files.items()
    }
    manifest = build_package_manifest_v06(certificate, inventory)
    certificate_signature = sign_certificate_v06(certificate, TEST_PRIVATE_KEY)
    package_signature = sign_package_manifest_v06(manifest, TEST_PRIVATE_KEY)
    return (
        certificate_bytes,
        canonicalize_jcs_bytes(certificate_signature),
        canonicalize_jcs_bytes(manifest),
        canonicalize_jcs_bytes(package_signature),
    )


def _verify(
    *,
    certificate_bytes: bytes,
    certificate_signature_bytes: bytes,
    package_manifest_bytes: bytes,
    package_signature_bytes: bytes,
    files: dict[str, bytes],
):
    return verify_end_to_end_v06(
        certificate_bytes=certificate_bytes,
        certificate_signature_bytes=certificate_signature_bytes,
        package_manifest_bytes=package_manifest_bytes,
        package_signature_bytes=package_signature_bytes,
        package_files=files,
        public_key=_public_key(),
        expected_fingerprint=META["public_key_fingerprint"],
    )


def test_golden_package_passes_single_end_to_end_entry_point():
    result = _verify(
        certificate_bytes=_raw("certificate.json"),
        certificate_signature_bytes=_raw("certificate_signature.json"),
        package_manifest_bytes=_raw("package_manifest.json"),
        package_signature_bytes=_raw("package_signature.json"),
        files=_golden_files(),
    )

    assert result["valid"], result["errors"]
    assert result["failed_stage"] is None
    assert all(result["stages"].values())
    assert result["certificate_semantic_hash"] == META["certificate_semantic_hash"]
    assert result["normalized_index_semantic_hash"] == META[
        "normalized_index_semantic_hash"
    ]
    assert result["claims"] == [
        {
            "claim_id": "C1",
            "kind": "computational",
            "decision": "COMPUTATIONALLY_SUPPORTED",
            "predicate": {
                "type": "reaction_balance",
                "reactants": [
                    {"formula": "H2", "coefficient": 2},
                    {"formula": "O2", "coefficient": 1},
                ],
                "products": [{"formula": "H2O", "coefficient": 2}],
            },
            "normalized_path": META["normalized_wire_path"],
            "wire_semantic_hash": META["normalized_wire_semantic_hash"],
        }
    ]


def test_end_to_end_fails_at_package_binding_before_replay_on_artifact_tamper():
    files = _golden_files()
    files["artifacts/fixture.bin"] = b"tampered artifact\n"

    result = _verify(
        certificate_bytes=_raw("certificate.json"),
        certificate_signature_bytes=_raw("certificate_signature.json"),
        package_manifest_bytes=_raw("package_manifest.json"),
        package_signature_bytes=_raw("package_signature.json"),
        files=files,
    )

    assert not result["valid"]
    assert result["failed_stage"] == "package_binding"
    assert result["stages"] == {
        "canonical_inputs": True,
        "certificate_signature": True,
        "package_binding": False,
        "provenance": False,
        "environment_replay": False,
        "workflow_replay": False,
        "replay": False,
        "normalized_set": False,
    }


def test_fully_rehashed_and_resigned_false_pass_fails_at_replay():
    certificate = parse_certificate_bytes_v06(_raw("certificate.json"))
    forged = deepcopy(certificate)
    false_predicate = {
        "type": "reaction_balance",
        "reactants": [{"formula": "H2", "coefficient": 1}],
        "products": [{"formula": "H2O", "coefficient": 1}],
    }
    forged["claims"][0]["predicate"] = deepcopy(false_predicate)
    forged["evidence"][0]["predicate"] = deepcopy(false_predicate)
    forged["evidence"][0]["check_spec"] = deepcopy(false_predicate)
    # Leave the recorded PASS and COMPUTATIONALLY_SUPPORTED assessment in place.
    # They are structurally consistent but scientifically false for this predicate.
    forged["semantic_hash"] = ""
    forged["integrity_hash"] = ""
    forged = finalize_certificate_hashes_v06(forged)

    files = _golden_files()
    cert_bytes, cert_sig, manifest_bytes, package_sig = _signed_inputs(forged, files)
    files["certificate.json"] = cert_bytes

    result = _verify(
        certificate_bytes=cert_bytes,
        certificate_signature_bytes=cert_sig,
        package_manifest_bytes=manifest_bytes,
        package_signature_bytes=package_sig,
        files=files,
    )

    assert not result["valid"]
    assert result["failed_stage"] == "replay"
    assert result["stages"]["canonical_inputs"]
    assert result["stages"]["certificate_signature"]
    assert result["stages"]["package_binding"]
    assert not result["stages"]["replay"]
    assert any("replay outcome mismatch" in error for error in result["errors"])


def test_resigned_normalized_forgery_fails_at_normalized_set():
    certificate = parse_certificate_bytes_v06(_raw("certificate.json"))
    files = _golden_files()

    wire = json.loads(files[META["normalized_wire_path"]])
    wire["context"][0]["statement"] = "attacker-controlled context"
    wire["wire_semantic_hash"] = wire_semantic_hash_v06(wire)
    files[META["normalized_wire_path"]] = canonicalize_jcs_bytes(wire)

    index = json.loads(files[INDEX_PATH_V06])
    index["entries"][0]["wire_semantic_hash"] = wire["wire_semantic_hash"]
    index["index_semantic_hash"] = index_semantic_hash_v06(index)
    files[INDEX_PATH_V06] = canonicalize_jcs_bytes(index)

    cert_bytes, cert_sig, manifest_bytes, package_sig = _signed_inputs(
        certificate,
        files,
    )
    files["certificate.json"] = cert_bytes

    result = _verify(
        certificate_bytes=cert_bytes,
        certificate_signature_bytes=cert_sig,
        package_manifest_bytes=manifest_bytes,
        package_signature_bytes=package_sig,
        files=files,
    )

    assert not result["valid"]
    assert result["failed_stage"] == "normalized_set"
    assert result["stages"]["canonical_inputs"]
    assert result["stages"]["certificate_signature"]
    assert result["stages"]["package_binding"]
    assert result["stages"]["replay"]
    assert not result["stages"]["normalized_set"]
    assert any("replay-derived bytes" in error for error in result["errors"])


def test_end_to_end_executes_scientific_replay_once(monkeypatch):
    import pcs.verifier_v06 as verifier

    calls = 0
    original = verifier.verify_certificate_replay_v06

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(verifier, "verify_certificate_replay_v06", counted)
    result = _verify(
        certificate_bytes=_raw("certificate.json"),
        certificate_signature_bytes=_raw("certificate_signature.json"),
        package_manifest_bytes=_raw("package_manifest.json"),
        package_signature_bytes=_raw("package_signature.json"),
        files=_golden_files(),
    )

    assert result["valid"], result["errors"]
    assert calls == 1



def test_resigned_false_static_workflow_claim_fails_at_workflow_replay():
    certificate = parse_certificate_bytes_v06(_raw("certificate.json"))
    forged = deepcopy(certificate)

    script = (
        b"import pandas as pd\n"
        b"df = pd.read_csv('input.csv')\n"
        b"df.to_csv('output.csv', index=False)\n"
    )
    input_bytes = b"id,x\n1,1\n"
    output_bytes = b"id,x\n1,1\n"
    added = [
        (
            "wf_source",
            "artifacts/wf_source/payload",
            "pipeline.py",
            "source-code",
            script,
        ),
        (
            "wf_input",
            "artifacts/wf_input/payload",
            "input.csv",
            "tabular-data",
            input_bytes,
        ),
        (
            "wf_output",
            "artifacts/wf_output/payload",
            "output.csv",
            "tabular-output",
            output_bytes,
        ),
    ]
    for ident, path, source_path, role, raw in added:
        forged["artifacts"].append(
            {
                "id": ident,
                "path": path,
                "role": role,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "media_type": "text/plain",
                "source_path": source_path,
            }
        )

    proposition = {
        "inference_format": "pcs-static-workflow-map-v1",
        "inference_id": "W_STATIC_wf_source",
        "static_only": True,
        "user_code_executed": False,
        "human_confirmed": True,
        "confirmation_scope": (
            "Static dependency inference confirmed; this does not prove "
            "source-code correctness or runtime behavior."
        ),
        "source_path": "pipeline.py",
        "source_kind": "python",
        "analysis_mode": "python_ast",
        "dependency_claim_mode": "exact_resolved_set",
        "confidence": 0.98,
        "imports": ["pandas"],
        "resolved_references": [],
        "references_truncated": True,
    }
    forged["workflow"]["nodes"].append(
        {
            "id": "N_STATIC_wf_source",
            "operation": "static_python_workflow",
            "inputs": ["wf_input", "wf_source"],
            # False edge: the source actually writes wf_output, not wf_input.
            "outputs": ["wf_input"],
            "contract": {
                "type": "external",
                "namespace": "pcs-manifest-workflow-contract-v1",
                "proposition": canonicalize_jcs(proposition),
            },
        }
    )
    forged["workflow_summary"] = workflow_summary_v06(
        forged["workflow"],
        {artifact["id"] for artifact in forged["artifacts"]},
    )
    forged["semantic_hash"] = ""
    forged["integrity_hash"] = ""
    forged = finalize_certificate_hashes_v06(forged)

    files = _golden_files()
    files["artifacts/wf_source/payload"] = script
    files["artifacts/wf_input/payload"] = input_bytes
    files["artifacts/wf_output/payload"] = output_bytes

    cert_bytes, cert_sig, manifest_bytes, package_sig = _signed_inputs(
        forged,
        files,
    )
    files["certificate.json"] = cert_bytes

    result = _verify(
        certificate_bytes=cert_bytes,
        certificate_signature_bytes=cert_sig,
        package_manifest_bytes=manifest_bytes,
        package_signature_bytes=package_sig,
        files=files,
    )

    assert result["valid"] is False
    assert result["failed_stage"] == "workflow_replay"
    assert result["stages"]["canonical_inputs"] is True
    assert result["stages"]["certificate_signature"] is True
    assert result["stages"]["package_binding"] is True
    assert result["stages"]["workflow_replay"] is False
    assert result["stages"]["replay"] is False
    assert any("output set differs" in error for error in result["errors"])



def test_resigned_false_environment_claim_fails_at_environment_replay():
    certificate = parse_certificate_bytes_v06(_raw("certificate.json"))
    forged = deepcopy(certificate)

    requirements = b"numpy==1.26.4 --hash=sha256:" + (b"a" * 64) + b"\n"
    env_artifact = {
        "id": "env_requirements",
        "path": "artifacts/env_requirements/payload",
        "role": "environment-specification",
        "sha256": hashlib.sha256(requirements).hexdigest(),
        "media_type": "text/plain",
        "source_path": "requirements.txt",
    }
    forged["artifacts"].append(env_artifact)

    false_environment = {
        "format": "pcs-environment-capture-v1",
        "static_only": True,
        "network_accessed": False,
        "user_code_executed": False,
        "source_artifact_ids": ["env_requirements"],
        "sources": [
            {
                "artifact_id": "env_requirements",
                "path": "requirements.txt",
                "kind": "requirements",
                "sha256": hashlib.sha256(requirements).hexdigest(),
                "size": len(requirements),
            }
        ],
        "python": {
            "interpreter_constraints": [],
            "dependencies": [
                {
                    "ecosystem": "python",
                    "name": "numpy",
                    "raw": "numpy==9.9.9",
                    "source_path": "requirements.txt",
                    "source_kind": "requirements",
                    "exact_pin": True,
                    "hash_pinned": True,
                    "version": "9.9.9",
                }
            ],
        },
        "r": {"interpreter_constraints": [], "dependencies": []},
        "conda": {"dependencies": []},
        "containers": [],
        "hermeticity": "hash_pinned_dependencies",
        "replay_plan": {
            "format": "pcs-environment-replay-plan-v1",
            "hermeticity": "hash_pinned_dependencies",
            "required_tools": ["python"],
            "steps": [
                {
                    "kind": "pip_install",
                    "source_path": "requirements.txt",
                    "command_template": (
                        "python -m pip install --require-hashes -r requirements.txt"
                    ),
                    "network_required": True,
                    "executes_project_build_instructions": True,
                }
            ],
            "automatic_execution_permitted_by_pcs": False,
            "reason": "forged but correctly signed environment claim",
        },
        "unresolved": [],
        "summary": {
            "source_files": 1,
            "dependency_records": 1,
            "python_dependency_records": 1,
            "r_dependency_records": 0,
            "conda_dependency_records": 0,
            "container_specs": 0,
            "unresolved_items": 0,
        },
        "semantic_sha256": "0" * 64,
        "human_confirmed": True,
        "confirmation_scope": "reviewed",
    }
    forged["environment"] = environment_binding_v06(false_environment)
    forged["semantic_hash"] = ""
    forged["integrity_hash"] = ""
    forged = finalize_certificate_hashes_v06(forged)

    files = _golden_files()
    files["artifacts/env_requirements/payload"] = requirements
    cert_bytes, cert_sig, manifest_bytes, package_sig = _signed_inputs(
        forged,
        files,
    )
    files["certificate.json"] = cert_bytes

    result = _verify(
        certificate_bytes=cert_bytes,
        certificate_signature_bytes=cert_sig,
        package_manifest_bytes=manifest_bytes,
        package_signature_bytes=package_sig,
        files=files,
    )

    assert result["valid"] is False
    assert result["failed_stage"] == "environment_replay"
    assert result["stages"]["canonical_inputs"] is True
    assert result["stages"]["certificate_signature"] is True
    assert result["stages"]["package_binding"] is True
    assert result["stages"]["environment_replay"] is False
    assert result["stages"]["workflow_replay"] is False
    assert result["stages"]["replay"] is False
    assert any("fresh capture" in error for error in result["errors"])
