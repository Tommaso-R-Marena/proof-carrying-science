"""Export one replayable evidence bundle per document and replay each one independently.

    python -m research.claimcheck_v1.benchmark.export_bundles --split heldout --results results/heldout --out results/bundles

For every original document the proposals of both models (read back from the committed response
cache; no network) and of the two deterministic proposers are verified afresh with obligation files
kept, written as a self-contained bundle, and then replayed by ``replay_independent.py`` in a
separate process (fresh Lean runs, re-derived obligations, second calculation).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from ..baseline import propose_rules, propose_search
from ..bundle import write_bundle
from ..lean import checker_sha256
from ..pipeline import verify_many
from ..propose import DEFAULT_MODELS, propose_with_model
from ..providers import Ledger
from .harness import dedupe
from .run import load_split

ROOT = Path(__file__).resolve().parents[1]


def export(split: str, results: Path, out: Path, workers: int, arms: tuple[str, ...]) -> dict:
    report = {"split": split, "bundles": []}
    ledger = Ledger(max_calls={"gemini": 0, "openrouter": 0})      # cache only
    for doc in (d for d in load_split(split) if d.variant == "original"):
        triples = []
        for arm in arms:
            if arm == "rules":
                props = propose_rules(doc.text, doc.data, doc.manifest)
            elif arm == "search":
                props = propose_search(doc.text, doc.data, doc.manifest)
            else:
                props, _meta = propose_with_model(arm, DEFAULT_MODELS[arm], doc.text, doc.data, doc.manifest, allow_network=False,
                                                  ledger=ledger, cache_dir=results / "model_responses")
            for p in dedupe(props):
                triples.append((p, f"{arm}:{DEFAULT_MODELS.get(arm, 'deterministic')}"))
        seen, unique = set(), []
        for p, origin in triples:
            key = json.dumps({"q": " ".join(p["quote"].split()), "s": p["spec"]}, sort_keys=True)
            if key not in seen:
                seen.add(key)
                unique.append((p, origin))
        target = out / doc.slug
        t0 = time.monotonic()
        receipts = verify_many([(f"c{i + 1:03d}", {k: v for k, v in p.items() if k in ("quote", "spec", "quote_start")}, origin)
                                for i, (p, origin) in enumerate(unique)],
                               source_text=doc.text, source_meta={"name": doc.key, "license": doc.meta.get("article_license"), "citation": doc.meta.get("citation")},
                               data=doc.data, manifest=doc.manifest, keep_dir=target / "obligations", workers=workers,
                               lean_timeout=1800, lean_when_ungrounded=False)
        index = write_bundle(target, source_text=doc.text, data=doc.data, manifest=doc.manifest, receipts=receipts,
                             source_name="article.txt", data_name=doc.meta["table"], extra={"document": doc.meta, "arms": list(arms)})
        verify_seconds = time.monotonic() - t0
        t1 = time.monotonic()
        proc = subprocess.run([sys.executable, str(ROOT / "replay_independent.py"), str(target), "--checker-sha256", checker_sha256(),
                               "--report", str(target.parent / f"{doc.slug}.replay.json"), "--timeout", "1800"],
                              capture_output=True, text=True)
        replay = json.loads((target.parent / f"{doc.slug}.replay.json").read_text(encoding="utf-8"))
        report["bundles"].append({
            "doc": doc.slug, "claims": len(receipts), "counts": index["counts"], "verify_seconds": round(verify_seconds, 1),
            "replay_seconds": round(time.monotonic() - t1, 1), "replay_exit_code": proc.returncode,
            "all_replayed": replay["all_replayed"], "obligation_files_rechecked": replay["results"][0].get("obligation_files_rechecked"),
            "kernel_checked_variants": sum(1 for r in receipts for v in r.get("q1_mathematics", {}).get("variants", []) if v.get("lean", {}).get("kernel_accepted")),
            "replay_failures": [r for r in replay["results"][1:] if not r["replayed"]][:10]})
    report["all_bundles_replayed"] = all(b["all_replayed"] for b in report["bundles"])
    (out / "replay_summary.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--split", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--arms", default="gemini,openrouter,search")
    args = ap.parse_args(argv)
    report = export(args.split, Path(args.results), Path(args.out), args.workers, tuple(args.arms.split(",")))
    print(json.dumps(report, indent=1))
    return 0 if report["all_bundles_replayed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
