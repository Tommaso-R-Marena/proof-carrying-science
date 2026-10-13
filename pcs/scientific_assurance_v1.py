"""Compose existing PCS packages with independently replayed scientific contracts.

The v0.6 signed certificate remains the package authority. Numerical evidence is
an existing signed external-validator assertion; this receiver additionally reruns
its bounded algorithm, without upgrading it to Lean or scientific authority.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .attest_v06 import build_attestation_directory_v06
from .bundle_v06 import create_verified_bundle_v06
from .canonical_json import canonicalize_jcs_bytes
from .check_registry_v06 import predicate_from_manifest_check_v06
from .discover_v06 import discover_project_v06, confirm_manifest_draft_v06
from .discovery_review_v06 import render_discovery_review_v06
from .external_validator_v06 import (
    EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06, EXTERNAL_VALIDATOR_TRUST_MODEL_V06,
    EXTERNAL_VALIDATOR_TRUST_POLICY_FORMAT_V06, build_external_validator_receipt_payload_v06,
    sign_external_validator_receipt_v06, verify_external_validator_receipt_v06,
    normalize_external_validator_check_spec_v06,
)
from .jsonio import strict_json_loads
from .scientific_contracts_v1 import (
    ScientificContractError, MAX_BYTES, evaluate, load_contract, primitive_checks, digest,
)
from .scientific_obligations_v1 import make_plan, resolve_plan
from .signing import public_key_fingerprint
from .verifier_zip_v06 import load_package_zip_v06, verify_package_zip_end_to_end_v06

FORMAT = "pcs-scientific-assurance-v1"
NAMESPACE = "pcs-bounded-mass-action-replay/v1"
VALIDATOR = "pcs-rational-mass-action-validator/1"
_FILES = {
    "adapter": "pcs-scientific/adapter.py.txt",
    "report": "pcs-scientific/domain-replay.json",
    "plan": "pcs-scientific/obligations.json",
    "resolved": "pcs-scientific/obligation-results.json",
    "trust": "pcs-scientific/validator-trust.json",
    "receipt": "pcs-scientific/numerical-receipt.json",
    "key": "pcs-scientific/validator-public.der",
    "binding": "pcs-scientific/binding.json",
    "spec": "pcs-scientific/numerical-spec.json",
}


class ScientificAssuranceError(ValueError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ScientificAssuranceError(f"refusing to replace existing evidence: {path.name}")
    path.write_bytes(canonicalize_jcs_bytes(value))


def _relative_file(root: Path, relative: str) -> Path:
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or PurePosixPath(relative).is_absolute() or PurePosixPath(relative).as_posix() != relative
            or any(x in {".", ".."} for x in PurePosixPath(relative).parts)):
        raise ScientificAssuranceError("source paths must be canonical project-relative paths")
    literal = root / relative
    if literal.is_symlink() or not literal.is_file():
        raise ScientificAssuranceError("scientific source artifact must be a regular nonsymlink file")
    try:
        literal.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ScientificAssuranceError("source artifact escapes project") from exc
    for parent in literal.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise ScientificAssuranceError("symlink source ancestor is unsupported")
    if literal.stat().st_size > MAX_BYTES:
        raise ScientificAssuranceError("scientific source artifact exceeds 2 MiB")
    return literal


def _adapter_source() -> bytes:
    from . import scientific_contracts_v1
    return Path(scientific_contracts_v1.__file__).read_bytes()


def _numerical_predicate() -> dict:
    return {"type": "external", "namespace": NAMESPACE,
        "proposition": "The bound concentration table satisfies the bound finite rational mass-action contract, including declared dimensions, grid, nonnegativity, reference tolerances and elemental conservation."}


def _claim(ident: str, statement: str, predicate: dict, evidence: str, assumptions: list[str]) -> dict:
    return {"id": ident, "statement": statement, "kind": "computational",
        "required_evidence": [evidence], "predicate": predicate, "assumptions": assumptions}


def prepare_scientific_project(project_root: str | Path, work_directory: str | Path,
        private_key_path: str | Path, public_key_path: str | Path, *,
        contract_path: str = "model.json", observations_path: str = "observations.csv",
        expected_fingerprint: str) -> dict:
    """Map an explicit external project and stage a reviewable draft; run no code.

    The workspace must be new and outside the source project. Private keys are
    consumed only by established Ed25519 routines and never copied into evidence.
    """
    root = Path(project_root).resolve()
    work = Path(work_directory).resolve()
    if not root.is_dir() or work.exists() or work == root or root in work.parents:
        raise ScientificAssuranceError("work_directory must be new and outside the source project")
    if (root / "pcs-scientific").exists():
        raise ScientificAssuranceError("reserved pcs-scientific directory already exists")
    contract_raw = _relative_file(root, contract_path).read_bytes()
    observations_raw = _relative_file(root, observations_path).read_bytes()
    replay = evaluate(contract_raw, observations_raw)
    if replay["outcome"] not in {"PASS", "FAIL"}:
        return {"format": FORMAT, "status": replay["outcome"], "package_created": False,
            "pcs_authority": False, "domain_replay": replay}
    contract = load_contract(contract_raw)
    key = serialization.load_pem_private_key(Path(private_key_path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ScientificAssuranceError("validator signing key must be Ed25519")
    public = serialization.load_pem_public_key(Path(public_key_path).read_bytes())
    if not isinstance(public, Ed25519PublicKey):
        raise ScientificAssuranceError("validator public key must be Ed25519")
    fingerprint = public_key_fingerprint(key.public_key())
    if fingerprint != expected_fingerprint or public_key_fingerprint(public) != fingerprint:
        raise ScientificAssuranceError("producer/validator public key must match the caller-pinned fingerprint")
    initial_discovery = discover_project_v06(root, subject=contract["question"])
    if not {contract_path, observations_path}.issubset({x["path"] for x in initial_discovery["inventory"]}):
        raise ScientificAssuranceError("model and observations must be included in safe discovery inventory")
    work.mkdir(parents=True)
    stage = work / "project"
    stage.mkdir()
    for item in initial_discovery["inventory"]:
        source = _relative_file(root, item["path"])
        target = stage / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        if _sha(raw) != item["sha256"]:
            raise ScientificAssuranceError("source changed after discovery")
        target.write_bytes(raw)
    plan = make_plan(contract, contract_artifact_sha256=_sha(contract_raw))
    resolved = resolve_plan(plan, replay)
    addons = {
        "adapter": _adapter_source(),
        "report": canonicalize_jcs_bytes(replay),
        "plan": canonicalize_jcs_bytes(plan),
        "resolved": canonicalize_jcs_bytes(resolved),
        "key": key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo),
        "trust": canonicalize_jcs_bytes({"format": EXTERNAL_VALIDATOR_TRUST_POLICY_FORMAT_V06,
            "validator": VALIDATOR, "validator_public_key_fingerprint": fingerprint,
            "allowed_check_types": ["external_empirical_validation"], "allowed_predicate_namespaces": [NAMESPACE]}),
        "receipt": b'{"pending":true}',
        "spec": b'{"pending":true}',
        "binding": canonicalize_jcs_bytes({"format": FORMAT, "contract_path": contract_path,
            "observations_path": observations_path, "adapter_sha256": _sha(_adapter_source()),
            "model_units": {"time": "s", "concentration": "mol/L"},
            "original_source_inventory": [{"path": item["path"], "sha256": item["sha256"]}
                                          for item in initial_discovery["inventory"]],
            "validator_independence": "producer-signed; independent algorithm replay is required by the receiver",
            "independent_human_review": False, "license": "CC0-1.0 declared by contract; legal adequacy not certified"}),
    }
    for name, raw in addons.items():
        path = stage / _FILES[name]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    discovered = discover_project_v06(stage, subject=contract["question"])
    ids = {item["path"]: item["artifact_id"] for item in discovered["inventory"]}
    bound_paths = sorted(path for path in ids if path not in {_FILES["receipt"], _FILES["key"]})
    predicate = _numerical_predicate()
    external_spec = {"id": "E_NUMERICAL", "type": "external_empirical_validation", "claim_ids": ["C_NUMERICAL"],
        "validator": VALIDATOR, "predicate": predicate, "receipt_format": EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06,
        "trust_model": EXTERNAL_VALIDATOR_TRUST_MODEL_V06, "receipt_artifact": ids[_FILES["receipt"]],
        "validator_public_key_artifact": ids[_FILES["key"]], "validator_public_key_fingerprint": fingerprint,
        "validator_trust_policy_artifact": ids[_FILES["trust"]], "bound_artifact_ids": sorted(ids[path] for path in bound_paths)}
    (stage / _FILES["spec"]).write_bytes(canonicalize_jcs_bytes(external_spec))
    bound = {ids[path]: (stage / path).read_bytes() for path in bound_paths}
    payload = build_external_validator_receipt_payload_v06(check_type="external_empirical_validation",
        validator=VALIDATOR, predicate=predicate, bound_artifact_ids=sorted(bound), artifact_bytes=bound,
        outcome=replay["outcome"])
    receipt = sign_external_validator_receipt_v06(payload, key)
    (stage / _FILES["receipt"]).write_bytes(canonicalize_jcs_bytes(receipt))
    discovered = discover_project_v06(stage, subject=contract["question"])
    manifest = discovered["manifest_draft"]
    # Every scientific assumption has an explicit exact source and stable ID.
    manifest["assumptions"] = list(contract["assumptions"])
    manifest["claims"] = []
    manifest["checks"] = []
    assumption_ids = [item["id"] for item in contract["assumptions"]]
    for check in primitive_checks(contract):
        evidence_id, claim_id = f"E_{check['id']}", f"C_{check['id']}"
        spec = {**check, "id": evidence_id, "claim_ids": [claim_id]}
        manifest["checks"].append(spec)
        manifest["claims"].append(_claim(claim_id,
            "The explicitly declared reaction satisfies " + check["type"] + " under the PCS builtin semantics.",
            predicate_from_manifest_check_v06(spec), evidence_id, assumption_ids))
    # The compiled Lean authority does not accept external validator check types.
    # Keep the signed numerical receipt/spec as artifact sidecars and leave this
    # original numerical claim OPEN with no certified evidence. The independent
    # receiver verifies the external signature and algorithm separately.
    numerical_claim = _claim("C_NUMERICAL", predicate["proposition"], predicate, "E_NUMERICAL", assumption_ids)
    numerical_claim["required_evidence"] = []
    manifest["claims"].append(numerical_claim)
    manifest["artifacts"] = [{"id": item["artifact_id"], "path": item["path"], "role": item["role"],
        "media_type": item["media_type"], "metadata": {"pcs_discovery_sha256": item["sha256"],
            "pcs_discovery_size": item["size"]}} for item in discovered["inventory"]]
    discovered["manifest_draft"] = manifest
    _write(stage / "pcs-manifest.draft.json", manifest)
    _write(work / "discovery.json", discovered)
    (work / "REVIEW.md").write_text(render_discovery_review_v06(discovered)
        + "\n## Numerical authority boundary\n\nThe numerical receipt is producer-signed. Its computational claim remains OPEN in PCS authority; use the scientific receiver for fresh bounded replay. No independent human review is asserted.\n",
        encoding="utf-8")
    return {"format": FORMAT, "status": "DRAFT", "project": str(stage),
        "manifest_draft": str(stage / "pcs-manifest.draft.json"), "review": str(work / "REVIEW.md"),
        "domain_outcome": replay["outcome"], "pcs_authority": False,
        "independent_human_review": False, "user_code_executed": False}


def build_scientific_bundle(project_root: str | Path, work_directory: str | Path,
        output_bundle: str | Path, private_key_path: str | Path, public_key_path: str | Path, *,
        expected_fingerprint: str, contract_path: str = "model.json", observations_path: str = "observations.csv",
        generated_at: str = "2026-10-12T00:00:00+00:00", lean_authority_path: str | Path | None = None,
        confirm_reviewed_draft: bool = False) -> dict:
    """Explicit opt-in confirmation; callers may use prepare alone for human review.

    The fixed timestamp is a reproducibility parameter, not an asserted execution
    time. Actual resource/runtime receipts are kept outside signed deterministic data.
    """
    if not confirm_reviewed_draft:
        raise ScientificAssuranceError("prepare_scientific_project first for review, or explicitly confirm the bounded generated draft")
    if Path(output_bundle).exists():
        raise ScientificAssuranceError("refusing to overwrite an existing scientific bundle")
    prepared = prepare_scientific_project(project_root, work_directory, private_key_path, public_key_path,
        contract_path=contract_path, observations_path=observations_path, expected_fingerprint=expected_fingerprint)
    if prepared["status"] != "DRAFT":
        return prepared
    stage = Path(prepared["project"])
    confirmed = stage / "manifest.confirmed.json"
    confirm_manifest_draft_v06(prepared["manifest_draft"], confirmed, project_root=stage)
    package = Path(work_directory) / "package"
    built = build_attestation_directory_v06(confirmed, package, private_key_path, public_key_path,
        expected_fingerprint=expected_fingerprint, generated_at=generated_at, lean_authority_path=lean_authority_path)
    bundled = create_verified_bundle_v06(package, output_bundle, public_key_path,
        expected_fingerprint=expected_fingerprint, lean_authority_path=lean_authority_path)
    independent = verify_scientific_bundle(output_bundle, public_key_path,
        expected_fingerprint=expected_fingerprint, lean_authority_path=lean_authority_path)
    if not independent["independent_replay_consistent"]:
        raise ScientificAssuranceError("new bundle failed independent scientific replay: " + "; ".join(independent["errors"]))
    return {"format": FORMAT, "status": "PACKAGED", "bundle": str(Path(output_bundle).resolve()),
        "bundle_sha256": bundled["bundle_sha256"], "certificate_semantic_hash": built["certificate_semantic_hash"],
        "pcs_package_valid": independent["pcs_package_valid"], "independent_replay_consistent": independent["independent_replay_consistent"],
        "bounded_contract_satisfied": independent["bounded_contract_satisfied"], "scientific_acceptance": False,
        "pcs_numerical_claim": "OPEN",
        "user_code_executed": False, "confirmation_mode": "caller explicitly confirmed generated bounded claims; not independent human review"}


def verify_scientific_bundle(bundle: str | Path, public_key_path: str | Path, *,
        expected_fingerprint: str, lean_authority_path: str | Path | None = None,
        policy_path: str | Path | None = None) -> dict:
    """Verify PCS first; independently recompute all scientific bindings and checks."""
    verification = verify_package_zip_end_to_end_v06(bundle, public_key_path,
        expected_fingerprint=expected_fingerprint, lean_authority_path=lean_authority_path, policy_path=policy_path)
    base = {"format": FORMAT, "pcs_package_valid": verification["valid"],
        "pcs_verification": verification, "independent_replay_consistent": False,
        "bounded_contract_satisfied": False, "scientific_acceptance": False,
        "independent_human_review": False, "errors": []}
    if not verification["valid"]:
        return {**base, "errors": ["existing PCS package authority rejected the bundle"]}
    try:
        loaded = load_package_zip_v06(bundle)
        certificate = strict_json_loads(loaded["certificate_bytes"].decode("utf-8"))
        files = loaded["package_files"]
        by_source = {}
        by_id = {}
        for artifact in certificate["artifacts"]:
            source = artifact.get("source_path")
            if not isinstance(source, str) or source in by_source:
                raise ScientificAssuranceError("missing or duplicate signed source path")
            by_source[source] = files[artifact["path"]]
            by_id[artifact["id"]] = artifact
        for path in _FILES.values():
            if path not in by_source:
                raise ScientificAssuranceError("scientific bundle is missing a required signed artifact")
        binding = strict_json_loads(by_source[_FILES["binding"]].decode("utf-8"))
        if (not isinstance(binding, dict) or set(binding) != {"format", "contract_path", "observations_path",
                "adapter_sha256", "model_units", "original_source_inventory", "validator_independence",
                "independent_human_review", "license"} or binding.get("format") != FORMAT):
            raise ScientificAssuranceError("scientific binding version mismatch")
        if binding["model_units"] != {"time": "s", "concentration": "mol/L"} or binding["independent_human_review"] is not False:
            raise ScientificAssuranceError("unsupported units or unauthenticated human review claim in binding")
        if binding.get("adapter_sha256") != _sha(_adapter_source()) or by_source[_FILES["adapter"]] != _adapter_source():
            raise ScientificAssuranceError("adapter source differs from the receiving pinned implementation")
        contract_raw = by_source[binding["contract_path"]]
        observed_raw = by_source[binding["observations_path"]]
        contract = load_contract(contract_raw)
        if [{"id": x["id"], "statement": x["statement"]} for x in certificate["assumptions"]] != contract["assumptions"]:
            raise ScientificAssuranceError("certificate assumptions differ from the original scientific contract")
        replay = evaluate(contract_raw, observed_raw)
        recorded = strict_json_loads(by_source[_FILES["report"]].decode("utf-8"))
        if replay != recorded:
            raise ScientificAssuranceError("signed numerical report differs from fresh independent replay")
        plan = make_plan(contract, contract_artifact_sha256=_sha(contract_raw))
        recorded_plan = strict_json_loads(by_source[_FILES["plan"]].decode("utf-8"))
        if plan != recorded_plan:
            raise ScientificAssuranceError("signed proof obligations differ from the typed source contract")
        resolved = resolve_plan(plan, replay)
        if resolved != strict_json_loads(by_source[_FILES["resolved"]].decode("utf-8")):
            raise ScientificAssuranceError("signed obligation results differ from fresh dependency propagation")
        for source in binding["original_source_inventory"]:
            if not isinstance(source, dict) or set(source) != {"path", "sha256"}:
                raise ScientificAssuranceError("malformed original source inventory")
            if _sha(by_source[source["path"]]) != source["sha256"]:
                raise ScientificAssuranceError("original source inventory binding mismatch")
        original_paths = [item["path"] for item in binding["original_source_inventory"]]
        if len(original_paths) != len(set(original_paths)) or set(original_paths) | set(_FILES.values()) != set(by_source):
            raise ScientificAssuranceError("scientific source inventory must account for every signed artifact exactly")
        evidence = {item["id"]: item for item in certificate["evidence"]}
        claims = {item["id"]: item for item in certificate["claims"]}
        for check in primitive_checks(contract):
            eid = f"E_{check['id']}"
            if evidence[eid]["predicate"] != predicate_from_manifest_check_v06(check):
                raise ScientificAssuranceError("builtin certificate predicate is not the source-derived scientific obligation")
            claim = claims[f"C_{check['id']}"]
            if (claim["kind"] != "computational" or claim["required_evidence"] != [eid]
                    or claim["predicate"] != predicate_from_manifest_check_v06(check)
                    or claim["assumptions"] != [x["id"] for x in contract["assumptions"]]):
                raise ScientificAssuranceError("builtin claim lost its exact original evidence/assumption chain")
        external_spec = strict_json_loads(by_source[_FILES["spec"]].decode("utf-8"))
        numerical_spec = normalize_external_validator_check_spec_v06(external_spec)
        numerical = verify_external_validator_receipt_v06(numerical_spec,
            {ident: files[artifact["path"]] for ident, artifact in by_id.items()})
        if (not numerical["valid"] or numerical_spec["validator"] != VALIDATOR
                or numerical_spec["predicate"] != _numerical_predicate()
                or numerical["outcome"] != replay["outcome"]):
            raise ScientificAssuranceError("external numerical receipt is not this adapter's independently replayed outcome")
        claim = claims["C_NUMERICAL"]
        if (claim["predicate"] != _numerical_predicate() or claim["required_evidence"] != []
                or claim["kind"] != "computational"
                or claim["assumptions"] != [x["id"] for x in contract["assumptions"]]):
            raise ScientificAssuranceError("numerical claim must remain outside certified builtin evidence authority")
        bound_ids = numerical_spec["bound_artifact_ids"]
        excluded_ids = {numerical_spec["receipt_artifact"], numerical_spec["validator_public_key_artifact"]}
        if set(bound_ids) != set(by_id) - excluded_ids:
            raise ScientificAssuranceError("numerical signature must bind every scientific artifact except its own receipt and public key")
        required_paths = {binding["contract_path"], binding["observations_path"], _FILES["adapter"],
            _FILES["report"], _FILES["plan"], _FILES["resolved"], _FILES["binding"], _FILES["trust"], _FILES["spec"],
            *(item["path"] for item in binding["original_source_inventory"])}
        if not required_paths.issubset({by_id[ident]["source_path"] for ident in bound_ids}):
            raise ScientificAssuranceError("numerical signature omits a required scientific source/assumption/evidence binding")
        decisions = {item["claim_id"]: item["decision"] for item in verification["claims"]}
        builtin_supported = all(decisions.get(f"C_{check['id']}") == "COMPUTATIONALLY_SUPPORTED"
                                for check in primitive_checks(contract))
        return {**base, "independent_replay_consistent": True,
            "bounded_contract_satisfied": (replay["outcome"] == "PASS"
                and verification.get("accepted") is True and builtin_supported),
            "compiled_builtin_obligations_supported": builtin_supported,
            "domain_replay": replay, "obligation_results": resolved,
            "external_numerical_signature": numerical,
            "bundle_sha256": loaded["bundle_sha256"],
            "cross_component_contract": {"sender": VALIDATOR, "receiver": "pcs-scientific-receiver/1",
                "certificate_authority": "existing PCS v0.6", "numerical_authority": "external trust plus bounded fresh Python replay",
                "kernel_refinement_proved": False, "scientific_acceptance": False}}
    except (KeyError, TypeError, ValueError) as exc:
        return {**base, "errors": [f"scientific receiver rejected: {type(exc).__name__}: {exc}"]}


def render_scientific_receipt_html(receipt: dict) -> str:
    escaped = html.escape(json.dumps(receipt, indent=2, ensure_ascii=False))
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>PCS bounded scientific replay</title><style>body{font-family:system-ui;max-width:70rem;margin:auto;padding:2rem}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Bounded scientific replay</h1>'
        '<p>The existing signed PCS certificate controls package authority. Numerical replay checks the explicit finite contract. '
        'It does not establish biological, clinical or general scientific acceptance.</p><pre>' + escaped + '</pre></html>')
