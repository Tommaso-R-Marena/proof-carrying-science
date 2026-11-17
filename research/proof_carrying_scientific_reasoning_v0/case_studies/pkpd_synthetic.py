"""Synthetic PK/PD argument: model math ∧ observation ⇒ conjunction under assumptions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from scientific_reasoning import (
    Authority,
    Context,
    Premise,
    build_certificate,
    derive_and_i,
    derive_hyp,
)
from scientific_reasoning.syntax import atom
from scientific_reasoning.explanation import explain


def main() -> None:
    Γ = Context(
        premises=(
            Premise(0, atom(0), Authority.mathVerified),  # model equation identity
            Premise(1, atom(1), Authority.empiricalAsserted),  # concentration observation
            Premise(2, atom(2), Authority.assumption),  # calibration model OK
        )
    )
    j0 = derive_hyp(Γ, 0)
    j1 = derive_hyp(Γ, 1)
    j = derive_and_i(j0, j1)
    cert = build_certificate(Γ, [j0, j1, j])
    out = ROOT / "results" / "case_pkpd_certificate.json"
    out.write_text(json.dumps(cert.to_json(), indent=2) + "\n", encoding="utf-8")
    print(explain(cert))
    assert cert.final_authority == Authority.empiricalAsserted.value


if __name__ == "__main__":
    main()
