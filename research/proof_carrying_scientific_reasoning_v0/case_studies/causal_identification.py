"""Causal estimate identified only under explicit assumptions (synthetic)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "independent_checker"))

from scientific_reasoning.certificates_v1 import Builder
from scientific_reasoning.syntax import Authority, Context, Premise, atom
from scientific_reasoning.explanation import explain
import check_certificate_v1 as v1


def main() -> None:
    # 0: observational association (empirical)
    # 1: no unmeasured confounding (assumption) — NOT established
    # 2: positivity (assumption)
    Γ = Context(
        premises=(
            Premise(0, atom(0), Authority.empiricalAsserted),
            Premise(1, atom(1), Authority.assumption),
            Premise(2, atom(2), Authority.assumption),
        )
    )
    b = Builder(Γ)
    o = b.hyp(0)
    a = b.hyp(1)
    p = b.hyp(2)
    oa = b.and_i(o, a)
    concl = b.and_i(oa, p)
    cert = b.finish(concl)
    j = v1.check(cert.to_json())
    assert j.math_established is False
    assert j.declared_authority in ("empiricalAsserted", "assumption")
    out = ROOT / "results" / "case_causal_certificate.json"
    out.write_text(json.dumps(cert.to_json(), indent=2) + "\n", encoding="utf-8")
    print("Causal certificate accepted as conditional derivation only.")
    print("math_established=", j.math_established, "declared=", j.declared_authority)


if __name__ == "__main__":
    main()
