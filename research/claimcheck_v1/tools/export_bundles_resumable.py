"""Resumable driver around the frozen bundle exporter (reporting tool; changes no result).

    python -m research.claimcheck_v1.tools.export_bundles_resumable --split heldout \
        --results benchmark/results/heldout --out benchmark/results/bundles --arms gemini,openrouter,search

Calls ``benchmark.export_bundles.export`` unchanged for one document at a time and keeps each
document's record, so an interrupted run continues where it stopped.  A document is redone unless
its record exists and names the same arms.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..benchmark import export_bundles as frozen
from ..benchmark.run import load_split


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--split", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--arms", default="gemini,openrouter,search")
    ap.add_argument("--batch-size", type=int, default=4)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    arms = tuple(args.arms.split(","))
    docs = [d for d in load_split(args.split) if d.variant == "original"]
    records = []
    original_loader = frozen.load_split
    original_verify = frozen.verify_many
    # Smaller kernel batches: the same per-claim theorems, grouped so that a large table cannot push
    # one obligation file past the time limit (which would only cause a slower one-by-one fallback).
    frozen.verify_many = lambda *a, **k: original_verify(*a, **{**k, "batch_size": args.batch_size})
    try:
        for doc in docs:
            record_path = out / f"{doc.slug}.record.json"
            if record_path.exists():
                rec = json.loads(record_path.read_text(encoding="utf-8"))
                if rec.get("arms") == list(arms) and (out / doc.slug / "bundle.json").exists():
                    records.append(rec["bundle"])
                    continue
            frozen.load_split = lambda split, only=doc.slug: [d for d in original_loader(split) if d.slug == only]
            report = frozen.export(args.split, Path(args.results), out, args.workers, arms)
            record_path.write_text(json.dumps({"arms": list(arms), "bundle": report["bundles"][0]}, indent=1), encoding="utf-8")
            records.append(report["bundles"][0])
            print(json.dumps({k: report["bundles"][0][k] for k in ("doc", "claims", "counts", "all_replayed", "verify_seconds", "replay_seconds")}), flush=True)
    finally:
        frozen.load_split = original_loader
        frozen.verify_many = original_verify
    summary = {"split": args.split, "arms": list(arms), "bundles": records, "all_bundles_replayed": all(b["all_replayed"] for b in records)}
    (out / "replay_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"all_bundles_replayed": summary["all_bundles_replayed"], "documents": len(records)}))
    return 0 if summary["all_bundles_replayed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
