"""
Local prior-state cache.

Lookup ≠ eligibility ≠ authority.
Never grant mathematical authority from lookup alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from model.graph import (
    Certificate,
    Graph,
    ObligationKey,
    Value,
    eligible,
)


@dataclass(frozen=True)
class CacheEntry:
    """Stored cache entry. prior_accepted records trusted prior acceptance."""

    key: ObligationKey
    cert: Certificate
    prior_accepted: bool

    def to_json(self) -> dict:
        return {
            "key": {
                "id": self.key.id,
                "op": self.key.op,
                "policy": self.key.policy,
                "version": self.key.version,
                "evidence": self.key.evidence,
                "dep_outputs": [list(x) for x in self.key.dep_outputs],
            },
            "cert": self.cert.to_json(),
            "prior_accepted": self.prior_accepted,
        }


def has_authority(entry: CacheEntry) -> bool:
    """Authority: entry was previously accepted under the trust model."""
    return entry.prior_accepted is True


def reuse_permitted(entry: CacheEntry, current: ObligationKey) -> bool:
    """Safe reuse premise: eligible key AND prior authority."""
    return eligible(entry.key, current) and has_authority(entry)


@dataclass
class Cache:
    """Finite cache with exact-key index. Lookup is retrieval only."""

    entries: List[CacheEntry] = field(default_factory=list)
    _index: Dict[ObligationKey, int] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._reindex()

    def _reindex(self) -> None:
        self._index = {e.key: i for i, e in enumerate(self.entries)}

    def lookup(self, key: ObligationKey) -> Optional[CacheEntry]:
        """
        Lookup by exact obligation key.
        Presence alone does NOT prove validity or grant authority.
        """
        i = self._index.get(key)
        if i is None:
            return None
        return self.entries[i]

    def lookup_by_node_id(self, node_id: int) -> List[CacheEntry]:
        return [e for e in self.entries if e.key.id == node_id]

    def put(self, entry: CacheEntry) -> None:
        i = self._index.get(entry.key)
        if i is not None:
            self.entries[i] = entry
        else:
            self._index[entry.key] = len(self.entries)
            self.entries.append(entry)

    def put_authoritative(self, key: ObligationKey, cert: Certificate) -> None:
        """Record an entry that a trusted verifier accepted."""
        self.put(CacheEntry(key=key, cert=cert, prior_accepted=True))

    def put_untrusted(self, key: ObligationKey, cert: Certificate) -> None:
        """Insert without authority (e.g. adversarial forgery fixture)."""
        self.put(CacheEntry(key=key, cert=cert, prior_accepted=False))

    def try_reuse(self, current: ObligationKey) -> Optional[CacheEntry]:
        """
        Attempt reuse. Returns entry only if lookup hits AND reuse_permitted.
        Lookup alone never returns a reusable entry without authority.
        """
        hit = self.lookup(current)
        if hit is None:
            return None
        if not reuse_permitted(hit, current):
            return None
        return hit

    def clear(self) -> None:
        self.entries.clear()
        self._index.clear()

    def copy(self) -> "Cache":
        return Cache(entries=list(self.entries))

    def authoritative_count(self) -> int:
        return sum(1 for e in self.entries if e.prior_accepted)


@dataclass
class ValidState:
    """
    Restrictive local fully-checked prior ValidState.

    graph + outputs + authoritative cache, with well-formed + acyclic checks
    performed at construction time by the verifier that produces this state.
    """

    graph: Graph
    outputs: Dict[int, Value]
    cache: Cache
    well_formed: bool = True
    acyclic: bool = True
    # optional certificate map used to reconstruct checks
    certs: Dict[int, Certificate] = field(default_factory=dict)

    def assert_sound_flags(self) -> None:
        if not self.well_formed or not self.acyclic:
            raise ValueError("ValidState must be well-formed and acyclic")
