"""Capture commits, toolchains, platforms, and available Python interpreters."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .hashing import sha256_file
from .paths import REPO_ROOT


def git_commit(repo: Path | None = None) -> str | None:
    root = repo or REPO_ROOT
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def git_describe(repo: Path | None = None) -> str | None:
    root = repo or REPO_ROOT
    try:
        proc = subprocess.run(
            ["git", "describe", "--always", "--dirty", "--tags"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _python_probe(executable: str) -> dict[str, Any] | None:
    exe = shutil.which(executable) if not os.path.isabs(executable) else executable
    if not exe or not Path(exe).is_file():
        return None
    try:
        proc = subprocess.run(
            [
                exe,
                "-c",
                "import platform,sys,json; print(json.dumps({"
                "'version': sys.version.split()[0],"
                "'implementation': platform.python_implementation(),"
                "'executable': sys.executable,"
                "}))",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        import json

        info = json.loads(proc.stdout.strip())
        info["sha256"] = sha256_file(exe)
        info["path"] = exe
        return info
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return {
            "path": exe,
            "sha256": sha256_file(exe) if Path(exe).is_file() else None,
            "probe_error": True,
        }


def discover_python_interpreters(extra: list[str] | None = None) -> list[dict[str, Any]]:
    """Return distinct Python interpreters available on this host.

    Probes common names plus the current interpreter. Does not install anything.
    """
    candidates = [
        sys.executable,
        "python3",
        "python3.11",
        "python3.12",
        "python3.13",
        "python",
    ]
    if extra:
        candidates.extend(extra)
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for cand in candidates:
        info = _python_probe(cand)
        if not info:
            continue
        key = info.get("path") or cand
        if key in seen:
            continue
        seen.add(key)
        out.append(info)
    return out


def resolve_lean_authority_path(repo: Path | None = None) -> Path | None:
    """Locate ``pcs-lean-authority`` without inventing a binary.

    Order:
    1. ``PCS_LEAN_AUTHORITY`` env (explicit override)
    2. ``<repo>/formal/.lake/build/bin/pcs-lean-authority``
    3. ``PATH`` lookup for ``pcs-lean-authority``
    4. Main git worktree sharing this object's store (cloud worktrees)
    """
    root = repo or REPO_ROOT
    env = os.environ.get("PCS_LEAN_AUTHORITY")
    if env:
        candidate = Path(env).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

    local = root / "formal" / ".lake" / "build" / "bin" / "pcs-lean-authority"
    if local.is_file() and os.access(local, os.X_OK):
        return local

    which = shutil.which("pcs-lean-authority")
    if which:
        path = Path(which)
        if path.is_file() and os.access(path, os.X_OK):
            return path

    try:
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=root,
            text=True,
        ).strip()
        git_common = Path(common)
        if not git_common.is_absolute():
            git_common = (root / git_common).resolve()
        main_root = git_common.parent if git_common.name == ".git" else git_common
        sibling = main_root / "formal" / ".lake" / "build" / "bin" / "pcs-lean-authority"
        if sibling.is_file() and os.access(sibling, os.X_OK):
            return sibling
    except (OSError, subprocess.CalledProcessError):
        pass
    return None


def probe_lean_authority(repo: Path | None = None) -> dict[str, Any]:
    """Locate pcs-lean-authority if present and record path + SHA-256.

    Absence is recorded as ``present=false`` — never assumed identical across hosts.
    """
    path = resolve_lean_authority_path(repo)
    if path is not None:
        return {
            "present": True,
            "path": str(path),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
            "discovery": "env_or_repo_or_path_or_common_worktree",
        }
    return {
        "present": False,
        "path": None,
        "sha256": None,
        "note": "pcs-lean-authority not found; reconstruction harness does not invent a binary hash",
    }


def capture_host_environment(repo: Path | None = None) -> dict[str, Any]:
    root = repo or REPO_ROOT
    lean_toolchain = None
    toolchain_path = root / "lean-toolchain"
    if toolchain_path.is_file():
        lean_toolchain = toolchain_path.read_text(encoding="utf-8").strip()

    crypto_version = None
    try:
        import cryptography

        crypto_version = getattr(cryptography, "__version__", None)
    except ImportError:
        crypto_version = None

    lean_authority = probe_lean_authority(root)

    return {
        "git_commit": git_commit(root),
        "git_describe": git_describe(root),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "python_runtime": sys.version,
            "python_executable": sys.executable,
            "python_executable_sha256": sha256_file(sys.executable) if Path(sys.executable).is_file() else None,
        },
        "toolchains": {
            "lean_toolchain_file": lean_toolchain,
            "pcs_lean_authority": lean_authority,
            "cryptography": crypto_version,
            "zipfile_module": "stdlib",
            "hashlib_sha256": "stdlib/openssl-backed",
        },
        "interpreters": discover_python_interpreters(),
    }
