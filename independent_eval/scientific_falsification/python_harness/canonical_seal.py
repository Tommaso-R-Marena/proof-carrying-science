"""Content-addressed seals for Workstream B summary artifacts.

Matches Assurance Card canonicalization id so program_context digests and
SUMMARY seals are comparable offline. Seal does not certify science.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

CANONICALIZATION_ID = "json-sort-keys-compact-utf8-v1"
INTEGRITY_KEY = "artifact_integrity"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def seal_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in payload.items() if k != INTEGRITY_KEY}
    digest = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    sealed = dict(payload)
    sealed[INTEGRITY_KEY] = {
        "algorithm": "sha256",
        "canonicalization": CANONICALIZATION_ID,
        "digest_sha256": digest,
        "sealed_fields_excluded": [INTEGRITY_KEY],
        "note": (
            "Digest binds summary bytes only. Does not issue ACCEPT/PASS and "
            "does not establish empirical adequacy."
        ),
    }
    return sealed


def verify_artifact_integrity(payload: dict[str, Any]) -> bool:
    embedded = payload.get(INTEGRITY_KEY)
    if not isinstance(embedded, dict):
        return False
    expected = seal_artifact(payload)[INTEGRITY_KEY]["digest_sha256"]
    return embedded.get("digest_sha256") == expected
