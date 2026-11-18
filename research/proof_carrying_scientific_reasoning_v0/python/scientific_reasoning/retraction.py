from __future__ import annotations

from typing import Iterable, Sequence

from .certificates import Certificate
from .syntax import Context, Premise


def retract_context(Γ: Context, withdrawn: Sequence[int]) -> Context:
    w = set(withdrawn)
    return Context(premises=tuple(p for p in Γ.premises if p.id not in w))


def certificate_invalidated(cert: Certificate, withdrawn: Sequence[int]) -> bool:
    w = set(withdrawn)
    return any(i in w for i in cert.final_support)
