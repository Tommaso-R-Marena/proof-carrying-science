"""Compare every exported bundle with the frozen benchmark run (reporting only; no Lean, no network).

    python -m research.claimcheck_v1.tools.crosscheck_bundles --results benchmark/results/heldout \
        --bundles benchmark/results/bundles --arms openrouter,search

A bundle is produced by verifying the arm's proposals afresh.  This checks that the fresh run gave
every proposal (same quoted sentence, same reading) the result the frozen benchmark run recorded.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ..benchmark.run import load_split
from .analyze import _CacheOnly, arm_proposals


def _key(r: dict) -> str:
    q = (r.get("q2_correspondence") or {}).get("quote") or {}
    return json.dumps([" ".join((q.get("text") or "").split()), (r.get("claim") or {}).get("spec"),
                       r.get("message") if "claim" not in r else None], sort_keys=True)


def crosscheck(split: str, results: Path, bundles: Path, arms: tuple[str, ...]) -> dict:
    verifier = _CacheOnly(results / "receipts")
    out = {}
    for doc in load_split(split):
        path = bundles / doc.slug / "receipts.json"
        if doc.variant != "original" or not path.exists():
            continue
        proposals = arm_proposals(doc, results)
        # distinct proposals: a reading proposed by two arms is stored once in a bundle
        frozen, fresh = set(), set()
        frozen_receipts = 0
        for arm in arms:
            for r in verifier.verify(doc, proposals[arm], arm):
                frozen.add((_key(r), r["result"]))
                frozen_receipts += 1
        receipts = json.loads(path.read_text(encoding="utf-8"))
        for r in receipts:
            fresh.add((_key(r), r["result"]))
        out[doc.slug] = {"bundle_receipts": len(receipts), "frozen_receipts_over_arms": frozen_receipts,
                         "distinct_proposals": len(fresh), "same_result_for_every_proposal": fresh == frozen,
                         "results": dict(sorted(Counter(r["result"] for r in receipts).items())),
                         "differences": [[k[1], json.loads(k[0])] for k in sorted(fresh ^ frozen)]}
    return {"split": split, "arms": list(arms), "documents": out,
            "all_bundles_match_frozen_run": bool(out) and all(v["same_result_for_every_proposal"] for v in out.values())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--split", default="heldout")
    ap.add_argument("--results", required=True)
    ap.add_argument("--bundles", required=True)
    ap.add_argument("--arms", default="gemini,openrouter,search")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    report = crosscheck(args.split, Path(args.results), Path(args.bundles), tuple(args.arms.split(",")))
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(json.dumps({k: (v if k != "documents" else {d: x["same_result_for_every_proposal"] for d, x in v.items()}) for k, v in report.items()}))
    return 0 if report["all_bundles_match_frozen_run"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
