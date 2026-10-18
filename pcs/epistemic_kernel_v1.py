"""Epistemic Stratification & Compositional Assurance Kernel (ESCA) v1.

Research-grade executable receiver for stratified scientific assurance:

* ordered epistemic strata with fail-closed promotion gates;
* compositional certificate meet with residual-obligation union;
* artifact-driven invalidation that reopens dependent claims;
* continuum/empirical/causal residuals that discrete ACCEPT cannot close.

This module does not grant scientific, clinical, regulatory, or causal authority.
It is intentionally independent of production Lean package authority.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .canonical_json import canonicalize_jcs_bytes
from .jsonio import strict_json_loads

FORMAT = "pcs-epistemic-certificate-v1"
COMPOSE_FORMAT = "pcs-epistemic-composition-v1"
INVALIDATION_FORMAT = "pcs-epistemic-invalidation-v1"
CAMPAIGN_FORMAT = "pcs-epistemic-campaign-v1"
BRIDGE_FORMAT = "pcs-epistemic-bridge-v1"
TRANSPORT_LIFT_FORMAT = "pcs-epistemic-transport-lift-v1"
LATTICE_FORMAT = "pcs-epistemic-lattice-v1"
ROOT = Path(__file__).resolve().parents[1]
FORMAL_ROOT = ROOT / "research" / "epistemic-stratification-v1" / "formal"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "epistemic_certificate_v1.schema.json"
STRATA = (
    "integrity",
    "computational",
    "formal",
    "continuum",
    "empirical",
    "causal",
)
STRATUM_RANK = {name: index for index, name in enumerate(STRATA)}
APPROVED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
PRINCIPAL_THEOREMS = [
    "PCSEpistemic.Stratum.formal_lt_continuum",
    "PCSEpistemic.Stratum.computational_lt_empirical",
    "PCSEpistemic.Stratum.meet_assoc",
    "PCSEpistemic.Stratum.meet_join_absorb",
    "PCSEpistemic.Stratum.discharge_table_complete",
    "PCSEpistemic.computational_cannot_assure_empirical",
    "PCSEpistemic.formal_cannot_assure_continuum",
    "PCSEpistemic.continuum_cannot_assure_causal",
    "PCSEpistemic.formal_support_keeps_continuum_residual",
    "PCSEpistemic.compose_meet_le_left",
    "PCSEpistemic.compose_meet_le_right",
    "PCSEpistemic.bad_bridge_rejected",
    "PCSEpistemic.checkSupportB_rejects_computational_to_empirical",
    "PCSEpistemic.Controls.positive_formal_support",
    "PCSEpistemic.Controls.negative_computational_to_empirical",
    "PCSEpistemic.Controls.negative_formal_to_continuum",
    "PCSEpistemic.Controls.composition_meet_is_computational",
    "PCSEpistemic.Controls.invalidation_marks_matrix_claim",
]
# Transport-kernel OPEN obligations that discrete ACCEPT cannot close.
TRANSPORT_OPEN_OBLIGATIONS = (
    "implementation_correspondence",
    "continuum_accuracy",
    "empirical_validity",
)


class EpistemicKernelError(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_stratum(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or value not in STRATUM_RANK:
        raise EpistemicKernelError(f"{field} must be one of {list(STRATA)}")
    return value


def _require_id(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value):
        raise EpistemicKernelError(f"{field} must be a bounded identifier")
    return value


def _require_text(value: Any, *, field: str, limit: int = 4096) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise EpistemicKernelError(f"{field} must be a non-empty string ≤ {limit} bytes")
    return value


def rank(stratum: str) -> int:
    return STRATUM_RANK[_require_stratum(stratum, field="stratum")]


def meet(a: str, b: str) -> str:
    return a if rank(a) <= rank(b) else b


def join(a: str, b: str) -> str:
    return b if rank(a) <= rank(b) else a


def can_discharge(evidence_stratum: str, claim_stratum: str) -> bool:
    return rank(claim_stratum) <= rank(evidence_stratum)


def forbidden_promotion(evidence_stratum: str, claim_stratum: str) -> bool:
    return rank(evidence_stratum) < rank(claim_stratum)


def validate_schema(certificate: dict[str, Any]) -> None:
    """Fail-closed structural schema check complementary to load_certificate."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - optional in minimal envs
        raise EpistemicKernelError("jsonschema is required for schema validation") from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(certificate), key=lambda e: list(e.path))
    if errors:
        raise EpistemicKernelError(f"schema validation failed: {errors[0].message}")


