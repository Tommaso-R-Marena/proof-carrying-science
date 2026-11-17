#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adversarial.attacks import run_all_attacks


def main() -> int:
    results = run_all_attacks()
    succeeded = [r for r in results if r.attack_succeeded]
    payload = {
        "n_attacks": len(results),
        "n_resisted": len(results) - len(succeeded),
        "n_succeeded": len(succeeded),
        "all_defenses_held": len(succeeded) == 0,
        "attacks": [r.to_json() for r in results],
        "counterexamples": [r.to_json() for r in succeeded],
    }
    out = ROOT / "results" / "adversarial_report.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print({"all_defenses_held": payload["all_defenses_held"], "n": len(results)})
    for r in results:
        print(f"  {r.name}: resisted={r.verifier_resisted} attack_succeeded={r.attack_succeeded}")
    print("wrote", out)
    return 0 if payload["all_defenses_held"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
