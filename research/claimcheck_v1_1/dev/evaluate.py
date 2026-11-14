"""DEVELOPMENT evaluation of the v1.1 policy on the v1 documents (not prospective; see ``common``).

    python -m research.claimcheck_v1_1.dev.evaluate --out research/claimcheck_v1_1/dev/results

1. Re-scores every v1 arm (rules, search, Gemini, Nemotron) under v1.1 from the cached, kernel-
   checked v1 receipts.  No Lean, no network.  Sibling corroboration uses oracle-predicted siblings
   (marked); the verification pipeline kernel-checks them instead.
2. Reports coverage lost, and false confirmations and false accusations separately.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path

from ...claimcheck_v1.benchmark.harness import spec_signature, token_outcomes
from ...claimcheck_v1.tools.analyze import _CacheOnly, arm_proposals
from ..policy import TAU, assess_document
from .common import SPLITS, context, documents, dump, oracle_receipts

MAP = {"CONFIRMATION": "PROVED", "DISCREPANCY_FOR_REVIEW": "REFUTED"}


def confirmed_specs(receipt: dict, decision: dict) -> list[dict]:
    """The proposed reading plus the equivalent row selections a CONFIRMATION also covers."""
    specs = [receipt["claim"]["spec"]]
    if decision["verdict"] == "CONFIRMATION":
        for f in decision["findings"]:
            specs += [e["spec"] for e in f.get("equivalent_row_selections", [])]
    return specs


def token_outcomes_v11(doc, receipts: list[dict], decisions: list[dict]) -> dict:
    by_token: dict[int, list] = {}
    for r, d in zip(receipts, decisions):
        rv = (r.get("q2_correspondence") or {}).get("reported_value")
        if rv:
            by_token.setdefault(rv["start"], []).append((r, d))
    out = {}
    for start, pairs in by_token.items():
        decided: dict = {}
        for r, d in pairs:
            if d["verdict"] in MAP:
                decided.setdefault(MAP[d["verdict"]], []).extend(confirmed_specs(r, d))
        if len(decided) == 1:
            res, specs = next(iter(decided.items()))
            out[start] = {"result": res, "specs": specs}
        else:
            review = bool(decided) or any(d["verdict"] == "REQUIRE_HUMAN_REVIEW" for _r, d in pairs)
            out[start] = {"result": "REQUIRE_HUMAN_REVIEW" if review else "UNKNOWN", "specs": []}
    return out


def v1_outcomes(doc, receipts) -> dict:
    out = {}
    for start, o in token_outcomes(doc, [None] * len(receipts), receipts).items():
        out[start] = {"result": o["result"], "specs": [o["spec"]] if o.get("spec") and o["result"] != "UNKNOWN" else []}
    return out


def classes(doc, outcomes: dict) -> Counter:
    """Per printed number, against the gold labels.  Confirmations and discrepancy flags are scored separately."""
    c: Counter = Counter()
    labelled = {g["start"] for g in doc.gold}
    for item in doc.gold:
        o = outcomes.get(item["start"], {"result": "NO_PROPOSAL", "specs": []})
        gold_sigs = {spec_signature(doc, g) for g in item.get("gold", [])}
        match = any(spec_signature(doc, s) in gold_sigs for s in o["specs"])
        kind, truth, res = item["kind"], item.get("truth"), o["result"]
        derivable = kind == "derivable"
        if res == "PROVED":
            c["correct_confirmation" if derivable and truth == "consistent" and match else "unsupported_confirmation"] += 1
        elif res == "REFUTED":
            c["correct_discrepancy" if derivable and truth == "inconsistent" and match else "misleading_refutation"] += 1
        else:
            c[("abstained_on_true" if truth == "consistent" else "abstained_on_false" if truth == "inconsistent" else "abstained_on_conditional")
              if derivable else "correct_abstention"] += 1
            if derivable:
                c["of_which_review_requested" if res == "REQUIRE_HUMAN_REVIEW" else "of_which_no_result"] += 1
    for start, o in outcomes.items():
        if start not in labelled and o["result"] in ("PROVED", "REFUTED"):
            c["unlabelled_confirmation" if o["result"] == "PROVED" else "unlabelled_discrepancy"] += 1
    return c


def run(taus: list[Fraction]) -> dict:
    out = {"note": "DEVELOPMENT data for v1.1 (the v1 development and held-out documents). Not prospective validation.",
           "splits": {}}
    for split, results in SPLITS.items():
        verifier = _CacheOnly(results / "receipts")
        table = {"v1": {}}
        table.update({f"v1.1 tau={t}": {} for t in taus})
        verdict_counts = {f"v1.1 tau={t}": {} for t in taus}
        reasons = Counter()
        oracle_only: set = set()
        for doc in documents(split):
            ctx = context(doc)
            try:
                arms = arm_proposals(doc, results)
            except SystemExit:
                continue
            for arm, props in arms.items():
                if arm == "union":
                    continue
                try:
                    receipts = verifier.verify(doc, props, arm)
                except SystemExit:           # no cached kernel receipts for this document: oracle-predicted, marked
                    receipts = oracle_receipts(doc, props)
                    oracle_only.add(doc.key)
                table["v1"].setdefault(arm, Counter()).update(classes(doc, v1_outcomes(doc, receipts)))
                for t in taus:
                    decisions = assess_document(ctx, receipts, tau=t, oracle_siblings=True)
                    key = f"v1.1 tau={t}"
                    table[key].setdefault(arm, Counter()).update(classes(doc, token_outcomes_v11(doc, receipts, decisions)))
                    verdict_counts[key].setdefault(arm, Counter()).update(d["verdict"] for d in decisions)
                    if t == TAU:
                        for r, d in zip(receipts, decisions):
                            if r.get("result") in ("PROVED", "REFUTED") and d["verdict"] == "REQUIRE_HUMAN_REVIEW":
                                for f in d["findings"]:
                                    if not f["passed"]:
                                        reasons[(arm, r["result"], f["rule"])] += 1
        out["splits"][split] = {
            "documents_scored_from_oracle_predictions_not_kernel_receipts": sorted(oracle_only),
            "by_policy": {p: {a: dict(sorted(c.items())) for a, c in arms.items()} for p, arms in table.items()},
            "record_verdicts": {p: {a: dict(c) for a, c in arms.items()} for p, arms in verdict_counts.items()},
            "why_v1_results_were_withheld_at_frozen_tau": [{"arm": a, "v1_result": r, "rule": rule, "records": n}
                                                           for (a, r, rule), n in sorted(reasons.items())]}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--taus", default="1/100,1/50,1/20,1/10,1")
    args = ap.parse_args(argv)
    start = time.time()
    res = run([Fraction(t) for t in args.taus.split(",")])
    res["seconds"] = round(time.time() - start, 1)
    dump(Path(args.out) / "dev_arms.json", res)
    keys = ["correct_confirmation", "unsupported_confirmation", "unlabelled_confirmation", "correct_discrepancy", "misleading_refutation",
            "unlabelled_discrepancy", "abstained_on_true", "abstained_on_false"]
    short = ["conf+", "conf-", "conf?", "disc+", "disc-", "disc?", "abs_true", "abs_false"]
    for split, body in res["splits"].items():
        print("==", split)
        for policy, arms in body["by_policy"].items():
            for arm, c in arms.items():
                print(f"  {policy:16s} {arm:11s} " + " ".join(f"{n}={c.get(k, 0)}" for k, n in zip(keys, short)))
    print("seconds", res["seconds"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