def lattice_self_check() -> dict[str, Any]:
    """Exhaustive finite lattice and discharge-table checks over all strata."""
    cases: dict[str, bool] = {}
    for a in STRATA:
        cases[f"meet_idempotent:{a}"] = meet(a, a) == a
        cases[f"join_idempotent:{a}"] = join(a, a) == a
        for b in STRATA:
            cases[f"meet_comm:{a}:{b}"] = meet(a, b) == meet(b, a)
            cases[f"join_comm:{a}:{b}"] = join(a, b) == join(b, a)
            cases[f"meet_le_left:{a}:{b}"] = rank(meet(a, b)) <= rank(a)
            cases[f"meet_le_right:{a}:{b}"] = rank(meet(a, b)) <= rank(b)
            cases[f"absorb_meet_join:{a}:{b}"] = meet(a, join(a, b)) == a
            cases[f"absorb_join_meet:{a}:{b}"] = join(a, meet(a, b)) == a
            for c in STRATA:
                cases[f"meet_assoc:{a}:{b}:{c}"] = meet(meet(a, b), c) == meet(a, meet(b, c))
                cases[f"join_assoc:{a}:{b}:{c}"] = join(join(a, b), c) == join(a, join(b, c))
            # Discharge table completeness: discharge ∨ forbidden ∨ equal.
            cases[f"discharge_complete:{a}:{b}"] = (
                can_discharge(a, b) or forbidden_promotion(a, b) or a == b
            )
            if forbidden_promotion(a, b):
                cases[f"forbidden_blocks:{a}:{b}"] = not can_discharge(a, b)
    return {
        "format": LATTICE_FORMAT,
        "cases": cases,
        "passed": all(cases.values()),
        "stratum_count": len(STRATA),
        "case_count": len(cases),
        "scientific_acceptance": False,
    }


def apply_bridge(
    bridge: dict[str, Any],
    residual: dict[str, Any],
    evidence: dict[str, Any],
    claim: dict[str, Any],
) -> dict[str, Any]:
    """Fail-closed typed residual bridge. Never silently raises stratum."""
    if not isinstance(bridge, dict) or not isinstance(residual, dict):
        raise EpistemicKernelError("bridge and residual objects required")
    if not isinstance(evidence, dict) or not isinstance(claim, dict):
        raise EpistemicKernelError("evidence and claim objects required")
    src = _require_stratum(bridge.get("src"), field="bridge.src")
    dst = _require_stratum(bridge.get("dst"), field="bridge.dst")
    residual_id = _require_id(bridge.get("residual_id"), field="bridge.residual_id")
    claim_stratum = _require_stratum(claim.get("stratum"), field="claim.stratum")
    residual_stratum = _require_stratum(residual.get("stratum"), field="residual.stratum")
    evidence_stratum = _require_stratum(evidence.get("stratum"), field="evidence.stratum")
    reasons = []
    well_typed = rank(src) < rank(dst)
    if not well_typed:
        reasons.append("bridge must strictly raise stratum")
    if residual.get("id") != residual_id:
        reasons.append("residual id does not match bridge")
    if residual_stratum != dst:
        reasons.append("residual stratum must equal bridge destination")
    if claim_stratum != dst:
        reasons.append("claim stratum must equal bridge destination")
    discharge_ok = (
        evidence.get("outcome") == "PASS"
        and evidence.get("predicate") == residual.get("reason")
        and can_discharge(evidence_stratum, residual_stratum)
    )
    if not discharge_ok:
        reasons.append("residual discharge evidence insufficient")
    accepted = (
        well_typed
        and residual.get("id") == residual_id
        and residual_stratum == dst
        and claim_stratum == dst
        and discharge_ok
    )
    if accepted:
        reasons = []
    return {
        "format": BRIDGE_FORMAT,
        "bridge": {"id": bridge.get("id"), "src": src, "dst": dst, "residual_id": residual_id},
        "accepted": accepted,
        "reasons": reasons,
        "scientific_acceptance": False,
        "note": "Bridge acceptance discharges only the named residual; broader strata remain OPEN.",
    }


def lift_transport_opens(
    *,
    claim_id: str = "C_transport",
    open_obligations: list[str] | None = None,
    discrete_supported: bool = True,
) -> dict[str, Any]:
    """Lift transport-kernel OPEN obligations into stratified residuals.

    Discrete/formal matrix support may be recorded, but continuum/empirical
    obligations remain OPEN residuals. This does not replay a transport package.
    """
    opens = list(open_obligations or TRANSPORT_OPEN_OBLIGATIONS)
    for name in opens:
        _require_id(name, field="open_obligation")
    residuals = []
    mapping = {
        "implementation_correspondence": ("formal", "Implementation correspondence remains OPEN."),
        "continuum_accuracy": ("continuum", "Continuum accuracy remains OPEN after discrete support."),
        "empirical_validity": ("empirical", "Empirical validity remains OPEN after discrete support."),
    }
    for name in opens:
        stratum, reason = mapping.get(name, ("empirical", f"Obligation {name} remains OPEN."))
        residuals.append(
            {
                "id": f"{claim_id}:{name}",
                "stratum": stratum,
                "reason": reason,
                "status": "OPEN",
            }
        )
    certificate = {
        "format": FORMAT,
        "assumptions": [
            {
                "id": "A_transport_model",
                "statement": "finite transport matrix assumptions are explicit",
            }
        ],
        "claim": {
            "id": claim_id,
            "stratum": "formal" if discrete_supported else "computational",
            "predicate": "transport-discrete-support",
            "required_evidence": ["E_transport_discrete"],
            "assumptions": ["A_transport_model"],
        },
        "evidence": [
            {
                "id": "E_transport_discrete",
                "stratum": "formal" if discrete_supported else "computational",
                "outcome": "PASS" if discrete_supported else "UNVERIFIED",
                "predicate": "transport-discrete-support",
                "artifact_ids": ["transport-contract.json"],
            }
        ],
        "stratum": "formal" if discrete_supported else "computational",
        "residuals": residuals,
        "scientific_acceptance": False,
    }
    assessment = assess(certificate)
    return {
        "format": TRANSPORT_LIFT_FORMAT,
        "open_obligations": opens,
        "certificate": certificate,
        "assessment": assessment,
        "continuum_residual_open": any(
            r["stratum"] == "continuum" and r["status"] == "OPEN" for r in assessment["residuals"]
        ),
        "empirical_residual_open": any(
            r["stratum"] == "empirical" and r["status"] == "OPEN" for r in assessment["residuals"]
        ),
        "scientific_acceptance": False,
        "accepted": assessment["accepted"] and any(
            r["stratum"] == "continuum" and r["status"] == "OPEN" for r in assessment["residuals"]
        ),
    }


