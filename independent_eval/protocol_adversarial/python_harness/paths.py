from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
FIXTURES = ROOT / "fixtures"
RESULTS = ROOT / "results"
RUST_CRATE = ROOT / "rust_jcs_ref"


def resolve_lean_authority() -> Path | None:
    """Locate ``pcs-lean-authority`` for black-box attest/verify.

    Order:
    1. ``PCS_LEAN_AUTHORITY`` env (explicit override)
    2. ``REPO_ROOT/formal/.lake/build/bin/pcs-lean-authority``
    3. Main git worktree checkout sharing this object's store (cloud worktrees)
    """
    env = os.environ.get("PCS_LEAN_AUTHORITY")
    if env:
        candidate = Path(env).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

    local = REPO_ROOT / "formal" / ".lake" / "build" / "bin" / "pcs-lean-authority"
    if local.is_file() and os.access(local, os.X_OK):
        return local

    try:
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
        git_common = Path(common)
        if not git_common.is_absolute():
            git_common = (REPO_ROOT / git_common).resolve()
        main_root = git_common.parent if git_common.name == ".git" else git_common
        sibling = main_root / "formal" / ".lake" / "build" / "bin" / "pcs-lean-authority"
        if sibling.is_file() and os.access(sibling, os.X_OK):
            return sibling
    except (OSError, subprocess.CalledProcessError):
        pass
    return None
