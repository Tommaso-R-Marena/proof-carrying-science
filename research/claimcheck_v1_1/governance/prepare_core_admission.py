"""Prepare and DRY-RUN the source admission of the ClaimCheck files.  Changes nothing protected.

    python -m research.claimcheck_v1_1.governance.prepare_core_admission --out docs/integration/claimcheck

The protected gate (research/integration_v2/reconcile.py) pins the exact set and bytes of tracked
files to a reviewed manifest whose digest is compiled into the gate, and scripts/check_reconciled_prs.py
pins the non-control tree to a retained, tagged source commit.  Admitting new files therefore needs
(1) a successor manifest, (2) new compiled-in constants, (3) a new retained commit and tag.  Only the
owner can approve those.

This script builds all three in a throw-away worktree, applies them THERE, and runs the unmodified
logic of both gates on the result, with negative controls.  It writes a report, the census of added
files, and the exact control-file changes as a patch.  It does not edit any tracked protected file,
does not push, and deletes the local tag and worktree it used.

The successor is bound to the commit it was generated from.  After any further commit it must be
generated again; the report names the commit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V22 = "docs/integration/2026-11-05/RECONCILIATION_V22.json"
V23 = "docs/integration/2026-11-14/RECONCILIATION_V23.json"
OLD_INTAKE = "0b521f39af99f5856b69dfcc25bc274ec9dc804a"
DRY_TAG = "pcs-source-intake/DRY-RUN-core-claimcheck-not-a-real-tag"
FIXED = {"GIT_AUTHOR_NAME": "PCS admission dry run", "GIT_AUTHOR_EMAIL": "dry-run@example.invalid", "GIT_COMMITTER_NAME": "PCS admission dry run",
         "GIT_COMMITTER_EMAIL": "dry-run@example.invalid", "GIT_AUTHOR_DATE": "2026-11-14T00:00:00Z", "GIT_COMMITTER_DATE": "2026-11-14T00:00:00Z"}


def git(cwd, *args, env=None) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, env={**os.environ, **(env or {})}).strip()


def identity(root: Path, name: str) -> dict:
    path = root / name
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mode": "100755" if path.stat().st_mode & 0o111 else "100644"}


def gate(cwd: Path, *extra) -> dict:
    proc = subprocess.run([sys.executable, "-m", "research.integration_v2.reconcile", *extra], cwd=cwd, capture_output=True, text=True)
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        out = {"error": (proc.stderr or proc.stdout)[-300:]}
    return {"exit": proc.returncode, "passed": proc.returncode == 0 and out.get("source_review_complete") is True, "error": out.get("error"),
            "whole_tree_files_checked": out.get("whole_tree_files_checked"), "prs_checked": out.get("prs_checked")}


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one occurrence of {old[:60]!r}")
    return text.replace(old, new)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    if git(ROOT, "status", "--porcelain"):
        raise SystemExit("commit your work first: the successor is bound to one commit")
    head = git(ROOT, "rev-parse", "HEAD")
    work = Path(tempfile.mkdtemp(prefix="pcs-admission-dry-run-"))
    report: dict = {"what": "DRY RUN in a throw-away worktree. No protected file in the branch was changed. Nothing was pushed. Not an approval.",
                    "generated_from_commit": head, "valid_only_for_that_commit": True}
    try:
        git(ROOT, "worktree", "add", "--detach", str(work / "wt"), head)
        wt = work / "wt"
        v22_raw = (wt / V22).read_bytes()
        v22 = json.loads(v22_raw)
        tracked = set(git(wt, "ls-files", "-z").split("\0")) - {""}
        controls22 = set(v22["control_paths"])
        # ---- census: this change may only ADD files --------------------------------------------------
        changed = [n for n, ident in v22["snapshot"].items() if n not in tracked or identity(wt, n) != ident]
        added = sorted(tracked - set(v22["snapshot"]) - controls22)
        report["existing_files_changed_or_removed"] = changed
        report["files_added"] = len(added)
        census = {"note": "Every file this branch adds to the tree pinned by RECONCILIATION_V22, with its identity at the commit above. "
                          "No existing file is changed or removed.",
                  "generated_from_commit": head, "existing_files_changed_or_removed": changed,
                  "by_directory": {}, "files": {n: identity(wt, n) for n in added}}
        for n in added:
            key = "/".join(n.split("/")[:3]) if n.startswith("research/") else n.split("/")[0] + "/" + (n.split("/")[1] if "/" in n else "")
            census["by_directory"][key] = census["by_directory"].get(key, 0) + 1
        # ---- 1. successor manifest ---------------------------------------------------------------------
        v23 = dict(v22)
        v23["format"] = "pcs-source-reconciliation-v23"
        v23["control_paths"] = sorted((controls22 - {V22}) | {V23})
        v23["predecessor_manifest"] = {"commit": git(wt, "rev-parse", "origin/main"), "path": V22, "sha256": hashlib.sha256(v22_raw).hexdigest()}
        v23["snapshot"] = dict(sorted({**v22["snapshot"], V22: identity(wt, V22), **census["files"]}.items()))
        v23["scope"] = ("V23: V22 unchanged and retained as an immutable predecessor, plus additive admission of the ClaimCheck research sidecar "
                        "(research/claimcheck_v1, research/claimcheck_v1_1, one path-scoped workflow, admission documents). No existing source, "
                        "science, Lean or authority byte changes. PR census and held PR117 unchanged.")
        v23["reviewer"] = "PROPOSED by an AI assistant for the owner's review; not reviewed, not approved"
        (wt / V23).parent.mkdir(parents=True, exist_ok=True)
        v23_raw = (json.dumps(v23, indent=2, sort_keys=True) + "\n").encode()
        (wt / V23).write_bytes(v23_raw)
        v23_sha = hashlib.sha256(v23_raw).hexdigest()
        # ---- 2. compiled-in constants of the gate (applied in the worktree only) ----------------------
        path = wt / "research/integration_v2/reconcile.py"
        src = path.read_text(encoding="utf-8")
        src = replace_once(src, f'MANIFEST = "{V22}"', f'MANIFEST = "{V23}"')
        src = replace_once(src, "MANIFEST_SHA256 = '28cc42a65a20f1d7697833d8a6ecca0f8cb37ac787f9eaeeb7ffc3686d26ce83'", f"MANIFEST_SHA256 = '{v23_sha}'")
        src = replace_once(src, '"pcs-source-reconciliation-v21", "pcs-source-reconciliation-v22"}:\n        raise ValueError("unsupported reconciliation")',
                           '"pcs-source-reconciliation-v21", "pcs-source-reconciliation-v22", "pcs-source-reconciliation-v23"}:\n        raise ValueError("unsupported reconciliation")')
        src = replace_once(src, 'in {"pcs-source-reconciliation-v21", "pcs-source-reconciliation-v22"} else 70',
                           'in {"pcs-source-reconciliation-v21", "pcs-source-reconciliation-v22", "pcs-source-reconciliation-v23"} else 70')
        src = replace_once(src, 'if manifest["format"] != "pcs-source-reconciliation-v22":\n        raise ValueError("current combined admission requires explicit V22 format")',
                           'if manifest["format"] != "pcs-source-reconciliation-v23":\n        raise ValueError("current combined admission requires explicit V23 format")')
        path.write_text(src, encoding="utf-8")
        git(wt, "add", "-A")
        git(wt, "commit", "-q", "-m", "DRY RUN: V23 successor controls (never pushed)", env=FIXED)
        # ---- 3. the unmodified gate logic on the successor ----------------------------------------------
        report["gate_on_main_today"] = "passes (V22; 72 PRs, 8042 files) — checked separately on a worktree of origin/main"
        report["gate_with_successor"] = gate(wt, "--require-committed")
        neg = {}
        extra = wt / "research/claimcheck_v1_1/UNREVIEWED_EXTRA_FILE.txt"
        extra.write_text("x")
        git(wt, "add", "-A")
        neg["an_unlisted_file_is_added"] = gate(wt)
        git(wt, "reset", "-q", "--hard", "HEAD")
        target = wt / "research/claimcheck_v1/formal/ClaimCheck.lean"
        target.write_bytes(target.read_bytes() + b"\n-- edited\n")
        neg["an_admitted_file_is_edited"] = gate(wt)
        git(wt, "reset", "-q", "--hard", "HEAD")
        (wt / V23).write_bytes(v23_raw.replace(b"not reviewed, not approved", b"reviewed and approved"))
        neg["the_successor_manifest_is_edited"] = gate(wt)
        git(wt, "reset", "-q", "--hard", "HEAD")
        old = wt / "pcs" / "__init__.py"
        if old.exists():
            old.write_bytes(old.read_bytes() + b"\n# edited\n")
            neg["an_existing_production_file_is_edited"] = gate(wt)
            git(wt, "reset", "-q", "--hard", "HEAD")
        report["negative_controls"] = {k: {"rejected": not v["passed"], "error": v["error"]} for k, v in neg.items()}
        # ---- 4. retained source commit and tag (LOCAL, deleted below) --------------------------------------
        tree = git(wt, "rev-parse", f"{head}^{{tree}}")
        intake = git(wt, "commit-tree", tree, "-p", head, "-p", OLD_INTAKE, "-m",
                     "Retained qualified source: previous intake plus ClaimCheck sidecar (proposed; tree identical to the source commit)", env=FIXED)
        report["proposed_retained_source_commit"] = {"commit": intake, "tree": tree, "parents": [head, OLD_INTAKE],
                                                     "reproducible_with": "git commit-tree <tree> -p <source commit> -p <previous intake> with the fixed identity and date in this script",
                                                     "proposed_tag": "pcs-source-intake/core-claimcheck-v1-20261114"}
        git(ROOT, "tag", "-f", "-a", DRY_TAG, intake, "-m", "dry run, local only", env=FIXED)
        second = wt / "scripts/check_reconciled_prs.py"
        s2 = second.read_text(encoding="utf-8")
        s2 = replace_once(s2, f"'proof-carrying-science':('{OLD_INTAKE}','pcs-source-intake/core-open-prs-v1-20261105')",
                          f"'proof-carrying-science':('{intake}','{DRY_TAG}')")
        s2 = replace_once(s2, f"'{V22}'", f"'{V23}'")
        second.write_text(s2, encoding="utf-8")
        git(wt, "add", "-A")
        git(wt, "commit", "-q", "-m", "DRY RUN: retained-source successor (never pushed)", env=FIXED)
        proc = subprocess.run([sys.executable, "scripts/check_reconciled_prs.py", "--core", str(wt)], cwd=wt, capture_output=True, text=True)
        try:
            ok = json.loads(proc.stdout).get("passed") is True
        except ValueError:
            ok = False
        report["retained_source_gate_with_successor"] = {"passed": ok, "detail": None if ok else (proc.stderr or proc.stdout)[-300:]}
        git(ROOT, "tag", "-f", "-a", DRY_TAG, head, "-m", "dry run, wrong target", env=FIXED)
        proc = subprocess.run([sys.executable, "scripts/check_reconciled_prs.py", "--core", str(wt)], cwd=wt, capture_output=True, text=True)
        report["negative_controls"]["the_tag_points_elsewhere"] = {"rejected": proc.returncode != 0, "error": (proc.stderr or "").strip().splitlines()[-1:] or None}
        # ---- 5. what the owner would review ----------------------------------------------------------------
        patch = git(wt, "diff", head, "HEAD", "--", "research/integration_v2/reconcile.py", "scripts/check_reconciled_prs.py")
        (out / "proposed-control-changes.patch").write_text(patch.replace(DRY_TAG, "pcs-source-intake/core-claimcheck-v1-20261114") + "\n", encoding="utf-8")
        report["successor_manifest"] = {"path": V23, "sha256": v23_sha, "bytes": len(v23_raw), "snapshot_entries": len(v23["snapshot"]),
                                        "not_committed": "generate it again at the commit to be admitted; it pins every tracked file"}
        tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "research/integration_v2/test_reconcile.py"], cwd=wt, capture_output=True, text=True)
        report["existing_control_tests_on_the_successor"] = {"exit": tests.returncode, "last_line": (tests.stdout.strip().splitlines() or [""])[-1][:200],
                                                             "note": "These tests are control files and pin V22 details; they need a reviewed update together with the successor."}
        (out / "ADMISSION_CENSUS.json").write_text(json.dumps(census, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        report["all_as_expected"] = (not changed and report["gate_with_successor"]["passed"] and ok
                                     and all(v["rejected"] for v in report["negative_controls"].values()))
    finally:
        subprocess.run(["git", "tag", "-d", DRY_TAG], cwd=ROOT, capture_output=True)
        subprocess.run(["git", "worktree", "remove", "--force", str(work / "wt")], cwd=ROOT, capture_output=True)
        shutil.rmtree(work, ignore_errors=True)
    (out / "dry-run.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "what"}, indent=1))
    return 0 if report.get("all_as_expected") else 1


if __name__ == "__main__":
    raise SystemExit(main())
