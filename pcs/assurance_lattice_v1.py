"""Proof-carrying epistemic composition — assurance lattice receiving kernel.

Evidence classes are strata, not interchangeable PASS tokens. Composition is a
typed morphism; silent cross-stratum promotion is rejected without an explicit
bridge; changed artifacts reopen dependent claims. Fresh Lean replay is required
for formal model support. This module does not grant scientific acceptance or
production package authority.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any

from .canonical_json import canonicalize_jcs_bytes
from .jsonio import strict_json_loads

FORMAT = "pcs-assurance-lattice-v1"
REPORT_FORMAT = "pcs-assurance-lattice-replay-v1"
KERNEL_FORMAT = "pcs-assurance-lattice-kernel-replay-v1"
MAX_BYTES = 2 * 1024 * 1024
MAX_CLAIMS = 64
MAX_EVIDENCE = 128
MAX_BRIDGES = 64
MAX_DEPS = 32
STRATA = ("unverified", "provenance", "computational", "formal", "empirical")
_ROOT = Path(__file__).resolve().parents[1]
_FORMAL = _ROOT / "formal" / "PCSAssuranceLattice.lean"

# Strength order: evidence may discharge requirement when (evidence, required) is listed.
_DISCHARGE: set[tuple[str, str]] = {
    ("unverified", "unverified"),
    ("provenance", "provenance"),
    ("computational", "provenance"),
    ("computational", "computational"),
    ("formal", "provenance"),
    ("formal", "computational"),
    ("formal", "formal"),
    ("empirical", "empirical"),
}


class AssuranceLatticeError(ValueError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(raw: bytes) -> Any:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise AssuranceLatticeError("input must be bytes within the 2 MiB limit")
    try:
        return strict_json_loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise AssuranceLatticeError("invalid strict UTF-8 JSON") from exc


def _object(value: Any, keys: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise AssuranceLatticeError(f"{label} must have exactly the declared fields")
    return value


def _nat(value: Any, label: str) -> int:
    if type(value) is not int or not 0 <= value < 65536:
        raise AssuranceLatticeError(f"{label} must be an exact natural below 65536")
    return value


def _stratum(value: Any, label: str) -> str:
    if value not in STRATA:
        raise AssuranceLatticeError(f"{label} must be one of {STRATA}")
    return value


def _ids(value: Any, maximum: int, label: str) -> list[int]:
    if not isinstance(value, list) or len(value) > maximum:
        raise AssuranceLatticeError(f"{label} list exceeds its resource bound")
    values = [_nat(x, label) for x in value]
    if values != sorted(set(values)):
        raise AssuranceLatticeError(f"{label} must contain sorted unique IDs")
    return values


def load_package(package_raw: bytes) -> dict:
    package = _object(_json(package_raw), {
        "format", "claims", "evidence", "bridges", "changed_artifacts", "assumptions",
    }, "package")
    if package["format"] != FORMAT:
        raise AssuranceLatticeError("unsupported assurance-lattice format")
    claims = package["claims"]
    if not isinstance(claims, list) or not 1 <= len(claims) <= MAX_CLAIMS:
        raise AssuranceLatticeError("claim count outside 1..64")
    parsed_claims = []
    seen_ids: set[int] = set()
    for claim in claims:
        claim = _object(claim, {
            "id", "required", "artifact_deps", "premise_claims",
        }, "claim")
        cid = _nat(claim["id"], "claim id")
        if cid in seen_ids:
            raise AssuranceLatticeError("claim IDs must be unique")
        seen_ids.add(cid)
        parsed_claims.append({
            "id": cid,
            "required": _stratum(claim["required"], "required stratum"),
            "artifact_deps": _ids(claim["artifact_deps"], MAX_DEPS, "artifact_deps"),
            "premise_claims": _ids(claim["premise_claims"], MAX_DEPS, "premise_claims"),
        })
    evidence = package["evidence"]
    if not isinstance(evidence, list) or len(evidence) > MAX_EVIDENCE:
        raise AssuranceLatticeError("evidence count exceeds 128")
    parsed_evidence = []
    for atom in evidence:
        atom = _object(atom, {"claim_id", "stratum", "accepted"}, "evidence")
        if type(atom["accepted"]) is not bool:
            raise AssuranceLatticeError("evidence accepted flag must be a boolean")
        parsed_evidence.append({
            "claim_id": _nat(atom["claim_id"], "evidence claim_id"),
            "stratum": _stratum(atom["stratum"], "evidence stratum"),
            "accepted": atom["accepted"],
        })
    bridges = package["bridges"]
    if not isinstance(bridges, list) or len(bridges) > MAX_BRIDGES:
        raise AssuranceLatticeError("bridge count exceeds 64")
    parsed_bridges = []
    for bridge in bridges:
        bridge = _object(bridge, {
            "claim_id", "from_stratum", "to_stratum", "accepted",
        }, "bridge")
        if type(bridge["accepted"]) is not bool:
            raise AssuranceLatticeError("bridge accepted flag must be a boolean")
        parsed_bridges.append({
            "claim_id": _nat(bridge["claim_id"], "bridge claim_id"),
            "from_stratum": _stratum(bridge["from_stratum"], "from_stratum"),
            "to_stratum": _stratum(bridge["to_stratum"], "to_stratum"),
            "accepted": bridge["accepted"],
        })
    changed = _ids(package["changed_artifacts"], MAX_DEPS, "changed_artifacts")
    assumptions = package["assumptions"]
    if not isinstance(assumptions, list) or len(assumptions) != 3:
        raise AssuranceLatticeError("three explicit OPEN assumptions are required")
    required_ids = {
        "dependency_completeness",
        "bridge_soundness",
        "empirical_correspondence",
    }
    ids = []
    for item in assumptions:
        item = _object(item, {"id", "statement", "status"}, "assumption")
        if (not isinstance(item["id"], str) or not isinstance(item["statement"], str)
                or not 1 <= len(item["statement"]) <= 2048
                or item["status"] != "OPEN"):
            raise AssuranceLatticeError("assumptions must remain explicit and OPEN")
        ids.append(item["id"])
    if set(ids) != required_ids or ids != sorted(required_ids):
        raise AssuranceLatticeError("missing, duplicate or unordered assumption IDs")
    return {
        "format": FORMAT,
        "claims": parsed_claims,
        "evidence": parsed_evidence,
        "bridges": parsed_bridges,
        "changed_artifacts": changed,
        "assumptions": assumptions,
    }


def _discharges(atom: dict, claim: dict) -> bool:
    return (atom["accepted"] and atom["claim_id"] == claim["id"]
            and (atom["stratum"], claim["required"]) in _DISCHARGE)


def _bridge_upgrades(bridge: dict, atom: dict, claim: dict) -> bool:
    return (bridge["accepted"] and atom["accepted"]
            and bridge["claim_id"] == claim["id"] and atom["claim_id"] == claim["id"]
            and atom["stratum"] == bridge["from_stratum"]
            and (bridge["to_stratum"], claim["required"]) in _DISCHARGE)


def _supports(package: dict, claim: dict) -> bool:
    for atom in package["evidence"]:
        if _discharges(atom, claim):
            return True
        if any(_bridge_upgrades(b, atom, claim) for b in package["bridges"]):
            return True
    return False


def _find_claim(package: dict, claim_id: int) -> dict | None:
    for claim in package["claims"]:
        if claim["id"] == claim_id:
            return claim
    return None


def _premise_supported(package: dict, premise_id: int) -> bool:
    claim = _find_claim(package, premise_id)
    return claim is not None and _supports(package, claim)


def _premises_ok(package: dict, claim: dict) -> bool:
    return all(_premise_supported(package, pid) for pid in claim["premise_claims"])


def _depends_on_changed(package: dict, claim: dict) -> bool:
    changed = set(package["changed_artifacts"])
    return any(a in changed for a in claim["artifact_deps"])


def _claim_certified(package: dict, claim: dict) -> bool:
    return (_supports(package, claim) and _premises_ok(package, claim)
            and not _depends_on_changed(package, claim))


def _has_accepted(package: dict, claim: dict) -> bool:
    return any(e["accepted"] and e["claim_id"] == claim["id"] for e in package["evidence"])


def evaluate(package_raw: bytes) -> dict:
    """Independent finite lattice check; not itself kernel evidence."""
    package = load_package(package_raw)
    violations: list[dict] = []
    claim_ids = {c["id"] for c in package["claims"]}
    for atom in package["evidence"]:
        if atom["accepted"] and atom["claim_id"] not in claim_ids:
            violations.append({"kind": "orphan_evidence", "claim_id": atom["claim_id"]})
    for bridge in package["bridges"]:
        if bridge["accepted"] and bridge["claim_id"] not in claim_ids:
            violations.append({"kind": "orphan_bridge", "claim_id": bridge["claim_id"]})
    certified = []
    for claim in package["claims"]:
        if not _has_accepted(package, claim):
            continue
        if not _supports(package, claim):
            violations.append({
                "kind": "silent_promotion_or_unsupported",
                "claim_id": claim["id"],
                "required": claim["required"],
            })
        elif not _premises_ok(package, claim):
            violations.append({"kind": "missing_premise", "claim_id": claim["id"]})
        elif _depends_on_changed(package, claim):
            violations.append({"kind": "invalidated_by_change", "claim_id": claim["id"]})
        elif _claim_certified(package, claim):
            certified.append(claim["id"])
    outcome = "PASS" if not violations else "FAIL"
    return {
        "format": REPORT_FORMAT,
        "package_sha256": _sha(package_raw),
        "outcome": outcome,
        "violations": violations,
        "certified_claim_ids": certified,
        "checks": {
            "unique_claim_ids": True,
            "no_silent_promotion": not any(
                v["kind"] == "silent_promotion_or_unsupported" for v in violations),
            "composition_closed": not any(v["kind"] == "missing_premise" for v in violations),
            "invalidation_honored": not any(
                v["kind"] == "invalidated_by_change" for v in violations),
            "no_orphan_bindings": not any(
                v["kind"] in {"orphan_evidence", "orphan_bridge"} for v in violations),
        },
        "assumptions": package["assumptions"],
        "formal_model_support": "REQUIRES_FRESH_KERNEL_REPLAY",
        "scientific_acceptance": False,
        "empirical_validity": "OPEN",
        "continuum_accuracy": "OPEN",
        "cryptographic_attribution": "OPEN",
        "untrusted_project_code_executed": False,
    }


def formal_source() -> bytes:
    return _FORMAL.read_bytes()


def _lean_stratum(name: str) -> str:
    return {
        "unverified": "PCSAssuranceLattice.Stratum.unverified",
        "provenance": "PCSAssuranceLattice.Stratum.provenance",
        "computational": "PCSAssuranceLattice.Stratum.computational",
        "formal": "PCSAssuranceLattice.Stratum.formal",
        "empirical": "PCSAssuranceLattice.Stratum.empirical",
    }[name]


def proof_source(package_raw: bytes) -> bytes:
    """Generate only literal integer/enum data and fixed first-party proof text."""
    package = load_package(package_raw)
    claim_lits = []
    for c in package["claims"]:
        arts = "[" + ", ".join(str(x) for x in c["artifact_deps"]) + "]"
        premises = "[" + ", ".join(str(x) for x in c["premise_claims"]) + "]"
        claim_lits.append(
            f"⟨{c['id']}, {_lean_stratum(c['required'])}, {arts}, {premises}⟩")
    evidence_lits = []
    for e in package["evidence"]:
        accepted = "true" if e["accepted"] else "false"
        evidence_lits.append(
            f"⟨{e['claim_id']}, {_lean_stratum(e['stratum'])}, {accepted}⟩")
    bridge_lits = []
    for b in package["bridges"]:
        accepted = "true" if b["accepted"] else "false"
        bridge_lits.append(
            f"⟨{b['claim_id']}, {_lean_stratum(b['from_stratum'])}, "
            f"{_lean_stratum(b['to_stratum'])}, {accepted}⟩")
    changed = "[" + ", ".join(str(x) for x in package["changed_artifacts"]) + "]"
    claims = "[" + ", ".join(claim_lits) + "]"
    evidence = "[" + ", ".join(evidence_lits) + "]"
    bridges = "[" + ", ".join(bridge_lits) + "]"
    return (
        "import PCSAssuranceLattice\n"
        "set_option autoImplicit false\n"
        "set_option maxRecDepth 8192\n"
        "set_option maxHeartbeats 2000000\n"
        f"-- Exact package SHA256: {_sha(package_raw)}\n"
        "namespace PCSAssuranceLatticeReplay\n"
        "open PCSAssuranceLattice\n"
        f"def package : Package := ⟨{claims}, {evidence}, {bridges}, {changed}⟩\n"
        "theorem certificate_checked : check package = true := by decide\n"
        "theorem certificate_certified : Certified package :=\n"
        "  (check_iff_certified package).mp certificate_checked\n"
        "#print axioms certificate_checked\n"
        "#print axioms certificate_certified\n"
        "end PCSAssuranceLatticeReplay\n"
    ).encode("utf-8")


def kernel_replay(package_raw: bytes, *, timeout: float = 60) -> dict:
    """Fresh kernel replay of a private immutable source/data snapshot."""
    if type(timeout) not in {int, float} or not 0 < timeout <= 180:
        raise AssuranceLatticeError("kernel timeout must be within 0..180 seconds")
    report = evaluate(package_raw)
    generated = proof_source(package_raw)
    core = formal_source()
    base = {
        "format": KERNEL_FORMAT,
        "kernel_checked": False,
        "package_sha256": _sha(package_raw),
        "formal_source_sha256": _sha(core),
        "proof_sha256": _sha(generated),
        "python_outcome": report["outcome"],
        "theorem": "PCSAssuranceLatticeReplay.certificate_certified",
        "kernel_axioms": [],
        "scientific_acceptance": False,
        "producer_proof_trusted": False,
    }
    if report["outcome"] != "PASS":
        return {**base, "status": "PYTHON_REJECTED", "violations": report["violations"]}
    started = time.monotonic()
    try:
        version = subprocess.run(
            ["lean", "--version"], capture_output=True, text=True, timeout=10)
        if version.returncode != 0 or "version 4.28.0" not in version.stdout:
            return {**base, "status": "UNSUPPORTED_LEAN_VERSION"}
        with tempfile.TemporaryDirectory(prefix="pcs-assurance-lattice-") as td:
            private = Path(td)
            source = private / "PCSAssuranceLattice.lean"
            proof = private / "Replay.lean"
            source.write_bytes(core)
            proof.write_bytes(generated)
            env = dict(os.environ)
            env["LEAN_PATH"] = str(private)
            built = subprocess.run(
                ["lean", "-j1", "-M1024", "-o",
                 str(private / "PCSAssuranceLattice.olean"), str(source)],
                cwd=private, env=env, capture_output=True, text=True, timeout=timeout)
            if built.returncode:
                return {
                    **base,
                    "status": "FORMAL_SOURCE_REJECTED",
                    "output": (built.stdout + built.stderr)[-8192:],
                }
            replay = subprocess.run(
                ["lean", "-j1", "-M1024", str(proof)],
                cwd=private, env=env, capture_output=True, text=True, timeout=timeout)
            output = replay.stdout + replay.stderr
            if replay.returncode:
                return {**base, "status": "CERTIFICATE_REJECTED", "output": output[-8192:]}
            audit = re.findall(r"depends on axioms: \[([^\]]*)\]", output)
            empty = output.count("does not depend on any axioms")
            axioms = sorted({a.strip() for row in audit for a in row.split(",") if a.strip()})
            if len(audit) + empty != 2 or not set(axioms).issubset(
                    {"propext", "Classical.choice", "Quot.sound"}):
                return {**base, "status": "AXIOM_AUDIT_REJECTED", "output": output[-8192:]}
            return {
                **base,
                "kernel_checked": True,
                "status": "KERNEL_CHECKED",
                "kernel_axioms": axioms,
                "lean_version": version.stdout.strip(),
                "elapsed_seconds": round(time.monotonic() - started, 6),
                "certified_claim_ids": report["certified_claim_ids"],
            }
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {**base, "status": "UNAVAILABLE_OR_EXHAUSTED", "error": type(exc).__name__}


def adversarial_campaign(package_raw: bytes) -> dict:
    """Finite adversarial mutations that must not create silent formal support."""
    package = load_package(package_raw)
    mutations = []

    def _forged_formal(altered: dict, report: dict) -> bool:
        for claim in altered["claims"]:
            if claim["required"] != "formal" or claim["id"] not in report["certified_claim_ids"]:
                continue
            weak = any(
                e["accepted"] and e["claim_id"] == claim["id"]
                and e["stratum"] in {"computational", "empirical"}
                for e in altered["evidence"])
            bridged = any(
                b["accepted"] and b["claim_id"] == claim["id"] for b in altered["bridges"])
            if weak and not bridged:
                return True
        return False

    def mutate(label: str, transform) -> None:
        altered = json.loads(canonicalize_jcs_bytes(package).decode("utf-8"))
        transform(altered)
        raw = canonicalize_jcs_bytes(altered)
        report = evaluate(raw)
        mutations.append({
            "mutation": label,
            "outcome": report["outcome"],
            "violations": report["violations"],
            "forged_formal": _forged_formal(altered, report),
        })

    def computational_as_formal(p: dict) -> None:
        p["claims"] = [{
            "id": 0, "required": "formal", "artifact_deps": [1], "premise_claims": [],
        }]
        p["evidence"] = [{"claim_id": 0, "stratum": "computational", "accepted": True}]
        p["bridges"] = []
        p["changed_artifacts"] = []

    def empirical_as_formal(p: dict) -> None:
        p["claims"] = [{
            "id": 0, "required": "formal", "artifact_deps": [1], "premise_claims": [],
        }]
        p["evidence"] = [{"claim_id": 0, "stratum": "empirical", "accepted": True}]
        p["bridges"] = []
        p["changed_artifacts"] = []

    def drop_premise_evidence(p: dict) -> None:
        used_premises = {
            pid for c in p["claims"] for pid in c["premise_claims"]
            if any(e["accepted"] and e["claim_id"] == c["id"] for e in p["evidence"])
        }
        p["evidence"] = [
            e for e in p["evidence"]
            if not (e["accepted"] and e["claim_id"] in used_premises)
        ]

    def mark_artifact_changed(p: dict) -> None:
        p["changed_artifacts"] = sorted({
            *p["changed_artifacts"],
            *(a for c in p["claims"] for a in c["artifact_deps"]),
        })

    mutate("computational_as_formal", computational_as_formal)
    mutate("empirical_as_formal", empirical_as_formal)
    mutate("drop_premise_evidence", drop_premise_evidence)
    mutate("mark_artifact_changed", mark_artifact_changed)

    false_accepts = [m for m in mutations if m["outcome"] == "PASS" and m["forged_formal"]]
    return {
        "format": "pcs-assurance-lattice-adversarial-v1",
        "package_sha256": _sha(package_raw),
        "mutations": mutations,
        "false_formal_accepts": len(false_accepts),
        "campaign_pass": len(false_accepts) == 0,
        "scientific_acceptance": False,
    }


def command(args) -> int:
    package_raw = Path(args.package).read_bytes()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    report = evaluate(package_raw)
    (out / "python-replay.json").write_bytes(canonicalize_jcs_bytes(report))
    campaign = adversarial_campaign(package_raw)
    (out / "adversarial-campaign.json").write_bytes(canonicalize_jcs_bytes(campaign))
    if args.kernel:
        kernel = kernel_replay(package_raw, timeout=args.timeout)
        (out / "kernel-replay.json").write_bytes(canonicalize_jcs_bytes(kernel))
        (out / "Replay.lean").write_bytes(proof_source(package_raw))
        ok = report["outcome"] == "PASS" and kernel.get("kernel_checked") is True
    else:
        ok = report["outcome"] == "PASS"
    summary = {
        "format": "pcs-assurance-lattice-summary-v1",
        "package_sha256": _sha(package_raw),
        "python_outcome": report["outcome"],
        "adversarial_campaign_pass": campaign["campaign_pass"],
        "kernel_requested": bool(args.kernel),
        "scientific_acceptance": False,
    }
    (out / "summary.json").write_bytes(canonicalize_jcs_bytes(summary))
    return 0 if ok and campaign["campaign_pass"] else 1


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "assurance-lattice-v1",
        help="experimental typed epistemic composition; no PCS package authority")
    parser.add_argument("--package", required=True, help="assurance lattice package JSON")
    parser.add_argument("--output", required=True, help="evidence output directory")
    parser.add_argument("--kernel", action="store_true",
                        help="request fresh Lean kernel replay")
    parser.add_argument("--timeout", type=float, default=60,
                        help="kernel replay wall budget, at most 180 seconds")
    parser.set_defaults(func=command)
