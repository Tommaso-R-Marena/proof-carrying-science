from __future__ import annotations

import hashlib
import re
import shutil
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .bundle_v06 import V06BundleBuildError, create_verified_bundle_v06
from .canonical_json import JCS_PROFILE, canonicalize_jcs, canonicalize_jcs_bytes
from .certificate_semantics_v06 import (
    V06CertificateSemanticsError,
    artifact_ids_from_predicate,
    workflow_summary_v06,
)
from .certificate_v06 import (
    CHECKER_VERSION_V06,
    SPEC_VERSION_V06,
    V06CertificateError,
    finalize_certificate_hashes_v06,
    write_certificate_v06,
)
from .crypto_domains_v06 import (
    CERTIFICATE_INTEGRITY_DOMAIN,
    CERTIFICATE_SEMANTIC_DOMAIN,
)
from .decision import assess_claim
from .jsonio import StrictJSONError, strict_json_load
from .normalized_set_v06 import V06NormalizedSetError, build_normalized_set_v06
from .package_v06 import (
    MAX_PACKAGE_SINGLE_FILE_V06,
    MAX_PACKAGE_TOTAL_BYTES_V06,
    V06PackageError,
    build_package_manifest_v06,
    sign_package_manifest_v06,
)
from .replay_v06 import replay_evidence_item_v06
from .schema_validation import SchemaValidationError, validate_manifest_shape
from .signing import public_key_fingerprint
from .signing_v06 import V06SignatureError, sign_certificate_v06
from .verifier_io_v06 import (
    V06VerifierIOError,
    load_public_key_v06,
    verify_package_directory_end_to_end_v06,
)
from .environment_replay_v06 import (
    V06EnvironmentReplayError,
    environment_binding_v06,
)


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SUPPORTED_CHECK_TYPES = {
    "csv_disjoint",
    "reaction_balance",
    "unit_compatible",
    "pkpd_contract",
    "pkpd_reference_match",
}


class V06AttestationError(ValueError):
    pass


