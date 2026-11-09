"""Pure reference model for an operator-controlled external authority witness.

The actual Writ/11 host adapter is separate. No file permissions, signing keys,
SQLite WAL behavior or cryptographic collision resistance is implied here.
"""
from __future__ import annotations
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class Fingerprint:
    sequence: int
    head: str
    seal: str

@dataclass(frozen=True)
class HostState:
    database: Fingerprint
    witness: Fingerprint

def ready(s: HostState) -> bool:
    return s.database == s.witness

def commit_database(s: HostState, next_identity: Fingerprint) -> HostState:
    """Database commit preceded the witness update; authority is suspended."""
    if not ready(s):
        raise ValueError("cannot commit from divergent state")
    if next_identity.sequence < s.database.sequence:
        raise ValueError("sequence cannot decrease during normal admission")
    return replace(s, database=next_identity)

def publish_witness(s: HostState) -> HostState:
    """Host-owned durable checkpoint; caller must implement actual durability."""
    return replace(s, witness=s.database)

def rollback_database(s: HostState, old_identity: Fingerprint) -> HostState:
    """Adversarial restoration of SQLite alone, leaving external witness pinned."""
    return replace(s, database=old_identity)
