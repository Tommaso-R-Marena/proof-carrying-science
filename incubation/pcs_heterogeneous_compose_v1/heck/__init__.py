"""HECK — Heterogeneous Evidence Composition Kernel (incubation v1).

Isolated research kernel. Does not modify production PCS authority.
"""

__version__ = "0.1.0"

from .levels import Level, meet, meet_list
from .compose import EvidenceAtom, CompositeClaim, accept, achieved_level
from .predictive import (
    PredStatus,
    PredictiveObligation,
    Observation,
    discharge,
    discharge_sticky,
    is_support,
)

__all__ = [
    "Level",
    "meet",
    "meet_list",
    "EvidenceAtom",
    "CompositeClaim",
    "accept",
    "achieved_level",
    "PredStatus",
    "PredictiveObligation",
    "Observation",
    "discharge",
    "discharge_sticky",
    "is_support",
    "__version__",
]
