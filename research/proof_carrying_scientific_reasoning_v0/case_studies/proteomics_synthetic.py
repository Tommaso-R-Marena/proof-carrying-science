"""Synthetic proteomics chain: peptide obs ∧ aggregation assumption ⇒ protein claim (declared)."""
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
            Premise(0, atom(0), Authority.empiricalAsserted),  # peptide intensities
            Premise(1, atom(1), Authority.assumption),  # aggregation model OK
            Premise(2, atom(2), Authority.hypothesis),  # functional interpretation
        )
    )
    b = Builder(Γ)
    pep = b.hyp(0)
    agg = b.hyp(1)
    protein = b.and_i(pep, agg)
    # Adversarial variant would andI with hyp(2) and claim mathVerified — rejected by meet/claims.
    cert = b.finish(protein)
    j = v1.check(cert.to_json())
    assert j.math_established is False
    path = ROOT / "results" / "case_proteomics_certificate.json"
    path.write_text(json.dumps(cert.to_json(), indent=2) + "\n", encoding="utf-8")
    print("proteomics declared=", j.declared_authority, "math_established=", j.math_established)


if __name__ == "__main__":
    main()
