"""Certificate format certnum-cert-v1 (independent of PCS production certificates)."""

from __future__ import annotations

from typing import Any, Dict, List

CERT_FORMAT = "certnum-cert-v1"
SUPPORTED_KINDS = {
    "interval_enclosure",
    "root_isolation",
    "global_optimization",
    "linear_residual",
    "markov_step",
    "thermo_partition",
    "ode_linear_scalar",
    "expression_equivalence",
}


def make_certificate(kind: str, claim: Dict[str, Any], witness: Dict[str, Any], meta: Dict[str, Any] | None = None) -> dict:
    if kind not in SUPPORTED_KINDS:
        raise ValueError(f"unsupported kind {kind}")
    return {
        "format": CERT_FORMAT,
        "kind": kind,
        "claim": claim,
        "witness": witness,
        "meta": meta or {},
    }
