#!/usr/bin/env python3
"""Replay a frozen v1 evidence bundle with the claim-binding checks the frozen v1 replayer lacks.

    python replay_v1_bundle_checked.py BUNDLE --checker-sha256 <digest of the reviewed ClaimCheck.lean>
                                      [--v1-replayer PATH] [--skip-lean] [--report FILE]

Why this exists.  The frozen v1 replayer (`research/claimcheck_v1/replay_independent.py`, pinned by
`research/claimcheck_v1/benchmark/FREEZE.json`) re-derives each proof obligation from the receipt's
claim and re-runs the Lean kernel, but never checks that the claim is the sentence's.  A resealed
bundle whose claim names another number, checks another statistic, or drops a standard-deviation
convention replays successfully, with the real kernel too (finding of 2026-11-17).  The frozen
replayer is evidence of the frozen run and is not changed.  On its own it must not be used to
establish the integrity of a bundle from an untrusted source.

This program runs the frozen v1 replayer unchanged, then requires for every receipt:
  * the claim's reported value is the printed literal (which the v1 replay binds to the source text)
    whenever the quote check found it;
  * the checked variants are exactly those the claim's statistic requires (both standard-deviation
    conventions unless the bundle's manifest declares one);
  * a decided result (PROVED / REFUTED) is the status its variants establish.
It passes only if the v1 replay passes and no receipt fails a check.  Standard library only; it reuses
the checks of `replay_independent_v1_1.py` (same directory) so there is one implementation of them.
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("replay_v11_checks", HERE / "replay_independent_v1_1.py")
_v11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_v11)
DECIDED = {"MATCH_PROVED": "PROVED", "MISMATCH_PROVED": "REFUTED"}


def receipt_problems(receipt: dict, manifest: dict) -> list:
    spec = (receipt.get("claim") or {}).get("spec") or {}
    q2 = receipt.get("q2_correspondence") or {}
    rv = q2.get("reported_value") or {}
    out = []
    if (q2.get("checks") or {}).get("reported_value_in_quote") and spec.get("reported") != rv.get("literal_checked"):
        out.append("the claim's reported value is not the number printed in the sentence")
    variants = (receipt.get("q1_mathematics") or {}).get("variants") or []
    if variants and [v.get("stat") for v in variants] != _v11.expected_variants(spec, manifest):
        out.append("the checked variants are not the ones the claim's statistic requires")
    result = receipt.get("result")
    if result in ("PROVED", "REFUTED") and DECIDED.get(_v11.math_status(receipt)) != result:
        out.append("the decided result is not the status the kernel-checked variants establish")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--checker-sha256", required=True, help="digest of the reviewed ClaimCheck.lean, obtained independently of the bundle")
    ap.add_argument("--v1-replayer", type=Path, default=HERE.parent / "claimcheck_v1" / "replay_independent.py")
    ap.add_argument("--skip-lean", action="store_true", help="integrity, second calculation and binding only (NOT a proof replay)")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args(argv)
    cmd = [sys.executable, str(args.v1_replayer), str(args.bundle), "--checker-sha256", args.checker_sha256, "--timeout", str(args.timeout)]
    if args.skip_lean:
        cmd.append("--skip-lean")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    summary = {"bundle": args.bundle.name, "v1_replayer_exit": proc.returncode, "binding": {"receipts": 0, "problems": []},
               "proof_replay": "skipped (--skip-lean): NOT a proof replay" if args.skip_lean else "the frozen v1 replayer re-ran the Lean kernel"}
    try:
        receipts = json.loads((args.bundle / "receipts.json").read_text(encoding="utf-8"))
        manifest = json.loads((args.bundle / "manifest.json").read_text(encoding="utf-8"))
        receipts = receipts if isinstance(receipts, list) else receipts.get("receipts", [])
        for r in receipts:
            summary["binding"]["receipts"] += 1
            for p in receipt_problems(r, manifest):
                summary["binding"]["problems"].append({"claim_id": r.get("claim_id"), "problem": p})
    except (OSError, ValueError, AttributeError, TypeError) as exc:
        summary["binding"]["problems"].append({"claim_id": None, "problem": "the bundle's receipts or manifest cannot be read: " + type(exc).__name__})
    summary["all_replayed"] = proc.returncode == 0 and not summary["binding"]["problems"] and summary["binding"]["receipts"] > 0
    text = json.dumps(summary, indent=1)
    if args.report:
        args.report.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if summary["all_replayed"] else 1


if __name__ == "__main__":
    sys.exit(main())
