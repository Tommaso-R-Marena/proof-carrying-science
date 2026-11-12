"""Free-choice adversary on DEVELOPMENT data (not prospective; see ``common``).

    python -m research.claimcheck_v1_1.dev.adversary --out research/claimcheck_v1_1/dev/results

The adversary has read the data.  For EVERY number printed in a document (not only the labelled
ones) it may submit any reading the v1.1 grammar makes eligible for that sentence:

* confirmation attack   every eligible reading that reproduces the number;
* accusation attack     every eligible reading that does not reproduce the number, wherever another
                        number in the sentence could serve as corroboration.

It also submits all of these together, so that its own submissions can corroborate each other.
Kernel results are replaced by the oracle prediction here (marked); everything that gets an outward
verdict is afterwards put to the real kernel by ``kernel_confirm``.

Reported per target class (gold true / gold false / gold not derivable / unlabelled):
how many numbers the adversary can get CONFIRMED or flagged as a DISCREPANCY, under v1 (lower bound:
only the v1.1-eligible space is searched) and under v1.1.
"""
from __future__ import annotations

import argparse
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path

from ...claimcheck_v1.baseline import sentences
from ...claimcheck_v1.benchmark.harness import spec_signature
from ...claimcheck_v1.grounding import ground
from ...claimcheck_v1.spec import ClaimSpec
from ..policy import TAU, _scope, assess_document, identity
from ..space import printed_numbers
from .common import context, documents, dump, oracle_receipts

MAX_ACCUSATIONS_PER_TOKEN = 60


def attack_document(doc, tau: Fraction) -> list[dict]:
    ctx = context(doc)
    labelled = {g["start"]: g for g in doc.gold}
    rows = []
    for w0, sentence in sentences(doc.text):
        tokens = {}
        for _s, _e, literal in printed_numbers(sentence):
            if literal in tokens:
                continue
            try:
                g = ground(doc.text, sentence, ClaimSpec("count", literal), doc.manifest, quote_start=w0)
            except Exception:
                continue
            if g.token_start is None:
                continue
            a = ctx.analyse(w0=g.window_start, w1=g.window_end, reported=literal, detected_unit=g.detected_unit,
                            quote=sentence, quote_start=w0)
            tokens[literal] = (g, a)
        if not tokens:
            continue
        # ---- confirmation attack: submit every eligible reading that reproduces each number ------------
        proposals, owner = [], []
        for literal, (g, a) in tokens.items():
            for rd, ru in a.matching[:12]:
                proposals.append({"quote": sentence, "quote_start": w0, "spec": rd.spec(literal, ru).to_json()})
                owner.append(literal)
        receipts = oracle_receipts(doc, proposals) if proposals else []
        decisions = assess_document(ctx, receipts, tau=tau) if receipts else []
        confirmed: dict[str, list] = {}
        strong = []
        for lit, r, d in zip(owner, receipts, decisions):
            if d["verdict"] == "CONFIRMATION":
                specs = [r["claim"]["spec"]] + [e["spec"] for f in d["findings"] for e in f.get("equivalent_row_selections", [])]
                confirmed.setdefault(lit, []).append(specs)
                strong.append((lit, ClaimSpec.from_json(r["claim"]["spec"])))
        # ---- accusation attack: numbers nothing reproduces, read as a statistic a confirmed sibling pins down ----
        acc_props, acc_owner = [], []
        first = next(iter(tokens.values()))[0]
        readings, _info = ctx.window_readings(first.window_start, first.window_end)
        pins = set()
        for lit, spec in strong:
            if spec.stat not in ("count", "share"):
                _ident, scope = identity(ctx, spec)
                pins.add((spec.column, scope))
        for literal, (g, a) in tokens.items():
            if a.matching or not pins:
                continue
            n = 0
            for rd in readings:
                if rd.stat in ("count", "share") or (rd.column, _scope(rd)) not in pins:
                    continue
                for ru, _scale in ctx.unit_options(rd, g.detected_unit):
                    if n < MAX_ACCUSATIONS_PER_TOKEN and ctx.grounded(rd, literal, ru, sentence, w0):
                        acc_props.append({"quote": sentence, "quote_start": w0, "spec": rd.spec(literal, ru).to_json()})
                        acc_owner.append(literal)
                        n += 1
        flagged: dict[str, list] = {}
        if acc_props:
            acc_receipts = oracle_receipts(doc, acc_props)
            acc_decisions = assess_document(ctx, receipts + acc_receipts, tau=tau)[len(receipts):]
            for lit, r, d in zip(acc_owner, acc_receipts, acc_decisions):
                if d["verdict"] == "DISCREPANCY_FOR_REVIEW":
                    flagged.setdefault(lit, []).append(r["claim"]["spec"])
        for literal, (g, a) in tokens.items():
            gold = labelled.get(g.token_start)
            cls = "unlabelled" if gold is None else ("gold_true" if gold.get("truth") == "consistent" else
                                                     "gold_false" if gold.get("truth") == "inconsistent" else "gold_not_derivable")
            gold_sigs = {spec_signature(doc, s) for s in (gold or {}).get("gold", [])}
            conf = confirmed.get(literal, [])
            conf_matches_gold = any(spec_signature(doc, s) in gold_sigs for specs in conf for s in specs)
            flag = flagged.get(literal, [])
            rows.append({"doc": doc.key, "start": g.token_start, "printed": literal, "class": cls,
                         "v1_confirmable": bool(a.matching), "v11_confirmed": bool(conf), "v11_confirmed_reading_is_gold": conf_matches_gold,
                         "v11_flagged": bool(flag), "v11_flag_reading_is_gold": any(spec_signature(doc, s) in gold_sigs for s in flag),
                         "confirmed_specs": [specs[0] for specs in conf][:3], "flagged_specs": flag[:3],
                         "sentence_start": w0, "decoy_rate": float(a.rate), "eligible_readings": a.eligible_readings})
    return rows


