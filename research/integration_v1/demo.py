"""Replay one synthetic scientific system through distinct research receivers.

Run: python -m research.integration_v1.demo --out /fresh/output/directory
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import hashlib
import html
import json
from pathlib import Path

from .scoped_evidence import (ROOT, component, digest, replay_conservation,
                              replay_interval, replay_nonidentifiability, falsify_dependency)
from .bridge_fixture import fixture


def run_demo():
    profile = ROOT / "docs/integration/2026-10-18/SOURCE_PROFILE.json"
    profile_sha256 = hashlib.sha256(profile.read_bytes()).hexdigest()
    contract = json.loads((ROOT / "incubation/pcs_conservation_algebra_v1/examples/mass_action/glucose_cleavage.json").read_text())
    conservation, report = replay_conservation(contract)
    trajectory = next(c for c in report["certificates"] if c["kind"] == "trajectory_conservation")
    claim = trajectory["claim"]
    position = claim["species"].index("glucose")
    values = [Fraction(state[position]) for state in claim["states"]]
    component("certnum")
    from certnum.expr.ast import expr_to_json
    from certnum.expr.parse import parse_expr
    from certnum.interval.interval import Interval
    from certnum.certificate.schema import make_certificate
    enclosure = Interval.mk(min(values), max(values)).to_json()
    numerical = make_certificate("interval_enclosure", claim={
        "expr": expr_to_json(parse_expr("glucose")),
        "box": {"glucose": enclosure}, "enclosure": enclosure,
    }, witness={"sample_points": [{"glucose": str(value)} for value in values]})
    observed = replay_interval(numerical)
    return {
        "format": "pcs-integrated-scientific-demo-v1",
        "source_profile_sha256": profile_sha256,
        "synthetic": True, "system_sha256": digest(contract),
        "contract": contract, "conservation": report,
        "scoped_observations": [o.to_dict() for o in conservation] + [observed.to_dict()],
        "numerical_certificate": numerical,
        "numerical_domain": "Enclosure of the 13 replayed rational Euler states; no continuum bound claimed.",
        "numeric_binding": {"trajectory_certificate_sha256": digest(trajectory),
                            "species": "glucose", "coordinate": position,
                            "state_count": len(values)},
        "causal_negative": replay_nonidentifiability(),
        "two_species_bridge_fixture": fixture(),
        "falsification": falsify_dependency(),
        "empirical_validity": "OPEN", "python_lean_refinement": "OPEN",
        "pcs_authority": False, "scientific_acceptance": False,
        "promotion_authority": False, "deployment_performed": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    # Preserve historical and newly generated evidence; require a fresh directory.
    args.out.mkdir(parents=True, exist_ok=False)
    result = run_demo()
    (args.out / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (args.out / "REPORT.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>PCS research replay</title>'
        '<h1>Synthetic cross-PR research replay</h1><p>Computational evidence. Empirical validity and '
        'implementation refinement remain OPEN. No production, promotion, or deployment authority.</p><pre>'
        + html.escape(json.dumps(result, indent=2, sort_keys=True)) + '</pre></html>')
    print(json.dumps({"output": str(args.out.resolve()), "report_sha256": digest(result),
                      "empirical_validity": "OPEN", "pcs_authority": False}))


if __name__ == "__main__":
    main()
