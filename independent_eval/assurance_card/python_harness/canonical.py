"""Canonical JSON serialization and content-addressed card seals.

The seal covers the card payload excluding ``card_integrity`` itself so the
digest is stable under re-sealing. Canonicalization is deliberately simple and
fully specified (no external JCS dependency): UTF-8 JSON with sorted object
keys and compact separators. This is inspectable offline and reproducible
across CPython versions for the card's JSON-compatible value types.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

CANONICALIZATION_ID = "json-sort-keys-compact-utf8-v1"
SEAL_ALGORITHM = "sha256"
INTEGRITY_KEY = "card_integrity"


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes for a JSON-compatible value."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def payload_for_seal(card: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of the card without the integrity block."""
    return {k: v for k, v in card.items() if k != INTEGRITY_KEY}


def compute_card_integrity(card: dict[str, Any]) -> dict[str, Any]:
    """Compute the integrity block for ``card`` (ignoring any existing seal)."""
    payload = payload_for_seal(card)
    digest = sha256_hex(canonical_json_bytes(payload))
    return {
        "algorithm": SEAL_ALGORITHM,
        "canonicalization": CANONICALIZATION_ID,
        "digest_sha256": digest,
        "sealed_fields_excluded": [INTEGRITY_KEY],
        "note": (
            "Digest covers the card JSON payload excluding card_integrity. "
            "Seal does not issue ACCEPT/PASS and does not certify science."
        ),
    }


def seal_card(card: dict[str, Any]) -> dict[str, Any]:
    """Return a new card dict with a fresh ``card_integrity`` block."""
    sealed = dict(card)
    sealed[INTEGRITY_KEY] = compute_card_integrity(sealed)
    return sealed


def verify_card_integrity(card: dict[str, Any]) -> dict[str, Any]:
    """Recompute the seal and compare to the embedded digest (observational)."""
    embedded = card.get(INTEGRITY_KEY)
    if not isinstance(embedded, dict) or not embedded.get("digest_sha256"):
        return {
            "checked": False,
            "ok": None,
            "reason": "card_integrity missing or incomplete",
        }
    expected = compute_card_integrity(card)
    ok = (
        embedded.get("algorithm") == expected["algorithm"]
        and embedded.get("canonicalization") == expected["canonicalization"]
        and embedded.get("digest_sha256") == expected["digest_sha256"]
    )
    return {
        "checked": True,
        "ok": ok,
        "expected_digest_sha256": expected["digest_sha256"],
        "embedded_digest_sha256": embedded.get("digest_sha256"),
        "reason": None if ok else "digest mismatch after recomputation",
    }
