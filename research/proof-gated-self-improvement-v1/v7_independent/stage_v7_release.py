#!/usr/bin/env python3
"""Stage the *exact* Aristotle V7 release into a clean, isolated PCS checkout.

Does not contact GitHub, push, merge, or touch production branches.
Stops on modified worktrees, mismatched release hashes and V5/V6 source drift.
Run from repo root after checkout of the intended V6 stacked research base.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import subprocess
import tarfile

SHA256 = "e98448c4d9493c54b88c876ea715c4c66d653565bf60d553c9627b14b7a5f8f8"
BASE = "integration/pcs-aristotle-v6-certificates-20261017"
MODULE_NAMES = (
    "ProofGatedPolicy", "ProofGatedBoundary", "ProofGatedReceipt",
    "ProofGatedSweepCert", "ProofGatedCert7", "ProofGatedRuntimeContract",
    "ProofGatedV7EndToEnd", "ProofGatedV7Limits",
)
EXPLICIT_FILES = {
    "PCS_PROOF_GATED_V7_REPORT.md",
    "PCS/V2/ProofGatedFullAudit.lean",
    "scripts/proof_gated_v7_vectors.lean",
    "scripts/proof_gated_ci.sh",
    "scripts/gen_full_audit.sh",
    "scripts/proof_gated_package.sh",
    "scripts/proof_gated_verify_archive.sh",
}
MODULES = {"PCS/V2/" + n + ".lean" for n in MODULE_NAMES}
def git(repo: pathlib.Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args],
                       text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError("git " + " ".join(args) + ": " + p.stderr)
    return p.stdout.strip()
def permitted(p: str) -> bool:
    return p in MODULES or p in EXPLICIT_FILES or p.startswith("fixtures/proof_gated/v7/")
def main() -> None:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--repo", type=pathlib.Path, required=True)
    a.add_argument("--release", type=pathlib.Path, required=True)
    a.add_argument("--branch", default="integration/pcs-aristotle-v7-authority-20261018")
    a.add_argument("--base", default=BASE)
    a.add_argument("--apply", action="store_true",
                   help="Write validated files to the *current* branch (otherwise dry-run)")
    ns = a.parse_args()
    repo = ns.repo.resolve()
    release = ns.release.resolve()
    if git(repo, "status", "--porcelain"):
        raise RuntimeError("Worktree not clean; refusing to stage V7")
    current = git(repo, "branch", "--show-current")
    if current != ns.branch:
        raise RuntimeError("Expected isolated branch " + ns.branch +
                           "; current=" + current +
                           ". Create from " + ns.base + " yourself.")
    actual = hashlib.sha256(release.read_bytes()).hexdigest()
    if actual != SHA256:
        raise RuntimeError("V7 archive SHA-256 mismatch: " + actual)
    changed: dict[str, bytes] = {}
    member_data: dict[str, bytes] = {}
    with tarfile.open(release, "r:gz") as tar:
        for m in tar.getmembers():
            p = pathlib.PurePosixPath(m.name)
            if (not m.isfile() or p.is_absolute() or ".." in p.parts
                    or str(p) != m.name):
                raise RuntimeError("Unsafe/non-file archive member: " + m.name)
            if m.name in member_data:
                raise RuntimeError("Duplicate release member: " + m.name)
            f = tar.extractfile(m)
            if f is None:
                raise RuntimeError("Missing member contents: " + m.name)
            member_data[m.name] = f.read()
    if len(member_data) != 516:
        raise RuntimeError("Unexpected release file count: " + str(len(member_data)))
    missing = (MODULES | EXPLICIT_FILES) - set(member_data)
    if missing:
        raise RuntimeError("Expected release files absent: " + repr(sorted(missing)))
    # Guard the prior formal layer: every old, named ProofGated module should
    # exactly agree with the checked-out V6 base. Never silently overwrite it.
    for name, data in member_data.items():
        if (name.startswith("PCS/V2/ProofGated") and name.endswith(".lean")
                and name not in MODULES
                and name != "PCS/V2/ProofGatedFullAudit.lean"):
            path = repo / name.removeprefix("PCS/")
            # The release is a standalone formal tree; the PCS repo formal tree differs.
            if not path.is_file():
                raise RuntimeError("Prior Lean module missing from PCS base: " + str(path))
            if path.read_bytes() != data:
                raise RuntimeError("Prior Lean source differs from V7 release: " + name)
    for name, data in member_data.items():
        if not permitted(name):
            continue
        target = repo / "formal" / name
        if name == "PCS_PROOF_GATED_V7_REPORT.md":
            target = repo / "formal" / name
        if target.exists() and target.read_bytes() == data:
            continue
        if name in MODULES and target.exists():
            raise RuntimeError("V7 new module would overwrite existing: " + str(target))
        changed[str(target.relative_to(repo))] = data
    print("V7 release SHA256:", actual)
    print("Valid V7 archive member count:", len(member_data))
    print("Permitted changed files:", len(changed))
    for name in sorted(changed):
        print(" ", name, hashlib.sha256(changed[name]).hexdigest())
    if not ns.apply:
        print("DRY RUN. No files, branches or refs were changed.")
        return
    for path, data in changed.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print("Staged V7 source files in isolated worktree. Review diff, then run")
    print("  cd formal && bash scripts/proof_gated_ci.sh")
    print("Inspect added and modified files carefully before git add/commit/push.")
if __name__ == "__main__":
    main()
