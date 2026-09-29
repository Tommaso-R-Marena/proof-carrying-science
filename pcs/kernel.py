from __future__ import annotations
import json
import shutil
import re
import hashlib
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .hashing import sha256_file, sha256_json
from .checks.splits import csv_key_disjoint
from .checks.chemistry import reaction_balanced
from .checks.units import units_compatible
from .adapters.pkpd import check_contract_file, check_output_file
from .schema_validation import validate_manifest_shape, validate_certificate_shape, SchemaValidationError
from .jsonio import strict_json_load, StrictJSONError

SPEC_VERSION = "pcs-0.5"
CHECKER_VERSION = "pcs-python-kernel/0.5.0"


class AssuranceError(ValueError):
    pass


def _semantic_projection(cert: dict[str, Any]) -> dict[str, Any]:
    """Stable scientific content, excluding run timestamp and envelope hashes."""
    out = deepcopy(cert)
    out.pop("generated_at", None)
    out.pop("integrity_hash", None)
    out.pop("semantic_hash", None)
    return out


def semantic_hash(cert: dict[str, Any]) -> str:
    return sha256_json(_semantic_projection(cert))


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _ids(items: list[dict], kind: str) -> set[str]:
    seen: set[str] = set()
    for x in items:
        i = x.get("id")
        if not isinstance(i, str) or not i:
            raise AssuranceError(f"{kind} missing non-empty id")
        if not _SAFE_ID.fullmatch(i):
            raise AssuranceError(f"unsafe {kind} id: {i!r}")
        if i in seen:
            raise AssuranceError(f"duplicate {kind} id: {i}")
        seen.add(i)
    return seen


