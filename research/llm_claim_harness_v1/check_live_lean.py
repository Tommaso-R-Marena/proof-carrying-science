"""Live (not mocked) Lean 4.28.0 smoke gate for GitHub Actions and local use.

Exit nonzero if any grounded fixture expression lacks a real kernel check.
This uses no provider network calls, API secrets, or production PCS authority.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from .core import Source
from .pipeline import LeanChecker, run, run_arithmetic


HERE = Path(__file__).parent


def main() -> int:
    lean = LeanChecker("lean", timeout=40)
    source = Source.from_bytes((HERE / "fixtures/arithmetic_source.txt").read_bytes())
    proposals = json.loads((HERE / "fixtures/arithmetic_proposals.json").read_text())
    reviewer = json.loads((HERE / "fixtures/arithmetic_reviewer.json").read_text())
    receipt = run_arithmetic(source, proposals, reviewer_proposals=reviewer, lean=lean)
    statuses = [c["status"] for c in receipt["claims"]]
    if statuses != ["ARITH_EXPR_PROVED", "ARITH_EXPR_PROVED", "ARITH_EXPR_REFUTED"]:
        print("FAIL: arithmetic Lean verification incomplete:", statuses, file=sys.stderr)
        for c in receipt["claims"]:
            if c["status"] != "ARITH_EXPR_PROVED" and c["status"] != "ARITH_EXPR_REFUTED":
                print("Lean diagnostic:", c.get("lean_diagnostic", "not available"), file=sys.stderr)
        return 1
    if receipt["counts"]["kernel_checked"] != 3:
        print("FAIL: not all arithmetic examples were kernel checked", file=sys.stderr)
        return 1
    original = Source.from_bytes((HERE / "fixtures/source.txt").read_bytes())
    literal_proposals = json.loads((HERE / "fixtures/proposals.json").read_text())
    legacy = run(original, literal_proposals, lean=lean)
    literal_statuses = [c["status"] for c in legacy["claims"]]
    if literal_statuses != ["NORMALIZED_PROVED", "NORMALIZED_REFUTED"]:
        print("FAIL: legacy Lean verification incomplete:", literal_statuses, file=sys.stderr)
        return 1
    print("PASS: Lean 4.28.0 checked 3 rational expression AST claims and 2 literal comparisons")
    print("Research-only: no source-context semantic or empirical claim is certified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
