"""Authority lane: black-box ``pcs verify`` / ``python -m pcs.cli verify``.

This lane is authoritative for computational / cryptographic validity of the
package. The Assurance Card records argv, return code, ok, stdout/stderr tails,
and duration. It does not rebuild Mathlib/Lean and does not issue science claims.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

TAIL_CHARS = 4000
VERIFY_TIMEOUT_S = 120

AUTHORITY_DISCLAIMER = (
    "Authority lane: black-box pcs verify (or python -m pcs.cli verify). "
    "This lane is authoritative for computational/cryptographic validity of the "
    "package. It does not certify empirical or scientific adequacy."
)


@dataclass
class AuthorityLaneResult:
    """Record of a single black-box verify invocation."""

    lane: str = "authority"
    cli_is_authority: bool = True
    disclaimer: str = AUTHORITY_DISCLAIMER
    certificate_path: str | None = None
    argv: list[str] | None = None
    returncode: int | None = None
    ok: bool | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    duration_seconds: float | None = None
    cli_valid: bool | None = None
    cli_errors: list[str] = field(default_factory=list)
    attempted: bool = False
    skipped: bool = False
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["cli_is_authority"] = True
        d["lane"] = "authority"
        return d


def _tail(text: str | None, limit: int = TAIL_CHARS) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[-limit:]


def resolve_verify_argv(certificate: Path) -> list[str] | None:
    """Prefer ``pcs verify``; fall back to ``python -m pcs.cli verify``."""
    cert = str(Path(certificate).resolve())
    pcs_bin = shutil.which("pcs")
    if pcs_bin:
        return [pcs_bin, "verify", cert]
    try:
        import pcs.cli  # noqa: F401
    except ImportError:
        return None
    return [sys.executable, "-m", "pcs.cli", "verify", cert]


def parse_cli_json(stdout: str) -> dict[str, Any] | None:
    text = (stdout or "").strip()
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def run_pcs_verify(
    certificate: str | Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    timeout: float = VERIFY_TIMEOUT_S,
) -> AuthorityLaneResult:
    """Execute black-box verify and return an AuthorityLaneResult."""
    cert = Path(certificate).resolve()
    result = AuthorityLaneResult(certificate_path=str(cert))

    argv = resolve_verify_argv(cert)
    if argv is None:
        result.skipped = True
        result.skip_reason = (
            "pcs CLI not available (neither `pcs` nor `pcs.cli` importable)"
        )
        return result

    result.argv = argv
    result.attempted = True
    run = runner or subprocess.run
    t0 = time.perf_counter()
    try:
        completed = run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        result.duration_seconds = round(time.perf_counter() - t0, 6)
        result.returncode = None
        result.ok = False
        result.stdout_tail = _tail(exc.stdout if isinstance(exc.stdout, str) else "")
        result.stderr_tail = _tail(exc.stderr if isinstance(exc.stderr, str) else "")
        result.skip_reason = f"CLI verify timed out after {timeout}s"
        return result
    except OSError as exc:
        result.duration_seconds = round(time.perf_counter() - t0, 6)
        result.ok = False
        result.skipped = True
        result.skip_reason = f"CLI verify OS error: {exc}"
        return result

    result.duration_seconds = round(time.perf_counter() - t0, 6)
    result.returncode = int(completed.returncode)
    result.stdout_tail = _tail(completed.stdout)
    result.stderr_tail = _tail(completed.stderr)

    parsed = parse_cli_json(completed.stdout or "")
    if parsed is not None:
        if "valid" in parsed:
            result.cli_valid = bool(parsed.get("valid"))
        errors = parsed.get("errors") or []
        if isinstance(errors, list):
            result.cli_errors = [str(e) for e in errors]
        elif errors:
            result.cli_errors = [str(errors)]

    if result.cli_valid is not None:
        result.ok = bool(result.cli_valid) and completed.returncode == 0
    else:
        result.ok = completed.returncode == 0
    return result
