"""Local prior-state cache (lookup ≠ eligibility ≠ authority)."""

from .store import Cache, CacheEntry, ValidState, has_authority, reuse_permitted

__all__ = [
    "Cache",
    "CacheEntry",
    "ValidState",
    "has_authority",
    "reuse_permitted",
]
