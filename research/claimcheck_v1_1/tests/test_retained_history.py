"""H1-b: the clean-history retained commit, built from this repository's own objects.

`git commit-tree` writes objects and no ref, so these tests change no branch or tag.  The gates
themselves are exercised by `governance/h1b_adversarial.py` (worktrees, placeholder tag).
"""
import os
import subprocess
import unittest

from research.claimcheck_v1_1.governance import prepare_core_admission as P
from research.claimcheck_v1_1.governance.retained_history import OUTPUT_COMMITS, is_ancestor, reach

ROOT = P.ROOT


def git(*args) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def parents(commit: str) -> list[str]:
    return git("rev-list", "--parents", "-n", "1", commit).split()[1:]


def history_available() -> str | None:
    """None if the objects the construction needs are present; else what is missing (a shallow clone, or no tags)."""
    for name, commit in (("protected main", P.PROTECTED_MAIN), ("previous intake", P.OLD_INTAKE)):
        if subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT, capture_output=True).returncode:
            return f"the {name} commit {commit} is not in this clone"
    if not is_ancestor(ROOT, P.PROTECTED_MAIN, "HEAD"):
        return "HEAD does not descend from protected main in this clone (shallow history?)"
    return None


class CleanHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = history_available()
        if missing:                         # fail clearly, and let the rest of the suite run (retained_commit would exit)
            raise AssertionError(f"needs full history and tags ({missing}); run: git fetch --unshallow --tags")
        cls.head = git("rev-parse", "HEAD")
        cls.clean = P.retained_commit(ROOT, cls.head, "clean")
        cls.dev = P.retained_commit(ROOT, cls.head, "development")

    def test_the_retained_commit_has_the_source_tree_and_a_snapshot_on_protected_main(self):
        c, s = self.clean["commit"], self.clean["snapshot"]["commit"]
        tree = git("rev-parse", f"{self.head}^{{tree}}")
        self.assertEqual(git("rev-parse", f"{c}^{{tree}}"), tree)
        self.assertEqual(git("rev-parse", f"{s}^{{tree}}"), tree)
        self.assertEqual(parents(c), [s, P.OLD_INTAKE])
        self.assertEqual(parents(s), [P.PROTECTED_MAIN])

    def test_no_commit_of_the_source_branch_is_reachable(self):
        c = self.clean["commit"]
        self.assertFalse(is_ancestor(ROOT, self.head, c))
        r = reach(ROOT, c, [P.PROTECTED_MAIN, P.OLD_INTAKE], {})
        self.assertEqual(r["commits_beyond_protected_history"], 2)          # the snapshot and the retained commit only
        self.assertEqual(r["output_commits_reachable"], [])

    def test_the_original_design_reaches_the_whole_branch(self):
        # Relative to HEAD: on the ClaimCheck branch HEAD descends from the three response commits; after the squash merge
        # onto main it does not.  H1-a reaches exactly what HEAD reaches; H1-b never reaches any of them.
        d = self.dev["commit"]
        self.assertEqual(parents(d), [self.head, P.OLD_INTAKE])
        self.assertTrue(is_ancestor(ROOT, self.head, d))
        r = reach(ROOT, d, [P.PROTECTED_MAIN, P.OLD_INTAKE], {})
        expected = sorted(c for c in OUTPUT_COMMITS if is_ancestor(ROOT, c, self.head))
        self.assertEqual(sorted(r["output_commits_reachable"]), expected)
        beyond_head = len(git("rev-list", self.head, "--not", P.PROTECTED_MAIN, P.OLD_INTAKE).split())
        self.assertEqual(r["commits_beyond_protected_history"], beyond_head + 1)          # HEAD's own commits, and the retained one
        self.assertEqual(reach(ROOT, self.clean["commit"], [P.PROTECTED_MAIN, P.OLD_INTAKE], {})["output_commits_reachable"], [])

    def test_both_designs_are_deterministic_and_differ(self):
        self.assertEqual(P.retained_commit(ROOT, self.head, "clean"), self.clean)
        self.assertEqual(P.retained_commit(ROOT, self.head, "development"), self.dev)
        self.assertNotEqual(self.clean["commit"], self.dev["commit"])

    def test_the_previous_intake_keeps_the_original_pull_requests(self):
        import json
        reg = json.loads(git("show", f"{self.head}:docs/reconciliation/OPEN_PRS.json"))
        core = next(r for r in reg["repositories"] if r["repository"].endswith("/proof-carrying-science"))
        for p in core["original_open_prs"]:
            self.assertTrue(is_ancestor(ROOT, p["head"], self.clean["commit"]), p["number"])
            self.assertFalse(is_ancestor(ROOT, p["head"], self.clean["snapshot"]["commit"]), p["number"])   # only through the intake
        self.assertTrue(is_ancestor(ROOT, core["protected"]["main"], self.clean["commit"]))

    def test_a_source_commit_not_based_on_protected_main_is_refused(self):
        # the fixed identity of the dry runs: a CI runner has no git identity configured
        orphan = subprocess.check_output(["git", "commit-tree", git("rev-parse", f"{self.head}^{{tree}}"), "-m", "not based on protected main"],
                                         cwd=ROOT, text=True, env={**os.environ, **P.FIXED}).strip()
        with self.assertRaises(SystemExit):
            P.retained_commit(ROOT, orphan, "clean")

    def test_an_unknown_design_is_refused(self):
        with self.assertRaises(ValueError):
            P.retained_commit(ROOT, self.head, "squashed")


if __name__ == "__main__":
    unittest.main()
