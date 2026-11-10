"""Writ/9 independent reference calculus for compositional delegated authority.

This is NOT a cryptographic verifier or tool-execution gateway.
"""
from __future__ import annotations
from dataclasses import dataclass
import re

IDENT = r"[A-Za-z_][A-Za-z0-9_-]*"
LABELS = {"public": 0, "internal": 1, "secret": 2}
MAX_HOPS = 8
HOP_RE = re.compile(
    rf"(delegate|subdelegate)\s+({IDENT})\s+from\s+({IDENT})\s+to\s+({IDENT})"
    rf"\s+actions\s+({IDENT}(?:\s*,\s*{IDENT})*)\s+uses\s+([0-9]+)"
    rf"\s+clearance\s+(public|internal|secret)\s+limit\s+([0-9]+)\s+bytes"
    rf"(?:\s+purpose\s+({IDENT}))?;?"
)

class PolicyError(ValueError):
    pass

@dataclass(frozen=True)
class Scope:
    actions: frozenset[str]
    clearance: int
    max_bytes: int
    quota: int
    purpose: str = ""

@dataclass(frozen=True)
class Hop:
    name: str
    parent: str
    actor: str
    scope: Scope
    is_root: bool = False

def attenuates(child: Scope, parent: Scope) -> bool:
    """A child is no more permissive than its ancestor."""
    return (
        child.actions <= parent.actions
        and 0 <= child.clearance <= parent.clearance
        and 0 < child.max_bytes <= parent.max_bytes
        and 0 < child.quota <= parent.quota
        and (not parent.purpose or child.purpose == parent.purpose)
    )

def parse_hops(source: str) -> dict[str, Hop]:
    """Parse only Writ delegation lines, not arbitrary complete Writ policies."""
    out: dict[str, Hop] = {}
    for number, raw in enumerate(source.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = HOP_RE.fullmatch(line)
        if not m:
            raise PolicyError(f"line {number}: unsupported/malformed delegation")
        kind, name, parent, actor, actions, uses, label, size, purpose = m.groups()
        if name in out:
            raise PolicyError("duplicate delegation")
        action_list = [a.strip() for a in actions.split(",")]
        if len(set(action_list)) != len(action_list):
            raise PolicyError("duplicate action")
        quota, byte_limit = int(uses), int(size)
        if not 1 <= quota <= 2**63-1 or not 1 <= byte_limit <= 2**63-1:
            raise PolicyError("invalid quota or byte bound")
        scope = Scope(frozenset(action_list), LABELS[label], byte_limit, quota, purpose or "")
        out[name] = Hop(name, parent, actor, scope, kind == "delegate")
    return out

def validate_chain(hops: dict[str, Hop], leaf: str, root_scope: Scope) -> tuple[Hop, ...]:
    """Return root-to-leaf chain; fail closed on graph or authority violations."""
    seen: set[str] = set()
    path: list[Hop] = []
    current = leaf
    while True:
        if current in seen or len(path) >= MAX_HOPS:
            raise PolicyError("cyclic or overlong delegation chain")
        seen.add(current)
        if current not in hops:
            raise PolicyError("missing parent delegation")
        hop = hops[current]
        path.append(hop)
        if hop.is_root:
            break
        current = hop.parent
    path.reverse()
    if len({h.actor for h in path}) != len(path):
        raise PolicyError("repeated actor identity")
    for i, hop in enumerate(path):
        parent = root_scope if i == 0 else path[i-1].scope
        if not attenuates(hop.scope, parent):
            raise PolicyError("delegation expanded ancestor authority")
    return tuple(path)

def admissible(path: tuple[Hop, ...], *, action: str, label: int, size: int,
               remaining: dict[str, int],
               revoked: frozenset[str] = frozenset()) -> bool:
    """Structural oracle; the real gateway must authenticate actor and credential."""
    return bool(path) and 0 <= label <= 2 and size >= 0 and all(
        h.name not in revoked and remaining.get(h.name, 0) > 0
        and action in h.scope.actions and label <= h.scope.clearance
        and size <= h.scope.max_bytes
        for h in path
    )

def debit(path: tuple[Hop, ...], remaining: dict[str, int]) -> dict[str, int]:
    """Pure proposed quota debit, NOT a database transaction."""
    if any(remaining.get(h.name, 0) <= 0 for h in path):
        raise PolicyError("insufficient quota")
    updated = dict(remaining)
    for hop in path:
        updated[hop.name] -= 1
    return updated
