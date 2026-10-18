"""Branch non-overlap auditor (read-only git).

Given known sibling branch names, runs
``git diff --name-only origin/main...<branch>`` for each and reports pairwise
changed-file overlaps. This package never modifies those branches.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


DiffRunner = Callable[[str, Path], list[str]]


@dataclass(frozen=True)
class PairOverlap:
    branch_a: str
    branch_b: str
    overlap: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "branch_a": self.branch_a,
            "branch_b": self.branch_b,
            "overlap_count": len(self.overlap),
            "overlap": list(self.overlap),
        }


@dataclass(frozen=True)
class NonoverlapReport:
    format: str
    base: str
    repo: str
    branches: tuple[str, ...]
    changed_files: Mapping[str, tuple[str, ...]]
    missing_branches: tuple[str, ...]
    pair_overlaps: tuple[PairOverlap, ...]
    errors: Mapping[str, str]

    @property
    def has_overlaps(self) -> bool:
        return any(p.overlap for p in self.pair_overlaps)

    def to_dict(self) -> dict:
        return {
            "format": self.format,
            "base": self.base,
            "repo": self.repo,
            "branches": list(self.branches),
            "missing_branches": list(self.missing_branches),
            "changed_file_counts": {b: len(files) for b, files in self.changed_files.items()},
            "changed_files": {b: list(files) for b, files in self.changed_files.items()},
            "pair_overlaps": [p.to_dict() for p in self.pair_overlaps],
            "has_overlaps": self.has_overlaps,
            "errors": dict(self.errors),
        }


def default_diff_runner(branch: str, repo: Path, *, base: str = "origin/main") -> list[str]:
    """Return changed paths for ``origin/main...<branch>`` (read-only)."""
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{branch}"],
        cwd=str(repo),
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            (proc.stderr or proc.stdout or f"git diff failed for {branch}").strip()
        )
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return lines


def branch_exists(branch: str, repo: Path) -> bool:
    """Return True if ``branch`` resolves as a local or remote ref."""
    for ref in (branch, f"origin/{branch}", f"refs/heads/{branch}", f"refs/remotes/origin/{branch}"):
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref],
            cwd=str(repo),
            check=False,
            capture_output=True,
        )
        if proc.returncode == 0:
            return True
    return False


def audit_branch_nonoverlap(
    branches: Sequence[str],
    *,
    repo: Path | str,
    base: str = "origin/main",
    diff_runner: DiffRunner | None = None,
    existence_check: Callable[[str, Path], bool] | None = None,
) -> NonoverlapReport:
    """Compute pairwise changed-file overlaps among ``branches``.

    When a branch is missing, it is recorded under ``missing_branches`` and
    skipped (no invented file lists). ``diff_runner`` may be injected for tests.
    """
    repo_path = Path(repo).resolve()
    runner = diff_runner or (lambda branch, repo: default_diff_runner(branch, repo, base=base))
    exists = existence_check or branch_exists

    changed: dict[str, tuple[str, ...]] = {}
    missing: list[str] = []
    errors: dict[str, str] = {}

    for branch in branches:
        if not exists(branch, repo_path):
            missing.append(branch)
            continue
        try:
            files = tuple(sorted(set(runner(branch, repo_path))))
            changed[branch] = files
        except Exception as exc:  # noqa: BLE001 — surface git failures in report
            errors[branch] = str(exc)
            missing.append(branch)

    ordered = tuple(branches)
    pairs: list[PairOverlap] = []
    present = [b for b in ordered if b in changed]
    for i, a in enumerate(present):
        set_a = set(changed[a])
        for b in present[i + 1 :]:
            overlap = tuple(sorted(set_a & set(changed[b])))
            pairs.append(PairOverlap(branch_a=a, branch_b=b, overlap=overlap))

    return NonoverlapReport(
        format="pcs-independent-branch-nonoverlap-audit-v1",
        base=base,
        repo=str(repo_path),
        branches=ordered,
        changed_files=changed,
        missing_branches=tuple(missing),
        pair_overlaps=tuple(pairs),
        errors=errors,
    )


def write_nonoverlap_report(report: NonoverlapReport, out_path: Path | str) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    import argparse

    from .paths import REPO_ROOT, RESULTS, SIBLING_BRANCHES

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--branch",
        action="append",
        dest="branches",
        help="Branch to audit (repeatable). Defaults to known sibling set.",
    )
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument(
        "--out",
        type=Path,
        default=RESULTS / "branch_nonoverlap_report.json",
    )
    parser.add_argument(
        "--fail-on-overlap",
        action="store_true",
        help="Exit non-zero when any pairwise overlap is non-empty",
    )
    args = parser.parse_args(argv)

    branches = tuple(args.branches) if args.branches else SIBLING_BRANCHES
    report = audit_branch_nonoverlap(branches, repo=args.repo, base=args.base)
    write_nonoverlap_report(report, args.out)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    if args.fail_on_overlap and report.has_overlaps:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
