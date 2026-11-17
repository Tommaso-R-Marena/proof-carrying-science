"""Tests of the two shell steps that make `claimcheck-required` safe to require.

    python3 research/claimcheck_v1_1/governance/test_required_check.py

The steps are taken verbatim from .github/workflows/pcs-claimcheck-v1.yml (PyYAML is needed to read
them; the test says so and stops if it is missing) and run with bash:

* `changes`, on real Git merge commits shaped like GitHub's pull-request merge ref (first parent the
  base, second the head): which changed paths count as ClaimCheck changes, and that anything other
  than a two-parent merge commit fails instead of guessing;
* `claimcheck-required`, on every combination of job results it can see: it passes only when change
  detection succeeded and either nothing relevant changed or both ClaimCheck jobs succeeded.

Tests of the scripts, not of GitHub: that a job skipped by its `if:` reports success and that a
workflow skipped by a path filter leaves a required check pending is GitHub's documented behaviour,
not something this file can run.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/pcs-claimcheck-v1.yml"


def steps():
    try:
        import yaml
    except ImportError:
        raise SystemExit("PyYAML is needed to read the workflow (pip install pyyaml); nothing was tested")
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    diff = next(s for s in jobs["changes"]["steps"] if s.get("id") == "diff")["run"]
    gate = jobs["claimcheck-required"]["steps"][0]["run"]
    assert jobs["claimcheck-required"]["if"] == "always()"
    assert set(jobs["claimcheck-required"]["needs"]) == {"changes", "offline-and-kernel", "meaning-theorems"}
    for name in ("offline-and-kernel", "meaning-theorems"):
        assert jobs[name]["needs"] == "changes" and jobs[name]["if"] == "needs.changes.outputs.relevant == 'true'"
    return diff, gate


def git(repo, *args):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
    return subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True).stdout.strip()


def run_changes(script, repo, event="pull_request"):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        out.touch()
        proc = subprocess.run(["bash", "-c", script], cwd=repo, capture_output=True, text=True,
                              env={**os.environ, "EVENT": event, "GITHUB_OUTPUT": str(out), "RUNNER_TEMP": tmp})
        values = dict(line.split("=", 1) for line in out.read_text().splitlines() if "=" in line)
        return proc.returncode, values.get("relevant")


def merge_repo(tmp, change):
    """A base commit, a pull-request head that applies `change`, and their merge (first parent = base)."""
    repo = Path(tmp) / "r"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    for name in ("README.md", "research/claimcheck_v1/x.py", "research/claimcheck_v1_1/y.py", "scripts/activate_lean_428.sh",
                 ".github/workflows/pcs-claimcheck-v1.yml", "research/claimcheck_v1_10/z.py", "pcs/core.py"):
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text("base\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")

    git(repo, "checkout", "-qb", "pr")
    change(repo)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "pr", "--allow-empty")
    git(repo, "checkout", "-q", "main")
    git(repo, "commit", "-qm", "base moved on", "--allow-empty")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge", "pr")
    return repo


def main() -> int:
    diff, gate = steps()
    report = {"workflow_sha256": hashlib.sha256(WORKFLOW.read_bytes()).hexdigest(), "changes": {}, "aggregate": {}}

    def write(path, text="changed\n"):
        return lambda repo: ((repo / path).parent.mkdir(parents=True, exist_ok=True), (repo / path).write_text(text))

    cases = {
        "documentation only": (write("README.md"), "false"),
        "production code only (pcs/)": (write("pcs/core.py"), "false"),
        "a look-alike directory research/claimcheck_v1_10/": (write("research/claimcheck_v1_10/z.py"), "false"),
        "research/claimcheck_v1/": (write("research/claimcheck_v1/x.py"), "true"),
        "research/claimcheck_v1_1/": (write("research/claimcheck_v1_1/y.py"), "true"),
        "a new file under research/claimcheck_v1_1/": (write("research/claimcheck_v1_1/new/n.py"), "true"),
        "the Lean bootstrap scripts/activate_lean_428.sh": (write("scripts/activate_lean_428.sh"), "true"),
        "the workflow itself": (write(".github/workflows/pcs-claimcheck-v1.yml"), "true"),
        "a ClaimCheck file deleted": (lambda repo: (repo / "research/claimcheck_v1/x.py").unlink(), "true"),
        "a ClaimCheck file renamed out of the tree": (lambda repo: (repo / "research/claimcheck_v1_1/y.py").rename(repo / "README2.md"), "true"),
        "an empty pull request": (lambda repo: None, "false"),
    }
    for name, (change, expected) in cases.items():
        with tempfile.TemporaryDirectory() as tmp:
            repo = merge_repo(tmp, change)
            code, relevant = run_changes(diff, repo)
        report["changes"][name] = {"exit": code, "relevant": relevant, "expected": expected, "ok": code == 0 and relevant == expected}
    with tempfile.TemporaryDirectory() as tmp:
        repo = merge_repo(tmp, write("README.md"))
        git(repo, "checkout", "-q", "HEAD^1")                      # not a merge commit
        code, relevant = run_changes(diff, repo)
        report["changes"]["the checked-out commit is not a merge commit"] = {"exit": code, "relevant": relevant, "expected": "failure",
                                                                              "ok": code != 0 and relevant is None}
        code, relevant = run_changes(diff, repo, event="workflow_dispatch")
        report["changes"]["a manual run (workflow_dispatch)"] = {"exit": code, "relevant": relevant, "expected": "true",
                                                                 "ok": code == 0 and relevant == "true"}

    results = ["success", "failure", "skipped", "cancelled"]
    for changes, relevant, offline, meaning in itertools.product(results, ["true", "false", ""], results, results):
        proc = subprocess.run(["bash", "-c", gate], capture_output=True, text=True,
                              env={**os.environ, "CHANGES": changes, "RELEVANT": relevant, "OFFLINE": offline, "MEANING": meaning})
        should_pass = changes == "success" and (relevant == "false" or (relevant == "true" and offline == meaning == "success"))
        report["aggregate"][f"{changes}/{relevant or '(none)'}/{offline}/{meaning}"] = proc.returncode == 0
        assert (proc.returncode == 0) == should_pass, (changes, relevant, offline, meaning, proc.stdout, proc.stderr)
    passing = sorted(k for k, v in report["aggregate"].items() if v)
    report["aggregate"] = {"combinations": len(report["aggregate"]), "passing": passing}
    report["passed"] = all(v["ok"] for v in report["changes"].values()) and len(passing) == 1 + 16
    print(json.dumps(report, indent=1))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
