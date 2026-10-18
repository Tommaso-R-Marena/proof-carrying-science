#!/usr/bin/env python3
"""Deterministic epistemic-calculus campaign with adversarial controls."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from pcs_epistemic.assures import assure
from pcs_epistemic.checker import verify_certificate
from pcs_epistemic.compose import compose_assures
from pcs_epistemic.dialectic import dialectic_report
from pcs_epistemic.invalidate import compute_impact, nonimpact


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    example = ROOT / "examples" / "pk_dialectic"
    ens = json.loads((example / "ensemble.json").read_text(encoding="utf-8"))
    graph = json.loads((example / "graph.json").read_text(encoding="utf-8"))
    dialectic = dialectic_report(ens["models"], ens["candidates"])
    impact = compute_impact(graph, ["raw_plasma"])
    hidden = nonimpact(graph, ["raw_plasma"], "c_hidden", dependency_complete=False)

    promotion = assure(
        {"id": "c", "required_class": "formal", "required_evidence": ["e"]},
        [{"id": "e", "class": "computational", "accepted": True}],
        level="formal",
    )
    composition = compose_assures(
        {"id": "c1", "required_class": "computational", "required_evidence": ["e1"]},
        [{"id": "e1", "class": "computational", "accepted": True}],
        {"id": "c2", "required_class": "computational", "required_evidence": ["e2"]},
        [{"id": "e2", "class": "computational", "accepted": True}],
        level_upstream="computational",
        level_downstream="computational",
    )
    receipt = verify_certificate((example / "dialectic_certificate.json").read_bytes())

    cases = [
        {
            "id": "dialectic_agreement_and_dispute",
            "passed": dialectic["agreement_core"] == ["mass_conserved", "cmax_bound"]
            and dialectic["dispute_frontier"] == ["terminal_slope_matches_ke"],
            "detail": dialectic,
        },
        {
            "id": "invalidation_transitive",
            "passed": "cmax_bound" in impact["affected_claims"]
            and "mass_conserved" in impact["affected_claims"],
            "detail": impact,
        },
        {
            "id": "hidden_dependency_blocks_endorsement",
            "passed": hidden["declared_nonimpact"] and not hidden["world_nonimpact_endorsed"],
            "detail": hidden,
        },
        {
            "id": "reject_computational_to_formal_promotion",
            "passed": promotion is False,
        },
        {
            "id": "compose_disjoint_pipeline",
            "passed": composition["composed_assured"] is True,
            "detail": composition,
        },
        {
            "id": "certificate_replay",
            "passed": receipt["accepted"] is True and receipt["production_authority"] is False,
            "detail": {"certificate_sha256": receipt["certificate_sha256"]},
        },
    ]
    passed = sum(1 for c in cases if c["passed"])
    report = {
        "format": "pcs-epistemic-campaign-v1",
        "total": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "cases": cases,
        "source_sha256": {
            "ensemble.json": sha_file(example / "ensemble.json"),
            "graph.json": sha_file(example / "graph.json"),
            "dialectic_certificate.json": sha_file(example / "dialectic_certificate.json"),
        },
        "production_authority": False,
        "scientific_authority": False,
    }
    out = ROOT / "campaign" / "CAMPAIGN_REPORT.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = ROOT / "campaign" / "CAMPAIGN_REPORT.md"
    md.write_text(
        "\n".join(
            [
                "# Epistemic Calculus Campaign",
                "",
                f"Passed **{passed}/{len(cases)}** deterministic controls.",
                "",
                "| Case | Result |",
                "| --- | --- |",
                *[
                    f"| `{c['id']}` | {'PASS' if c['passed'] else 'FAIL'} |"
                    for c in cases
                ],
                "",
                "No production or scientific authority is granted.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({"passed": passed, "total": len(cases), "report": str(out)}, indent=2))
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
