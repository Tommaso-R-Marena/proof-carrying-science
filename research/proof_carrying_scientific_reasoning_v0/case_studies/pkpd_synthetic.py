"""Synthetic PK/PD argument under schema v1."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "independent_checker"))

from scientific_reasoning.certificates_v1 import Builder
from scientific_reasoning.syntax import Authority, Context, Premise, atom
import check_certificate_v1 as v1


def main() -> None:
    Γ = Context(
        premises=(
            Premise(0, atom(0), Authority.mathVerified),
            Premise(1, atom(1), Authority.empiricalAsserted),
            Premise(2, atom(2), Authority.assumption),
        )
    )
    b = Builder(Γ)
    j0 = b.hyp(0)
    j1 = b.hyp(1)
    j = b.and_i(j0, j1)
    cert = b.finish(j)
    out = v1.check(cert.to_json())
    path = ROOT / "results" / "case_pkpd_certificate_v1.json"
    path.write_text(json.dumps(cert.to_json(), indent=2) + "\n", encoding="utf-8")
    print("PKPD declared=", out.declared_authority, "math_established=", out.math_established)
    assert out.declared_authority == "empiricalAsserted"
    assert out.math_established is False


if __name__ == "__main__":
    main()
