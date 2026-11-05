"""Conservative chemistry / reaction balance checks."""

from __future__ import annotations

from typing import Any

from ..core.statuses import AssuranceStatus, ClaimClass, status_record

SUPPORTED = {
    "fragment": "pcs-next-mass-action-stoichiometry-v1",
    "limitations": [
        "Stoichiometric atom balance only; not kinetic or thermodynamic validity.",
    ],
}


def atom_balance(reaction: dict[str, Any]) -> dict[str, Any]:
    """reaction: {reactants: [{formula_atoms: {C:1,O:2}, coeff:1}], products: [...]}"""
    def tally(side):
        tot: dict[str, int] = {}
        for sp in side:
            coeff = int(sp.get("coeff", 1))
            for atom, n in sp.get("formula_atoms", {}).items():
                tot[atom] = tot.get(atom, 0) + coeff * int(n)
        return tot
    left = tally(reaction.get("reactants", []))
    right = tally(reaction.get("products", []))
    atoms = sorted(set(left) | set(right))
    deltas = {a: left.get(a, 0) - right.get(a, 0) for a in atoms}
    if any(v != 0 for v in deltas.values()):
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="atom balance failure",
            evidence_ids=[f"delta:{k}={v}" for k, v in deltas.items() if v != 0],
            limitations=list(SUPPORTED["limitations"]),
        )
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason="stoichiometric atom balance holds",
        limitations=list(SUPPORTED["limitations"]),
    )
