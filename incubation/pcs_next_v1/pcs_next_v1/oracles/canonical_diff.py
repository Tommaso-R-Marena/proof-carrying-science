"""Differential canonicalization vs production PCS when importable."""

from __future__ import annotations

from typing import Any

from ..core.canonical import canonicalize


def compare_to_production(value: Any) -> dict[str, Any]:
    ours = canonicalize(value)
    try:
        from pcs.canonical_json import canonicalize_jcs_bytes  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "SKIPPED",
            "reason": f"production pcs.canonical_json unavailable: {exc}",
            "ours_sha256_prefix": __import__("hashlib").sha256(ours).hexdigest()[:16],
        }
    try:
        prod = canonicalize_jcs_bytes(value)
    except Exception as exc:  # noqa: BLE001
        return {"status": "OPEN", "reason": f"production canonicalize failed: {exc}"}
    match = ours == prod
    return {
        "status": "COMPUTATIONALLY_TESTED" if match else "REFUTED",
        "match": match,
        "ours_len": len(ours),
        "prod_len": len(prod),
        "ours_prefix": ours[:80].decode("utf-8", errors="replace"),
        "prod_prefix": prod[:80].decode("utf-8", errors="replace"),
    }
