"""Prepare and DRY-RUN the source admission of the ClaimCheck files.  Changes nothing protected.

    python -m research.claimcheck_v1_1.governance.prepare_core_admission --out docs/integration/claimcheck \
        [--pytest-python PY] [--emit DIR] [--history clean|development]

The protected gate (research/integration_v2/reconcile.py) pins the exact set and bytes of tracked
files to a reviewed manifest whose digest is compiled into the gate, and scripts/check_reconciled_prs.py
pins the non-control tree to a retained, tagged source commit.  Admitting new files therefore needs
one control commit with (1) a successor manifest V23, (2) new compiled-in constants in reconcile.py,
(3) the successor of its protected test file, (4) a new retained-source entry in
check_reconciled_prs.py, and, outside the tree, (5) the retained commit and its tag.  Only the owner
can approve those.

Order matters: the retained commit depends only on the source commit; check_reconciled_prs.py names
it; V23 pins every tracked file, including the new bytes of check_reconciled_prs.py; reconcile.py
pins the digest of V23.

The script builds the control commit twice from the same source commit:
  * the PROPOSAL, with the proposed tag name.  No ref is created.  These are the bytes the owner
    would commit; their digests are reported and the three edited files are written as a patch.
  * the DRY RUN, identical except for a placeholder tag name, applied in a throw-away worktree with
    a local placeholder tag (deleted at the end).  The unmodified logic of both gates and both
    protected test files runs on it, with negative controls.
It then checks that the two differ only in the tag name and in the digests that follow from it.

It does not edit any tracked file outside --out, does not push, and creates no tag with a real
name.  --emit DIR writes the proposed control files (V23 included) under DIR, outside the tree.

The successor is bound to the source commit it was generated from.  After any further commit it
must be generated again; the report names the commit.

Retained history (owner decision H1).  `--history clean` (H1-b, proposed): the retained commit's first
parent is a snapshot commit with the source commit's exact tree on the protected main commit the
branch is based on, so the tag keeps no commit of the source branch reachable (in particular not the
commits that added the withheld model responses).  `--history development` (H1-a, the original
design): its first parent is the source commit itself, so the tag keeps the branch's whole history
reachable.  In both, the second parent is the previous intake, the tree is the source commit's tree,
and the gates check exactly the same things; only the commit ID the owner pins differs.  Neither
removes anything from existing pull-request refs or clones.
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
GATE = "research/integration_v2/reconcile.py"
GATE_TEST = "research/integration_v2/test_reconcile.py"
RETAINED = "scripts/check_reconciled_prs.py"
EDITED = (GATE, GATE_TEST, RETAINED)
OLD_INTAKE = "0b521f39af99f5856b69dfcc25bc274ec9dc804a"
OLD_TAG = "pcs-source-intake/core-open-prs-v1-20261105"
# the protected main commit that introduced V22 (PR 198); pinned, so the successor does not depend on where origin/main is
V22_COMMIT = "bc78660b5fac857fce3873eb6cda0445d1903da1"
V22_SHA256 = "28cc42a65a20f1d7697833d8a6ecca0f8cb37ac787f9eaeeb7ffc3686d26ce83"
PROPOSED_TAG = "pcs-source-intake/core-claimcheck-v1-20261114"
DRY_TAG = "pcs-source-intake/DRY-RUN-core-claimcheck-not-a-real-tag"
ADDED_ROOTS = ("research/claimcheck_v1/", "research/claimcheck_v1_1/", "docs/integration/claimcheck/")
ADDED_FILES = (".github/workflows/pcs-claimcheck-v1.yml",)
# files the dry run and the audit rewrite; a commit that changes only these after the commit they describe adds no source
EVIDENCE = {"docs/integration/claimcheck/dry-run.json", "docs/integration/claimcheck/ADMISSION_CENSUS.json",
            "docs/integration/claimcheck/proposed-control-changes.patch", "docs/integration/claimcheck/ADMISSION_AUDIT.json"}
# H1-b: the protected main commit the source branch is based on; the snapshot's only parent (pinned, like V22_COMMIT)
PROTECTED_MAIN = V22_COMMIT
RETAINED_MESSAGE = "Retained qualified source: previous intake plus ClaimCheck sidecar (proposed; tree identical to the source commit)"
SNAPSHOT_MESSAGE = ("ClaimCheck admitted source snapshot (proposed): the exact tree of reviewed source commit {head}, on protected main "
                    "{main}. Clean history: no commit of the source branch is an ancestor.")
CLEAN_MESSAGE = ("Retained qualified source: previous intake plus ClaimCheck sidecar (proposed; clean history; tree identical to reviewed "
                 "source commit {head})")
FIXED = {"GIT_AUTHOR_NAME": "PCS admission dry run", "GIT_AUTHOR_EMAIL": "dry-run@example.invalid", "GIT_COMMITTER_NAME": "PCS admission dry run",
         "GIT_COMMITTER_EMAIL": "dry-run@example.invalid", "GIT_AUTHOR_DATE": "2026-11-14T00:00:00Z", "GIT_COMMITTER_DATE": "2026-11-14T00:00:00Z"}

V23_TEST = '''

def test_v23_keeps_v22_and_only_adds_the_claimcheck_sidecar():
    v22_path='{v22}'
    raw=(gate.ROOT/v22_path).read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='{v22_sha}'
    v22=gate._json(raw)
    current=gate._json((gate.ROOT/gate.MANIFEST).read_bytes())
    assert current['format']=='pcs-source-reconciliation-v23'
    assert current['predecessor_manifest']==dict(commit='{v22_commit}',path=v22_path,sha256='{v22_sha}')
    assert current['prs']==v22['prs'] and len(current['prs'])==72
    assert current['control_paths']==sorted((set(v22['control_paths'])-{{v22_path}})|{{gate.MANIFEST}})
    # one pinned control script changes: it names the new retained source commit and the V23 control path
    changed={{n for n,identity in v22['snapshot'].items() if current['snapshot'].get(n)!=identity}}
    assert changed=={{'{retained}'}}
    assert current['snapshot'][v22_path]==dict(sha256='{v22_sha}',mode='100644')
    added=set(current['snapshot'])-set(v22['snapshot'])-{{v22_path}}
    assert added and all(n.startswith({roots!r}) or n in {files!r} for n in added)
'''


def git(cwd, *args, env=None) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, env={**os.environ, **(env or {})}).strip()


def show(cwd, commit: str, name: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=cwd)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def identity(root: Path, name: str) -> dict:
    path = root / name
    return {"sha256": sha(path.read_bytes()), "mode": "100755" if path.stat().st_mode & 0o111 else "100644"}


def gate(cwd: Path, *extra) -> dict:
    proc = subprocess.run([sys.executable, "-m", "research.integration_v2.reconcile", *extra], cwd=cwd, capture_output=True, text=True)
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        out = {"error": (proc.stderr or proc.stdout)[-300:]}
    return {"exit": proc.returncode, "passed": proc.returncode == 0 and out.get("source_review_complete") is True, "error": out.get("error"),
            "prs_checked": out.get("prs_checked"), "source_bindings_checked": out.get("source_bindings_checked")}


def retained_gate(cwd: Path) -> dict:
    proc = subprocess.run([sys.executable, RETAINED, "--core", str(cwd)], cwd=cwd, capture_output=True, text=True)
    try:
        ok = json.loads(proc.stdout).get("passed") is True
    except ValueError:
        ok = False
    lines = (proc.stderr or proc.stdout or "").strip().splitlines()
    return {"exit": proc.returncode, "passed": ok and proc.returncode == 0, "error": None if ok else (lines[-1][:300] if lines else None)}


def suite(cmd, cwd: Path) -> dict:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    text = (proc.stdout + "\n" + proc.stderr).strip()
    result = {"exit": proc.returncode, "last_line": (text.splitlines() or [""])[-1][:200]}
    if proc.returncode:
        result["failure"] = text[-2500:]
    return result


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one occurrence of {old[:60]!r}")
    return text.replace(old, new)


def retained_commit(cwd: Path, head: str, history: str = "clean") -> dict:
    """The proposed retained source commit for `head`, written with `git commit-tree` (objects only, no ref).

    development (H1-a): parents [head, previous intake].
    clean (H1-b): a snapshot commit S with head's tree and the single parent PROTECTED_MAIN, then parents [S, previous intake].
    Deterministic: fixed identity, date and messages."""
    tree = git(cwd, "rev-parse", f"{head}^{{tree}}")
    if history == "development":
        commit = git(cwd, "commit-tree", tree, "-p", head, "-p", OLD_INTAKE, "-m", RETAINED_MESSAGE, env=FIXED)
        return {"history": "development", "commit": commit, "tree": tree, "parents": [head, OLD_INTAKE], "source_commit": head}
    if history != "clean":
        raise ValueError(f"unknown retained history design {history!r}")
    if subprocess.run(["git", "merge-base", "--is-ancestor", PROTECTED_MAIN, head], cwd=cwd, capture_output=True).returncode != 0:
        raise SystemExit(f"the source commit is not based on the pinned protected main commit {PROTECTED_MAIN}")
    snapshot = git(cwd, "commit-tree", tree, "-p", PROTECTED_MAIN, "-m", SNAPSHOT_MESSAGE.format(head=head, main=PROTECTED_MAIN), env=FIXED)
    commit = git(cwd, "commit-tree", tree, "-p", snapshot, "-p", OLD_INTAKE, "-m", CLEAN_MESSAGE.format(head=head), env=FIXED)
    return {"history": "clean", "commit": commit, "tree": tree, "parents": [snapshot, OLD_INTAKE], "source_commit": head,
            "snapshot": {"commit": snapshot, "tree": tree, "parents": [PROTECTED_MAIN]}}


def history_review(cwd: Path, head: str, retained: dict) -> dict:
    """Review-time facts about the retained commit that the gate does not check (it accepts either design)."""
    from .retained_history import is_ancestor, reach, withheld_blobs
    reg = json.loads(show(cwd, head, "docs/reconciliation/OPEN_PRS.json"))
    core = next(r for r in reg["repositories"] if r["repository"].endswith("/proof-carrying-science"))
    required = [core["protected"]["main"], *[p["head"] for p in core["original_open_prs"]], OLD_INTAKE]
    r = retained["commit"]
    facts = {"design": retained["history"],
             "tree_equals_source_tree": git(cwd, "rev-parse", f"{r}^{{tree}}") == git(cwd, "rev-parse", f"{head}^{{tree}}"),
             "no_file_differs_from_source": subprocess.run(["git", "diff", "--quiet", head, r], cwd=cwd).returncode == 0,
             "registry_main_original_pr_heads_and_previous_intake_are_ancestors": all(is_ancestor(cwd, c, r) for c in required),
             "source_commit_is_an_ancestor": is_ancestor(cwd, head, r)}
    if retained["history"] == "clean":
        s = retained["snapshot"]["commit"]
        facts["snapshot_changes_exactly_what_the_source_branch_changes"] = (
            git(cwd, "diff", "--name-status", PROTECTED_MAIN, s) == git(cwd, "diff", "--name-status", PROTECTED_MAIN, head))
    facts.update(reach(cwd, r, [PROTECTED_MAIN, OLD_INTAKE], withheld_blobs(cwd, search_from=head)))
    return facts


def build(src: Path, head: str, intake: str, tag: str, v22: dict, v22_raw: bytes, added: dict) -> dict:
    """The control commit's files for one tag name: {path: bytes}.  Reads the originals from the source commit."""
    files: dict[str, bytes] = {}
    # (4) the retained-source gate names the new retained commit and tag, and V23 in place of V22 as a control
    s2 = show(src, head, RETAINED).decode("utf-8")
    s2 = replace_once(s2, f"'proof-carrying-science':('{OLD_INTAKE}','{OLD_TAG}')", f"'proof-carrying-science':('{intake}','{tag}')")
    s2 = replace_once(s2, f"'{V22}'", f"'{V23}'")
    files[RETAINED] = s2.encode("utf-8")
    # (1) V23: V22 unchanged as an immutable predecessor; the added files; the new bytes of the one edited pinned control script
    v23 = dict(v22)
    v23["format"] = "pcs-source-reconciliation-v23"
    v23["control_paths"] = sorted((set(v22["control_paths"]) - {V22}) | {V23})
    v23["predecessor_manifest"] = {"commit": V22_COMMIT, "path": V22, "sha256": sha(v22_raw)}
    retained_mode = v22["snapshot"][RETAINED]["mode"]
    v23["snapshot"] = dict(sorted({**v22["snapshot"], V22: {"sha256": sha(v22_raw), "mode": "100644"}, **added,
                                   RETAINED: {"sha256": sha(files[RETAINED]), "mode": retained_mode}}.items()))
    v23["scope"] = ("V23: V22 unchanged and retained as an immutable predecessor, plus additive admission of the ClaimCheck research sidecar "
                    "(research/claimcheck_v1, research/claimcheck_v1_1, one path-scoped workflow, admission documents). One pinned control "
                    "script (scripts/check_reconciled_prs.py) names the new retained source commit and the V23 control path. No existing "
                    "source, science, Lean or authority byte changes. PR census and held PR117 unchanged.")
    v23["reviewer"] = "PROPOSED by an AI assistant for the owner's review; not reviewed, not approved"
    files[V23] = (json.dumps(v23, indent=2, sort_keys=True) + "\n").encode()
    # (2) the compiled-in constants of the gate
    g = show(src, head, GATE).decode("utf-8")
    g = replace_once(g, f'MANIFEST = "{V22}"', f'MANIFEST = "{V23}"')
    g = replace_once(g, f"MANIFEST_SHA256 = '{V22_SHA256}'", f"MANIFEST_SHA256 = '{sha(files[V23])}'")
    g = replace_once(g, '"pcs-source-reconciliation-v21", "pcs-source-reconciliation-v22"}:\n        raise ValueError("unsupported reconciliation")',
                     '"pcs-source-reconciliation-v21", "pcs-source-reconciliation-v22", "pcs-source-reconciliation-v23"}:\n        raise ValueError("unsupported reconciliation")')
    g = replace_once(g, 'in {"pcs-source-reconciliation-v21", "pcs-source-reconciliation-v22"} else 70',
                     'in {"pcs-source-reconciliation-v21", "pcs-source-reconciliation-v22", "pcs-source-reconciliation-v23"} else 70')
    g = replace_once(g, 'if manifest["format"] != "pcs-source-reconciliation-v22":\n        raise ValueError("current combined admission requires explicit V22 format")',
                     'if manifest["format"] != "pcs-source-reconciliation-v23":\n        raise ValueError("current combined admission requires explicit V23 format")')
    g = replace_once(g, 'relations_scope="V22_LINEAR_INTEGRATION_WITH_IMMUTABLE_V21_AND_V20_PREDECESSORS"',
                     'relations_scope="V23_ADDITIVE_ADMISSION_WITH_IMMUTABLE_V22_V21_AND_V20_PREDECESSORS"')
    files[GATE] = g.encode("utf-8")
    # (3) the protected test file pins "the current manifest is V22": that test now reads V22 by path; one test about V23 is added
    t = show(src, head, GATE_TEST).decode("utf-8")
    t = replace_once(t, "    current=gate._json((gate.ROOT/gate.MANIFEST).read_bytes())\n    assert current['format']=='pcs-source-reconciliation-v22'",
                     f"    current=gate._json((gate.ROOT/'{V22}').read_bytes())\n    assert current['format']=='pcs-source-reconciliation-v22'")
    t = t.rstrip("\n") + "\n" + V23_TEST.format(v22=V22, v22_sha=sha(v22_raw), v22_commit=V22_COMMIT, retained=RETAINED,
                                                roots=ADDED_ROOTS, files=ADDED_FILES)
    files[GATE_TEST] = t.encode("utf-8")
    return files