def _safe_under(root: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise AssuranceError(f"{label} path must be a non-empty string")
    root = root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as e:
        raise AssuranceError(f"{label} escapes package root: {relative!r}") from e
    return candidate


_CLAIM_KINDS = {"formal", "computational", "empirical", "mixed"}


def _normalized_predicate_from_check(check: dict) -> dict | None:
    t = check.get("type")
    if t == "csv_disjoint":
        return {"type": t, "left_artifact": check.get("left_artifact"), "right_artifact": check.get("right_artifact"), "key": check.get("key")}
    if t == "reaction_balance":
        return {"type": t, "reactants": check.get("reactants"), "products": check.get("products")}
    if t == "unit_compatible":
        return {"type": t, "left_unit": check.get("left_unit"), "right_unit": check.get("right_unit")}
    if t == "pkpd_contract":
        return {"type": t, "model_artifact": check.get("model_artifact")}
    if t == "pkpd_reference_match":
        return {
            "type": t,
            "model_artifact": check.get("model_artifact"),
            "output_artifact": check.get("output_artifact"),
            "time_column": check.get("time_column", "time"),
            "concentration_column": check.get("concentration_column", "concentration"),
            "effect_column": check.get("effect_column", "effect"),
            "rel_tol": check.get("rel_tol", 1e-9),
            "abs_tol": check.get("abs_tol", 1e-12),
        }
    return None


def _validate_claim_semantics(claim: dict, evidence_map: dict[str, dict]) -> None:
    """Require exact semantic binding for every evidence object named as required.

    This deliberately matches the Lean refinement invariant
    `RequiredEvidenceBound`: once a claim says evidence is required, that evidence
    must be about the same machine-readable predicate as the claim. Allowing one
    matching check plus unrelated required checks would make Python certificate
    validity weaker than the machine-checked bridge.
    """
    kind = claim.get("kind")
    if kind not in _CLAIM_KINDS:
        raise AssuranceError(f"claim {claim.get('id')} has unsupported kind {kind!r}")

    predicate = claim.get("predicate")
    if predicate is None and kind == "computational":
        raise AssuranceError(
            f"computational claim {claim.get('id')} requires a machine-readable predicate"
        )
    if predicate is not None and (
        not isinstance(predicate, dict) or not predicate.get("type")
    ):
        raise AssuranceError(f"claim {claim.get('id')} has invalid predicate")

    for eid in claim.get("required_evidence", []):
        e = evidence_map.get(eid)
        if not e:
            # Missing required evidence is rejected elsewhere; keep this routine
            # focused on the semantic relation when an object is present.
            continue
        evidence_predicate = _normalized_predicate_from_check(e.get("check_spec", {}))
        if evidence_predicate != predicate:
            raise AssuranceError(
                f"claim {claim.get('id')} required evidence {eid} is not "
                "predicate-bound to the claim"
            )


def validate_workflow(workflow: dict, artifact_ids: set[str]) -> dict:
    nodes = workflow.get("nodes", [])
    node_ids = _ids(nodes, "workflow node")
    producers: dict[str, str] = {}
    edges: dict[str, set[str]] = {n: set() for n in node_ids}
    consumers_by_artifact: dict[str, list[str]] = {}

    for n in nodes:
        for a in n.get("inputs", []) + n.get("outputs", []):
            if a not in artifact_ids:
                raise AssuranceError(f"workflow node {n['id']} references unknown artifact {a}")
        for out in n.get("outputs", []):
            if out in producers:
                raise AssuranceError(f"artifact {out} has multiple producers: {producers[out]}, {n['id']}")
            producers[out] = n["id"]
        for inp in n.get("inputs", []):
            consumers_by_artifact.setdefault(inp, []).append(n["id"])

    for artifact, prod in producers.items():
        for cons in consumers_by_artifact.get(artifact, []):
            if cons != prod:
                edges[prod].add(cons)

    temp, perm = set(), set()
    order: list[str] = []
    def visit(n: str):
        if n in perm:
            return
        if n in temp:
            raise AssuranceError(f"workflow cycle detected at node {n}")
        temp.add(n)
        for m in sorted(edges[n]):
            visit(m)
        temp.remove(n)
        perm.add(n)
        order.append(n)

    for n in sorted(node_ids):
        visit(n)
    order.reverse()
    return {"node_count": len(nodes), "topological_order": order}


def _artifact_by_id(artifacts: list[dict]) -> dict[str, dict]:
    return {a["id"]: a for a in artifacts}


def _run_check(check: dict, artifact_map: dict[str, dict], root: Path) -> dict:
    ctype = check.get("type")
    cid = check["id"]
    claims = check.get("claim_ids", [])

    def path_for(aid: str) -> Path:
        if aid not in artifact_map:
            raise AssuranceError(f"check {cid} references unknown artifact {aid}")
        return _safe_under(root, artifact_map[aid]["path"], f"artifact {aid}")

    try:
        if ctype == "csv_disjoint":
            left_id, right_id = check["left_artifact"], check["right_artifact"]
            ok, details = csv_key_disjoint(path_for(left_id), path_for(right_id), check["key"])
            arts = [left_id, right_id]
            kind = "computational_test"
        elif ctype == "reaction_balance":
            ok, details = reaction_balanced(check["reactants"], check["products"])
            arts = []
            kind = "computational_test"
        elif ctype == "unit_compatible":
            ok, details = units_compatible(check["left_unit"], check["right_unit"])
            arts = []
            kind = "computational_test"
        elif ctype == "pkpd_contract":
            model_id = check["model_artifact"]
            ok, details = check_contract_file(path_for(model_id))
            arts = [model_id]
            kind = "computational_test"
        elif ctype == "pkpd_reference_match":
            model_id, output_id = check["model_artifact"], check["output_artifact"]
            ok, details = check_output_file(
                path_for(model_id),
                path_for(output_id),
                time_column=check.get("time_column", "time"),
                concentration_column=check.get("concentration_column", "concentration"),
                effect_column=check.get("effect_column", "effect"),
                rel_tol=float(check.get("rel_tol", 1e-9)),
                abs_tol=float(check.get("abs_tol", 1e-12)),
            )
            arts = [model_id, output_id]
            kind = "computational_test"
        elif ctype == "external_formal_proof":
            # v0.4 records external proof evidence but does not execute or trust arbitrary checkers.
            ok = None
            details = {
                "reason": "external formal proof recorded but not independently checked by v0.4",
                "proof_artifact": check.get("proof_artifact"),
                "checker_declared": check.get("checker"),
            }
            arts = [check["proof_artifact"]] if check.get("proof_artifact") else []
            kind = "formal_proof"
        else:
            raise AssuranceError(f"unsupported check type: {ctype}")
    except Exception as e:
        return {
            "id": cid,
            "kind": "check_error",
            "claim_ids": claims,
            "outcome": "FAIL",
            "checker": CHECKER_VERSION,
            "details": {"error": type(e).__name__, "message": str(e), "check_type": ctype},
            "artifact_ids": [],
            "check_spec": deepcopy(check),
        }

    return {
        "id": cid,
        "kind": kind,
        "claim_ids": claims,
        "outcome": ("PASS" if ok is True else "FAIL" if ok is False else "UNVERIFIED"),
        "checker": CHECKER_VERSION,
        "details": details,
        "artifact_ids": arts,
        "check_spec": deepcopy(check),
    }


def derive_claim_status(claim: dict, evidence_map: dict[str, dict]) -> dict:
    """Compatibility wrapper around the pure decision kernel."""
    from .decision import assess_claim
    return assess_claim(claim, evidence_map)

def build_certificate(manifest_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    src_root = manifest_path.parent
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    artifact_out = out / "artifacts"
    artifact_out.mkdir(exist_ok=True)

    try:
        manifest = strict_json_load(manifest_path)
    except StrictJSONError as exc:
        raise AssuranceError(str(exc)) from exc
    try:
        validate_manifest_shape(manifest)
    except SchemaValidationError as exc:
        raise AssuranceError(str(exc)) from exc
    assumptions = deepcopy(manifest.get("assumptions", []))
    claims = deepcopy(manifest.get("claims", []))
    artifacts = deepcopy(manifest.get("artifacts", []))
    checks = deepcopy(manifest.get("checks", []))
    workflow = deepcopy(manifest.get("workflow", {"nodes": []}))

    assumption_ids = _ids(assumptions, "assumption")
    claim_ids = _ids(claims, "claim")
    artifact_ids = _ids(artifacts, "artifact")
    check_ids = _ids(checks, "check")

    for claim in claims:
        for aid in claim.get("assumptions", []):
            if aid not in assumption_ids:
                raise AssuranceError(f"claim {claim['id']} references unknown assumption {aid}")
        for eid in claim.get("required_evidence", []):
            if eid not in check_ids:
                raise AssuranceError(f"claim {claim['id']} requires unknown evidence/check {eid}")

    for check in checks:
        for cid in check.get("claim_ids", []):
            if cid not in claim_ids:
                raise AssuranceError(f"check {check['id']} references unknown claim {cid}")

    # Self-contained artifact package: copy files and hash copies.
    packaged_artifacts: list[dict] = []
    for a in artifacts:
        src = _safe_under(src_root, a["path"], f"artifact {a['id']}")
        if not src.is_file():
            raise AssuranceError(f"artifact {a['id']} not found: {src}")
        # Keep customer filenames and artifact IDs as metadata, but do not
        # use them as delivery filesystem names. A stable ASCII key avoids
        # Windows-reserved names, Unicode/case collisions, and separator quirks.
        storage_key = hashlib.sha256(a["id"].encode("utf-8")).hexdigest()[:24]
        target_dir = artifact_out / storage_key
        target_dir.mkdir(parents=True, exist_ok=True)
        dst = target_dir / "payload"
        shutil.copy2(src, dst)
        aa = deepcopy(a)
        aa["source_path"] = a["path"]
        aa["storage_key"] = storage_key
        aa["path"] = dst.relative_to(out).as_posix()
        aa["sha256"] = sha256_file(dst)
        packaged_artifacts.append(aa)

    artifact_map_src = _artifact_by_id(artifacts)
    workflow_summary = validate_workflow(workflow, artifact_ids)
    evidence = [_run_check(c, artifact_map_src, src_root) for c in checks]
    evidence_map = {e["id"]: e for e in evidence}
    for c in claims:
        for eid in c.get("required_evidence", []):
            if c["id"] not in evidence_map[eid].get("claim_ids", []):
                raise AssuranceError(f"claim {c['id']} requires evidence {eid}, but that evidence does not declare support for the claim")
        _validate_claim_semantics(c, evidence_map)
    claim_results = []
    for c in claims:
        cc = deepcopy(c)
        cc["assessment"] = derive_claim_status(c, evidence_map)
        claim_results.append(cc)

    cert: dict[str, Any] = {
        "spec_version": SPEC_VERSION,
        "checker_version": CHECKER_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "subject": manifest.get("subject", manifest_path.stem),
        "mission_scope": "computational assurance; not a substitute for empirical scientific validation",
        "assumptions": assumptions,
        "claims": claim_results,
        "artifacts": packaged_artifacts,
        "evidence": evidence,
        "workflow": workflow,
        "workflow_summary": workflow_summary,
        "semantic_hash": "",
        "integrity_hash": "",
    }
    cert["semantic_hash"] = semantic_hash(cert)
    cert_for_hash = deepcopy(cert)
    cert_for_hash["integrity_hash"] = ""
    cert["integrity_hash"] = sha256_json(cert_for_hash)
    try:
        validate_certificate_shape(cert)
    except SchemaValidationError as exc:
        raise AssuranceError(str(exc)) from exc
    (out / "certificate.json").write_text(json.dumps(cert, indent=2, sort_keys=True), encoding="utf-8")
    return cert


def verify_certificate(certificate_path: str | Path) -> dict[str, Any]:
    path = Path(certificate_path).resolve()
    root = path.parent
    try:
        cert = strict_json_load(path)
    except StrictJSONError as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "certificate": str(path),
            "integrity_hash": None,
            "semantic_hash": None,
            "claim_statuses": {},
        }
    errors: list[str] = []
    try:
        validate_certificate_shape(cert)
    except SchemaValidationError as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "certificate": str(path),
            "integrity_hash": cert.get("integrity_hash"),
            "semantic_hash": cert.get("semantic_hash"),
            "claim_statuses": {},
        }

    if cert.get("spec_version") != SPEC_VERSION:
        errors.append(f"unsupported spec_version: {cert.get('spec_version')!r}")
    if cert.get("checker_version") != CHECKER_VERSION:
        errors.append(f"certificate checker_version differs from replay checker: {cert.get('checker_version')!r}")

    supplied = cert.get("integrity_hash", "")
    ccopy = deepcopy(cert)
    ccopy["integrity_hash"] = ""
    expected = sha256_json(ccopy)
    if supplied != expected:
        errors.append("certificate integrity hash mismatch")

    supplied_semantic = cert.get("semantic_hash", "")
    expected_semantic = semantic_hash(cert)
    if supplied_semantic != expected_semantic:
        errors.append("certificate semantic hash mismatch")

    try:
        assumption_ids = _ids(cert.get("assumptions", []), "assumption")
        claim_ids = _ids(cert.get("claims", []), "claim")
        artifact_ids = _ids(cert.get("artifacts", []), "artifact")
        evidence_ids = _ids(cert.get("evidence", []), "evidence")
    except AssuranceError as e:
        errors.append(str(e))
        assumption_ids = claim_ids = artifact_ids = evidence_ids = set()

    for a in cert.get("artifacts", []):
        try:
            p = _safe_under(root, a.get("path", ""), f"packaged artifact {a.get('id')}")
        except AssuranceError as ex:
            errors.append(str(ex))
            continue
        if not p.is_file():
            errors.append(f"missing packaged artifact {a.get('id')}: {p}")
        elif sha256_file(p) != a.get("sha256"):
            errors.append(f"artifact hash mismatch: {a.get('id')}")

    evidence_map = {e["id"]: e for e in cert.get("evidence", []) if "id" in e}

    # Replay every built-in check from its recorded specification. The certificate's
    # recorded PASS/FAIL value is not trusted. External formal proofs remain
    # UNVERIFIED until a dedicated independently checking adapter is implemented.
    artifact_map_packaged = _artifact_by_id(cert.get("artifacts", []))
    for e in cert.get("evidence", []):
        spec = e.get("check_spec")
        if not isinstance(spec, dict):
            errors.append(f"evidence {e.get('id')} missing replayable check_spec")
            continue
        replayed = _run_check(spec, artifact_map_packaged, root)
        if replayed.get("outcome") != e.get("outcome"):
            errors.append(f"evidence replay outcome mismatch: {e.get('id')} recorded={e.get('outcome')} replayed={replayed.get('outcome')}")
        if replayed.get("kind") != e.get("kind"):
            errors.append(f"evidence replay kind mismatch: {e.get('id')}")
        if replayed.get("details") != e.get("details"):
            errors.append(f"evidence replay details mismatch: {e.get('id')}")
        if replayed.get("claim_ids") != e.get("claim_ids"):
            errors.append(f"evidence replay claim binding mismatch: {e.get('id')}")
        if replayed.get("artifact_ids") != e.get("artifact_ids"):
            errors.append(f"evidence replay artifact binding mismatch: {e.get('id')}")

    for e in cert.get("evidence", []):
        for cid in e.get("claim_ids", []):
            if cid not in claim_ids:
                errors.append(f"evidence {e.get('id')} references unknown claim {cid}")
        for aid in e.get("artifact_ids", []):
            if aid not in artifact_ids:
                errors.append(f"evidence {e.get('id')} references unknown artifact {aid}")

    for c in cert.get("claims", []):
        for aid in c.get("assumptions", []):
            if aid not in assumption_ids:
                errors.append(f"claim {c.get('id')} references unknown assumption {aid}")
        for eid in c.get("required_evidence", []):
            if eid not in evidence_ids:
                errors.append(f"claim {c.get('id')} references unknown evidence {eid}")
            elif c.get("id") not in evidence_map[eid].get("claim_ids", []):
                errors.append(f"claim {c.get('id')} requires evidence {eid} that does not declare support for it")
        try:
            _validate_claim_semantics(c, evidence_map)
        except AssuranceError as ex:
            errors.append(str(ex))
        expected_assessment = derive_claim_status(c, evidence_map)
        if c.get("assessment") != expected_assessment:
            errors.append(f"claim assessment mismatch: {c.get('id')}")

    try:
        replay_summary = validate_workflow(cert.get("workflow", {"nodes": []}), artifact_ids)
        if cert.get("workflow_summary") != replay_summary:
            errors.append("workflow_summary mismatch")
    except AssuranceError as e:
        errors.append(str(e))

    return {
        "valid": not errors,
        "errors": errors,
        "certificate": str(path),
        "integrity_hash": supplied,
        "semantic_hash": supplied_semantic,
        "claim_statuses": {c.get("id"): c.get("assessment", {}).get("status") for c in cert.get("claims", [])},
    }
