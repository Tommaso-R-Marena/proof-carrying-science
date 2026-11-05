"""Prospective experiment registration with frozen plans."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..core.canonical import canonical_hash
from ..core.errors import ErrorCode, PcsNextError


def freeze_experiment_plan(plan: dict[str, Any]) -> dict[str, Any]:
    required = [
        "experiment_id",
        "hypotheses",
        "outcomes",
        "metrics",
        "split_rules",
        "baselines",
        "stopping_criteria",
        "randomization",
        "negative_controls",
        "planned_comparisons",
        "analysis_class",
    ]
    missing = [k for k in required if k not in plan]
    if missing:
        raise PcsNextError(ErrorCode.SCHEMA_INVALID, f"experiment plan missing {missing}")
    if plan["analysis_class"] not in {"confirmatory", "exploratory"}:
        raise PcsNextError(ErrorCode.SCHEMA_INVALID, "analysis_class must be confirmatory|exploratory")
    body = deepcopy(plan)
    return {
        "format": "pcs-next-experiment-plan-v1",
        "plan": body,
        "plan_hash": canonical_hash(body),
        "prospective": plan["analysis_class"] == "confirmatory",
        "note": "A retrospectively selected experiment must not be relabeled prospective.",
    }


def record_deviation(frozen: dict[str, Any], deviation: dict[str, Any]) -> dict[str, Any]:
    if canonical_hash(frozen["plan"]) != frozen["plan_hash"]:
        raise PcsNextError(ErrorCode.HASH_MISMATCH, "frozen plan mutated")
    return {
        "format": "pcs-next-experiment-deviation-v1",
        "plan_hash": frozen["plan_hash"],
        "deviation": deviation,
        "analysis_class_after": "exploratory" if frozen.get("prospective") else frozen["plan"]["analysis_class"],
        "note": "Deviations demote confirmatory claims to exploratory unless pre-specified amendment process exists.",
    }
