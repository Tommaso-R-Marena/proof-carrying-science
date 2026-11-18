#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "independent_checker"))

from scientific_reasoning.certificates_v1 import Builder
from scientific_reasoning.syntax import Authority, Context, Premise, atom
import check_certificate_v1 as v1


def make_chain(n: int) -> dict:
    premises = tuple(Premise(i, atom(i), Authority.empiricalAsserted) for i in range(n))
    Γ = Context(premises=premises)
    b = Builder(Γ)
    ids = [b.hyp(i) for i in range(n)]
    cur = ids[0]
    for i in ids[1:]:
        cur = b.and_i(cur, i)
    return b.finish(cur).to_json()


def main() -> None:
    results = []
    for n in (2, 8, 32, 64):
        cert = make_chain(n)
        t0 = time.perf_counter()
        for _ in range(50):
            v1.check(cert)
        dt = (time.perf_counter() - t0) / 50
        results.append({"n_premises": n, "steps": len(cert["steps"]), "sec_per_check": dt})
    out = ROOT / "benchmarks" / "RESULTS.md"
    lines = ["# Results", "", "| n | steps | sec/check |", "|---|---|---|"]
    for r in results:
        lines.append(f"| {r['n_premises']} | {r['steps']} | {r['sec_per_check']:.6f} |")
    lines.append("")
    lines.append("Baseline: schema-v1 independent checker only; no external library comparison.")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
