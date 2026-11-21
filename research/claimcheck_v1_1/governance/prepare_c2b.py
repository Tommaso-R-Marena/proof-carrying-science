"""C2b, a proposal (nothing is applied): make the core retained-source gate part of the required source-policy path.

    python -m research.claimcheck_v1_1.governance.prepare_c2b --out DIR [--pytest-python PY]

**Why.** On the core repository, `scripts/check_reconciled_prs.py --core` runs only in the path-filtered,
non-required workflow `model-assurance-studio-research.yml`. It checks:

* the retained-source lineage: the tag points at the commit the gate pins, and the original PR heads
  are ancestors;
* the exact non-control bytes.

On every other pull request nothing runs it. The required path is `source-policy`, which runs
`python -m research.integration_v2.reconcile --require-committed` and feeds the required
`verified-public-integration`.

**The smallest change.** `reconcile.py --require-committed` also runs the retained-source gate:

* in a separate process in Python's isolated mode (`-I`), so that no module the pull request adds (a
  `json.py` in `scripts/`, say) can shadow the standard library it imports; and with `PYTHONOPTIMIZE`
  removed, so `python -O` cannot strip its assertions;
* failing the source contract if the gate fails.

Two control files change: `research/integration_v2/reconcile.py` (two imports, one function, three
lines in `check`) and `research/integration_v2/test_reconcile.py` (one test). No workflow, manifest,
pinned file or ruleset changes. Both files are control paths of both gates, so this is its own control
commit, after C1. Every workflow that runs `reconcile --require-committed` checks out full history
with tags (`fetch-depth: 0`).

**The dry run** happens in a throw-away worktree at HEAD, with a local placeholder tag, both deleted
at the end:

* C1's dry-run control commit is built with the same function as `prepare_core_admission`, and C2b
  is applied on top as a second commit;
* **positive:** at C1+C2b, the gate passes and reports the retained source, and both protected
  suites pass;
* **no false failure:** the `source-policy` steps that run before the gate in CI leave no untracked
  file;
* **negative controls**, each run at C1 alone (where the manifest gate passes: the gap) and at
  C1+C2b (which must fail):
  * the retained tag is deleted;
  * the tag points at another commit;
  * an untracked file is present.

Writes `DIR/c2b-dry-run.json`, and `DIR/proposed-c2b.patch` (against C1's two files). Not an approval.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from . import prepare_core_admission as P

C2B_FUNCTION = '''# C2b: the retained-source gate (lineage, tag and exact non-control bytes: scripts/check_reconciled_prs.py,
# core mode) runs in the required source-policy path.  A separate process in Python's isolated mode (-I: neither
# the script's directory nor PYTHON* variables are used, so a module the pull request adds cannot shadow the
# standard library it imports), and without PYTHONOPTIMIZE, so that its assertions cannot be optimised away.
RETAINED_SOURCE_GATE = "scripts/check_reconciled_prs.py"


def _retained_source(root):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONOPTIMIZE"}
    proc = subprocess.run([sys.executable, "-I", RETAINED_SOURCE_GATE, "--core", str(root)], cwd=root,
                          capture_output=True, text=True, env=env)
    try:
        result = json.loads(proc.stdout)
    except ValueError:
        result = {}
    if proc.returncode != 0 or result.get("passed") is not True:
        detail = ((proc.stderr or proc.stdout).strip().splitlines() or ["no output"])[-1][:300]
        raise ValueError("retained-source gate failed: " + detail)
    entry = result["checked"][0]
    return {"passed": True, "qualified_source_commit": entry["qualified_source_commit"], "retention_tag": entry["retention_tag"]}


'''

C2B_TEST = '''

def test_require_committed_runs_the_retained_source_gate(monkeypatch):
    """C2b: the retained-source gate runs in a separate process without PYTHONOPTIMIZE; its failure fails the contract."""
    calls = []

    class Done:
        def __init__(self, code, out):
            self.returncode, self.stdout, self.stderr = code, out, "AssertionError: Retained source tag differs"

    def failing(cmd, **kw):
        calls.append((cmd, kw.get("env", {})))
        return Done(1, "")
    monkeypatch.setenv("PYTHONOPTIMIZE", "1")
    monkeypatch.setattr(gate.subprocess, "run", failing)
    with pytest.raises(ValueError, match="retained-source gate failed: AssertionError: Retained source tag differs"):
        gate._retained_source(gate.ROOT)
    cmd, env = calls[0]
    assert cmd[1:] == ["-I", gate.RETAINED_SOURCE_GATE, "--core", str(gate.ROOT)] and "PYTHONOPTIMIZE" not in env
    ok = json.dumps({"passed": True, "checked": [{"qualified_source_commit": "c", "retention_tag": "t"}]})
    monkeypatch.setattr(gate.subprocess, "run", lambda cmd, **kw: Done(0, ok))
    assert gate._retained_source(gate.ROOT) == {"passed": True, "qualified_source_commit": "c", "retention_tag": "t"}
    monkeypatch.setattr(gate.subprocess, "run", lambda cmd, **kw: Done(0, json.dumps({"passed": False})))
    with pytest.raises(ValueError):
        gate._retained_source(gate.ROOT)
'''

# the source-policy steps that run before the gate in CI (pcs-public-full-verification.yml), as far as they run locally
CI_STEPS_BEFORE_THE_GATE = (["scripts/check_repository_integrity.py"], ["scripts/check_research_platform_evidence.py"],
                            ["scripts/check_mathlib_v4_evidence.py"], ["-m", "compileall", "-q", "pcs", "scripts", "tests"],
                            ["scripts/check_pr_contributions.py"])
REQUIRED_WORKFLOW = ".github/workflows/pcs-public-full-verification.yml"


def required_path_static_check(cwd: Path) -> dict:
    """The workflow that feeds the required check, read as text (unchanged by C2b): the gate cannot be skipped silently."""
    text = (cwd / REQUIRED_WORKFLOW).read_text(encoding="utf-8")
    on = text.split("\npermissions:", 1)[0]
    policy = text.split("\n  source-policy:\n", 1)[1].split("\n  core-full-gate:\n", 1)[0]
    aggregate = text.split("\n  verified-public-integration:\n", 1)[1]
    checks = {
        "runs_on_every_pull_request_to_main_without_a_path_filter": "pull_request:\n    branches: [main]" in on and "paths" not in on,
        "source_policy_runs_on_the_public_repository": "if: ${{ github.event.repository.private == false }}" in policy
                                                        and policy.count("if:") == 2,      # the job condition and one PR-only step
        "full_history_and_tags_are_checked_out": "fetch-depth: 0" in policy,
        "the_manifest_gate_runs_with_require_committed": ("run: python -m research.integration_v2.reconcile --require-committed" in policy
                                                           or P.G2.step() in policy),          # G2's isolated form, if chosen
        "the_aggregate_needs_source_policy": "needs: [source-policy," in aggregate and "if: ${{ always()" in aggregate,
        "the_aggregate_rejects_a_skipped_or_failed_source_policy": 'test "$SOURCE_POLICY" = success' in aggregate,
    }
    return {**checks, "passed": all(checks.values())}


def apply_c2b(gate_text: str, test_text: str) -> tuple[str, str]:
    """C2b on top of the gate and its test file (C1's versions, or main's): exact, single-occurrence edits."""
    g = gate_text
    g = P.replace_once(g, "import json\n", "import json\nimport os\n")
    g = P.replace_once(g, "import subprocess\n", "import subprocess\nimport sys\n")
    g = P.replace_once(g, "def check(*, require_committed=False, live=False):\n", C2B_FUNCTION + "def check(*, require_committed=False, live=False):\n")
    g = P.replace_once(g, "    pr117 = _pr117_resolution(ROOT)\n    if require_committed:\n",
                       "    pr117 = _pr117_resolution(ROOT)\n    retained = None\n    if require_committed:\n")
    g = P.replace_once(g, '                raise ValueError("control source must match committed HEAD")\n    if live:\n',
                       '                raise ValueError("control source must match committed HEAD")\n        retained = _retained_source(ROOT)\n    if live:\n')
    g = P.replace_once(g, "                pr117_integration=pr117,\n", "                pr117_integration=pr117, retained_source=retained,\n")
    return g, test_text.rstrip("\n") + "\n" + C2B_TEST


def gate_full(cwd: Path) -> dict:
    proc = subprocess.run([sys.executable, "-m", "research.integration_v2.reconcile", "--require-committed"], cwd=cwd, capture_output=True, text=True)
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        out = {"error": (proc.stderr or proc.stdout)[-300:]}
    return {"exit": proc.returncode, "passed": proc.returncode == 0 and out.get("source_review_complete") is True,
            "error": out.get("error"), "retained_source": out.get("retained_source"), "prs_checked": out.get("prs_checked")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--pytest-python", default=sys.executable)
    ap.add_argument("--history", choices=("clean", "development"), default="clean", help="C1's retained commit design (H1-b clean, or H1-a)")
    args = ap.parse_args(argv)
    out = P.ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    if P.git(P.ROOT, "status", "--porcelain"):
        raise SystemExit("commit your work first")
    head = P.git(P.ROOT, "rev-parse", "HEAD")
    work = Path(tempfile.mkdtemp(prefix="pcs-c2b-dry-run-"))
    wt = work / "wt"
    report: dict = {"what": "DRY RUN of proposal C2b in a throw-away worktree, on top of C1's dry-run control commit. Nothing in the branch "
                            "changed; nothing pushed; only a local placeholder tag, deleted at the end. Not an approval.",
                    "generated_from_commit": head}
    try:
        P.git(P.ROOT, "worktree", "add", "--detach", str(wt), head)
        v22_raw = (wt / P.V22).read_bytes()
        v22 = json.loads(v22_raw)
        tracked = set(P.git(wt, "ls-files", "-z").split("\0")) - {""}
        added = {n: P.identity(wt, n) for n in sorted(tracked - set(v22["snapshot"]) - set(v22["control_paths"]))}
        retained = P.retained_commit(wt, head, args.history)       # C1 as proposed: H1-b clean history unless told otherwise
        intake = retained["commit"]
        report["c1_retained_commit"] = {k: retained[k] for k in ("history", "commit", "parents")}
        c1 = P.build(wt, head, intake, P.DRY_TAG, v22, v22_raw, added)
        P.write(wt, c1)
        P.git(wt, "add", "-A")
        P.git(wt, "commit", "-q", "-m", "DRY RUN: C1 control commit (never pushed)", env=P.FIXED)
        c1_commit = P.git(wt, "rev-parse", "HEAD")
        g2, t2 = apply_c2b(c1[P.GATE].decode("utf-8"), c1[P.GATE_TEST].decode("utf-8"))
        (wt / P.GATE).write_text(g2, encoding="utf-8")
        (wt / P.GATE_TEST).write_text(t2, encoding="utf-8")
        P.git(wt, "add", "-A")
        P.git(wt, "commit", "-q", "-m", "DRY RUN: C2b control commit (never pushed)", env=P.FIXED)
        c2b_commit = P.git(wt, "rev-parse", "HEAD")
        changed = sorted(set(P.git(wt, "diff", "--name-only", c1_commit, c2b_commit).splitlines()) - {""})
        (out / "proposed-c2b.patch").write_text(P.git(wt, "diff", c1_commit, c2b_commit) + "\n", encoding="utf-8")
        report["patch"] = {"file": "proposed-c2b.patch", "applies_on_top_of": "C1's reconcile.py and test_reconcile.py", "files_changed": changed,
                           "lines_added": int(P.git(wt, "diff", "--numstat", c1_commit, c2b_commit).split()[0])
                           + int(P.git(wt, "diff", "--numstat", c1_commit, c2b_commit).split()[3])}
        P.git(P.ROOT, "tag", "-f", "-a", P.DRY_TAG, intake, "-m", "C2b dry run, local only, deleted at the end", env=P.FIXED)

        def at(commit):
            P.git(wt, "checkout", "-q", "--detach", commit)

        # ---- positive -----------------------------------------------------------------------------------
        at(c2b_commit)
        report["positive_c1_plus_c2b"] = gate_full(wt)
        report["gate_tests_with_c2b"] = P.suite([args.pytest_python, "-m", "pytest", "-q", "-p", "no:cacheprovider", P.GATE_TEST], wt)
        report["retained_source_gate_tests_with_c2b"] = P.suite([sys.executable, "scripts/test_reconciled_prs.py"], wt)
        # ---- no false failure: the CI steps before the gate leave no untracked file ----------------------
        steps = {}
        ci_env = {**__import__("os").environ, "GITHUB_REPOSITORY": "Tommaso-R-Marena/proof-carrying-science", "GITHUB_BASE_SHA": P.PROTECTED_MAIN}
        for step in CI_STEPS_BEFORE_THE_GATE:
            proc = subprocess.run([sys.executable, *step], cwd=wt, capture_output=True, text=True, env=ci_env)
            steps[" ".join(step)] = proc.returncode
        untracked = P.git(wt, "status", "--porcelain", "--untracked-files=all")
        report["ci_steps_before_the_gate"] = {"exit_codes": steps, "untracked_files_left": untracked.splitlines()[:10],
                                              "gate_after_them": gate_full(wt)}
        P.git(wt, "clean", "-qfdx")
        # ---- negative controls: C1 alone passes (the gap); C1 + C2b must fail -------------------------------
        neg = {}

        def both(name, damage, repair):
            damage()
            at(c1_commit)
            alone = gate_full(wt)
            at(c2b_commit)
            with_c2b = gate_full(wt)
            repair()
            neg[name] = {"c1_alone_passes": alone["passed"], "c1_plus_c2b_rejects": not with_c2b["passed"], "error_with_c2b": with_c2b["error"]}

        both("the_retained_tag_is_deleted",
             lambda: P.git(P.ROOT, "tag", "-d", P.DRY_TAG),
             lambda: P.git(P.ROOT, "tag", "-f", "-a", P.DRY_TAG, intake, "-m", "restored", env=P.FIXED))
        both("the_tag_points_at_another_commit",
             lambda: P.git(P.ROOT, "tag", "-f", "-a", P.DRY_TAG, head, "-m", "moved", env=P.FIXED),
             lambda: P.git(P.ROOT, "tag", "-f", "-a", P.DRY_TAG, intake, "-m", "restored", env=P.FIXED))
        probe = wt / "research" / "claimcheck_v1_1" / "UNTRACKED_PROBE.txt"
        both("an_untracked_file_is_present",
             lambda: probe.write_text("not committed\n", encoding="utf-8"),
             lambda: probe.unlink())
        report["negative_controls"] = neg
        report["required_path_static_check"] = required_path_static_check(wt)
        report["notes"] = {
            "annotated_tag_not_enforced": "the gate resolves refs/tags/<tag>^{commit}; a lightweight tag at the right commit also passes. "
                                          "Authority rests on the commit ID compiled into the gate, not on the tag object.",
            "order": "apply after C1 (it edits C1's versions of the two control files); no manifest or retained commit changes",
            "what_it_does_not_add": "no new restriction beyond the manifest gate's exact census, except the lineage, the tag and a clean working tree"}
        report["all_as_expected"] = (report["positive_c1_plus_c2b"]["passed"] and (report["positive_c1_plus_c2b"]["retained_source"] or {}).get("passed") is True
                                     and report["gate_tests_with_c2b"]["exit"] == 0 and report["retained_source_gate_tests_with_c2b"]["exit"] == 0
                                     and not report["ci_steps_before_the_gate"]["untracked_files_left"]
                                     and report["ci_steps_before_the_gate"]["gate_after_them"]["passed"]
                                     and all(v["c1_alone_passes"] and v["c1_plus_c2b_rejects"] for v in neg.values())
                                     and report["required_path_static_check"]["passed"]
                                     and changed == sorted([P.GATE, P.GATE_TEST]))
    finally:
        subprocess.run(["git", "tag", "-d", P.DRY_TAG], cwd=P.ROOT, capture_output=True)
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=P.ROOT, capture_output=True)
    (out / "c2b-dry-run.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("generated_from_commit", "all_as_expected", "negative_controls")}, indent=1))
    return 0 if report["all_as_expected"] else 1


if __name__ == "__main__":
    sys.exit(main())