def load_certificate(raw: bytes) -> dict[str, Any]:
    if len(raw) > 2 * 1024 * 1024:
        raise EpistemicKernelError("certificate exceeds 2 MiB")
    data = strict_json_loads(raw)
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise EpistemicKernelError(f"exact {FORMAT} required")
    allowed = {
        "format",
        "assumptions",
        "claim",
        "evidence",
        "stratum",
        "residuals",
        "scientific_acceptance",
    }
    extra = set(data) - allowed
    if extra:
        raise EpistemicKernelError(f"unsupported certificate fields: {sorted(extra)}")
    if data.get("scientific_acceptance", False) is not False:
        raise EpistemicKernelError("scientific_acceptance must be false")
    assumptions = data.get("assumptions")
    claim = data.get("claim")
    evidence = data.get("evidence")
    residuals = data.get("residuals", [])
    stratum = _require_stratum(data.get("stratum"), field="stratum")
    if not isinstance(assumptions, list) or not (1 <= len(assumptions) <= 64):
        raise EpistemicKernelError("bounded non-empty assumptions required")
    if not isinstance(evidence, list) or not (1 <= len(evidence) <= 64):
        raise EpistemicKernelError("bounded non-empty evidence required")
    if not isinstance(residuals, list) or len(residuals) > 64:
        raise EpistemicKernelError("bounded residuals required")
    if not isinstance(claim, dict):
        raise EpistemicKernelError("claim object required")
    claim_allowed = {"id", "stratum", "predicate", "required_evidence", "assumptions"}
    if set(claim) - claim_allowed:
        raise EpistemicKernelError(f"unsupported claim fields: {sorted(set(claim) - claim_allowed)}")
    parsed_assumptions = []
    for item in assumptions:
        if not isinstance(item, dict):
            raise EpistemicKernelError("assumption objects required")
        if set(item) - {"id", "statement"}:
            raise EpistemicKernelError("unsupported assumption fields")
        parsed_assumptions.append(
            {
                "id": _require_id(item.get("id"), field="assumption.id"),
                "statement": _require_text(item.get("statement", item.get("id")), field="assumption.statement"),
            }
        )
    parsed_evidence = []
    for item in evidence:
        if not isinstance(item, dict):
            raise EpistemicKernelError("evidence objects required")
        if set(item) - {"id", "stratum", "outcome", "predicate", "artifact_ids"}:
            raise EpistemicKernelError("unsupported evidence fields")
        artifacts = item.get("artifact_ids", [])
        if not isinstance(artifacts, list) or len(artifacts) > 32:
            raise EpistemicKernelError("bounded artifact_ids required")
        parsed_evidence.append(
            {
                "id": _require_id(item.get("id"), field="evidence.id"),
                "stratum": _require_stratum(item.get("stratum"), field="evidence.stratum"),
                "outcome": _require_text(item.get("outcome"), field="evidence.outcome", limit=32),
                "predicate": _require_text(item.get("predicate"), field="evidence.predicate"),
                "artifact_ids": [
                    _require_id(a, field="artifact_id") for a in artifacts
                ],
            }
        )
        if parsed_evidence[-1]["outcome"] not in {"PASS", "FAIL", "UNVERIFIED"}:
            raise EpistemicKernelError("evidence.outcome must be PASS|FAIL|UNVERIFIED")
    required = claim.get("required_evidence", [])
    claim_assumptions = claim.get("assumptions", [])
    if not isinstance(required, list) or not required or len(required) > 32:
        raise EpistemicKernelError("claim.required_evidence must be a bounded non-empty list")
    if not isinstance(claim_assumptions, list) or len(claim_assumptions) > 32:
        raise EpistemicKernelError("claim.assumptions must be a bounded list")
    parsed_claim = {
        "id": _require_id(claim.get("id"), field="claim.id"),
        "stratum": _require_stratum(claim.get("stratum"), field="claim.stratum"),
        "predicate": _require_text(claim.get("predicate"), field="claim.predicate"),
        "required_evidence": [_require_id(x, field="required_evidence") for x in required],
        "assumptions": [_require_id(x, field="claim.assumptions") for x in claim_assumptions],
    }
    parsed_residuals = []
    for item in residuals:
        if not isinstance(item, dict):
            raise EpistemicKernelError("residual objects required")
        if set(item) - {"id", "stratum", "reason", "status"}:
            raise EpistemicKernelError("unsupported residual fields")
        if item.get("status", "OPEN") != "OPEN":
            raise EpistemicKernelError("residual.status must be OPEN")
        parsed_residuals.append(
            {
                "id": _require_id(item.get("id"), field="residual.id"),
                "stratum": _require_stratum(item.get("stratum"), field="residual.stratum"),
                "reason": _require_text(item.get("reason"), field="residual.reason"),
                "status": "OPEN",
            }
        )
    if parsed_claim["stratum"] != stratum:
        raise EpistemicKernelError("certificate stratum must equal claim stratum")
    return {
        "format": FORMAT,
        "assumptions": parsed_assumptions,
        "claim": parsed_claim,
        "evidence": parsed_evidence,
        "stratum": stratum,
        "residuals": parsed_residuals,
        "scientific_acceptance": False,
    }


