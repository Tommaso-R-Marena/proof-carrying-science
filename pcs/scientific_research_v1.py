"""A bounded, deterministic scientific investigation with immutable premises.

It diagnoses an authored finite workflow and may propose regenerated numerical
artifacts. It never changes the question, substitutes evidence, authorizes a
release, or asserts novel mathematics/scientific discovery.
"""
from __future__ import annotations

import hashlib
from typing import Any

from .scientific_contracts_v1 import evaluate, load_contract, trajectory_csv
from .scientific_obligations_v1 import make_plan, resolve_plan


def investigate_scientific_contract(contract_raw: bytes, observations_raw: bytes, *,
        allow_reference_proposal: bool = False, max_rounds: int = 2) -> dict[str, Any]:
    if type(max_rounds) is not int or not 1 <= max_rounds <= 4:
        raise ValueError("investigation max_rounds must be an integer in [1,4]")
    if type(allow_reference_proposal) is not bool:
        raise ValueError("allow_reference_proposal must be boolean")
    original_contract = hashlib.sha256(contract_raw).hexdigest()
    original_observations = hashlib.sha256(observations_raw).hexdigest()
    initial = evaluate(contract_raw, observations_raw)
    result = {"format": "pcs-bounded-scientific-investigation-v1",
        "original_contract_sha256": original_contract, "original_observations_sha256": original_observations,
        "planner": "deterministic_dependency_baseline", "learned_policy_used": False,
        "original_outcome": initial["outcome"], "pcs_authority": False,
        "scientific_acceptance": False, "release_authorization": False,
        "attempts": [{"round": 0, "operation": "independent_contract_replay", "replay": initial}],
        "proposals": [], "unresolved": [], "resources": {"adapter_invocations": 1}}
    if initial["outcome"] not in {"PASS", "FAIL"}:
        result["unresolved"] = initial["diagnostics"]
        return result
    contract = load_contract(contract_raw)
    plan = make_plan(contract, contract_artifact_sha256=original_contract)
    result["plan"] = plan
    result["original_obligations"] = resolve_plan(plan, initial)
    # All candidates are separate, inspectable artifacts. Original evidence is
    # retained, and a successful repair is never attributed to the original table.
    if initial["outcome"] == "FAIL" and allow_reference_proposal and max_rounds >= 2:
        candidate = trajectory_csv(contract)
        fresh = evaluate(contract_raw, candidate)
        if hashlib.sha256(contract_raw).hexdigest() != original_contract:
            raise RuntimeError("immutable scientific premises changed during investigation")
        result["attempts"].append({"round": 1, "operation": "check_separate_rational_euler_proposal",
            "replay": fresh, "original_evidence_replaced": False})
        result["resources"]["adapter_invocations"] += 1
        result["proposals"].append({"type": "regenerated_rational_euler_table",
            "observations_csv": candidate.decode("utf-8"), "sha256": hashlib.sha256(candidate).hexdigest(),
            "source_contract_sha256": original_contract, "outcome": fresh["outcome"],
            "obligations": resolve_plan(plan, fresh), "production_authority": False,
            "requires_human_selection_and_new_signed_package": True})
    result["unresolved"] = [{"obligation": "biological_adequacy", "status": "OPEN",
        "reason": "Neither deterministic planning nor finite numerical replay supplies scientific domain validation."}]
    return result
