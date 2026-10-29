"""Proof-carrying scientific dialectic over finite model ensembles."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .assures import supports_claim


def model_supports(model: Mapping[str, Any], claim: Mapping[str, Any]) -> bool:
    if not supports_claim(claim, model.get("evidence", [])):
        return False
    for c in model.get("claims", []):
        if c.get("id") == claim.get("id") and c.get("required_class") == claim.get("required_class"):
            return True
    return False


def agreement_core(
    models: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    if not models:
        return []
    return [c for c in candidates if all(model_supports(m, c) for m in models)]


def dispute_frontier(
    models: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    return [
        c
        for c in candidates
        if any(model_supports(m, c) for m in models) and not all(model_supports(m, c) for m in models)
    ]


def distinguishing(models: Sequence[Mapping[str, Any]], obs: Mapping[str, Any]) -> bool:
    return any(model_supports(m, obs) for m in models) and any(
        not model_supports(m, obs) for m in models
    )


def merge_ensembles(
    left: Sequence[Mapping[str, Any]],
    right: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    return list(left) + list(right)


def dialectic_report(
    models: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    core = agreement_core(models, candidates)
    dispute = dispute_frontier(models, candidates)
    return {
        "format": "pcs-epistemic-dialectic-v1",
        "model_count": len(models),
        "agreement_core": [c["id"] for c in core],
        "dispute_frontier": [c["id"] for c in dispute],
        "distinguishing": [c["id"] for c in dispute if distinguishing(models, c)],
        "scientific_authority": False,
        "limitations": [
            "Agreement is computational support intersection, not empirical truth.",
            "Dispute preservation is intentional; consensus is never forced.",
        ],
    }
