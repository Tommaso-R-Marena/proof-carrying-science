from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class BranchRecord:
    branch: str
    status: str
    ahead: int
    behind: int
    head: str
    subject: str


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode:
        raise SystemExit(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def _classify(ahead: int, behind: int) -> str:
    if ahead == 0 and behind == 0:
        return "IDENTICAL"
    if ahead == 0:
        return "BEHIND_OR_ANCESTOR"
    if behind == 0:
        return "AHEAD"
    return "DIVERGED"


def collect(base: str, remote: str) -> list[BranchRecord]:
    refs = _git(
        "for-each-ref",
        "--format=%(refname:short)",
        f"refs/remotes/{remote}",
    ).splitlines()
    records: list[BranchRecord] = []
    base_short = base.removeprefix(f"{remote}/")
    for branch in sorted(refs):
        if branch in {f"{remote}/HEAD", base, f"{remote}/{base_short}"}:
            continue
        counts = _git("rev-list", "--left-right", "--count", f"{base}...{branch}")
        behind_text, ahead_text = counts.split()
        behind = int(behind_text)
        ahead = int(ahead_text)
        records.append(
            BranchRecord(
                branch=branch,
                status=_classify(ahead, behind),
                ahead=ahead,
                behind=behind,
                head=_git("rev-parse", branch),
                subject=_git("log", "-1", "--format=%s", branch),
            )
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report remote branch graph shape relative to main. "
            "This is evidence for reconciliation, not proof that divergent commits "
            "contain unique functionality; squash merges require PR/content review."
        )
    )
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    records = collect(args.base, args.remote)
    if args.json:
        print(
            json.dumps(
                {
                    "format": "pcs-branch-reconciliation-graph-v1",
                    "base": args.base,
                    "warning": (
                        "Ahead/diverged counts are not semantic merge decisions. "
                        "Squash-merged branches can remain graph-divergent."
                    ),
                    "branches": [asdict(record) for record in records],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    print(f"# Branch graph relative to {args.base}\n")
    print(
        "> Graph shape is not a merge decision. A squash-merged branch may appear "
        "ahead or diverged even when its functionality is already on main.\n"
    )
    print("| Branch | Graph status | Ahead | Behind | Head | Latest subject |")
    print("|---|---:|---:|---:|---|---|")
    for record in records:
        subject = record.subject.replace("|", "\\|")
        print(
            f"| `{record.branch}` | {record.status} | {record.ahead} | "
            f"{record.behind} | `{record.head[:12]}` | {subject} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
