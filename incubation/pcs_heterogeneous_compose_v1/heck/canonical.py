"""Canonical JSON helpers for HECK receipts (JCS-style sorted keys)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonicalize(obj: Any) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest_obj(obj: Any) -> str:
    return sha256_hex(canonicalize(obj))
