"""Signed finite-model assurance, with a fresh receiving kernel proof.

The existing package verifier authenticates artifacts and keeps the new external
claims OPEN. This separate receiving interface regenerates the exact model proof;
it does not grant deployed-world, empirical or general AI-safety authority.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from . import action_shield_v1 as shield
from .attest_v06 import build_attestation_directory_v06
from .bundle_v06 import create_verified_bundle_v06
from .canonical_json import canonicalize_jcs_bytes as encode
from .discover_v06 import discover_project_v06, confirm_manifest_draft_v06
from .experimental import conditional
from .jsonio import strict_json_loads
from .verifier_zip_v06 import load_package_zip_v06, verify_package_zip_end_to_end_v06

FORMAT = "pcs-action-shield-assurance-package-v1"
PREFIX = "pcs-action-shield"
FILES = {name: f"{PREFIX}/{name}.json" for name in ("binding", "replay", "obligations")}
STATEMENTS = {
    "C_MODEL_SAFE": "Every finite admitted history of the exact declared transition model stays in the declared safe states and excludes the declared forbidden actions.",
    "C_GUARD_EQ": "The bound candidate Boolean guard denotes the same allowed state-action table as the bound reference guard.",
    "C_DEPLOYED_SAFE": "The deployed agent satisfies these safety properties under faithful model, observations and shield enforcement.",
    "C_LIVENESS": "The deployed agent can complete useful tasks without deadlock.",
}


class ShieldAssuranceError(ValueError):
    pass


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    if not isinstance(raw, bytes) or len(raw) > shield.MAX_BYTES:
        raise ShieldAssuranceError("bounded byte artifact required")
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ShieldAssuranceError("invalid bounded strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ShieldAssuranceError("object artifact required")
    return value


def _balanced(op, values):
    if len(values) == 1:
        return values[0]
    middle = len(values) // 2
    return {"op": op, "left": _balanced(op, values[:middle]), "right": _balanced(op, values[middle:])}


def guard_task(model_raw, shield_raw):
    model = shield.load_model(model_raw)
    cert = shield.load_shield(shield_raw, model, model_sha256=sha(model_raw))
    if len(cert["allowed"]) > 24:
        raise ShieldAssuranceError("this guard adapter supports at most 24 allowed pairs")
    variables = sorted(f"P{i}" for i in range(len(cert["allowed"])))
    atoms = [{"op": "atom", "symbol": x, "args": []} for x in variables]
    source = _balanced("or", atoms) if atoms else {"op": "false"}
    candidate = {"op": "not", "body": _balanced("and", [{"op": "not", "body": x} for x in atoms])} if atoms else {"op": "false"}
    return {"format": conditional.TASK, "variables": variables, "source": source,
            "candidate": candidate, "assumptions": []}


def replay(model_raw, shield_raw, guard_raw):
    """Independent finite closure/guard replay; producer reports are never inputs."""
    model = shield.load_model(model_raw)
    cert = shield.load_shield(shield_raw, model, model_sha256=sha(model_raw))
    task = conditional.validate(_json(guard_raw))
    expected = guard_task(model_raw, shield_raw)
    if task["variables"] != expected["variables"] or task["source"] != expected["source"] or task["assumptions"] != []:
        raise ShieldAssuranceError("guard reference or context differs from the exact allowed table")
    receipt = conditional.check(task)
    variables = task["variables"]
    pairs = dict(zip(variables, map(tuple, cert["allowed"])))
    mismatches = []
    for state in model["states"]:
        for action in model["actions"]:
            assignment = {name: pair == (state, action) for name, pair in pairs.items()}
            if conditional.evaluate(task["candidate"], assignment) != ((state, action) in pairs.values()):
                mismatches.append([state, action])
    report = shield.evaluate(model_raw, shield_raw)
    return {"format": FORMAT, "model": report,
        "guard": {"task_sha256": sha(guard_raw), "receipt": receipt,
            "complete_state_action_domain_checked": len(model["states"]) * len(model["actions"]),
            "mismatches": mismatches, "outcome": "PASS" if receipt["decision"] == "equivalent_under_assumptions" and not mismatches else "FAIL",
            "mapping": {name: list(pair) for name, pair in pairs.items()},
            "formal_boundary": "Extracted conditional runtime assumes validation and digest contracts; JavaScript additionally assumes task bounds and helper contracts. Language/runtime/OS correspondence remains external."},
        "scientific_acceptance": False, "deployment_safety": "OPEN", "liveness": "OPEN"}


def obligations(model_raw, report, *, kernel_checked=False):
    model = shield.load_model(model_raw)
    return {"format": "pcs-action-shield-obligations-v1", "model_sha256": sha(model_raw),
        "nodes": [
            {"id": "model_invariant", "claim_id": "C_MODEL_SAFE", "dependencies": [],
             "status": "FORMALLY_SUPPORTED" if kernel_checked and report["model"]["outcome"] == "PASS" else "REQUIRES_FRESH_KERNEL_REPLAY"},
            {"id": "guard_table", "claim_id": "C_GUARD_EQ", "dependencies": ["model_invariant"],
             "status": "COMPUTATIONALLY_REPLAYED" if report["guard"]["outcome"] == "PASS" else "FAIL"},
            *[{"id": x["id"], "dependencies": [], "status": "OPEN", "statement": x["statement"]} for x in model["assumptions"]],
            {"id": "deployment", "claim_id": "C_DEPLOYED_SAFE", "dependencies": ["model_invariant", "guard_table", *[x["id"] for x in model["assumptions"]]], "status": "OPEN"},
            {"id": "liveness", "claim_id": "C_LIVENESS", "dependencies": ["deployment"], "status": "OPEN"}],
        "independent_human_review": False, "scientific_acceptance": False}


def implementation():
    root = Path(__file__).resolve().parents[1]
    paths = ["pcs/action_shield_v1.py", "pcs/ai_safety_assurance_v1.py", "pcs/experimental/conditional.py",
             "pcs/canonical_json.py", "pcs/jsonio.py", "formal/PCSActionShield.lean", "formal/PCSConditionalShieldBridge.lean",
             "formal/PCSConditionalShieldRuntime.lean", "research/aristotle-conditional-runtime-v1/source-manifest.json",
             "research/aristotle-conditional-runtime-v1/theorem-inventory.json"]
    return {f"{PREFIX}/sources/{path}.txt": (root / path).read_bytes() for path in paths}


def admit_guarded_action(model_raw, shield_raw, guard_raw, state, action):
    """Executable proposal filter. Mathematical support requires receiving replay.

    All fields are receiver-parsed; unknown state/actions and failed, inconsistent
    or exhausted guard checks grant no admission. Deployment enforcement is OPEN.
    """
    if type(state) is not int or type(action) is not int:
        raise ShieldAssuranceError("exact integer state/action required")
    report = replay(model_raw, shield_raw, guard_raw)
    if report["model"]["outcome"] != "PASS" or report["guard"]["outcome"] != "PASS":
        return False
    if not shield.admit_action(model_raw, shield_raw, state, action):
        return False
    task = conditional.validate(_json(guard_raw))
    assignment = {name: pair == [state, action] for name, pair in report["guard"]["mapping"].items()}
    return conditional.evaluate(task["candidate"], assignment)


def _claims(model_raw, shield_raw, guard_raw):
    model = shield.load_model(model_raw)
    binding = f"model={sha(model_raw)};shield={sha(shield_raw)};guard={sha(guard_raw)}"
    return [{"id": ident, "statement": statement, "kind": "formal" if ident in {"C_MODEL_SAFE", "C_GUARD_EQ"} else "empirical",
        "required_evidence": [], "assumptions": [x["id"] for x in model["assumptions"]],
        "predicate": {"type": "external", "namespace": FORMAT, "proposition": f"{ident};{binding};{statement}"}}
        for ident, statement in STATEMENTS.items()]


def build_bundle(model_path, shield_path, guard_path, work_directory, output_bundle,
                 private_key_path, public_key_path, *, expected_fingerprint, lean_authority_path=None):
    work, bundle = Path(work_directory).resolve(), Path(output_bundle).resolve()
    if work.exists() or bundle.exists() or bundle.is_relative_to(work):
        raise ShieldAssuranceError("new work and separate output paths required")
    model_raw, shield_raw, guard_raw = (Path(p).read_bytes() for p in (model_path, shield_path, guard_path))
    report = replay(model_raw, shield_raw, guard_raw)
    if report["model"]["outcome"] != "PASS" or report["guard"]["outcome"] != "PASS":
        raise ShieldAssuranceError("false model certificate or inequivalent guard")
    kernel = shield.kernel_replay(model_raw, shield_raw)
    if kernel["kernel_checked"] is not True:
        raise ShieldAssuranceError("fresh exact-model kernel proof required")
    pinned = implementation()
    binding = {"format": FORMAT, "implementation_sha256": {p: sha(raw) for p, raw in pinned.items()},
        "model_sha256": sha(model_raw), "shield_sha256": sha(shield_raw), "guard_sha256": sha(guard_raw),
        "proof_sha256": sha(shield.proof_source(model_raw, shield_raw)),
        "independent_human_review": False, "producer_proof_trusted": False}
    additions = {**pinned, "model.json": model_raw, "shield.json": shield_raw, "guard.json": guard_raw,
        f"{PREFIX}/proof.lean.txt": shield.proof_source(model_raw, shield_raw),
        FILES["binding"]: encode(binding), FILES["replay"]: encode(report),
        FILES["obligations"]: encode(obligations(model_raw, report))}
    stage = work / "project"
    stage.mkdir(parents=True)
    for path, raw in additions.items():
        target = stage / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    found = discover_project_v06(stage, subject=STATEMENTS["C_MODEL_SAFE"])
    manifest = found["manifest_draft"]
    manifest["assumptions"] = [{"id": x["id"], "statement": x["statement"]} for x in shield.load_model(model_raw)["assumptions"]]
    manifest["claims"], manifest["checks"] = _claims(model_raw, shield_raw, guard_raw), []
    manifest["artifacts"] = [{"id": x["artifact_id"], "path": x["path"], "role": x["role"], "media_type": x["media_type"],
        "metadata": {"pcs_discovery_sha256": x["sha256"], "pcs_discovery_size": x["size"]}} for x in found["inventory"]]
    draft, confirmed = stage / "pcs-manifest.draft.json", stage / "manifest.confirmed.json"
    draft.write_bytes(encode(manifest))
    confirm_manifest_draft_v06(draft, confirmed, project_root=stage)
    package = work / "package"
    build_attestation_directory_v06(confirmed, package, private_key_path, public_key_path,
        expected_fingerprint=expected_fingerprint, generated_at="2026-10-14T00:00:00+00:00", lean_authority_path=lean_authority_path)
    create_verified_bundle_v06(package, bundle, public_key_path, expected_fingerprint=expected_fingerprint, lean_authority_path=lean_authority_path)
    return verify_bundle(bundle, public_key_path, expected_fingerprint=expected_fingerprint, lean_authority_path=lean_authority_path)


def verify_bundle(bundle, public_key_path, *, expected_fingerprint, lean_authority_path=None):
    base = {"format": FORMAT, "pcs_package_valid": False, "independent_replay_consistent": False,
        "formal_model_supported": False, "bounded_assurance_satisfied": False,
        "deployment_safety": "OPEN", "liveness": "OPEN", "scientific_acceptance": False,
        "independent_human_review": False, "producer_proof_trusted": False, "errors": []}
    try:
        verification = verify_package_zip_end_to_end_v06(bundle, public_key_path,
            expected_fingerprint=expected_fingerprint, lean_authority_path=lean_authority_path)
        base["pcs_package_valid"] = verification["valid"]
        if not verification["valid"] or not verification["accepted"]:
            raise ShieldAssuranceError("existing signed package authority rejected")
        loaded = load_package_zip_v06(bundle)
        certificate = _json(loaded["certificate_bytes"])
        sources = {}
        for item in certificate["artifacts"]:
            path = item["source_path"]
            if path in sources:
                raise ShieldAssuranceError("duplicate signed source path")
            sources[path] = loaded["package_files"][item["path"]]
        pinned = implementation()
        expected_paths = set(pinned) | set(FILES.values()) | {"model.json", "shield.json", "guard.json", f"{PREFIX}/proof.lean.txt"}
        if set(sources) != expected_paths or any(sources[p] != raw for p, raw in pinned.items()):
            raise ShieldAssuranceError("receiving source or exact artifact inventory mismatch")
        model_raw, shield_raw, guard_raw = (sources[p] for p in ("model.json", "shield.json", "guard.json"))
        report = replay(model_raw, shield_raw, guard_raw)
        proof = shield.proof_source(model_raw, shield_raw)
        expected_binding = {"format": FORMAT, "implementation_sha256": {p: sha(raw) for p, raw in pinned.items()},
            "model_sha256": sha(model_raw), "shield_sha256": sha(shield_raw), "guard_sha256": sha(guard_raw),
            "proof_sha256": sha(proof), "independent_human_review": False, "producer_proof_trusted": False}
        if sources[FILES["binding"]] != encode(expected_binding) or sources[f"{PREFIX}/proof.lean.txt"] != proof:
            raise ShieldAssuranceError("source/claim/proof binding mismatch")
        if sources[FILES["replay"]] != encode(report) or sources[FILES["obligations"]] != encode(obligations(model_raw, report)):
            raise ShieldAssuranceError("producer report differs from fresh receiving replay")
        expected_claims = _claims(model_raw, shield_raw, guard_raw)
        fields = {"id", "statement", "kind", "required_evidence", "assumptions", "predicate"}
        if [{k: x[k] for k in fields} for x in certificate["claims"]] != expected_claims or certificate["evidence"]:
            raise ShieldAssuranceError("unexpected claims or producer evidence authority")
        if certificate["assumptions"] != [{"id": x["id"], "statement": x["statement"], "scope": list(STATEMENTS)} for x in shield.load_model(model_raw)["assumptions"]]:
            raise ShieldAssuranceError("changed explicit deployment premises")
        if any(x["decision"] != "OPEN" for x in verification["claims"]):
            raise ShieldAssuranceError("unregistered claims must remain OPEN in base certificate authority")
        kernel = shield.kernel_replay(model_raw, shield_raw)
        supported = kernel["kernel_checked"] is True and report["model"]["outcome"] == "PASS"
        return {**base, "pcs_verification": verification, "independent_replay_consistent": True,
            "formal_model_supported": supported, "bounded_assurance_satisfied": supported and report["guard"]["outcome"] == "PASS",
            "domain_replay": report, "kernel_replay": kernel,
            "obligations": obligations(model_raw, report, kernel_checked=supported), "bundle_sha256": sha(Path(bundle).read_bytes())}
    except (ValueError, KeyError, TypeError, UnicodeError, OSError, RecursionError) as exc:
        return {**base, "errors": [f"receiving assurance rejected: {type(exc).__name__}: {exc}"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--fingerprint", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output must be new; historical evidence is never replaced")
    result = verify_bundle(args.bundle, args.public_key, expected_fingerprint=args.fingerprint)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as output:
        output.write(encode(result) + b"\n")
    print(encode({k: result[k] for k in ("pcs_package_valid", "formal_model_supported", "bounded_assurance_satisfied", "deployment_safety", "scientific_acceptance", "errors")}).decode())
    return 0 if result["bounded_assurance_satisfied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