def implied_residuals(claim_id: str, stratum: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if rank(stratum) < rank("continuum"):
        out.append(
            {
                "id": f"{claim_id}:continuum-residual",
                "stratum": "continuum",
                "reason": (
                    "Discrete/formal support does not discharge continuum accuracy; "
                    "residual truncation/refinement obligations remain OPEN."
                ),
                "status": "OPEN",
            }
        )
    if rank(stratum) < rank("empirical"):
        out.append(
            {
                "id": f"{claim_id}:empirical-residual",
                "stratum": "empirical",
                "reason": (
                    "Continuum residual bounds do not discharge empirical/statistical "
                    "adequacy; observational validation remains OPEN."
                ),
                "status": "OPEN",
            }
        )
    if rank(stratum) < rank("causal"):
        out.append(
            {
                "id": f"{claim_id}:causal-residual",
                "stratum": "causal",
                "reason": (
                    "Empirical association does not discharge causal/external-world "
                    "claims; identification assumptions remain OPEN."
                ),
                "status": "OPEN",
            }
        )
    return out


def assess(certificate: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(certificate, dict) or certificate.get("format") != FORMAT:
        raise EpistemicKernelError(f"exact {FORMAT} required")
    # Re-validate through the loader so callers cannot smuggle extra fields.
    cert = load_certificate(canonicalize_jcs_bytes(certificate))
    claim = cert["claim"]
    assumption_ids = {a["id"] for a in cert["assumptions"]}
    missing_context = [aid for aid in claim["assumptions"] if aid not in assumption_ids]
    evidence_map = {e["id"]: e for e in cert["evidence"]}
    if len(evidence_map) != len(cert["evidence"]):
        raise EpistemicKernelError("duplicate evidence ids are rejected")
    promotions = []
    discharging = []
    for eid in claim["required_evidence"]:
        ev = evidence_map.get(eid)
        if ev is None:
            continue
        if forbidden_promotion(ev["stratum"], claim["stratum"]):
            promotions.append(
                {
                    "evidence_id": eid,
                    "evidence_stratum": ev["stratum"],
                    "claim_stratum": claim["stratum"],
                }
            )
        if (
            ev["outcome"] == "PASS"
            and ev["predicate"] == claim["predicate"]
            and can_discharge(ev["stratum"], claim["stratum"])
        ):
            discharging.append(eid)
    failed = [eid for eid in claim["required_evidence"] if evidence_map.get(eid, {}).get("outcome") == "FAIL"]
    residuals = list(cert["residuals"])
    for residual in implied_residuals(claim["id"], cert["stratum"]):
        if all(existing["id"] != residual["id"] for existing in residuals):
            residuals.append(residual)
    if missing_context:
        status = "OPEN"
        reason = "assumption context incomplete"
    elif failed:
        status = "FALSIFIED_OR_CHECK_FAILED"
        reason = "required evidence failed"
    elif promotions and not discharging:
        status = "OPEN"
        reason = "forbidden promotion: evidence stratum below claim stratum"
    elif not discharging:
        status = "OPEN"
        reason = "no predicate-bound passing evidence at sufficient stratum"
    else:
        status = "STRATIFIED_SUPPORT"
        reason = "passing evidence discharges the claim stratum; residuals remain OPEN"
    return {
        "format": "pcs-epistemic-assessment-v1",
        "claim_id": claim["id"],
        "stratum": cert["stratum"],
        "status": status,
        "reason": reason,
        "discharging_evidence": discharging,
        "forbidden_promotions": promotions,
        "residuals": residuals,
        "scientific_acceptance": False,
        "accepted": status == "STRATIFIED_SUPPORT",
    }


def compose(left_raw: bytes, right_raw: bytes) -> dict[str, Any]:
    left = load_certificate(left_raw)
    right = load_certificate(right_raw)
    left_assess = assess(left)
    right_assess = assess(right)
    cites = any(a["id"] == left["claim"]["id"] for a in right["assumptions"])
    if not cites:
        raise EpistemicKernelError(
            "downstream certificate must cite upstream claim id as an assumption"
        )
    if not left_assess["accepted"] or not right_assess["accepted"]:
        raise EpistemicKernelError("both certificates must independently assess as supported")
    # Retain the upstream claim as a discharged assumption so the downstream
    # claim's context coverage still holds after cut/composition.
    merged_assumptions = list(left["assumptions"])
    seen = {a["id"] for a in merged_assumptions}
    if left["claim"]["id"] not in seen:
        merged_assumptions.append(
            {
                "id": left["claim"]["id"],
                "statement": f"supported claim {left['claim']['id']} at stratum",
            }
        )
        seen.add(left["claim"]["id"])
    for assumption in right["assumptions"]:
        if assumption["id"] not in seen:
            merged_assumptions.append(assumption)
            seen.add(assumption["id"])
    merged_evidence = list(left["evidence"])
    evidence_ids = {e["id"] for e in merged_evidence}
    for item in right["evidence"]:
        if item["id"] in evidence_ids:
            prior = next(e for e in merged_evidence if e["id"] == item["id"])
            if prior != item:
                raise EpistemicKernelError("conflicting evidence ids during composition")
            continue
        merged_evidence.append(item)
        evidence_ids.add(item["id"])
    result_stratum = meet(left["stratum"], right["stratum"])
    residuals: list[dict[str, str]] = []
    seen_residuals: set[str] = set()
    for residual in (
        left_assess["residuals"]
        + right_assess["residuals"]
        + implied_residuals(right["claim"]["id"], result_stratum)
    ):
        if residual["id"] in seen_residuals:
            continue
        residuals.append({**residual, "status": "OPEN"})
        seen_residuals.add(residual["id"])
    composed = {
        "format": FORMAT,
        "assumptions": merged_assumptions,
        "claim": right["claim"],
        "evidence": merged_evidence,
        "stratum": result_stratum,
        "residuals": residuals,
        "scientific_acceptance": False,
    }
    # Re-index claim stratum to the meet; composition never raises assurance.
    composed["claim"] = {**right["claim"], "stratum": result_stratum}
    assessment = assess(composed)
    return {
        "format": COMPOSE_FORMAT,
        "left_sha256": sha(left_raw),
        "right_sha256": sha(right_raw),
        "result_stratum": result_stratum,
        "composed": composed,
        "assessment": assessment,
        "scientific_acceptance": False,
        "accepted": assessment["accepted"],
    }


def invalidate(certificate_raw: bytes, changed_artifacts: list[str]) -> dict[str, Any]:
    cert = load_certificate(certificate_raw)
    if not changed_artifacts or len(changed_artifacts) > 64:
        raise EpistemicKernelError("bounded non-empty changed_artifacts required")
    changed = [_require_id(a, field="changed_artifact") for a in changed_artifacts]
    changed_set = set(changed)
    affected_evidence = [
        e["id"] for e in cert["evidence"] if changed_set.intersection(e["artifact_ids"])
    ]
    affected_set = set(affected_evidence)
    affected_claims = []
    if affected_set.intersection(cert["claim"]["required_evidence"]):
        affected_claims.append(cert["claim"]["id"])
    marked = []
    for evidence in cert["evidence"]:
        item = dict(evidence)
        if evidence["id"] in affected_set:
            item["outcome"] = "UNVERIFIED"
        marked.append(item)
    reopened = {
        "format": FORMAT,
        "assumptions": cert["assumptions"],
        "claim": cert["claim"],
        "evidence": marked,
        "stratum": cert["stratum"],
        "residuals": cert["residuals"]
        + [
            {
                "id": f"{cert['claim']['id']}:invalidated",
                "stratum": cert["stratum"],
                "reason": "dependent artifact bytes changed; prior stratified support is OPEN",
                "status": "OPEN",
            }
        ]
        if affected_claims
        else cert["residuals"],
        "scientific_acceptance": False,
    }
    assessment = assess(reopened) if affected_claims else assess(cert)
    if affected_claims:
        assessment = {
            **assessment,
            "status": "OPEN",
            "reason": "artifact invalidation reopened dependent claims",
            "accepted": False,
        }
    return {
        "format": INVALIDATION_FORMAT,
        "certificate_sha256": sha(certificate_raw),
        "changed_artifacts": changed,
        "affected_evidence": affected_evidence,
        "affected_claims": affected_claims,
        "reopened": reopened,
        "assessment": assessment,
        "scientific_acceptance": False,
        "accepted": False if affected_claims else assessment["accepted"],
    }


def _fixture_cert(*, stratum: str, evidence_stratum: str, claim_id: str, predicate: str,
                  evidence_id: str, artifacts: list[str], cite: str | None = None) -> dict[str, Any]:
    assumptions = [
        {"id": "A_model", "statement": "bounded finite model assumptions are explicit"},
    ]
    claim_assumptions = ["A_model"]
    if cite:
        assumptions.append({"id": cite, "statement": f"upstream claim {cite}"})
        claim_assumptions.append(cite)
    return {
        "format": FORMAT,
        "assumptions": assumptions,
        "claim": {
            "id": claim_id,
            "stratum": stratum,
            "predicate": predicate,
            "required_evidence": [evidence_id],
            "assumptions": claim_assumptions,
        },
        "evidence": [
            {
                "id": evidence_id,
                "stratum": evidence_stratum,
                "outcome": "PASS",
                "predicate": predicate,
                "artifact_ids": artifacts,
            }
        ],
        "stratum": stratum,
        "residuals": implied_residuals(claim_id, stratum),
        "scientific_acceptance": False,
    }


def run_campaign() -> dict[str, Any]:
    """Deterministic adversarial campaign: promotion, composition, residual, invalidation."""
    formal = _fixture_cert(
        stratum="formal",
        evidence_stratum="formal",
        claim_id="C_discrete",
        predicate="amount-conserved",
        evidence_id="E_matrix",
        artifacts=["matrix.json"],
    )
    false_empirical = _fixture_cert(
        stratum="empirical",
        evidence_stratum="computational",
        claim_id="C_world",
        predicate="amount-conserved",
        evidence_id="E_matrix",
        artifacts=["matrix.json"],
    )
    false_continuum = _fixture_cert(
        stratum="continuum",
        evidence_stratum="formal",
        claim_id="C_continuum",
        predicate="amount-conserved",
        evidence_id="E_matrix",
        artifacts=["matrix.json"],
    )
    downstream = _fixture_cert(
        stratum="computational",
        evidence_stratum="computational",
        claim_id="C_pipeline",
        predicate="pipeline-ok",
        evidence_id="E_pipe",
        artifacts=["pipe.json"],
        cite="C_discrete",
    )
    formal_assessment = assess(formal)
    false_empirical_assessment = assess(false_empirical)
    false_continuum_assessment = assess(false_continuum)
    composition = compose(
        canonicalize_jcs_bytes(formal),
        canonicalize_jcs_bytes(downstream),
    )
    invalidation = invalidate(canonicalize_jcs_bytes(formal), ["matrix.json"])
    lattice = lattice_self_check()
    bad_bridge = apply_bridge(
        {
            "id": "B_bad",
            "src": "formal",
            "dst": "continuum",
            "residual_id": "R_continuum",
        },
        {
            "id": "R_continuum",
            "stratum": "continuum",
            "reason": "continuum-accuracy",
        },
        {
            "id": "E_comp",
            "stratum": "computational",
            "outcome": "PASS",
            "predicate": "continuum-accuracy",
        },
        {
            "id": "C_continuum",
            "stratum": "continuum",
        },
    )
    transport_lift = lift_transport_opens()
    predicate_mismatch = assess(
        {
            **formal,
            "evidence": [
                {
                    **formal["evidence"][0],
                    "predicate": "different-predicate",
                }
            ],
        }
    )
    failed_evidence = assess(
        {
            **formal,
            "evidence": [
                {
                    **formal["evidence"][0],
                    "outcome": "FAIL",
                }
            ],
        }
    )
    cases = {
        "positive_formal_support": formal_assessment["accepted"] is True,
        "reject_computational_to_empirical": (
            false_empirical_assessment["accepted"] is False
            and bool(false_empirical_assessment["forbidden_promotions"])
        ),
        "reject_formal_to_continuum": false_continuum_assessment["accepted"] is False,
        "formal_keeps_continuum_residual": any(
            r["stratum"] == "continuum" and r["status"] == "OPEN"
            for r in formal_assessment["residuals"]
        ),
        "composition_meet_computational": composition["accepted"]
        and composition["result_stratum"] == "computational",
        "composition_preserves_residuals": any(
            r["stratum"] == "continuum" for r in composition["composed"]["residuals"]
        ),
        "invalidation_reopens_claim": invalidation["affected_claims"] == ["C_discrete"]
        and invalidation["accepted"] is False,
        "lattice_self_check": lattice["passed"] is True,
        "reject_computational_continuum_bridge": bad_bridge["accepted"] is False,
        "transport_lift_keeps_continuum_open": transport_lift["continuum_residual_open"] is True,
        "transport_lift_keeps_empirical_open": transport_lift["empirical_residual_open"] is True,
        "reject_predicate_mismatch": predicate_mismatch["accepted"] is False,
        "reject_failed_evidence": failed_evidence["status"] == "FALSIFIED_OR_CHECK_FAILED",
    }
    return {
        "format": CAMPAIGN_FORMAT,
        "cases": cases,
        "passed": all(cases.values()),
        "details": {
            "formal_assessment": formal_assessment,
            "false_empirical_assessment": false_empirical_assessment,
            "false_continuum_assessment": false_continuum_assessment,
            "composition": {
                "accepted": composition["accepted"],
                "result_stratum": composition["result_stratum"],
                "residual_strata": sorted({r["stratum"] for r in composition["composed"]["residuals"]}),
            },
            "invalidation": {
                "affected_claims": invalidation["affected_claims"],
                "affected_evidence": invalidation["affected_evidence"],
                "accepted": invalidation["accepted"],
            },
            "lattice": {
                "passed": lattice["passed"],
                "case_count": lattice["case_count"],
            },
            "bad_bridge": bad_bridge,
            "transport_lift": {
                "accepted": transport_lift["accepted"],
                "continuum_residual_open": transport_lift["continuum_residual_open"],
                "empirical_residual_open": transport_lift["empirical_residual_open"],
            },
        },
        "scientific_acceptance": False,
        "theorem_targets": PRINCIPAL_THEOREMS,
    }


def _lean_available() -> bool:
    return shutil.which("lean") is not None and shutil.which("lake") is not None


def kernel_audit(*, timeout: float = 180.0) -> dict[str, Any]:
    """Optionally compile the research Lean library and audit principal axioms."""
    if not _lean_available():
        return {
            "format": "pcs-epistemic-lean-audit-v1",
            "attempted": False,
            "accepted": False,
            "reason": "lean/lake not available in PATH",
            "scientific_acceptance": False,
        }
    if timeout <= 0 or timeout > 180:
        raise EpistemicKernelError("timeout must be in (0, 180]")
    env = os.environ.copy()
    with tempfile.TemporaryDirectory(prefix="pcs-epistemic-") as folder:
        work = Path(folder)
        # Copy only the research library sources into an isolated Lake package.
        pkg = work / "pkg"
        (pkg / "PCSEpistemic").mkdir(parents=True)
        shutil.copy2(FORMAL_ROOT / "PCSEpistemic.lean", pkg / "PCSEpistemic.lean")
        for path in sorted((FORMAL_ROOT / "PCSEpistemic").glob("*.lean")):
            shutil.copy2(path, pkg / "PCSEpistemic" / path.name)
        (pkg / "lakefile.toml").write_text(
            'name = "PCSEpistemic"\nversion = "0.1.0"\n\n[[lean_lib]]\n'
            'name = "PCSEpistemic"\nroots = ["PCSEpistemic"]\n'
            'defaultFacets = ["leanArts"]\n',
            encoding="utf-8",
        )
        (pkg / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
        build = subprocess.run(
            ["lake", "build", "PCSEpistemic"],
            cwd=pkg,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if build.returncode != 0:
            return {
                "format": "pcs-epistemic-lean-audit-v1",
                "attempted": True,
                "accepted": False,
                "reason": "lake build failed",
                "stdout_tail": build.stdout[-4000:],
                "stderr_tail": build.stderr[-4000:],
                "scientific_acceptance": False,
            }
        printer = pkg / "PrintAxioms.lean"
        printer.write_text(
            "import PCSEpistemic\n"
            + "\n".join(f"#print axioms {name}" for name in PRINCIPAL_THEOREMS)
            + "\n",
            encoding="utf-8",
        )
        printed = subprocess.run(
            ["lake", "env", "lean", str(printer)],
            cwd=pkg,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if printed.returncode != 0:
            return {
                "format": "pcs-epistemic-lean-audit-v1",
                "attempted": True,
                "accepted": False,
                "reason": "axiom inventory failed",
                "stderr_tail": printed.stderr[-4000:],
                "scientific_acceptance": False,
            }
        inventory = {}
        current = None
        for line in printed.stdout.splitlines():
            if line.startswith("'") and "' depends on axioms:" in line:
                current = line.split("'")[1]
                inventory[current] = []
            elif current and line.strip():
                for part in line.replace("[", "").replace("]", "").split(","):
                    name = part.strip()
                    if name:
                        inventory[current].append(name)
        bad = {
            name: axioms
            for name, axioms in inventory.items()
            if not set(axioms) <= APPROVED_AXIOMS and axioms != ["'[anonymous]'"] and axioms
        }
        # Lean prints "depends on axioms: [propext, ...]" or "does not depend on any axioms"
        normalized = {}
        for name in PRINCIPAL_THEOREMS:
            short = name.split(".")[-1]
            matched = None
            for key, axioms in inventory.items():
                if key.endswith(name) or key.endswith(short) or key == name:
                    matched = axioms
                    break
            normalized[name] = matched if matched is not None else ["MISSING"]
        missing = [name for name, axioms in normalized.items() if axioms == ["MISSING"]]
        unapproved = {
            name: axioms
            for name, axioms in normalized.items()
            if axioms != ["MISSING"] and not set(axioms) <= APPROVED_AXIOMS
        }
        # Re-parse using full print output more carefully.
        inventory = {}
        for name in PRINCIPAL_THEOREMS:
            pattern = rf"'{re.escape(name)}' (?:depends on axioms: (\[.*?\])|does not depend on any axioms)"
            match = re.search(pattern, printed.stdout, flags=re.S)
            if not match:
                inventory[name] = ["MISSING"]
            elif match.group(1) is None:
                inventory[name] = []
            else:
                axioms = [
                    part.strip().strip("'")
                    for part in match.group(1).strip("[]").split(",")
                    if part.strip()
                ]
                inventory[name] = axioms
        missing = [name for name, axioms in inventory.items() if axioms == ["MISSING"]]
        unapproved = {
            name: axioms
            for name, axioms in inventory.items()
            if axioms != ["MISSING"] and any(a not in APPROVED_AXIOMS for a in axioms)
        }
        accepted = not missing and not unapproved
        return {
            "format": "pcs-epistemic-lean-audit-v1",
            "attempted": True,
            "accepted": accepted,
            "inventory": inventory,
            "missing": missing,
            "unapproved": unapproved,
            "approved_axioms": sorted(APPROVED_AXIOMS),
            "scientific_acceptance": False,
            "source_sha256": {
                path.name: sha(path.read_bytes())
                for path in sorted((FORMAL_ROOT / "PCSEpistemic").glob("*.lean"))
            },
        }


def export_evidence(output: Path, result: dict[str, Any]) -> None:
    output = Path(output)
    if output.exists():
        raise EpistemicKernelError(f"refusing to replace existing evidence directory: {output}")
    output.mkdir(parents=True)
    (output / "RESULT.json").write_bytes(canonicalize_jcs_bytes(result))
    inventory = {
        str(path.relative_to(output)): sha(path.read_bytes())
        for path in sorted(output.rglob("*"))
        if path.is_file()
    }
    (output / "SHA256.json").write_bytes(canonicalize_jcs_bytes(inventory))


def command(args) -> int:
    try:
        if args.mode == "campaign":
            result = run_campaign()
            if args.lean_audit:
                result = {**result, "lean_audit": kernel_audit(timeout=args.timeout)}
                result["passed"] = result["passed"] and result["lean_audit"].get("accepted", False)
        elif args.mode == "assess":
            cert = load_certificate(Path(args.certificate).read_bytes())
            if args.schema:
                validate_schema(cert)
            result = assess(cert)
        elif args.mode == "compose":
            result = compose(Path(args.left).read_bytes(), Path(args.right).read_bytes())
        elif args.mode == "invalidate":
            changed = json.loads(Path(args.changed).read_text(encoding="utf-8"))
            if not isinstance(changed, list):
                raise EpistemicKernelError("changed artifacts JSON must be a list of ids")
            result = invalidate(Path(args.certificate).read_bytes(), changed)
        elif args.mode == "lean-audit":
            result = kernel_audit(timeout=args.timeout)
        elif args.mode == "lattice":
            result = lattice_self_check()
        elif args.mode == "transport-lift":
            result = lift_transport_opens()
        elif args.mode == "bridge":
            payload = strict_json_loads(Path(args.bridge).read_bytes())
            if not isinstance(payload, dict):
                raise EpistemicKernelError("bridge request must be a JSON object")
            result = apply_bridge(
                payload.get("bridge", {}),
                payload.get("residual", {}),
                payload.get("evidence", {}),
                payload.get("claim", {}),
            )
        else:
            raise EpistemicKernelError(f"unsupported mode: {args.mode}")
        export_evidence(Path(args.output), result)
        accepted = bool(result.get("passed", result.get("accepted", False)))
        print(
            json.dumps(
                {
                    "accepted": accepted,
                    "scientific_acceptance": False,
                    "output": str(Path(args.output).resolve()),
                    "format": result.get("format"),
                }
            )
        )
        return 0 if accepted else 1
    except (EpistemicKernelError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"accepted": False, "error": str(exc), "scientific_acceptance": False}))
        return 1


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "epistemic-kernel-v1",
        help=(
            "stratified compositional assurance kernel; rejects forbidden promotion and "
            "keeps continuum/empirical/causal residuals OPEN"
        ),
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "campaign",
            "assess",
            "compose",
            "invalidate",
            "lean-audit",
            "lattice",
            "transport-lift",
            "bridge",
        ],
    )
    parser.add_argument("--certificate", help="stratified certificate JSON")
    parser.add_argument("--left", help="upstream certificate JSON for compose")
    parser.add_argument("--right", help="downstream certificate JSON for compose")
    parser.add_argument("--changed", help="JSON list of changed artifact ids")
    parser.add_argument("--bridge", help="bridge request JSON for --mode bridge")
    parser.add_argument(
        "--schema",
        action="store_true",
        help="with assess mode, also validate against the JSON schema",
    )
    parser.add_argument(
        "--lean-audit",
        action="store_true",
        help="with campaign mode, also compile/audit the research Lean library",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output", required=True, help="new evidence directory")
    parser.set_defaults(func=command)
