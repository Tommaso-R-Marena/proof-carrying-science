"""What a retained-source tag keeps reachable (H1-b).  Read-only git queries; creates no ref.

A tag protects its commit and, through it, every ancestor and every object those commits contain.
The original C1 design (H1-a) gives the retained commit the source branch head as first parent, so
the tag keeps that branch's whole development history reachable, including the commits that added
the raw model responses later withheld (MODEL_OUTPUT_LICENSING.md, sections 5 and 6).  The clean
design (H1-b) gives it instead a snapshot commit with the identical tree on the protected main commit
the branch is based on.  These helpers measure the difference: which source-branch commits, and
which withheld blobs, a candidate retained commit reaches.

Neither design changes what the retained-source gate checks (scripts/check_reconciled_prs.py: the
pinned commit and tag, the registry's protected main and original PR heads as ancestors, the exact
non-control tree).  The gate accepts both; the choice is fixed when the owner pins one commit ID.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

INVENTORY = "docs/integration/claimcheck/model_outputs_inventory.json"
# the commits that added the recorded model responses (MODEL_OUTPUT_LICENSING.md, section 5)
OUTPUT_COMMITS = ("f17649ca", "dbe31d72", "87900a17")


def git(cwd, *args) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def is_ancestor(cwd, older: str, newer: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=cwd, capture_output=True).returncode == 0


def withheld_blobs(cwd, inventory: str = INVENTORY, search_from: str = "HEAD") -> dict[str, str]:
    """{git blob id: path} of the original bytes of every inventoried response whose disposition is to withhold it,
    found in history and checked against the inventory's SHA-256.  Raises if one cannot be found: the check would be
    incomplete."""
    inv = json.loads(Path(cwd, inventory).read_text(encoding="utf-8")) if Path(cwd, inventory).exists() else \
        json.loads(git(cwd, "show", f"{search_from}:{inventory}"))
    out: dict[str, str] = {}
    for f in inv["files"]:
        if not f["action"].startswith("withhold"):
            continue
        found = None
        for c in git(cwd, "log", "--format=%H", search_from, "--", f["path"]).split():
            try:
                raw = subprocess.check_output(["git", "show", f"{c}:{f['path']}"], cwd=cwd, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                continue
            if hashlib.sha256(raw).hexdigest() == f["original_sha256"]:
                found = git(cwd, "rev-parse", f"{c}:{f['path']}")
                break
        if found is None:
            raise SystemExit(f"original bytes of {f['path']} not found in the history of {search_from}")
        out[found] = f["path"]
    return out


def reach(cwd, commit: str, protected: list[str], blobs: dict[str, str]) -> dict:
    """What `commit` keeps reachable beyond the protected history."""
    objects = {line.split()[0] for line in git(cwd, "rev-list", "--objects", commit).splitlines() if line}
    beyond = git(cwd, "rev-list", commit, "--not", *protected).split()
    return {"commits_beyond_protected_history": len(beyond),
            "output_commits_reachable": [c for c in OUTPUT_COMMITS if is_ancestor(cwd, c, commit)],
            "withheld_blobs_reachable": sorted(blobs[b] for b in objects & set(blobs))}
