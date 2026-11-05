"""Security execution modes — fail closed on missing sandbox."""

from __future__ import annotations

from enum import Enum

from ..core.errors import ErrorCode, PcsNextError


class ExecutionMode(str, Enum):
    PASSIVE_INSPECTION = "PASSIVE_INSPECTION"
    SANDBOXED_EXPERIMENTAL = "SANDBOXED_EXPERIMENTAL"
    INDEPENDENT_VERIFICATION = "INDEPENDENT_VERIFICATION"
    RESEARCH_ONLY_MODEL_UPDATE = "RESEARCH_ONLY_MODEL_UPDATE"
    OFFLINE_EXPORT = "OFFLINE_EXPORT"


def require_mode(requested: ExecutionMode, *, sandbox_available: bool) -> None:
    if requested == ExecutionMode.SANDBOXED_EXPERIMENTAL and not sandbox_available:
        raise PcsNextError(
            ErrorCode.SANDBOX_UNAVAILABLE,
            "sandbox unavailable; refusing silent downgrade to unrestricted execution",
        )
    if requested == ExecutionMode.PASSIVE_INSPECTION:
        return
    # Research-only and offline export do not use production credentials by policy.
    return


def resource_limits(default: dict | None = None) -> dict:
    return {
        "max_seconds": 30,
        "max_memory_mb": 512,
        "max_artifact_bytes": 5_000_000,
        **(default or {}),
    }