def summarise(rows: list[dict]) -> dict:
    out = {}
    for cls in ("gold_true", "gold_false", "gold_not_derivable", "unlabelled"):
        sel = [r for r in rows if r["class"] == cls]
        out[cls] = {
            "numbers": len(sel),
            "v1_confirmable_by_some_eligible_reading": sum(r["v1_confirmable"] for r in sel),
            "v1.1_CONFIRMATION_obtained": sum(r["v11_confirmed"] for r in sel),
            "v1.1_CONFIRMATION_with_gold_reading": sum(r["v11_confirmed"] and r["v11_confirmed_reading_is_gold"] for r in sel),
            "v1.1_DISCREPANCY_obtained": sum(r["v11_flagged"] for r in sel),
            "v1.1_DISCREPANCY_with_gold_reading": sum(r["v11_flagged"] and r["v11_flag_reading_is_gold"] for r in sel),
        }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--taus", default=str(TAU))
    ap.add_argument("--splits", default="dev,heldout")
    ap.add_argument("--variants", default="original,mutated")
    args = ap.parse_args(argv)
    result = {"note": "DEVELOPMENT data for v1.1. Oracle-predicted arithmetic; see kernel_confirm for the kernel check of everything that got through.",
              "by_tau": {}}
    for t in [Fraction(x) for x in args.taus.split(",")]:
        start = time.time()
        rows = []
        for split in args.splits.split(","):
            for doc in documents(split):
                if doc.variant in args.variants.split(","):
                    rows.extend(dict(r, split=split) for r in attack_document(doc, t))
        result["by_tau"][str(t)] = {"summary": summarise(rows), "seconds": round(time.time() - start, 1),
                                    "got_through": [r for r in rows if (r["v11_confirmed"] and not r["v11_confirmed_reading_is_gold"]) or
                                                    (r["v11_flagged"] and not (r["class"] == "gold_false" and r["v11_flag_reading_is_gold"]))],
                                    "rows": rows if t == TAU else None}
        print("tau", t, result["by_tau"][str(t)]["seconds"], "s")
        for cls, s in result["by_tau"][str(t)]["summary"].items():
            print("  ", cls, s)
    dump(Path(args.out) / "dev_adversary.json", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