def write(root: Path, files: dict) -> None:
    for name, raw in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(raw)


def differences(proposal: dict, dry: dict) -> dict:
    """Show that the dry run tested the proposal: only the tag name and the digests that follow from it differ."""
    out = {}
    out[RETAINED] = dry[RETAINED].replace(DRY_TAG.encode(), PROPOSED_TAG.encode()) == proposal[RETAINED]
    a, b = json.loads(proposal[V23]), json.loads(dry[V23])
    a["snapshot"] = {k: v for k, v in a["snapshot"].items() if k != RETAINED}
    b["snapshot"] = {k: v for k, v in b["snapshot"].items() if k != RETAINED}
    out[V23] = a == b
    out[GATE] = (dry[GATE].replace(sha(dry[V23]).encode(), sha(proposal[V23]).encode()) == proposal[GATE])
    out[GATE_TEST] = dry[GATE_TEST] == proposal[GATE_TEST]
    return {"only_the_tag_name_and_its_consequent_digests_differ": all(out.values()), "per_file": out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--pytest-python", default=sys.executable,
                    help="a Python with pytest installed, for research/integration_v2/test_reconcile.py in the throw-away worktree")
    ap.add_argument("--emit", help="also write the proposed control files (V23 included) under this directory, outside the tree")
    ap.add_argument("--history", choices=("clean", "development"), default="clean",
                    help="retained commit design: clean (H1-b, proposed) or development (H1-a, the original design)")
    args = ap.parse_args(argv)
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    if git(ROOT, "status", "--porcelain"):
        raise SystemExit("commit your work first: the successor is bound to one commit")
    head = git(ROOT, "rev-parse", "HEAD")
    work = Path(tempfile.mkdtemp(prefix="pcs-admission-dry-run-"))
    report: dict = {"what": "DRY RUN in a throw-away worktree. No protected file in the branch was changed. Nothing was pushed. "
                            "No tag with a real name was created. Not an approval.",
                    "generated_from_commit": head, "valid_only_for_that_commit": True}
    # the evidence committed in this tree describes an earlier commit (it cannot describe the commit that contains it):
    # check that everything after that commit is evidence only, so the numbers below are the ones for this commit
    committed = subprocess.run(["git", "show", f"{head}:docs/integration/claimcheck/dry-run.json"], cwd=ROOT, capture_output=True)
    if committed.returncode == 0:
        described = json.loads(committed.stdout).get("generated_from_commit")
        since = sorted(set(git(ROOT, "diff", "--name-only", described, head).splitlines()) - {""}) if described else None
        report["evidence_committed_in_this_tree"] = {"describes_commit": described, "files_changed_since_then": since,
                                                     "only_evidence_files_changed": since is not None and set(since) <= EVIDENCE}
    try:
        git(ROOT, "worktree", "add", "--detach", str(work / "main"), V22_COMMIT)
        report["gate_on_the_protected_v22_commit"] = gate(work / "main", "--require-committed")
        git(ROOT, "worktree", "remove", "--force", str(work / "main"))
        git(ROOT, "worktree", "add", "--detach", str(work / "wt"), head)
        wt = work / "wt"
        v22_raw = (wt / V22).read_bytes()
        if sha(v22_raw) != V22_SHA256 or show(wt, V22_COMMIT, V22) != v22_raw:
            raise SystemExit("V22 in this commit differs from V22 at the protected commit that introduced it")
        v22 = json.loads(v22_raw)
        tracked = set(git(wt, "ls-files", "-z").split("\0")) - {""}
        controls22 = set(v22["control_paths"])
        # ---- census: the source commit may only ADD files ----------------------------------------------
        # the gate already binds one reviewed test repair (same file, new bytes); use its own rule
        sys.path.insert(0, str(wt))
        from research.integration_v2.reconcile import _current_expected
        changed = [n for n, ident in v22["snapshot"].items() if n not in tracked or identity(wt, n) != _current_expected(n, ident)]
        added_names = sorted(tracked - set(v22["snapshot"]) - controls22)
        outside = [n for n in added_names if not (n.startswith(ADDED_ROOTS) or n in ADDED_FILES)]
        added = {n: identity(wt, n) for n in added_names}
        report["existing_files_changed_or_removed"] = changed
        report["files_added"] = len(added_names)
        report["added_files_outside_the_admitted_roots"] = outside
        census = {"note": "Every file this branch adds to the tree pinned by RECONCILIATION_V22, with its identity at the commit above. "
                          "No existing file is changed or removed.",
                  "generated_from_commit": head, "existing_files_changed_or_removed": changed,
                  "by_directory": {}, "files": added}
        for n in added_names:
            key = "/".join(n.split("/")[:3]) if n.startswith("research/") else n.split("/")[0] + "/" + (n.split("/")[1] if "/" in n else "")
            census["by_directory"][key] = census["by_directory"].get(key, 0) + 1
        # ---- (5) the retained source commit: depends only on the source commit -------------------------
        retained = retained_commit(wt, head, args.history)
        intake = retained["commit"]
        how = ("git commit-tree <tree> -p <source commit> -p <previous intake>" if args.history == "development" else
               "git commit-tree <tree> -p <protected main> (the snapshot), then git commit-tree <tree> -p <snapshot> -p <previous intake>")
        report["retained_history_design"] = {"development": "H1-a (original): first parent is the source commit",
                                             "clean": "H1-b (proposed): first parent is a snapshot on protected main"}[args.history]
        report["proposed_retained_source_commit"] = {**retained, "proposed_tag": PROPOSED_TAG,
                                                     "reproducible_with": how + ", with the fixed identity, date and messages in this script",
                                                     "tag_created": False}
        report["retained_history_review"] = history_review(wt, head, retained)
        # ---- the proposal (real tag name; no ref) and the dry run (placeholder tag name) ---------------
        proposal = build(wt, head, intake, PROPOSED_TAG, v22, v22_raw, added)
        dry = build(wt, head, intake, DRY_TAG, v22, v22_raw, added)
        report["proposal"] = {"control_commit_files": {n: {"sha256": sha(b), "bytes": len(b)} for n, b in sorted(proposal.items())},
                              "successor_manifest": {"path": V23, "sha256": sha(proposal[V23]), "snapshot_entries": len(json.loads(proposal[V23])["snapshot"])},
                              "not_committed": "generate it again at the commit to be admitted; it pins every tracked file"}
        report["dry_run_tested_the_proposal"] = differences(proposal, dry)
        write(wt, dry)
        git(wt, "add", "-A")
        git(wt, "commit", "-q", "-m", "DRY RUN: V23 successor control commit (never pushed)", env=FIXED)
        control_commit = git(wt, "rev-parse", "HEAD")
        git(ROOT, "tag", "-f", "-a", DRY_TAG, intake, "-m", "dry run, local only, deleted at the end", env=FIXED)
        # ---- positive: both gates and both protected test files, unmodified, on the control commit -----
        report["gate_with_successor"] = gate(wt, "--require-committed")
        report["retained_source_gate_with_successor"] = retained_gate(wt)
        report["gate_tests_on_the_successor"] = suite([args.pytest_python, "-m", "pytest", "-q", "-p", "no:cacheprovider", GATE_TEST], wt)
        # includes a squash of the whole tree onto the protected baseline, checked by both gates
        report["retained_source_gate_tests_on_the_successor"] = suite([sys.executable, "scripts/test_reconciled_prs.py"], wt)
        # ---- negative controls: each alteration on top of the control commit must be rejected -----------
        neg = {}

        def reset():
            git(wt, "reset", "-q", "--hard", control_commit)
            git(wt, "clean", "-qfdx")

        (wt / "research/claimcheck_v1_1/UNREVIEWED_EXTRA_FILE.txt").write_text("x")
        git(wt, "add", "-A")
        neg["an_unlisted_file_is_added"] = gate(wt)
        reset()
        target = wt / "research/claimcheck_v1/formal/ClaimCheck.lean"
        target.write_bytes(target.read_bytes() + b"\n-- edited\n")
        neg["an_admitted_file_is_edited"] = gate(wt)
        reset()
        (wt / V23).write_bytes(dry[V23].replace(b"not reviewed, not approved", b"reviewed and approved"))
        neg["the_successor_manifest_is_edited"] = gate(wt)
        reset()
        (wt / V22).write_bytes(v22_raw.replace(b'"format": "pcs-source-reconciliation-v22"', b'"format": "pcs-source-reconciliation-v22" '))
        neg["the_predecessor_manifest_is_edited"] = gate(wt)
        reset()
        frozen = wt / "research/claimcheck_v1/benchmark/results/heldout/summary.json"
        frozen.write_bytes(frozen.read_bytes().replace(b"1", b"2", 1))
        neg["a_frozen_benchmark_result_is_edited"] = gate(wt)
        reset()
        old = wt / "pcs" / "__init__.py"
        old.write_bytes(old.read_bytes() + b"\n# edited\n")
        neg["an_existing_production_file_is_edited"] = gate(wt)
        reset()
        ctl = wt / GATE
        ctl.write_bytes(ctl.read_bytes() + b"\n# edited after the control commit\n")
        neg["a_gate_control_file_is_edited_after_the_control_commit"] = gate(wt, "--require-committed")
        reset()
        s2 = wt / RETAINED
        s2.write_bytes(s2.read_bytes().replace(intake.encode(), OLD_INTAKE.encode()))
        git(wt, "commit", "-qam", "retarget the retained source without review", env=FIXED)
        neg["the_retained_source_entry_is_retargeted_and_committed"] = gate(wt, "--require-committed")
        reset()
        git(ROOT, "tag", "-f", "-a", DRY_TAG, head, "-m", "dry run, wrong target", env=FIXED)
        neg["the_tag_points_elsewhere"] = retained_gate(wt)
        other = retained_commit(wt, head, "development" if args.history == "clean" else "clean")["commit"]
        git(ROOT, "tag", "-f", "-a", DRY_TAG, other, "-m", "dry run, same tree, other design", env=FIXED)
        neg["the_tag_points_to_the_other_design_with_the_same_tree"] = retained_gate(wt)
        subprocess.run(["git", "tag", "-d", DRY_TAG], cwd=ROOT, capture_output=True)
        neg["the_tag_is_deleted"] = retained_gate(wt)
        report["negative_controls"] = {k: {"rejected": not v["passed"], "error": v["error"]} for k, v in neg.items()}
        # ---- what the owner would review ----------------------------------------------------------------
        reset()
        git(wt, "checkout", "-q", "--detach", head)
        write(wt, {n: proposal[n] for n in EDITED})
        patch = git(wt, "diff", "--", *EDITED)
        (out / "proposed-control-changes.patch").write_text(patch + "\n", encoding="utf-8")
        report["patch"] = {"file": "proposed-control-changes.patch", "files": list(EDITED),
                           "not_in_the_patch": f"{V23} (4.7 MB, regenerated by this script; its digest is above)"}
        if args.emit:
            write(Path(args.emit), proposal)
            report["emitted_to"] = "a directory outside the tree (--emit)"
        (out / "ADMISSION_CENSUS.json").write_text(json.dumps(census, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        hr = report["retained_history_review"]
        history_ok = (hr["tree_equals_source_tree"] and hr["no_file_differs_from_source"]
                      and hr["registry_main_original_pr_heads_and_previous_intake_are_ancestors"]
                      and (args.history == "development" or (not hr["source_commit_is_an_ancestor"] and not hr["output_commits_reachable"]
                                                             and not hr["withheld_blobs_reachable"]
                                                             and hr["commits_beyond_protected_history"] == 2
                                                             and hr["snapshot_changes_exactly_what_the_source_branch_changes"])))
        report["retained_history_as_designed"] = history_ok
        report["all_as_expected"] = (history_ok and not changed and not outside and report["gate_on_the_protected_v22_commit"]["passed"]
                                     and report["dry_run_tested_the_proposal"]["only_the_tag_name_and_its_consequent_digests_differ"]
                                     and report["gate_with_successor"]["passed"] and report["gate_with_successor"]["prs_checked"] == 72
                                     and report["retained_source_gate_with_successor"]["passed"]
                                     and report["gate_tests_on_the_successor"]["exit"] == 0
                                     and report["retained_source_gate_tests_on_the_successor"]["exit"] == 0
                                     and all(v["rejected"] for v in report["negative_controls"].values()))
    finally:
        subprocess.run(["git", "tag", "-d", DRY_TAG], cwd=ROOT, capture_output=True)
        for name in ("wt", "main"):
            subprocess.run(["git", "worktree", "remove", "--force", str(work / name)], cwd=ROOT, capture_output=True)
        shutil.rmtree(work, ignore_errors=True)
        subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True)
    (out / "dry-run.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("what", "proposal")}, indent=1))
    return 0 if report.get("all_as_expected") else 1


if __name__ == "__main__":
    raise SystemExit(main())
