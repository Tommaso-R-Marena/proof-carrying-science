#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.suite import run_benchmarks


def main() -> int:
    rows = run_benchmarks(seed=0)
    if "--fast" in sys.argv:
        rows = [r for r in rows if r.nodes <= 500]
    payload = {
        "rows": [r.to_json() for r in rows],
        "summary": {
            "n_cases": len(rows),
            "total_nodes_max": max((r.nodes for r in rows), default=0),
            "all_agree": all(r.agree for r in rows),
        },
        "cases": [
            {
                "name": r.name,
                "n_nodes": r.nodes,
                "incremental_ms": round(r.incr_ms, 3),
                "fresh_ms": round(r.fresh_ms, 3),
                "reused": r.reused,
                "rechecked": r.rechecked,
                "accepted": True,
                "agrees_with_fresh": r.agree,
                "speedup": round(r.fresh_ms / r.incr_ms, 3) if r.incr_ms else None,
            }
            for r in rows
        ],
    }
    out = ROOT / "results" / "benchmark_report.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"cases={payload['summary']['n_cases']} max_nodes={payload['summary']['total_nodes_max']}")
    for c in payload["cases"]:
        print(
            f"  {c['name']}: nodes={c['n_nodes']} inc={c['incremental_ms']}ms "
            f"fresh={c['fresh_ms']}ms reused={c['reused']} rechecked={c['rechecked']} "
            f"agree={c['agrees_with_fresh']} speedup={c['speedup']}"
        )
    print("wrote", out)
    return 0 if payload["summary"]["all_agree"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
