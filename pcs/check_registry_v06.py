from __future__ import annotations

from copy import deepcopy
from typing import Any

from .numeric_contract_v06 import canonical_nonnegative_number_text_v06


CERTIFIED_BUILTIN_CHECK_TYPES_V06 = frozenset(
    {
        "reaction_balance",
        "unit_compatible",
        "csv_disjoint",
        "pkpd_contract",
        "pkpd_reference_match",
    }
)

EXTERNAL_CHECK_KIND_BY_TYPE_V06 = {
    "external_formal_proof": "formal_proof",
    "external_empirical_validation": "empirical_validation",
    "external_statistical_validation": "statistical_validation",
    "provenance_record": "provenance",
}


FORMAL_TARGETS_V06: dict[str, dict[str, Any]] = {
    "reaction_balance": {
        "formal_module": "PCS.V2.Checkers",
        "checker": "PCS.V2.Checkers.reactionChecker",
        "soundness_theorem": "PCS.V2.Checkers.chem_sound",
        "decision_theorem": "PCS.V2.Chemistry.balancedB_iff",
        "semantic_proposition": "PCS.V2.Chemistry.ReactionHolds",
        "high_assurance_theorem": "PCS.V2.HighAssurance.pcs_verified_builtin_acceptance_sound",
        "proof_level": "LEAN_KERNEL",
    },
    "unit_compatible": {
        "formal_module": "PCS.V2.Units",
        "checker": "PCS.V2.Checkers.unitChecker",
        "soundness_theorem": "PCS.V2.Units.unitRun_sound",
        "decision_theorem": "PCS.V2.Units.unitCompatibleB_iff",
        "semantic_proposition": "PCS.V2.Units.UnitCompatible",
        "high_assurance_theorem": "PCS.V2.HighAssurance.pcs_verified_builtin_acceptance_sound",
        "proof_level": "LEAN_KERNEL",
    },
    "csv_disjoint": {
        "formal_module": "PCS.V2.Csv",
        "checker": "PCS.V2.Checkers.csvChecker",
        "soundness_theorem": "PCS.V2.Csv.csvRun_sound",
        "decision_theorem": "PCS.V2.Csv.csvDisjointB_iff",
        "semantic_proposition": "PCS.V2.Csv.CsvDisjoint",
        "high_assurance_theorem": "PCS.V2.HighAssurance.pcs_verified_builtin_acceptance_sound",
        "proof_level": "LEAN_KERNEL",
    },
    "pkpd_contract": {
        "formal_module": "PCS.V2.PKPDCheck",
        "checker": "PCS.V2.Checkers.pkpdContractChecker",
        "soundness_theorem": "PCS.V2.PKPDCheck.pkpdContractRun_sound",
        "decision_theorem": None,
        "semantic_proposition": "PCS.V2.PKPDCheck.PkpdContractHolds",
        "high_assurance_theorem": "PCS.V2.HighAssurance.pcs_verified_builtin_acceptance_sound",
        "proof_level": "LEAN_KERNEL",
    },
    "pkpd_reference_match": {
        "formal_module": "PCS.V2.PKPDCheck",
        "checker": "PCS.V2.Checkers.pkpdMatchChecker",
        "soundness_theorem": "PCS.V2.PKPDCheck.pkpdMatchRun_sound",
        "decision_theorem": None,
        "semantic_proposition": "PCS.V2.PKPDCheck.PkpdMatchHolds",
        "high_assurance_theorem": "PCS.V2.HighAssurance.pcs_verified_builtin_acceptance_sound",
        "real_bridge_theorem": "PCSReal.PKPD.pcs_pkpd_reference_match_real",
        "proof_level": "LEAN_KERNEL_PLUS_MATHLIB_REAL",
    },
}


def certified_builtin_check_types_v06() -> list[str]:
    return sorted(CERTIFIED_BUILTIN_CHECK_TYPES_V06)


def formal_target_for_check_v06(check_type: str) -> dict[str, Any] | None:
    target = FORMAL_TARGETS_V06.get(check_type)
    return deepcopy(target) if target is not None else None


def predicate_from_manifest_check_v06(check: dict[str, Any]) -> dict[str, Any]:
    check_type = check.get("type")
    if check_type not in CERTIFIED_BUILTIN_CHECK_TYPES_V06:
        raise ValueError(f"unsupported certified built-in check type: {check_type!r}")

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
        "rel_tol": canonical_nonnegative_number_text_v06(
            check.get("rel_tol", 1e-9),
            label=f"check {check.get('id')} rel_tol",
        ),
        "abs_tol": canonical_nonnegative_number_text_v06(
            check.get("abs_tol", 1e-12),
            label=f"check {check.get('id')} abs_tol",
        ),
    }


def check_artifact_references_v06(check: dict[str, Any]) -> list[str]:
    check_type = check.get("type")
    if check_type == "csv_disjoint":
        return [check["left_artifact"], check["right_artifact"]]
    if check_type == "pkpd_contract":
        return [check["model_artifact"]]
    if check_type == "pkpd_reference_match":
        return [check["model_artifact"], check["output_artifact"]]
    return []
