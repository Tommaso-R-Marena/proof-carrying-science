"""Fail-closed inference snapshot for proof-gated experimental integer neurons.

The inference runtime consumes one immutable Python bytes snapshot, never a
mutable artifact pathname. Validation is bound to the content-addressed HEAD
and replayed receipt chain under the store's cooperative lock.

This is not an independently isolated trusted execution environment. It does
not prove the operating system, Python interpreter, compiler, hash primitive,
or storage runtime faithfully implements Lean semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from proof_gate import Model, POLICY_HASH, wire_bytes
from promotion_v2 import (
    Head, IntegrityFailure, ResearchPromotionStore, StaleHead, blob_hash
)

_CANONICAL_WIRE = re.compile(rb"PGSI1\|([RL])\|(-?(?:0|[1-9][0-9]*))\|(-?(?:0|[1-9][0-9]*))\Z", re.ASCII)
# An exact grammar match alone is not enough: "-0" is not canonical.

def decode_sealed_model(raw: bytes) -> Model:
    """Parse exact canonical model bytes without trusting a Python model proposal."""
    if type(raw) is not bytes or len(raw) > 80:
        raise IntegrityFailure("invalid inference artifact type/size")
    match = _CANONICAL_WIRE.fullmatch(raw)
    if match is None:
        raise IntegrityFailure("invalid canonical inference model")
    activation, weight, bias = match.groups()
    try:
        model = Model(activation == b"R", int(weight), int(bias))
    except (ValueError, TypeError, OverflowError) as e:
        raise IntegrityFailure("out-of-policy model weight") from e
    if wire_bytes(model) != raw:
        raise IntegrityFailure("noncanonical model byte representation")
    return model

@dataclass(frozen=True)
class SealedInference:
    """An immutable in-memory inference snapshot, not a filesystem handle."""
    head: Head
    artifact: bytes
    model: Model

    def predict(self, x: int) -> int:
        if type(x) is not int:
            raise TypeError("input must be an exact integer")
        return self.model.predict(x)

    def batch(self, xs: tuple[int, ...]) -> tuple[int, ...]:
        if type(xs) is not tuple:
            raise TypeError("batch must be a tuple of exact integers")
        return tuple(self.predict(x) for x in xs)

    @property
    def active_digest(self) -> str:
        return blob_hash(self.artifact)

def load_sealed(store: ResearchPromotionStore, *,
                expected: Head | None = None) -> SealedInference:
    """Audit HEAD/receipt chain and snapshot exact authenticated blob bytes.

    Read under one cooperative store lock, then decode *that same* immutable
    bytes object. No future filesystem reads occur in predict/batch.
    """
    with store._locked():
        current = store._audit_locked()
        if expected is not None and current != expected:
            raise StaleHead("refuse to serve unexpected model generation")
        raw = store._blob(current.active_sha256)
        if blob_hash(raw) != current.active_sha256:
            raise IntegrityFailure("snapshot content-address mismatch")
        model = decode_sealed_model(raw)
        return SealedInference(current, raw, model)

def load_path_sealed(path: Path, expected_digest: str) -> SealedInference:
    """Intentionally not implemented: paths alone cannot attest promotions.

    Call load_sealed(store) using full ledger verification instead.
    """
    raise IntegrityFailure("untrusted path-only loading prohibited")
