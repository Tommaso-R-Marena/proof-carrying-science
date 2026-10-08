#!/usr/bin/env python3
"""Standalone PCS semantic-precheck and optional existing Claim IR binding.

Does NOT invoke the Lean authority. Outputs are never certificates.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pcs.semantic_translation_v1 import (  # noqa: E402
    attach_to_claim_ir, check_translation, interpretation_digest, sha256,
)


def read_json(path: Path) -> dict:
    if path.stat().st_size > 1_000_000:
        raise ValueError("semantic input exceeds 1 MB bound")

    def unique_pairs(pairs):
        obj = {}
        for key, val in pairs:
            if key in obj:
                raise ValueError("duplicate JSON key")
            obj[key] = val
        return obj

    def reject_constant(name):
        raise ValueError("nonstandard nonfinite JSON number: " + name)

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs,
                       parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="PCS bounded semantic translation precheck (never PCS authority)")
    p.add_argument("--registry", required=True, type=Path)
    p.add_argument("--approved-registry-sha256", required=True,
                   help="digest approved OUTSIDE the model/proposal channel")
    p.add_argument("--interpretation", required=True, type=Path)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--claim-ir", type=Path, help="optional pcs-claim-ir-v1 artifact from existing translation engine")
    p.add_argument("--confirmed-interpretation-sha256",
                   help="digest recorded by an authorized interpretation-confirmation process")
    p.add_argument("--output", type=Path, help="write machine-readable decision JSON")
    p.add_argument("--overlay", type=Path, help="write non-authoritative PCS Claim IR semantic overlay")
    p.add_argument("--print-interpretation-sha256", action="store_true", help="print digest to request explicit confirmation")
    args = p.parse_args(argv)
    try:
        registry, interpretation, candidate = (read_json(x) for x in
                                                [args.registry, args.interpretation, args.candidate])
        claim_ir = read_json(args.claim_ir) if args.claim_ir else None
        if args.print_interpretation_sha256:
            print("SELECTED_INTERPRETATION_SHA256=" + interpretation_digest(interpretation), file=sys.stderr)
        decision = check_translation(
            registry, interpretation, candidate,
            approved_registry_sha256=args.approved_registry_sha256,
            confirmed_interpretation_sha256=args.confirmed_interpretation_sha256,
            claim_ir=claim_ir,
        )
        encoded = json.dumps(decision, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output:
            args.output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")
        if args.overlay:
            if claim_ir is None:
                raise ValueError("--overlay requires --claim-ir")
            overlay = attach_to_claim_ir(claim_ir, decision)
            args.overlay.write_text(json.dumps(overlay, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0 if decision["structural_precheck_pass"] and decision["decision"] == "STRUCTURALLY_CONFORMANT_NONAUTHORITATIVE" else 1
    except (OSError, ValueError, TypeError) as exc:
        # Never echo user-supplied JSON or cryptographic secrets in log output.
        print("PCS semantic precheck failed to load/verify inputs: " + type(exc).__name__, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
