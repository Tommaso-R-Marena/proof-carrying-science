"""Put everything the development adversary got through the v1.1 policy to the REAL Lean kernel.

    python -m research.claimcheck_v1_1.dev.kernel_confirm --out research/claimcheck_v1_1/dev/results

The adversary analysis predicts arithmetic with the untrusted oracle.  This step checks, for every
reading that obtained CONFIRMATION or DISCREPANCY_FOR_REVIEW there, that the kernel agrees and that
the full pipeline (gates -> kernel -> policy) gives the same outward verdict.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ...claimcheck_v1.baseline import sentences
from ..verify import verify
from .common import documents, dump, manifest_v11


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--variants", default="original")
    args = ap.parse_args(argv)
    adv = json.loads((Path(args.out) / "dev_adversary.json").read_text(encoding="utf-8"))
    rows = next(iter(adv["by_tau"].values()))["rows"]
    docs = {d.key: d for split in ("dev", "heldout") for d in documents(split)}
    wanted: dict[str, list] = {}
    for r in rows:
        if r["doc"].split(":")[1] in args.variants.split(",") and (r["v11_confirmed"] or r["v11_flagged"]):
            for spec in r["confirmed_specs"][:1] + r["flagged_specs"][:1]:
                wanted.setdefault(r["doc"], []).append((r, spec, "CONFIRMATION" if r["v11_confirmed"] else "DISCREPANCY_FOR_REVIEW"))
    out, tally = [], Counter()
    for key, items in sorted(wanted.items()):
        doc = docs[key]
        spans = dict(sentences(doc.text))
        triples = [(f"k{i:03d}", {"quote": spans[r["sentence_start"]], "quote_start": r["sentence_start"], "spec": spec}, "development adversary")
                   for i, (r, spec, _want) in enumerate(items)]
        result = verify(triples, source_text=doc.text, source_meta={"name": key}, data=doc.data, manifest=manifest_v11(doc),
                        workers=1, batch_size=2)
        for (r, spec, want), rec in zip(items, result["records"]):
            same = rec["outward"]["verdict"] == want
            tally["same_verdict_with_real_kernel" if same else "DIFFERENT"] += 1
            out.append({"doc": key, "printed": r["printed"], "class": r["class"], "spec": spec, "oracle_based_verdict": want,
                        "kernel_based_verdict": rec["outward"]["verdict"], "mathematical": rec["mathematical"]["status"],
                        "kernel_accepted": rec["mathematical"]["kernel_accepted_every_theorem"]})
        print(key, dict(tally), flush=True)
    dump(Path(args.out) / "adversary_kernel_confirmation.json",
         {"note": "DEVELOPMENT data. Every reading the oracle-based adversary got through, re-run through the full pipeline with the real kernel.",
          "variants": args.variants, "tally": dict(tally), "items": out})
    return 0 if not tally["DIFFERENT"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
