"""Live (not mocked) Lean 4.28.0 smoke gate for GitHub Actions and local use.

Exit nonzero if any grounded fixture expression lacks a real kernel check.
This uses no provider network calls, API secrets, or production PCS authority.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from .core import Source
from .pipeline import LeanChecker, run, run_arithmetic, run_typed
from .evidence import discover_evidence, run_evidence
from .table_evidence import run_table


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
    typed_src = Source.from_bytes((HERE / "fixtures/typed_source.txt").read_bytes())
    typed_proposals = json.loads((HERE / "fixtures/typed_proposals.json").read_text())
    typed_reviewer = json.loads((HERE / "fixtures/typed_reviewer.json").read_text())
    typed = run_typed(typed_src, typed_proposals, reviewer_proposals=typed_reviewer, lean=lean)
    typed_statuses = [c["status"] for c in typed["claims"]]
    if typed_statuses != ["TYPED_QTY_PROVED"] * 4 + ["TYPED_QTY_REFUTED"]:
        print("FAIL: typed quantity Lean verification incomplete:", typed_statuses, file=sys.stderr)
        for c in typed["claims"]:
            if c["status"] not in ("TYPED_QTY_PROVED", "TYPED_QTY_REFUTED"):
                print("Lean diagnostic:", c.get("lean_diagnostic", "not available"), file=sys.stderr)
        return 1
    if typed["counts"]["kernel_checked"] != 5:
        print("FAIL: not all typed quantity examples were kernel checked", file=sys.stderr)
        return 1
    evidence_src = Source.from_bytes((HERE / "fixtures/evidence_source.txt").read_bytes())
    evidence_proposals = discover_evidence(evidence_src)
    evidence = run_evidence(evidence_src, evidence_proposals,
                            reviewer_proposals=evidence_proposals, lean=lean)
    evidence_formal = [c["formal_status"] for c in evidence["claims"]]
    if evidence_formal != ["TYPED_QTY_PROVED", "TYPED_QTY_REFUTED"]:
        print("FAIL: source-linked evidence Lean checks incomplete:", evidence_formal, file=sys.stderr)
        for c in evidence["claims"]:
            if c["formal_status"] not in ("TYPED_QTY_PROVED", "TYPED_QTY_REFUTED"):
                print("Lean diagnostic:", c.get("lean_diagnostic", "not available"), file=sys.stderr)
        return 1
    if evidence["counts"]["kernel_checked"] != 2 or any(
        c["status"] != "SEMANTIC_REVIEW_REQUIRED" or c["scientific_status"] != "NOT_ASSESSED"
        for c in evidence["claims"]
    ):
        print("FAIL: evidence mode must preserve semantics/science boundary", file=sys.stderr)
        return 1
    table_source = Source.from_bytes((HERE / "fixtures/table_data.csv").read_bytes())
    table_manifest = (HERE / "fixtures/table_spec.json").read_bytes()
    table_receipt = run_table(table_source, table_manifest, lean=lean)
    table_statuses = [c["formal_status"] for c in table_receipt["claims"]]
    expected_table = ["TYPED_QTY_PROVED", "TYPED_QTY_PROVED", "TYPED_QTY_REFUTED", "TYPED_QTY_PROVED"]
    if table_statuses != expected_table or table_receipt["counts"]["kernel_checked"] != 4:
        print("FAIL: CSV-linked quantity Lean checks incomplete:", table_statuses, file=sys.stderr)
        for c in table_receipt["claims"]:
            if c["formal_status"] not in ("TYPED_QTY_PROVED", "TYPED_QTY_REFUTED"):
                print("Lean diagnostic:", c.get("lean_diagnostic", "not available"), file=sys.stderr)
        return 1
    if any(c["status"] != "SEMANTIC_REVIEW_REQUIRED" or c["scientific_status"] != "NOT_ASSESSED"
           for c in table_receipt["claims"]):
        print("FAIL: table math cannot claim scientific validation", file=sys.stderr)
        return 1
    print("PASS: Lean 4.28.0 checked 3 arithmetic, 2 literal, 5 typed, 2 evidence-linked and 4 CSV-linked claims")
    print("Research-only: no source-context semantic or empirical claim is certified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
