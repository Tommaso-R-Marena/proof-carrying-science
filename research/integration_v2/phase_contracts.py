"""Replay original Git-tree guards and separately admit the combined source.

No historical guard is made to say its additions-only predicate holds on the
combined tree. These are source-identity checks, never Lean/verifier verdicts.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from . import reconcile

PHASES = {
    "local_weights_v1": ("5a0dad902c89917298179c269680954ddb5e22b8", 6382),
    "causal_firewall_v1": ("d7ec58d968fae5051daa7fd8d4bad5b2622b02af", 6394),
    "relational_release_v1": ("12dd713bd726fccf136f9bdaa71d50c5ad3f2a84", 6413),
    "compositional_disclosure_v1": ("b025ad4297252c0601b7b9c9a85859267a89c1fb", 6431),
}


def historical(profile):
    if profile not in PHASES:
        raise ValueError("unknown historical source phase")
    commit, count = PHASES[profile]
    relative = "research/" + profile + "/preservation.py"
    raw = reconcile._git(reconcile.ROOT, "show", commit + ":" + relative)
    common = Path(reconcile._git(reconcile.ROOT, "rev-parse", "--git-common-dir").decode().strip())
    if not common.is_absolute():
        common = (reconcile.ROOT / common).resolve()
    with tempfile.TemporaryDirectory(prefix="pcs-original-source-phase-") as temporary:
        root = Path(temporary)
        subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
        (root / ".git/objects/info/alternates").write_text(str(common / "objects") + "\n")
        # A detached reference to the existing original object, not a new commit.
        (root / ".git/HEAD").write_text(commit + "\n")
        guard = root / relative
        guard.parent.mkdir(parents=True)
        guard.write_bytes(raw)
        response = subprocess.run([sys.executable, str(guard)], cwd=root,
                                  check=True, capture_output=True, text=True, timeout=30)
        result = json.loads(response.stdout)
    if (result.get("passed") is not True or result.get("previous_files_preserved") != count
            or result.get("production_authority") is not False):
        raise ValueError("original phase guard failed its unchanged contract")
    return dict(result, evaluated_commit=commit,
                scope="ORIGINAL_COMMITTED_GIT_TREES_NOT_COMBINED_WORKING_TREE")


def check(profile):
    current = reconcile.check(require_committed=True)
    return dict(current=current, historical=historical(profile))
