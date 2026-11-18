"""Proof-Gated Recursive Autoformalization (PGRA) v1 — research only.

This package joins PCS proof-gated self-improvement (PGSI) with a Lean
formalization capability lattice. It is an isolated research experiment:

- ``pcs_authority`` / ``pcs_scientific_authority`` are always false
- ``automatic_deployment`` is always false
- It does not modify sealed lean-learning-v1/v2 trees or production promotion

No production scientific authority is claimed or conferred.
"""

from __future__ import annotations

PCS_AUTHORITY = False
PCS_SCIENTIFIC_AUTHORITY = False
AUTOMATIC_DEPLOYMENT = False

__all__ = [
    "PCS_AUTHORITY",
    "PCS_SCIENTIFIC_AUTHORITY",
    "AUTOMATIC_DEPLOYMENT",
]
