from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import Candidate
from .evolve import run_evolution
from .formal_check import check_formal
from .live_stress import stress_champion_gemini


def main() -> int:
    p = argparse.ArgumentParser(
        description="Evolving safety gate: Lean admission + empirical evolution"
    )
    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("formal")
    f.add_argument("out", type=Path)

    e = sub.add_parser("evolve")
    e.add_argument("out", type=Path)
    e.add_argument("--evidence", type=Path, default=None)
    e.add_argument("--generations", type=int, default=4)
    e.add_argument("--live-gemini", action="store_true")
    e.add_argument("--max-requests", type=int, default=12)

    a = p.parse_args()
    try:
        if a.command == "formal":
            result = check_formal(a.out)
        else:
            result = run_evolution(
                a.out, evidence_root=a.evidence, generations=a.generations
            )
            if a.live_gemini:
                champ = Candidate(**result["champion"])
                live = stress_champion_gemini(
                    champ, a.out / "live", max_requests=a.max_requests
                )
                result = dict(result, live_stress=live)
                (a.out / "lineage.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"ok": True, "result_keys": sorted(result.keys())}, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, AssertionError) as err:
        print(
            json.dumps(
                {"ok": False, "error": str(err), "production_authority": False}
            )
        )
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
