#!/usr/bin/env python3
"""Branch-local noninterference checker for incubation/pcs_next_v1 ownership."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

OWNED_PREFIX = "incubation/pcs_next_v1/"
OWNED_EXACT = {
    "incubation/pcs_next_v1",
}


def run(cmd: list[str], cwd: Path) -> str:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 and cmd[1] not in {"diff", "status"}:
        # diff returns 1 when differences exist
        pass
    return proc.stdout


def repo_root_from_cwd(start: Path) -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start,
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(proc.stdout.strip())


def normalize_path(p: str) -> str:
    # Unicode normalize + strip trailing slashes
    p = unicodedata.normalize("NFC", p.replace("\\", "/"))
    while p.startswith("./"):
        p = p[2:]
    return p.rstrip("/")


def is_owned(path: str) -> bool:
    path = normalize_path(path)
    if path in OWNED_EXACT or path == OWNED_PREFIX.rstrip("/"):
        return True
    return path.startswith(OWNED_PREFIX)


def collect_paths(repo: Path, base: str) -> set[str]:
    paths: set[str] = set()
    # committed diff vs base
    out = subprocess.run(
        ["git", "diff", "--name-status", "--find-renames", f"{base}...HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            paths.add(parts[1])
            paths.add(parts[2])
        else:
            paths.add(parts[-1])

    # working tree + index
    out2 = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for line in out2.splitlines():
        # XY PATH or XY ORIG -> PATH
        if " -> " in line:
            paths.add(line.split(" -> ", 1)[1].strip())
            left = line[3:].split(" -> ", 1)[0].strip()
            paths.add(left)
        else:
            paths.add(line[3:].strip())

    # filter empties
    return {normalize_path(p) for p in paths if p and p != "."}


def check_special(repo: Path, paths: set[str]) -> list[str]:
    issues = []
    for p in sorted(paths):
        if not is_owned(p):
            continue
        full = repo / p
        if full.is_symlink():
            target = os.readlink(full)
            # symlink must not escape owned namespace when resolved
            try:
                resolved = full.resolve()
                owned_root = (repo / OWNED_PREFIX).resolve()
                if owned_root not in resolved.parents and resolved != owned_root:
                    issues.append(f"symlink escapes owned namespace: {p} -> {target}")
            except FileNotFoundError:
                issues.append(f"broken symlink: {p}")
        # case-insensitive collision within owned tree
    lower_map: dict[str, str] = {}
    for p in paths:
        if not is_owned(p):
            continue
        key = p.lower()
        if key in lower_map and lower_map[key] != p:
            issues.append(f"case-insensitive collision: {lower_map[key]} vs {p}")
        lower_map[key] = p
    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None, help="git base commit (default: read BASE_SHA.txt)")
    ap.add_argument("--repo", default=None)
    args = ap.parse_args()
    repo = Path(args.repo) if args.repo else repo_root_from_cwd(Path.cwd())
    base = args.base
    if base is None:
        base_file = repo / "incubation/pcs_next_v1/BASE_SHA.txt"
        text = base_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("base_sha:"):
                base = line.split(":", 1)[1].strip()
                break
    if not base:
        print("FAIL: could not determine base sha", file=sys.stderr)
        return 2

    paths = collect_paths(repo, base)
    # If no changes yet, success
    bad = sorted(p for p in paths if not is_owned(p))
    special = check_special(repo, paths)
    print(f"base={base}")
    print(f"changed_paths={len(paths)}")
    for p in sorted(paths):
        mark = "OWNED" if is_owned(p) else "FOREIGN"
        print(f"  [{mark}] {p}")
    if bad:
        print("FAIL: noninterference violation — paths outside owned namespace:")
        for p in bad:
            print(f"  - {p}")
        return 1
    if special:
        print("FAIL: special-path issues:")
        for s in special:
            print(f"  - {s}")
        return 1
    print("PASS: all changed paths within incubation/pcs_next_v1/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
