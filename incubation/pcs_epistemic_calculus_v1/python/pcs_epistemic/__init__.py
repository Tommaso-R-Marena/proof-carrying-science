"""PCS Epistemic Calculus v1 — graded evidence, composition, invalidation, dialectic.

Incubation research only. Not production PCS authority.
"""

from .lattice import EvidenceClass, discharges
from .assures import supports_claim, assure
from .compose import compose_assures
from .invalidate import compute_impact, nonimpact
from .dialectic import agreement_core, dispute_frontier, distinguishing, merge_ensembles
from .checker import verify_certificate, CheckerError

__all__ = [
    "EvidenceClass",
    "discharges",
    "supports_claim",
    "assure",
    "compose_assures",
    "compute_impact",
    "nonimpact",
    "agreement_core",
    "dispute_frontier",
    "distinguishing",
    "merge_ensembles",
    "verify_certificate",
    "CheckerError",
]

__version__ = "0.1.0"
