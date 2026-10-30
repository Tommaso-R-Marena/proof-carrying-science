"""PCS Causal Laboratory — independent proof-carrying causal inference.

This package is intentionally isolated from PCS production verification.
Mathematical identification certificates here do NOT confer scientific
acceptance of their modeling assumptions.
"""

from __future__ import annotations

__version__ = "0.1.0"
__isolation__ = "incubation/pcs_causal_laboratory_v1"

from pcs_causal.hypothesis.states import ScientificStatus

__all__ = ["__version__", "__isolation__", "ScientificStatus"]
