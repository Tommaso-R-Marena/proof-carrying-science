"""Command-line entry point for the causal laboratory."""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pcs-causal",
        description="Proof-carrying causal laboratory (independent incubation package)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="Print version and isolation path")
    sub.add_parser("adversarial", help="Run adversarial graphical benchmarks")
    sub.add_parser("witness", help="Build and verify a non-identifiability witness")
    sub.add_parser("demo-drug", help="Run synthetic drug-response case study")
    sub.add_parser("backdoor-demo", help="Demonstrate backdoor identification on synthetic SCM")
    p_ui = sub.add_parser("ui", help="Launch local research UI (Flask)")
    p_ui.add_argument("--port", type=int, default=8765)

    args = parser.parse_args(argv)

    if args.cmd == "version":
        from pcs_causal import __isolation__, __version__

        print(json.dumps({"version": __version__, "isolation": __isolation__}, indent=2))
        return 0

    if args.cmd == "adversarial":
        from pcs_causal.benchmarks.adversarial import run_adversarial_suite

        results = run_adversarial_suite()
        print(json.dumps(results, indent=2))
        return 0 if all(results.values()) else 1

    if args.cmd == "witness":
        from pcs_causal.nonident.witness_search import classic_confounding_witness
        from pcs_causal.nonident.witness_verifier import verify_witness

        w = classic_confounding_witness()
        v = verify_witness(w)
        print(json.dumps(v.to_dict(), indent=2))
        return 0 if v.accepted else 1

    if args.cmd == "demo-drug":
        from pcs_causal.cases.biology_synth import drug_response_confounding_case

        print(json.dumps(drug_response_confounding_case(), indent=2))
        return 0

    if args.cmd == "backdoor-demo":
        from fractions import Fraction

        from pcs_causal.benchmarks.synthetic import generate_backdoor_scm
        from pcs_causal.identification.backdoor import (
            apply_backdoor_to_distribution,
            verify_backdoor_set,
        )

        scm, meta = generate_backdoor_scm()
        obs = scm.observational_distribution()
        res = verify_backdoor_set(scm.dag, "X", "Y", ["Z"])
        est1 = apply_backdoor_to_distribution(obs, "X", "Y", 1, ["Z"])
        est0 = apply_backdoor_to_distribution(obs, "X", "Y", 0, ["Z"])
        ate_id = None if est1 is None or est0 is None else est1 - est0
        true = scm.ate("X", "Y", 1, 0)
        out = {
            "meta": meta,
            "backdoor": res.to_dict(),
            "identified_ate": None
            if ate_id is None
            else [ate_id.numerator, ate_id.denominator],
            "true_ate": [true.numerator, true.denominator],
            "match": ate_id == true,
        }
        print(json.dumps(out, indent=2))
        return 0 if out["match"] and res.valid else 1

    if args.cmd == "ui":
        from pcs_causal.ui.app import run_app

        run_app(port=args.port)
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
