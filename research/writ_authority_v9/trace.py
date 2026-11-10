"""Independent, pure Writ/9 transition checker for scoped agent delegations.

A structural reference model, not a cryptographic identity verifier. Callers must
authenticate their original gateway receipts before projecting them to these
events. Rejection raises PolicyError; no external side effects are performed.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Union
from .core import Hop, Scope, PolicyError, validate_chain, admissible, debit

@dataclass(frozen=True)
class Admit:
    actor: str
    leaf: str
    action: str
    label: int
    size: int

@dataclass(frozen=True)
class Revoke:
    delegation: str

Event = Union[Admit, Revoke]

@dataclass(frozen=True)
class Projection:
    root_remaining: int
    delegation_remaining: dict[str, int]
    revoked: frozenset[str]
    admitted: int
    debit_count: int

def replay(hops: dict[str, Hop], root: Scope, events: tuple[Event, ...]) -> Projection:
    """Check arbitrary finite event sequence against all ancestor restrictions.

    Scope checks are static; each admission spends one root unit plus one unit
    of every delegation on its path. Revocation is monotonic. A child cannot
    evade a shared ancestor budget by using another descendant branch.
    """
    if not isinstance(events, tuple):
        raise PolicyError("immutable tuple of replay events required")
    remaining = {name: hop.scope.quota for name, hop in hops.items()}
    revoked: set[str] = set()
    root_remaining, admitted, debits = root.quota, 0, 0
    for idx, event in enumerate(events):
        if isinstance(event, Revoke):
            if event.delegation not in hops or event.delegation in revoked:
                raise PolicyError(f"event {idx}: invalid monotonic revocation")
            revoked.add(event.delegation)
            continue
        if not isinstance(event, Admit):
            raise PolicyError(f"event {idx}: unknown event kind")
        if (type(event.label) is not int or type(event.size) is not int or
            root_remaining <= 0 or event.action not in root.actions or
            event.label < 0 or event.label > root.clearance or
            event.size < 0 or event.size > root.max_bytes):
            raise PolicyError(f"event {idx}: root authorization denied")
        path = validate_chain(hops, event.leaf, root)
        if not path or path[-1].actor != event.actor:
            raise PolicyError(f"event {idx}: actor misbound to delegation")
        if not admissible(path, action=event.action, label=event.label,
                          size=event.size, remaining=remaining,
                          revoked=frozenset(revoked)):
            raise PolicyError(f"event {idx}: ancestor authority denied")
        remaining = debit(path, remaining)
        root_remaining -= 1
        admitted += 1
        debits += len(path)
    return Projection(root_remaining, remaining, frozenset(revoked), admitted, debits)
