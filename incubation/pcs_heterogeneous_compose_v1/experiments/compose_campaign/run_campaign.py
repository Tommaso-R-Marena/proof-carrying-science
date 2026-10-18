#!/usr/bin/env python3
"""End-to-end HECK composition campaign on synthetic scientific scenarios."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from heck.canonical import canonicalize, digest_obj
from heck.compose import CompositeClaim, EvidenceAtom, compose_receipt
from heck.falsify import run_attack_campaign
from heck.levels import Level
from heck.theory_ir import TheoryObject, evaluate_theory

OUT = Path(__file__).resolve().parents[2] / "results" / "compose_campaign"


def scenario_transport_plus_prediction() -> dict:
    """Formal transport leaf + empirical peak prediction → empirical closure."""
    theory = TheoryObject(
        id="transport-peak-v1",
        title="Discrete transport conservation with predicted peak",
        assumptions=(
            "positive_cell_volumes",
            "row_stochastic_nonnegative_matrix",
            "invariant_volume_measure",
        ),
        formal_leaf_ids=("transport-amount-all-times",),
        required_composite_level=Level.EMPIRICAL,
    )
    theory.add_prediction(
        obligation_id="peak-holdout",
        prediction={"t_h": 2.0, "concentration": 0.85, "unit": "mmol/L"},
    )
    atoms = [
        EvidenceAtom(
            id="transport-amount-all-times",
            level=Level.FORMAL,
            supported=True,
            claim_id="amount_all_times",
            evidence_sha256=digest_obj({"kernel": "transport", "thm": "amount_all_times"}),
        )
    ]
    before = evaluate_theory(theory, atoms)
    theory.apply_observation(
        "peak-holdout",
        {"t_h": 2.0, "concentration": 0.85, "unit": "mmol/L"},
    )
    after = evaluate_theory(theory, atoms)
    # Adversarial: demand Formal for the same leaves — must fail.
    formal_claim = CompositeClaim(
        id="illegal-formal",
        required_level=Level.FORMAL,
        leaf_ids=("transport-amount-all-times", "pred:peak-holdout"),
    )
    # Rebuild predictive atom as in evaluate_theory for the attack attempt.
    pred_atom = EvidenceAtom(
        id="pred:peak-holdout",
        level=Level.EMPIRICAL,
        supported=True,
        claim_id="peak-holdout",
        evidence_sha256=theory.predictive_obligations[0].prediction_key,
    )
    illegal = compose_receipt(atoms + [pred_atom], formal_claim)
    return {
        "name": "transport_plus_prediction",
        "before_closure": before["scientific_closure"],
        "after_closure": after["scientific_closure"],
        "achieved_level": after["compose_receipt"]["achieved_level"],
        "illegal_formal_accepted": illegal["accepted"],
        "pass": (
            before["scientific_closure"] is False
            and after["scientific_closure"] is True
            and after["compose_receipt"]["achieved_level"] == "empirical"
            and illegal["accepted"] is False
        ),
    }


def scenario_calibration_style_minimax() -> dict:
    """Computational fit leaf + empirical holdout → empirical, not formal."""
    atoms = [
        EvidenceAtom(
            id="normal-eq",
            level=Level.COMPUTATIONAL,
            supported=True,
            claim_id="normal_equations",
            evidence_sha256=digest_obj({"check": "normal"}),
        ),
        EvidenceAtom(
            id="holdout",
            level=Level.EMPIRICAL,
            supported=True,
            claim_id="holdout_sse",
            evidence_sha256=digest_obj({"check": "holdout"}),
        ),
    ]
    ok = compose_receipt(
        atoms, CompositeClaim("cal", Level.EMPIRICAL, ("normal-eq", "holdout"))
    )
    bad = compose_receipt(
        atoms, CompositeClaim("cal-f", Level.FORMAL, ("normal-eq", "holdout"))
    )
    return {
        "name": "calibration_style_minimax",
        "empirical_accepted": ok["accepted"],
        "formal_accepted": bad["accepted"],
        "achieved_level": ok["achieved_level"],
        "pass": ok["accepted"] and not bad["accepted"] and ok["achieved_level"] == "empirical",
    }


def scenario_falsified_prediction() -> dict:
    theory = TheoryObject(
        id="wrong-peak",
        title="Falsifiable peak theory",
        assumptions=("one_compartment",),
        formal_leaf_ids=("pk-replay",),
    )
    theory.add_prediction(obligation_id="peak", prediction={"cmax": 10.0})
    atoms = [
        EvidenceAtom(
            "pk-replay",
            Level.COMPUTATIONAL,
            True,
            "replay",
            digest_obj({"pk": True}),
        )
    ]
    theory.apply_observation("peak", {"cmax": 3.0})
    result = evaluate_theory(theory, atoms)
    return {
        "name": "falsified_prediction",
        "falsified": result["falsified"],
        "closure": result["scientific_closure"],
        "pass": result["falsified"] and not result["scientific_closure"],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    scenarios = [
        scenario_transport_plus_prediction(),
        scenario_calibration_style_minimax(),
        scenario_falsified_prediction(),
    ]
    attacks = run_attack_campaign()
    report = {
        "format": "heck-compose-campaign-v1",
        "scenarios": scenarios,
        "scenario_pass": all(s["pass"] for s in scenarios),
        "attacks": {
            "caught": attacks["caught"],
            "total": attacks["attacks"],
            "catch_rate": attacks["catch_rate"],
            "missed": attacks["missed"],
        },
        "non_claims": [
            "not_production_pcs_authority",
            "not_empirical_scientific_discovery",
            "catch_rate_is_suite_specific",
        ],
    }
    (OUT / "CAMPAIGN_REPORT.json").write_bytes(canonicalize(report) + b"\n")
    md = [
        "# HECK composition campaign",
        "",
        f"- Scenarios passed: {report['scenario_pass']}",
        f"- Attacks caught: {attacks['caught']}/{attacks['attacks']}",
        f"- Catch rate: {attacks['catch_rate']}",
        "",
        "## Scenarios",
        "",
    ]
    for s in scenarios:
        md.append(f"- `{s['name']}`: {'PASS' if s['pass'] else 'FAIL'}")
    md.extend(["", "## Non-claims", ""])
    for n in report["non_claims"]:
        md.append(f"- {n}")
    (OUT / "CAMPAIGN_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"scenario_pass": report["scenario_pass"], "attacks": attacks["catch_rate"]}))
    return 0 if report["scenario_pass"] and attacks["caught"] == attacks["attacks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
