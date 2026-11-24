"""Adversarial tests of H1-b, the clean-history retained-source design.  Changes nothing protected.

    python -m research.claimcheck_v1_1.governance.h1b_adversarial --out docs/integration/claimcheck/h1b \
        [--research-head REF]

Builds, in throw-away worktrees, the C1 control commit with the H1-b retained commit and runs the two
unmodified gates on it (research/integration_v2/reconcile.py, the manifest gate; and
scripts/check_reconciled_prs.py, the retained-source gate) with a local placeholder tag, deleted at
the end.  It then runs the twelve tests the owner set (2026-11-19):

   1. the retained tree equals the reviewed source tree exactly;
   2. no file is introduced or removed;
   3. the registry's protected main, the original PR heads and the previous intake stay ancestors;
   4. the retained tag reaches none of the commits that added the model responses, and none of the
      withheld response blobs (the H1-a commit is measured too, as the positive control);
   5. a changed file fails;            6. a substituted retained commit fails;
   7. a moved or deleted tag fails;    8. an altered predecessor or broken ancestry fails;
   9. a changed protected control file fails;
  10. the successor manifest enforces the same reviewed authority as under H1-a;
  11. a squash of the pull request onto protected main passes both gates (linear history);
  12. a V24 assurance-research admission built the same way does not bring the development history
      back, and one built the H1-a way would.

If the source commit still contains the responses whose disposition is to withhold them, test 4's blob
check and test 12 run on a throw-away commit that applies the withholding stubs (reported as
simulated).  No ref other than the placeholder tag is created; nothing is pushed.  Not an approval.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import prepare_core_admission as P
from . import withhold_model_outputs as W
from .retained_history import INVENTORY, OUTPUT_COMMITS, is_ancestor, reach, withheld_blobs

SIMULATED = "SIMULATION in a throw-away worktree (not an owner decision)"


def run(cwd, *cmd, check=False) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, check=check)


def commit_all(wt: Path, message: str) -> str:
    P.git(wt, "add", "-A")
    P.git(wt, "commit", "-q", "--allow-empty", "-m", message, env=P.FIXED)
    return P.git(wt, "rev-parse", "HEAD")


def tag(target: str | None) -> None:
    run(P.ROOT, "git", "tag", "-d", P.DRY_TAG)
    if target:
        P.git(P.ROOT, "tag", "-a", P.DRY_TAG, target, "-m", "h1b adversarial tests, local only, deleted at the end", env=P.FIXED)


def gates(wt: Path) -> dict:
    return {"manifest_gate": P.gate(wt, "--require-committed"), "retained_source_gate": P.retained_gate(wt)}


def withheld_at(wt: Path, commit: str, inventory: dict) -> bool:
    """True if no response the inventory withholds is present at `commit` with its original bytes (each is a stub or absent)."""
    present = set(P.git(wt, "ls-tree", "-r", "--name-only", commit).splitlines())
    for f in inventory["files"]:
        if f["action"].startswith("withhold") and f["path"] in present and not json.loads(P.show(wt, commit, f["path"])).get("withheld"):
            return False
    return True


def with_stubs(wt: Path, base: str, label: str, inventory: dict) -> tuple[str, bool]:
    """`base` if the responses are already withheld there; else a throw-away commit on top of it with the stubs the governed
    tool would write (its own stub function, from the source commit's inventory)."""
    if withheld_at(wt, base, inventory):
        return base, False
    P.git(wt, "checkout", "-q", "--detach", base)
    for f in inventory["files"]:
        if f["action"].startswith("withhold") and (wt / f["path"]).exists():
            (wt / f["path"]).write_text(json.dumps(W.stub(f, SIMULATED), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    c = commit_all(wt, f"{label}: withholding stubs applied ({SIMULATED})")
    if not withheld_at(wt, c, inventory):
        raise SystemExit("simulated withholding did not take effect")
    return c, True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--research-head", default="tommaso-r-marena/claimcheck-assurance-research",
                    help="the assurance research branch head, for test 12")
    args = ap.parse_args(argv)
    out = P.ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    if P.git(P.ROOT, "status", "--porcelain"):
        raise SystemExit("commit your work first")
    head = P.git(P.ROOT, "rev-parse", "HEAD")
    research_head = P.git(P.ROOT, "rev-parse", args.research_head)
    work = Path(tempfile.mkdtemp(prefix="pcs-h1b-"))
    wt = work / "wt"
    T: dict = {}
    report: dict = {"what": "Adversarial tests of H1-b in throw-away worktrees. Nothing in the branch changed; nothing pushed; only a "
                            "local placeholder tag, deleted at the end. Not an approval.", "generated_from_commit": head,
                    "research_head": research_head, "tests": T}
    try:
        P.git(P.ROOT, "worktree", "add", "--detach", str(wt), head)
        inventory = json.loads(P.show(wt, head, INVENTORY))
        source, simulated = with_stubs(wt, head, "source", inventory)
        report["source_commit_tested"] = source
        report["withholding_simulated"] = simulated
        v22_raw = P.show(wt, source, P.V22)
        v22 = json.loads(v22_raw)
        P.git(wt, "checkout", "-q", "--detach", source)
        tracked = set(P.git(wt, "ls-files", "-z").split("\0")) - {""}
        added = {n: P.identity(wt, n) for n in sorted(tracked - set(v22["snapshot"]) - set(v22["control_paths"]))}
        clean = P.retained_commit(wt, source, "clean")
        dev = P.retained_commit(wt, source, "development")
        r, snap = clean["commit"], clean["snapshot"]["commit"]
        report["retained"] = {"clean": clean, "development": dev}
        files = P.build(wt, source, r, P.DRY_TAG, v22, v22_raw, added)
        files_dev = P.build(wt, source, dev["commit"], P.DRY_TAG, v22, v22_raw, added)
        P.write(wt, files)
        control = commit_all(wt, "DRY RUN: C1 control commit with the H1-b retained commit (never pushed)")
        tag(r)
        positive = gates(wt)
        report["positive"] = positive

        def reset():
            P.git(wt, "reset", "-q", "--hard", control)
            P.git(wt, "clean", "-qfdx")
            tag(r)

        def rejected(res: dict) -> bool:
            return not res["passed"]

        reg = json.loads(P.show(wt, source, "docs/reconciliation/OPEN_PRS.json"))
        core = next(x for x in reg["repositories"] if x["repository"].endswith("/proof-carrying-science"))
        required = {"registry protected main": core["protected"]["main"], "previous intake": P.OLD_INTAKE,
                    **{f"original PR {p['number']} head": p["head"] for p in core["original_open_prs"]}}
        blobs = withheld_blobs(wt, search_from=source)
        # 1 ---------------------------------------------------------------------------------------------
        T["1_retained_tree_equals_reviewed_tree"] = {
            "retained_tree": clean["tree"], "source_tree": P.git(wt, "rev-parse", f"{source}^{{tree}}"),
            "snapshot_tree": P.git(wt, "rev-parse", f"{snap}^{{tree}}"),
            "passed": clean["tree"] == P.git(wt, "rev-parse", f"{source}^{{tree}}") == P.git(wt, "rev-parse", f"{snap}^{{tree}}")
            and run(wt, "git", "diff", "--quiet", source, r).returncode == 0}
        # 2 ---------------------------------------------------------------------------------------------
        census_source = P.git(wt, "ls-tree", "-r", "--name-only", source).splitlines()
        census_retained = P.git(wt, "ls-tree", "-r", "--name-only", r).splitlines()
        against_main = P.git(wt, "diff", "--name-status", "--no-renames", P.PROTECTED_MAIN, source).splitlines()
        if P.G2.carried(wt, P.PROTECTED_MAIN, source):          # G2's reviewed successors, bound by C1's control files
            against_main = [x for x in against_main if x not in {"M\t" + p for p in P.G2.MODIFIED}]
        T["2_no_file_introduced_or_removed"] = {
            "files": len(census_retained),
            "snapshot_tree_id_equals_source_tree_id": P.git(wt, "rev-parse", f"{snap}^{{tree}}") == P.git(wt, "rev-parse", f"{source}^{{tree}}"),
            "files_added_to_protected_main": len(against_main),
            "existing_files_changed_or_removed_against_protected_main": [x for x in against_main if not x.startswith("A\t")][:10],
            "passed": census_source == census_retained and not P.git(wt, "diff", "--name-only", source, r)
            and P.git(wt, "rev-parse", f"{snap}^{{tree}}") == P.git(wt, "rev-parse", f"{source}^{{tree}}")
            and all(x.startswith("A\t") for x in against_main)}
        # 3 ---------------------------------------------------------------------------------------------
        anc = {k: is_ancestor(wt, v, r) for k, v in required.items()}
        T["3_required_ancestors_preserved"] = {"ancestors": anc, "gates_on_the_control_commit": positive,
                                               "passed": all(anc.values()) and positive["manifest_gate"]["passed"]
                                               and positive["retained_source_gate"]["passed"]}
        # 4 ---------------------------------------------------------------------------------------------
        protected = [P.PROTECTED_MAIN, P.OLD_INTAKE]
        rc, rd = reach(wt, r, protected, blobs), reach(wt, dev["commit"], protected, blobs)
        T["4_no_ancestry_to_the_model_response_commits"] = {
            "withheld_blobs_checked": len(blobs), "clean_h1b": rc, "development_h1a_positive_control": rd,
            "passed": not rc["output_commits_reachable"] and not rc["withheld_blobs_reachable"] and rc["commits_beyond_protected_history"] == 2
            and len(rd["output_commits_reachable"]) == len(OUTPUT_COMMITS) and len(rd["withheld_blobs_reachable"]) == len(blobs)}
        # 5 ---------------------------------------------------------------------------------------------
        target = wt / "research/claimcheck_v1/formal/ClaimCheck.lean"
        target.write_bytes(target.read_bytes() + b"\n-- edited\n")
        t5 = {"uncommitted": P.gate(wt)}
        commit_all(wt, "edit an admitted file")
        t5["committed"] = gates(wt)
        T["5_changed_file_fails"] = {**t5, "passed": rejected(t5["uncommitted"]) and rejected(t5["committed"]["manifest_gate"])
                                     and rejected(t5["committed"]["retained_source_gate"])}
        reset()
        # 6 ---------------------------------------------------------------------------------------------
        t6 = {}
        tag(dev["commit"])
        t6["tag_on_the_h1a_commit_same_tree"] = P.retained_gate(wt)
        forged = P.git(wt, "commit-tree", clean["tree"], "-p", snap, "-p", P.OLD_INTAKE, "-m", "forged retained commit, same tree and parents",
                       env={**P.FIXED, "GIT_AUTHOR_NAME": "someone else"})
        tag(forged)
        t6["tag_on_a_forged_commit_same_tree_and_parents"] = P.retained_gate(wt)
        reset()
        (wt / P.RETAINED).write_bytes(files[P.RETAINED].replace(r.encode(), forged.encode()))
        commit_all(wt, "retarget the retained entry to a forged commit")
        tag(forged)
        t6["retained_entry_and_tag_both_retargeted"] = gates(wt)
        T["6_substituted_retained_commit_fails"] = {
            **t6, "passed": rejected(t6["tag_on_the_h1a_commit_same_tree"]) and rejected(t6["tag_on_a_forged_commit_same_tree_and_parents"])
            and rejected(t6["retained_entry_and_tag_both_retargeted"]["manifest_gate"])}
        reset()
        # 7 ---------------------------------------------------------------------------------------------
        tag(source)
        t7 = {"tag_moved_to_the_source_commit": P.retained_gate(wt)}
        tag(snap)
        t7["tag_moved_to_the_snapshot"] = P.retained_gate(wt)
        tag(None)
        t7["tag_deleted"] = P.retained_gate(wt)
        T["7_moved_or_deleted_tag_fails"] = {**t7, "passed": all(rejected(v) for v in t7.values())}
        reset()
        # 8 ---------------------------------------------------------------------------------------------
        t8 = {}
        no_prev = P.git(wt, "commit-tree", clean["tree"], "-p", snap, "-m", "retained commit without the previous intake", env=P.FIXED)
        fake_prev = P.git(wt, "commit-tree", P.git(wt, "rev-parse", f"{P.OLD_INTAKE}^{{tree}}"), "-m", "previous intake's tree, no history",
                          env=P.FIXED)
        fake = P.git(wt, "commit-tree", clean["tree"], "-p", snap, "-p", fake_prev, "-m", "retained commit on a forged previous intake",
                     env=P.FIXED)
        for label, bad in (("previous_intake_missing", no_prev), ("previous_intake_forged_same_tree_no_history", fake)):
            (wt / P.RETAINED).write_bytes(files[P.RETAINED].replace(r.encode(), bad.encode()))
            commit_all(wt, f"pin {label}")
            tag(bad)
            t8[label] = P.retained_gate(wt)          # the manifest gate rejects too (the entry changed); this isolates the ancestry check
            reset()
        (wt / P.V22).write_bytes(v22_raw.replace(b'"format": "pcs-source-reconciliation-v22"', b'"format": "pcs-source-reconciliation-v22" '))
        commit_all(wt, "edit the predecessor manifest")
        t8["predecessor_manifest_edited"] = P.gate(wt, "--require-committed")
        T["8_altered_predecessor_or_broken_ancestry_fails"] = {**t8, "passed": all(rejected(v) for v in t8.values())}
        reset()
        # 9 --------------------------------------------------------------------------------------------
        # Two kinds of control file.  Pinned ones (V23 pins their bytes; reconcile.py pins V23's digest) must be rejected when
        # changed and committed.  The manifest gate's own sources are, by its documented design, "trusted checked-in
        # configuration" (reconcile.py, _snapshot): a committed edit to them is not detectable by the gate it changes, nor by the
        # retained-source gate, which lists them as controls.  The test records which kind behaves how, and whether the
        # proposed gate-definition guard (G1) would flag each change.
        def edit_commit(name: str) -> str:
            f = wt / name
            f.write_bytes(f.read_bytes() + (b"\n" if name.endswith(".json") else b"\n# edited after the control commit\n"))
            return commit_all(wt, f"edit {name}")

        def g1_flags(commit: str) -> bool:      # the guard's own rule, from g1/gate-definition-guard.core.yml
            return bool(P.git(wt, "diff", "--name-only", f"{P.PROTECTED_MAIN}...{commit}", "--", ".github/workflows", P.RETAINED,
                              "scripts/test_reconciled_prs.py", "docs/reconciliation/OPEN_PRS.json", "research/integration_v2",
                              "docs/integration/2026-11-05", "docs/integration/2026-11-14"))
        pinned, trusted = {}, {}
        for name in (P.RETAINED, "scripts/test_reconciled_prs.py", P.V23, P.V22, ".github/workflows/pcs-public-full-verification.yml"):
            edit_commit(name)
            pinned[name] = {"manifest_gate": P.gate(wt, "--require-committed")}
            reset()
        for name in (P.GATE, P.GATE_TEST, "research/integration_v2/boundary.py", "research/integration_v2/__init__.py"):
            c = edit_commit(name)
            trusted[name] = {**gates(wt), "g1_guard_would_fail": g1_flags(c)}
            reset()
        f = wt / P.GATE
        f.write_bytes(f.read_bytes() + b"\n# uncommitted\n")
        uncommitted = P.gate(wt, "--require-committed")
        reset()
        pinned_ok = all(rejected(v["manifest_gate"]) for v in pinned.values())
        undetected = sorted(n for n, v in trusted.items() if v["manifest_gate"]["passed"] and v["retained_source_gate"]["passed"])
        T["9_changed_protected_control_file_fails"] = {
            "pinned_control_files_committed_edit": pinned, "pinned_control_files_rejected": pinned_ok,
            "gate_source_files_committed_edit": trusted,
            "gate_source_files_neither_gate_detects": undetected,
            "g1_guard_would_flag_every_gate_source_edit": all(v["g1_guard_would_fail"] for v in trusted.values()),
            "uncommitted_edit_of_the_gate_rejected": rejected(uncommitted),
            "note": "Holds for every pinned control file. It does not hold for the files listed under gate_source_files_neither_gate_detects: "
                    "the manifest gate treats its own sources as trusted configuration (reconcile.py, _snapshot), and the retained-source "
                    "gate lists the same files as controls, so a committed edit to them passes both gates. This predates H1-b and is the "
                    "same under H1-a; only review of the control commit, the pre-merge gate-definition check, or G1 catches it.",
            "passed": pinned_ok and not undetected}
        # 10 --------------------------------------------------------------------------------------------
        a, b = json.loads(files[P.V23]), json.loads(files_dev[P.V23])
        snap_diff = sorted(k for k in set(a["snapshot"]) | set(b["snapshot"]) if a["snapshot"].get(k) != b["snapshot"].get(k))
        rest_equal = {k: a[k] == b[k] for k in a if k != "snapshot"}
        gate_diff = files[P.GATE].replace(P.sha(files[P.V23]).encode(), P.sha(files_dev[P.V23]).encode()) == files_dev[P.GATE]
        retained_diff = files[P.RETAINED].replace(r.encode(), dev["commit"].encode()) == files_dev[P.RETAINED]
        T["10_successor_manifest_enforces_the_same_authority"] = {
            "snapshot_entries": len(a["snapshot"]), "entries_that_differ_between_h1a_and_h1b": snap_diff,
            "all_other_manifest_fields_equal": rest_equal, "gate_differs_only_in_the_manifest_digest": gate_diff,
            "retained_entry_differs_only_in_the_commit_id": retained_diff,
            "gate_test_identical": files[P.GATE_TEST] == files_dev[P.GATE_TEST],
            "prs_checked_on_the_control_commit": positive["manifest_gate"]["prs_checked"],
            "passed": snap_diff == [P.RETAINED] and all(rest_equal.values()) and gate_diff and retained_diff
            and files[P.GATE_TEST] == files_dev[P.GATE_TEST] and positive["manifest_gate"]["prs_checked"] == 72}
        # 11 --------------------------------------------------------------------------------------------
        squash = P.git(wt, "commit-tree", P.git(wt, "rev-parse", f"{control}^{{tree}}"), "-p", P.PROTECTED_MAIN, "-m",
                       "squash of the pull request onto protected main (dry run)", env=P.FIXED)
        P.git(wt, "checkout", "-q", "--detach", squash)
        tag(r)
        t11 = gates(wt)
        T["11_squash_onto_protected_main_passes_both_gates"] = {
            "squash_commit_parents": P.git(wt, "rev-list", "--parents", "-n", "1", squash).split()[1:], **t11,
            "retained_and_snapshot_are_not_on_main": not is_ancestor(wt, r, squash) and not is_ancestor(wt, snap, squash),
            "passed": t11["manifest_gate"]["passed"] and t11["retained_source_gate"]["passed"]
            and not is_ancestor(wt, r, squash) and not is_ancestor(wt, snap, squash)}
        # 12 --------------------------------------------------------------------------------------------
        research_stubbed, research_simulated = with_stubs(wt, research_head, "research", inventory)
        research_raw_tree_blobs = reach(wt, P.git(wt, "commit-tree", P.git(wt, "rev-parse", f"{research_head}^{{tree}}"), "-m", "tree only",
                                                  env=P.FIXED), [], blobs)["withheld_blobs_reachable"]
        tree24 = P.git(wt, "rev-parse", f"{research_stubbed}^{{tree}}")
        snap24 = P.git(wt, "commit-tree", tree24, "-p", squash, "-m", "V24 snapshot on post-C1 main (dry run)", env=P.FIXED)
        v24_clean = P.git(wt, "commit-tree", tree24, "-p", snap24, "-p", r, "-m", "V24 retained commit, clean history (dry run)", env=P.FIXED)
        v24_dev = P.git(wt, "commit-tree", tree24, "-p", research_stubbed, "-p", r, "-m", "V24 retained commit, development history (dry run)",
                        env=P.FIXED)
        prot24 = [squash, r]
        c24, d24 = reach(wt, v24_clean, prot24, blobs), reach(wt, v24_dev, prot24, blobs)
        chain = {k: is_ancestor(wt, v, v24_clean) for k, v in {**required, "C1 retained commit": r}.items()}
        T["12_v24_does_not_reintroduce_the_development_history"] = {
            "research_tree_contains_withheld_blobs_before_withholding": len(research_raw_tree_blobs),
            "research_withholding_simulated": research_simulated, "v24_clean": c24, "v24_development_positive_control": d24,
            "intake_chain_preserved_in_v24_clean": chain,
            "passed": not c24["output_commits_reachable"] and not c24["withheld_blobs_reachable"] and all(chain.values())
            and len(d24["output_commits_reachable"]) == len(OUTPUT_COMMITS) and len(d24["withheld_blobs_reachable"]) == len(blobs)}
        report["all_passed"] = all(v["passed"] for v in T.values())
    finally:
        run(P.ROOT, "git", "tag", "-d", P.DRY_TAG)
        run(P.ROOT, "git", "worktree", "remove", "--force", str(wt))
        shutil.rmtree(work, ignore_errors=True)
        run(P.ROOT, "git", "worktree", "prune")
    (out / "h1b-adversarial.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"all_passed": report.get("all_passed"), **{k: v.get("passed") for k, v in T.items()}}, indent=1))
    return 0 if report.get("all_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
