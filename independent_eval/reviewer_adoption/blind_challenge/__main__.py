"""Default entry: print help pointing at blind / score submodules."""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "Use:\n"
        "  python -m independent_eval.reviewer_adoption.blind_challenge.blind ...\n"
        "  python -m independent_eval.reviewer_adoption.blind_challenge.score ...\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
