"""What withholding the responses changes offline (L2, L3).  Changes nothing in the branch.

    python -m research.claimcheck_v1_1.governance.withholding_effect --out docs/integration/claimcheck/withholding [--lean]

In two throw-away worktrees of HEAD, one unchanged and one with the governed withholding applied by
the tool itself (`withhold_model_outputs --apply`, decision marked as a simulation), it runs:

* the frozen v1 freeze check;
* the v1 and the v1.1 offline test suites;
* the post-run analysis of the frozen held-out run (`claimcheck_v1.tools.analyze`);
* the development evaluation (`dev/evaluate.py`), against the committed `dev_arms.json`;
* the draft-3 demonstration (`prospective/score.py demo`), against the committed file;
* with `--lean`, the independent and the checked replay of one committed bundle.

For each step it reports the exit status with and without the stubs, and which outputs differ.  That
is the effect on offline reproducibility the owner asked to have recorded.  Nothing is committed and
the worktrees are removed.  Not an owner decision.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SIMULATED = "SIMULATION in a throw-away worktree (not an owner decision)"
BUNDLE = "research/claimcheck_v1/benchmark/results/bundles/08_pmc6238128"


def run(cwd: Path, *cmd: str) -> dict:
    proc = subprocess.run([sys.executable, *cmd], cwd=cwd, capture_output=True, text=True)
    tail = (proc.stdout + "\n" + proc.stderr).strip().splitlines()
    return {"exit": proc.returncode, "last_line": tail[-1][:240] if tail else ""}


def diff(a, b, path: str = "", out: list | None = None, limit: int = 40, recorded_only: bool = False) -> list:
    """Paths at which JSON value `b` differs from `a` (at most `limit`).  With `recorded_only`, keys present only in `b`
    are ignored: the question is then whether every value recorded in `a` is reproduced in `b`."""
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k == "seconds":
                continue
            if k not in b:
                out.append(f"{path}/{k}: missing from the new output")
            elif k not in a:
                if not recorded_only:
                    out.append(f"{path}/{k}: only in the new output")
            else:
                diff(a[k], b[k], f"{path}/{k}", out, limit, recorded_only)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f"{path}[{i}]", out, limit, recorded_only)
    elif a != b:
        out.append(f"{path}: {json.dumps(a)[:80]} -> {json.dumps(b)[:80]}")
    return out


def steps(wt: Path, tmp: Path, lean: bool) -> dict:
    tmp.mkdir(parents=True, exist_ok=True)
    checker = (wt / "research/claimcheck_v1/formal/ClaimCheck.lean.sha256").read_text().split()[0]
    r = {"freeze_check": run(wt, "-m", "research.claimcheck_v1.benchmark.freeze", "check"),
         "v1_offline_tests": run(wt, "-m", "unittest", "discover", "-s", "research/claimcheck_v1/tests"),
         "v1_1_offline_tests": run(wt, "-m", "unittest", "discover", "-s", "research/claimcheck_v1_1/tests"),
         "heldout_analysis": run(wt, "-m", "research.claimcheck_v1.tools.analyze", "--results",
                                 "research/claimcheck_v1/benchmark/results/heldout", "--out", str(tmp / "analysis.json")),
         "development_evaluation": run(wt, "-m", "research.claimcheck_v1_1.dev.evaluate", "--out", str(tmp)),
         "demonstration": run(wt, "-m", "research.claimcheck_v1_1.prospective.score", "demo", "--out", str(tmp / "demo.json"))}
    if lean:
        r["independent_replay_of_one_bundle"] = run(wt, "research/claimcheck_v1/replay_independent.py", BUNDLE, "--checker-sha256", checker)
        r["checked_replay_of_one_bundle"] = run(wt, "research/claimcheck_v1_1/replay_v1_bundle_checked.py", BUNDLE, "--checker-sha256", checker)
    return r


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--lean", action="store_true", help="also replay one committed bundle with the real kernel (needs lean on PATH)")
    args = ap.parse_args(argv)
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    work = Path(tempfile.mkdtemp(prefix="pcs-withholding-effect-"))
    report: dict = {"what": "Effect of withholding on offline reproducibility, measured in throw-away worktrees. Nothing in the branch "
                            "changed and nothing was committed. Not an owner decision.", "head": head}
    try:
        for name in ("baseline", "stubbed"):
            subprocess.run(["git", "worktree", "add", "-q", "--detach", str(work / name), head], cwd=ROOT, check=True)
        applied = run(work / "stubbed", "-m", "research.claimcheck_v1_1.governance.withhold_model_outputs", "--apply", "--decision", SIMULATED)
        changed = subprocess.check_output(["git", "status", "--porcelain"], cwd=work / "stubbed", text=True).splitlines()
        report["stubs_applied"] = {"exit": applied["exit"], "files_changed": len(changed),
                                   "outside_model_responses": [c for c in changed if "/model_responses/" not in c]}
        base = steps(work / "baseline", work / "out-baseline", args.lean)
        stub = steps(work / "stubbed", work / "out-stubbed", args.lean)
        report["steps"] = {k: {"exit_baseline": base[k]["exit"], "exit_stubbed": stub[k]["exit"],
                               "last_line_stubbed": stub[k]["last_line"]} for k in base}
        committed_arms = load(ROOT / "research/claimcheck_v1_1/dev/results/dev_arms.json")
        committed_demo = load(ROOT / "research/claimcheck_v1_1/prospective/DEMONSTRATION_ON_DEVELOPMENT_DATA.json")
        committed_analysis = load(ROOT / "research/claimcheck_v1/benchmark/results/heldout/analysis.json")
        comparisons = {
            "heldout_analysis_baseline_vs_committed": diff(committed_analysis, load(work / "out-baseline/analysis.json"), recorded_only=True),
            "heldout_analysis_stubbed_vs_baseline": diff(load(work / "out-baseline/analysis.json"), load(work / "out-stubbed/analysis.json")),
            "dev_arms_baseline_vs_committed": diff(committed_arms, load(work / "out-baseline/dev_arms.json"), recorded_only=True),
            "dev_arms_stubbed_vs_committed": diff(committed_arms, load(work / "out-stubbed/dev_arms.json"), recorded_only=True),
            "demonstration_baseline_vs_committed": diff(committed_demo, load(work / "out-baseline/demo.json"), recorded_only=True),
            "demonstration_stubbed_vs_committed": diff(committed_demo, load(work / "out-stubbed/demo.json"), recorded_only=True),
        }
        kept = out / "outputs"                                     # derived counts only; no model text
        for side in ("baseline", "stubbed"):
            (kept / side).mkdir(parents=True, exist_ok=True)
            for name in ("analysis.json", "dev_arms.json", "demo.json"):
                if (work / f"out-{side}" / name).exists():
                    shutil.copy(work / f"out-{side}" / name, kept / side / name)
        report["output_differences"] = {k: {"count_shown": len(v), "first": v[:12]} for k, v in comparisons.items()}
        report["summary"] = {
            "every_check_and_suite_passes_with_the_stubs": all(stub[k]["exit"] == 0 for k in ("freeze_check", "v1_offline_tests", "v1_1_offline_tests")),
            "tools_that_read_the_cache_still_run": all(stub[k]["exit"] == 0 for k in ("heldout_analysis", "development_evaluation", "demonstration")),
            "baseline_reproduces_every_recorded_value": not comparisons["dev_arms_baseline_vs_committed"]
            and not comparisons["demonstration_baseline_vs_committed"] and not comparisons["heldout_analysis_baseline_vs_committed"],
            "results_that_change_without_the_originals": [k for k in ("heldout_analysis_stubbed_vs_baseline", "dev_arms_stubbed_vs_committed",
                                                                      "demonstration_stubbed_vs_committed") if comparisons[k]],
        }
    finally:
        for name in ("baseline", "stubbed"):
            subprocess.run(["git", "worktree", "remove", "--force", str(work / name)], cwd=ROOT, capture_output=True)
        shutil.rmtree(work, ignore_errors=True)
        subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True)
    (out / "withholding-effect.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report.get("summary"), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