def _load_private_key_v06(path: str | Path) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(
            Path(path).read_bytes(),
            password=None,
        )
    except (OSError, ValueError, TypeError) as exc:
        raise V06AttestationError(
            f"cannot load Ed25519 private key: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise V06AttestationError("private key is not Ed25519")
    return key


def _id_map(items: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        ident = item.get("id")
        if not isinstance(ident, str) or not _SAFE_ID.fullmatch(ident):
            raise V06AttestationError(f"unsafe or missing {label} id: {ident!r}")
        if ident in out:
            raise V06AttestationError(f"duplicate {label} id: {ident}")
        out[ident] = item
    return out


def _safe_source_file(root: Path, relative: str, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise V06AttestationError(f"{label} path must be a non-empty string")
    root = root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise V06AttestationError(
            f"{label} escapes manifest directory: {relative!r}"
        ) from exc
    if not candidate.is_file():
        raise V06AttestationError(f"{label} is not a regular file: {relative!r}")
    if (root / relative).is_symlink():
        raise V06AttestationError(f"{label} must not be a symlink: {relative!r}")
    return candidate


def _check_spec_from_manifest(check: dict[str, Any]) -> dict[str, Any]:
    check_type = check.get("type")
    if check_type not in _SUPPORTED_CHECK_TYPES:
        raise V06AttestationError(
            f"attest-v06 does not yet produce external evidence type {check_type!r}; "
            f"supported built-in checks are {sorted(_SUPPORTED_CHECK_TYPES)}"
        )

    if check_type == "csv_disjoint":
        return {
            "type": check_type,
            "left_artifact": check["left_artifact"],
            "right_artifact": check["right_artifact"],
            "key": check["key"],
        }
    if check_type == "reaction_balance":
        return {
            "type": check_type,
            "reactants": deepcopy(check["reactants"]),
            "products": deepcopy(check["products"]),
        }
    if check_type == "unit_compatible":
        return {
            "type": check_type,
            "left_unit": check["left_unit"],
            "right_unit": check["right_unit"],
        }
    if check_type == "pkpd_contract":
        return {
            "type": check_type,
            "model_artifact": check["model_artifact"],
        }
    return {
        "type": check_type,
        "model_artifact": check["model_artifact"],
        "output_artifact": check["output_artifact"],
        "time_column": check.get("time_column", "time"),
        "concentration_column": check.get("concentration_column", "concentration"),
        "effect_column": check.get("effect_column", "effect"),
        "rel_tol": check.get("rel_tol", 1e-9),
        "abs_tol": check.get("abs_tol", 1e-12),
    }


def _workflow_contract_v06(value: Any) -> dict[str, Any]:
    if value is None:
        return {"type": "none"}
    if value == {"type": "none"}:
        return {"type": "none"}
    if (
        isinstance(value, dict)
        and value.get("type") == "external"
        and set(value) == {"type", "namespace", "proposition"}
    ):
        return deepcopy(value)

    try:
        proposition = canonicalize_jcs(value)
    except Exception as exc:
        raise V06AttestationError(
            f"workflow contract cannot be represented canonically: {exc}"
        ) from exc
    if len(proposition) > 16384:
        raise V06AttestationError("workflow contract exceeds v0.6 proposition limit")
    return {
        "type": "external",
        "namespace": "pcs-manifest-workflow-contract-v1",
        "proposition": proposition,
    }


def _normalize_workflow_v06(workflow: dict[str, Any]) -> dict[str, Any]:
    nodes = workflow.get("nodes", [])
    if not isinstance(nodes, list):
        raise V06AttestationError("workflow.nodes must be an array")
    out: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            raise V06AttestationError("workflow nodes must be objects")
        out.append(
            {
                "id": node.get("id"),
                "operation": node.get("operation"),
                "inputs": list(node.get("inputs", [])),
                "outputs": list(node.get("outputs", [])),
                "contract": _workflow_contract_v06(node.get("contract")),
            }
        )
    return {"nodes": out}


def _package_artifacts_v06(
    manifest_artifacts: list[dict[str, Any]],
    *,
    source_root: Path,
    package_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Path], dict[str, bytes]]:
    _id_map(manifest_artifacts, "artifact")
    packaged: list[dict[str, Any]] = []
    paths: dict[str, Path] = {}
    bytes_by_path: dict[str, bytes] = {}
    storage_keys: dict[str, str] = {}
    total = 0

    for artifact in manifest_artifacts:
        artifact_id = artifact["id"]
        source_rel = artifact.get("path")
        source = _safe_source_file(
            source_root,
            source_rel,
            label=f"artifact {artifact_id}",
        )
        size = source.stat().st_size
        if size > MAX_PACKAGE_SINGLE_FILE_V06:
            raise V06AttestationError(
                f"artifact {artifact_id} exceeds v0.6 byte limit"
            )
        total += size
        if total > MAX_PACKAGE_TOTAL_BYTES_V06:
            raise V06AttestationError("source artifacts exceed v0.6 total byte limit")

        raw = source.read_bytes()
        if len(raw) != size:
            raise V06AttestationError(
                f"artifact {artifact_id} changed while being read"
            )

        metadata = artifact.get("metadata")
        if isinstance(metadata, dict):
            expected_hash = metadata.get("pcs_discovery_sha256")
            expected_size = metadata.get("pcs_discovery_size")
            if expected_hash is not None or expected_size is not None:
                actual_hash = hashlib.sha256(raw).hexdigest()
                if not isinstance(expected_hash, str) or not isinstance(expected_size, int):
                    raise V06AttestationError(
                        f"artifact {artifact_id} has incomplete PCS discovery snapshot metadata"
                    )
                if actual_hash != expected_hash or len(raw) != expected_size:
                    raise V06AttestationError(
                        f"artifact {artifact_id} changed after PCS discovery/confirmation"
                    )

        storage_key = hashlib.sha256(artifact_id.encode("utf-8")).hexdigest()[:24]
        other = storage_keys.get(storage_key)
        if other is not None and other != artifact_id:
            raise V06AttestationError(
                f"artifact storage-key collision: {other!r} vs {artifact_id!r}"
            )
        storage_keys[storage_key] = artifact_id

        rel = f"artifacts/{storage_key}/payload"
        target = package_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

        packaged_artifact: dict[str, Any] = {
            "id": artifact_id,
            "path": rel,
            "role": artifact.get("role"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "media_type": artifact.get("media_type", "application/octet-stream"),
            "source_path": source_rel,
            "storage_key": storage_key,
        }
        if "metadata" in artifact:
            packaged_artifact["metadata"] = deepcopy(artifact["metadata"])

        packaged.append(packaged_artifact)
        paths[artifact_id] = target
        bytes_by_path[rel] = raw

    return packaged, paths, bytes_by_path


def build_attestation_directory_v06(
    manifest_path: str | Path,
    output_dir: str | Path,
    private_key_path: str | Path,
    public_key_path: str | Path,
    *,
    expected_fingerprint: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build one complete signed v0.6 evidence directory from a PCS manifest."""
    manifest_path = Path(manifest_path).resolve()
    source_root = manifest_path.parent
    out = Path(output_dir).resolve()

    if out.exists():
        if not out.is_dir():
            raise V06AttestationError(f"v0.6 output is not a directory: {out}")
        if any(out.iterdir()):
            raise V06AttestationError(
                "v0.6 attestation output directory must be empty"
            )
    else:
        out.mkdir(parents=True, exist_ok=False)

    try:
        manifest = strict_json_load(manifest_path)
        validate_manifest_shape(manifest)
    except (OSError, StrictJSONError, SchemaValidationError) as exc:
        raise V06AttestationError(str(exc)) from exc
    if not isinstance(manifest, dict):
        raise V06AttestationError("manifest root must be an object")

    intake = manifest.get("pcs_intake")
    if isinstance(intake, dict) and intake.get("format") == "pcs-manifest-draft-v1":
        if intake.get("status") != "confirmed" or intake.get("requires_confirmation") is not False:
            raise V06AttestationError(
                "refusing to attest an unconfirmed PCS discovery draft; "
                "review it and run pcs confirm-v06 first"
            )

    private_key = _load_private_key_v06(private_key_path)
    try:
        public_key = load_public_key_v06(public_key_path)
    except V06VerifierIOError as exc:
        raise V06AttestationError(str(exc)) from exc
    private_fingerprint = public_key_fingerprint(private_key.public_key())
    public_fingerprint = public_key_fingerprint(public_key)
    if private_fingerprint != public_fingerprint:
        raise V06AttestationError(
            "private/public Ed25519 keypair mismatch"
        )
    if (
        expected_fingerprint is not None
        and public_fingerprint.lower() != expected_fingerprint.lower()
    ):
        raise V06AttestationError(
            "provided signer fingerprint does not match public key"
        )

    assumptions_in = deepcopy(manifest.get("assumptions", []))
    claims_in = deepcopy(manifest.get("claims", []))
    artifacts_in = deepcopy(manifest.get("artifacts", []))
    checks_in = deepcopy(manifest.get("checks", []))
    workflow = _normalize_workflow_v06(deepcopy(manifest.get("workflow", {"nodes": []})))
    try:
        environment = environment_binding_v06(
            deepcopy(manifest.get("environment"))
            if manifest.get("environment") is not None
            else None
        )
    except V06EnvironmentReplayError as exc:
        raise V06AttestationError(str(exc)) from exc

    assumption_map_in = _id_map(assumptions_in, "assumption")
    claim_map_in = _id_map(claims_in, "claim")
    check_map_in = _id_map(checks_in, "check")

    packaged_artifacts, artifact_paths, artifact_bytes = _package_artifacts_v06(
        artifacts_in,
        source_root=source_root,
        package_root=out,
    )
    artifact_ids = {artifact["id"] for artifact in packaged_artifacts}

    evidence: list[dict[str, Any]] = []
    evidence_map: dict[str, dict[str, Any]] = {}
    for check in checks_in:
        check_id = check["id"]
        claim_ids = list(check.get("claim_ids", []))
        if len(claim_ids) != len(set(claim_ids)):
            raise V06AttestationError(
                f"check {check_id} contains duplicate claim ids"
            )
        for claim_id in claim_ids:
            if claim_id not in claim_map_in:
                raise V06AttestationError(
                    f"check {check_id} references unknown claim {claim_id}"
                )

        spec = _check_spec_from_manifest(check)
        artifact_refs = artifact_ids_from_predicate(spec)
        for artifact_id in artifact_refs:
            if artifact_id not in artifact_ids:
                raise V06AttestationError(
                    f"check {check_id} references unknown artifact {artifact_id}"
                )

        item: dict[str, Any] = {
            "id": check_id,
            "kind": "computational_test",
            "claim_ids": claim_ids,
            "outcome": "UNVERIFIED",
            "checker": CHECKER_VERSION_V06,
            "predicate": deepcopy(spec),
            "artifact_ids": artifact_refs,
            "check_spec": deepcopy(spec),
        }
        replayed = replay_evidence_item_v06(item, artifact_paths)
        item["kind"] = replayed["kind"]
        item["outcome"] = replayed["outcome"]
        evidence.append(item)
        evidence_map[check_id] = item

    claims: list[dict[str, Any]] = []
    for raw_claim in claims_in:
        claim_id = raw_claim["id"]
        required = list(raw_claim.get("required_evidence", []))
        if len(required) != len(set(required)):
            raise V06AttestationError(
                f"claim {claim_id} contains duplicate required evidence ids"
            )
        required_items: list[dict[str, Any]] = []
        for evidence_id in required:
            item = evidence_map.get(evidence_id)
            if item is None:
                raise V06AttestationError(
                    f"claim {claim_id} requires unknown evidence {evidence_id}"
                )
            if claim_id not in item["claim_ids"]:
                raise V06AttestationError(
                    f"claim {claim_id} requires evidence {evidence_id}, "
                    "but that evidence does not declare support for the claim"
                )
            required_items.append(item)

        predicate = deepcopy(raw_claim.get("predicate"))
        if predicate is None:
            if not required_items:
                raise V06AttestationError(
                    f"claim {claim_id} needs a predicate or required evidence"
                )
            predicate = deepcopy(required_items[0]["predicate"])

        for item in required_items:
            if item["predicate"] != predicate:
                raise V06AttestationError(
                    f"claim {claim_id} predicate differs from required "
                    f"evidence {item['id']}"
                )

        assumptions = list(raw_claim.get("assumptions", []))
        if len(assumptions) != len(set(assumptions)):
            raise V06AttestationError(
                f"claim {claim_id} contains duplicate assumption ids"
            )
        for assumption_id in assumptions:
            if assumption_id not in assumption_map_in:
                raise V06AttestationError(
                    f"claim {claim_id} references unknown assumption {assumption_id}"
                )

        claim: dict[str, Any] = {
            "id": claim_id,
            "statement": raw_claim.get("statement"),
            "kind": raw_claim.get("kind"),
            "predicate": predicate,
            "required_evidence": required,
            "assumptions": assumptions,
            "assessment": {},
        }
        claim["assessment"] = assess_claim(claim, evidence_map)
        claims.append(claim)

    assumptions: list[dict[str, Any]] = []
    for raw_assumption in assumptions_in:
        assumption_id = raw_assumption["id"]
        derived_scope = [
            claim["id"]
            for claim in claims
            if assumption_id in claim["assumptions"]
        ]
        if (
            "scope" in raw_assumption
            and list(raw_assumption["scope"]) != derived_scope
        ):
            raise V06AttestationError(
                f"assumption {assumption_id} scope differs from claim references: "
                f"declared={raw_assumption['scope']} derived={derived_scope}"
            )
        assumption: dict[str, Any] = {
            "id": assumption_id,
            "statement": raw_assumption.get("statement"),
            "scope": derived_scope,
        }
        if "rationale" in raw_assumption:
            assumption["rationale"] = raw_assumption["rationale"]
        assumptions.append(assumption)

    try:
        workflow_summary = workflow_summary_v06(workflow, artifact_ids)
    except V06CertificateSemanticsError as exc:
        raise V06AttestationError(str(exc)) from exc

    certificate: dict[str, Any] = {
        "spec_version": SPEC_VERSION_V06,
        "checker_version": CHECKER_VERSION_V06,
        "canonical_json_profile": JCS_PROFILE,
        "semantic_hash_format": CERTIFICATE_SEMANTIC_DOMAIN,
        "integrity_hash_format": CERTIFICATE_INTEGRITY_DOMAIN,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "subject": manifest.get("subject", manifest_path.stem),
        "mission_scope": manifest.get(
            "mission_scope",
            "computational assurance; not a substitute for empirical, clinical, "
            "safety, efficacy, GxP, or regulatory validation",
        ),
        "assumptions": assumptions,
        "claims": claims,
        "artifacts": packaged_artifacts,
        "evidence": evidence,
        "workflow": workflow,
        "workflow_summary": workflow_summary,
        **({"environment": environment} if environment is not None else {}),
        "semantic_hash": "",
        "integrity_hash": "",
    }

    try:
        certificate = finalize_certificate_hashes_v06(certificate)
        write_certificate_v06(str(out / "certificate.json"), certificate)
    except V06CertificateError as exc:
        raise V06AttestationError(str(exc)) from exc

    package_files: dict[str, bytes] = {
        "certificate.json": (out / "certificate.json").read_bytes(),
        **artifact_bytes,
    }

    try:
        normalized = build_normalized_set_v06(certificate, package_files)
    except V06NormalizedSetError as exc:
        raise V06AttestationError(str(exc)) from exc

    for rel, raw in normalized["files"].items():
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        package_files[rel] = raw

    try:
        certificate_signature = sign_certificate_v06(certificate, private_key)
        (out / "certificate_signature.json").write_bytes(
            canonicalize_jcs_bytes(certificate_signature)
        )

        inventory = {
            name: {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
            }
            for name, raw in package_files.items()
        }
        package_manifest = build_package_manifest_v06(certificate, inventory)
        (out / "package_manifest.json").write_bytes(
            canonicalize_jcs_bytes(package_manifest)
        )

        package_signature = sign_package_manifest_v06(
            package_manifest,
            private_key,
        )
        (out / "package_signature.json").write_bytes(
            canonicalize_jcs_bytes(package_signature)
        )
    except (V06SignatureError, V06PackageError) as exc:
        raise V06AttestationError(str(exc)) from exc

    try:
        final = verify_package_directory_end_to_end_v06(
            out,
            public_key_path,
            expected_fingerprint=public_fingerprint,
        )
    except V06VerifierIOError as exc:
        raise V06AttestationError(str(exc)) from exc
    if not final["valid"]:
        raise V06AttestationError(
            "generated v0.6 evidence directory failed end-to-end verification: "
            f"stage={final.get('failed_stage')} errors={final.get('errors', [])}"
        )

    return {
        "valid": True,
        "certificate_semantic_hash": certificate["semantic_hash"],
        "certificate_integrity_hash": certificate["integrity_hash"],
        "normalized_index_semantic_hash": final[
            "normalized_index_semantic_hash"
        ],
        "public_key_fingerprint": public_fingerprint,
        "claims": final["claims"],
        "package_root": str(out),
    }


def attest_v06(
    manifest_path: str | Path,
    output_bundle: str | Path,
    private_key_path: str | Path,
    public_key_path: str | Path,
    *,
    expected_fingerprint: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Produce one self-verified v0.6 delivery ZIP from a project manifest."""
    output = Path(output_bundle).resolve()
    if output.exists():
        if output.is_dir():
            raise V06AttestationError(
                f"v0.6 attestation output must be a file path, not a directory: {output}"
            )
        if not overwrite:
            raise V06AttestationError(
                f"refusing to overwrite existing v0.6 bundle: {output}"
            )
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=".pcs-v06-attest-",
        dir=output.parent,
    ) as tmp:
        package_root = Path(tmp) / "package"
        package_root.mkdir()
        built = build_attestation_directory_v06(
            manifest_path,
            package_root,
            private_key_path,
            public_key_path,
            expected_fingerprint=expected_fingerprint,
        )

        try:
            bundle = create_verified_bundle_v06(
                package_root,
                output,
                public_key_path,
                expected_fingerprint=built["public_key_fingerprint"],
                overwrite=overwrite,
            )
        except V06BundleBuildError as exc:
            raise V06AttestationError(str(exc)) from exc

    return {
        "format": "pcs-v06-attestation-v1",
        "valid": True,
        "bundle": bundle["bundle"],
        "bundle_sha256": bundle["bundle_sha256"],
        "post_build_verified": bundle["post_build_verified"],
        "certificate_semantic_hash": built["certificate_semantic_hash"],
        "certificate_integrity_hash": built["certificate_integrity_hash"],
        "normalized_index_semantic_hash": built[
            "normalized_index_semantic_hash"
        ],
        "public_key_fingerprint": built["public_key_fingerprint"],
        "claims": built["claims"],
    }
