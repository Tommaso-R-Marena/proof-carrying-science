"""Versioned scientific planning metadata, never an alternative PCS authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .scientific_contracts_v1 import digest, primitive_checks, validate_contract

FORMAT = "pcs-scientific-obligation-graph-v1"
REVIEW_FORMAT = "pcs-scientific-review-revision-v1"
MAX_NODES = 128


class ScientificObligationError(ValueError):
    pass


def make_plan(contract: dict, *, contract_artifact_sha256: str) -> dict:
    validate_contract(contract)
    assumptions = [{"id": f"assumption_{item['id']}", "kind": "assumption",
        "statement": item["statement"], "dependencies": [], "required_evidence": [],
        "assumption_sha256": digest(item), "authority": "EXPLICIT_UNVERIFIED_PREMISE"}
        for item in contract["assumptions"]]
    assumption_ids = [item["id"] for item in assumptions]
    primitives = []
    for item in primitive_checks(contract):
        primitives.append({"id": item["id"], "kind": "domain_predicate",
            "statement": ("Element balance" if item["type"] == "reaction_balance" else "Rate dimensions")
                         + " for " + item["id"].split("_", 1)[1],
            "dependencies": assumption_ids, "required_evidence": [f"E_{item['id']}"],
            "typed_interpretation": item, "authority": "EXISTING_PCS_BUILTIN_CERTIFICATE_REQUIRED"})
    numerical = []
    for ident, dependencies, text in (
        ("time_grid", [], "The observation grid equals the explicit contract grid."),
        ("nonnegative", ["time_grid"], "Each recorded concentration is nonnegative."),
        ("reference_match", ["time_grid", "nonnegative"], "Recorded concentrations match rational simultaneous Euler within the declared tolerance."),
        ("element_conservation", [x["id"] for x in primitives if x["id"].startswith("balance_")] + ["time_grid"],
         "Every recorded elemental amount is conserved within the declared tolerance."),
    ):
        numerical.append({"id": ident, "kind": "domain_predicate", "statement": text,
            "dependencies": [*assumption_ids, *dependencies], "required_evidence": ["E_NUMERICAL"],
            "typed_interpretation": {"predicate": ident, "quantifier": "for_every_declared_observation",
                "domain": "finite rational concentration table", "concentration_unit": "mol/L", "time_unit": "s"},
            "authority": "EXTERNAL_TRUST_PLUS_INDEPENDENT_BOUNDED_REPLAY"})
    nodes = [*assumptions, *primitives, *numerical,
        {"id": "workflow", "kind": "aggregate", "statement": "All explicit finite reaction, dimensional, grid, nonnegativity, reference and conservation obligations pass under the declared premises.",
         "dependencies": [x["id"] for x in [*primitives, *numerical]],
         "required_evidence": [], "authority": "CONDITIONAL_PLANNING_SUMMARY_ONLY"},
        {"id": "biological_adequacy", "kind": "unsupported", "statement": "The workflow is biologically or clinically adequate.",
         "dependencies": ["workflow"], "required_evidence": [], "authority": "NONE"}]
    plan = {"format": FORMAT, "source_contract_sha256": contract_artifact_sha256,
        "original_claim": contract["question"], "domain": "bounded synthetic biochemical reaction network",
        "original_language_grounding": "NOT_CERTIFIED: the free-text question is retained as provenance; the typed contract determines the checked meaning",
        "pcs_authority": False, "nodes": nodes,
        "unresolved_questions": ["Are these modeling premises empirically applicable?",
            "What independent domain review and data would support biological adequacy?"],
        "planner": "deterministic_dependency_topological_v1"}
    topological_order(plan)
    return plan


def topological_order(plan: dict) -> list[str]:
    if not isinstance(plan, dict) or plan.get("format") != FORMAT:
        raise ScientificObligationError("unsupported obligation graph version")
    nodes = plan.get("nodes")
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES:
        raise ScientificObligationError("obligation graph node count is outside bounds")
    by_id = {}
    for node in nodes:
        ident = node.get("id") if isinstance(node, dict) else None
        if not isinstance(ident, str) or ident in by_id:
            raise ScientificObligationError("duplicate or invalid obligation identifier")
        by_id[ident] = node
    for node in nodes:
        dependencies = node.get("dependencies")
        if (not isinstance(dependencies, list) or any(not isinstance(x, str) or x not in by_id for x in dependencies)
                or len(dependencies) != len(set(dependencies))):
            raise ScientificObligationError("invalid or unknown obligation dependency")
    emitted: list[str] = []
    pending = set(by_id)
    while pending:
        ready = sorted(ident for ident in pending if all(x in emitted for x in by_id[ident]["dependencies"]))
        if not ready:
            raise ScientificObligationError("dependency_cycle: graph cannot be scheduled")
        emitted.extend(ready)
        pending.difference_update(ready)
    return emitted


def resolve_plan(plan: dict, replay: dict, *, previous: dict | None = None) -> dict:
    """Inspectable conditional summary. Callers must obtain replay independently.

    This function deliberately grants no certificate authority, even if passed a
    forged report. The independent package receiver recomputes all inputs itself.
    """
    order = topological_order(plan)
    old_nodes = {x["id"]: x for x in (previous or {}).get("nodes", [])}
    current = {x["id"]: x for x in plan["nodes"]}
    attempts = {x["id"]: x for x in replay.get("checks", [])}
    matching_source = replay.get("contract_sha256") == plan["source_contract_sha256"]
    results = {}
    for ident in order:
        node = current[ident]
        fingerprint = digest(node)
        earlier = old_nodes.get(ident)
        changed = bool(earlier and earlier.get("definition_sha256") != fingerprint)
        invalidated_by = [dep for dep in node["dependencies"] if results[dep]["invalidated"]]
        invalidated = changed or bool(invalidated_by) or not matching_source
        dependencies = [results[dep] for dep in node["dependencies"]]
        failed = [x["id"] for x in dependencies if x["status"] == "FAILED"]
        unresolved = [x["id"] for x in dependencies if x["status"] not in {"SATISFIED_WITHIN_SCOPE", "ASSUMED"}]
        attempt = attempts.get(ident)
        if invalidated:
            status, reason = "INVALIDATED", "source/premise/obligation changed; dependent evidence requires new replay"
        elif node["kind"] == "assumption":
            status, reason = "ASSUMED", "explicit premise; not independently established"
        elif failed:
            status, reason = "BLOCKED", "failed prerequisites: " + ", ".join(failed)
        elif unresolved:
            status, reason = "BLOCKED", "unresolved prerequisites: " + ", ".join(unresolved)
        elif node["kind"] == "unsupported":
            status, reason = "OPEN", "adapter does not establish biological/clinical adequacy"
        elif node["kind"] == "aggregate":
            status, reason = "SATISFIED_WITHIN_SCOPE", "bounded obligations passed under explicit unverified premises"
        elif attempt and attempt.get("outcome") == "FAIL":
            status, reason = "FAILED", "independently replayed bounded predicate has a counterexample"
        elif attempt and attempt.get("outcome") == "PASS":
            status, reason = "SATISFIED_WITHIN_SCOPE", "bounded predicate replay passed; authority scope remains explicit"
        else:
            status, reason = "OPEN", "missing, unsupported or exhausted evidence"
        results[ident] = {"id": ident, "definition_sha256": fingerprint, "status": status,
            "reason": reason, "invalidated": invalidated, "invalidated_by": invalidated_by,
            "assumption_change": changed and node["kind"] == "assumption",
            "dependencies": list(node["dependencies"]), "authority": node["authority"],
            "attempt": deepcopy(attempt), "pcs_authority": False}
    return {"format": "pcs-scientific-obligation-result-v1", "plan_sha256": digest(plan),
        "source_contract_sha256": plan["source_contract_sha256"], "pcs_authority": False,
        "scientific_acceptance": False, "execution_order": order,
        "nodes": [results[ident] for ident in order]}


def new_review_revision(*, previous: dict | None, evidence_sha256: str,
                        reviewer_id: str, decisions: list[dict], independent: bool = False) -> dict:
    """Append-only proposal metadata; reviewer identity/independence is self-asserted.

    It does not produce authorization, certify a human review, or become training
    data. Production reviewer authentication remains the existing external policy.
    """
    if (not isinstance(reviewer_id, str) or not 1 <= len(reviewer_id) <= 128
            or not isinstance(evidence_sha256, str) or len(evidence_sha256) != 64
            or any(c not in "0123456789abcdef" for c in evidence_sha256)
            or type(independent) is not bool):
        raise ScientificObligationError("invalid review metadata")
    if previous is not None and (previous.get("format") != REVIEW_FORMAT
            or previous.get("evidence_sha256") != evidence_sha256):
        raise ScientificObligationError("review history must stay bound to the same original evidence")
    if not isinstance(decisions, list) or not 1 <= len(decisions) <= 128:
        raise ScientificObligationError("review needs bounded structured decisions")
    allowed = {"interpretation", "assumptions", "evidence_adequacy", "false_positive", "false_negative",
        "unresolved_obligation", "missing_domain_support", "suggested_repair", "accept", "reject"}
    for decision in decisions:
        if (not isinstance(decision, dict) or set(decision) != {"obligation_id", "type", "message"}
                or not isinstance(decision["obligation_id"], str) or decision["type"] not in allowed
                or not isinstance(decision["message"], str) or not 1 <= len(decision["message"]) <= 4096):
            raise ScientificObligationError("unsupported review decision")
    return {"format": REVIEW_FORMAT, "revision": (previous["revision"] + 1) if previous else 1,
        "previous_revision_sha256": digest(previous) if previous else None,
        "evidence_sha256": evidence_sha256, "reviewer_id": reviewer_id,
        "independence_claimed": independent, "identity_authenticated": False,
        "independent_human_review_verified": False, "decisions": deepcopy(decisions),
        "pcs_authority": False, "training_authorization": False}


def unsupported_claim_diagnostics(statement: str, *, available_evidence: list[str] | None = None) -> dict:
    if not isinstance(statement, str) or not 1 <= len(statement) <= 4096:
        raise ScientificObligationError("claim must be a bounded nonempty string")
    # Keyword analysis is advisory, not semantic interpretation or verification.
    text = statement.lower()
    diagnostics = []
    if any(x in text for x in ("safe", "effective", "clinical", "cure", "patient", "biological")):
        diagnostics.append({"code": "scientific_adequacy_not_supported", "missing_adapter": "independent scientific/clinical validation",
            "missing_assumptions": ["population, intervention, endpoint and applicability scope"],
            "suggested_obligations": ["dimensional consistency", "element conservation", "reproducibility under fixed parameters"]})
    if any(x in text for x in ("all models", "always", "every possible", "real world")):
        diagnostics.append({"code": "unbounded_domain_not_supported", "missing_adapter": "universal semantic grounding",
            "missing_assumptions": ["finite parameter bounds and an explicit model"],
            "suggested_obligations": ["finite-domain counterexample search", "exact artifact replay"]})
    if any(x in text for x in ("this", "it", "better", "significant")):
        diagnostics.append({"code": "possible_ambiguity", "missing_adapter": None,
            "missing_assumptions": ["explicit referent, metric, tolerance and comparator"],
            "suggested_obligations": ["submit a typed scientific contract for review"]})
    if not available_evidence:
        diagnostics.append({"code": "missing_evidence", "missing_adapter": None,
            "missing_assumptions": [], "suggested_obligations": ["bind model, data, license and environment source digests"]})
    if not diagnostics:
        diagnostics.append({"code": "typed_formalization_required", "missing_adapter": "controlled scientific contract",
            "missing_assumptions": ["explicit model and applicability conditions"],
            "suggested_obligations": ["reaction balance", "rate dimensions", "bounded rational replay"]})
    return {"format": "pcs-unsupported-scientific-claim-v1", "original_claim": statement,
        "status": "OPEN", "pcs_authority": False, "interpretation_verified": False,
        "ambiguity_analysis": "advisory lexical screening only", "diagnostics": diagnostics,
        "remaining_acceptance": "Independent domain evidence and reviewer policy are required; suggestions are not verified meanings."}
