"""Versioned, read-only interface to production PCS executables.

Prefer subprocess invocation over importing mutable production internals.
Never accept a producer-supplied verdict as a replacement for verification.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import ErrorCode, PcsNextError


@dataclass(frozen=True)
class AuthorityIdentity:
    executable: str
    sha256: str
    version_stdout: str
    argv0: str


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_authority(
    *,
    preferred: str | None = None,
    repo_root: str | Path | None = None,
) -> AuthorityIdentity:
    """Locate a PCS CLI without writing to production trees."""
    candidates: list[Path] = []
    if preferred:
        candidates.append(Path(preferred))
    which = shutil.which("pcs")
    if which:
        candidates.append(Path(which))
    if repo_root is not None:
        root = Path(repo_root)
        # Module invocation fallback: python -m pcs.cli (no single file hash)
        candidates.append(root / "pcs" / "cli.py")

    for cand in candidates:
        if cand.is_file():
            digest = _sha256_path(cand)
            # Probe help/version carefully
            version_stdout = ""
            argv = [sys.executable, str(cand), "--help"] if cand.suffix == ".py" else [str(cand), "--help"]
            try:
                proc = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
                version_stdout = (proc.stdout or "")[:2000]
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise PcsNextError(ErrorCode.AUTHORITY_IDENTITY, f"authority probe failed: {exc}") from exc
            return AuthorityIdentity(
                executable=str(cand.resolve()),
                sha256=digest,
                version_stdout=version_stdout,
                argv0=argv[0],
            )
    raise PcsNextError(
        ErrorCode.AUTHORITY_IDENTITY,
        "no PCS authority executable found",
        details={"preferred": preferred, "repo_root": str(repo_root) if repo_root else None},
    )


def invoke_authority_help(identity: AuthorityIdentity) -> dict[str, Any]:
    return {
        "executable": identity.executable,
        "sha256": identity.sha256,
        "help_excerpt": identity.version_stdout[:500],
        "trust_note": "Identity recorded; producer PASS fields remain ignored.",
    }


def try_import_pcs_readonly() -> dict[str, Any]:
    """Optional introspection when running inside the PCS checkout."""
    try:
        import pcs  # type: ignore

        return {
            "importable": True,
            "module_file": getattr(pcs, "__file__", None),
            "mode": "readonly_introspection_only",
        }
    except Exception as exc:  # noqa: BLE001
        return {"importable": False, "error": str(exc)}
