#!/usr/bin/env python3
"""Fail if git diff vs base touches paths outside the exclusive namespace."""
from __future__ import annotations

import subprocess
import sys

NS = "research/proof_carrying_scientific_reasoning_v0/"
BASE = open(
    __file__.replace("scripts/check_isolation.py", "BASE_COMMIT.txt"), encoding="utf-8"
).read().strip()


def main() -> int:
    out = subprocess.check_output(
        ["git", "diff", "--name-only", BASE], text=True
    )
    bad = [p for p in out.splitlines() if p and not p.startswith(NS)]
    if bad:
        print("ISOLATION_VIOLATION:", *bad, sep="\n")
        return 1
    print("ISOLATION_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
