"""Theory IR — first-class scientific theories with predictive obligations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .canonical import digest_obj
from .compose import CompositeClaim, EvidenceAtom, compose_receipt
from .levels import Level, parse_level
from .predictive import (
    PredStatus,
    PredictiveObligation,
    discharge_sticky,
    is_support,
    observe_against_prediction,
)


@dataclass
class TheoryObject:
    """A scoped scientific theory with formal leaves and predictive obligations."""

    id: str
    title: str
    assumptions: tuple[str, ...]
    formal_leaf_ids: tuple[str, ...]
    predictive_obligations: list[PredictiveObligation] = field(default_factory=list)
    required_composite_level: Level = Level.EMPIRICAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "heck-theory-object-v1",
            "id": self.id,
            "title": self.title,
            "assumptions": list(self.assumptions),
            "formal_leaf_ids": list(self.formal_leaf_ids),
            "required_composite_level": self.required_composite_level.value,
            "predictive_obligations": [o.to_dict() for o in self.predictive_obligations],
        }

    @classmethod
    def from_dict(cls, obj: Mapping[str, Any]) -> "TheoryObject":
        if obj.get("format") != "heck-theory-object-v1":
            raise ValueError("unsupported theory object format")
        obligations = []
        for raw in obj.get("predictive_obligations", []):
            obligations.append(
                PredictiveObligation(
                    id=raw["id"],
                    theory_id=raw["theory_id"],
                    prediction_key=raw["prediction_key"],
                    status=PredStatus(raw["status"]),
                    prediction=dict(raw["prediction"]),
                )
            )
        return cls(
            id=obj["id"],
            title=obj["title"],
            assumptions=tuple(obj.get("assumptions", [])),
            formal_leaf_ids=tuple(obj.get("formal_leaf_ids", [])),
            predictive_obligations=obligations,
            required_composite_level=parse_level(
                obj.get("required_composite_level", "empirical")
            ),
        )

    def add_prediction(
        self, *, obligation_id: str, prediction: Mapping[str, Any]
    ) -> PredictiveObligation:
        obl = PredictiveObligation.from_prediction(
            id=obligation_id, theory_id=self.id, prediction=prediction
        )
        self.predictive_obligations.append(obl)
        return obl

    def apply_observation(
        self, obligation_id: str, observed: Mapping[str, Any], *, tolerance: float = 0.0
    ) -> PredictiveObligation:
        for i, obl in enumerate(self.predictive_obligations):
            if obl.id == obligation_id:
                obs = observe_against_prediction(obl, observed, tolerance=tolerance)
                updated = discharge_sticky(obl, obs)
                self.predictive_obligations[i] = updated
                return updated
        raise KeyError(f"unknown predictive obligation: {obligation_id}")


def evaluate_theory(
    theory: TheoryObject,
    atoms: Sequence[EvidenceAtom],
) -> dict[str, Any]:
    """Evaluate a theory: compose formal leaves + predictive statuses.

    Scientific acceptance remains false unless every predictive obligation that
    is part of the theory's closure is either OPEN (reported) or empirically
    supported — never Formal-promoted. Any FALSIFIED obligation fails closure.
    """
    leaf_ids = list(theory.formal_leaf_ids)
    predictive_atoms: list[EvidenceAtom] = []
    statuses: dict[str, str] = {}
    falsified = False
    open_count = 0
    for obl in theory.predictive_obligations:
        statuses[obl.id] = obl.status.value
        if obl.status is PredStatus.FALSIFIED:
            falsified = True
            predictive_atoms.append(
                EvidenceAtom(
                    id=f"pred:{obl.id}",
                    level=Level.OPEN,
                    supported=False,
                    claim_id=obl.id,
                    evidence_sha256=obl.prediction_key,
                )
            )
            leaf_ids.append(f"pred:{obl.id}")
        elif obl.status is PredStatus.EMPIRICALLY_SUPPORTED:
            predictive_atoms.append(
                EvidenceAtom(
                    id=f"pred:{obl.id}",
                    level=Level.EMPIRICAL,
                    supported=True,
                    claim_id=obl.id,
                    evidence_sha256=obl.prediction_key,
                )
            )
            leaf_ids.append(f"pred:{obl.id}")
        else:
            open_count += 1

    all_atoms = list(atoms) + predictive_atoms
    claim = CompositeClaim(
        id=f"theory-closure:{theory.id}",
        required_level=theory.required_composite_level,
        leaf_ids=tuple(leaf_ids),
    )
    receipt = compose_receipt(all_atoms, claim, predictive_statuses=statuses)
    # OPEN predictive obligations block scientific closure but are not Formal claims.
    # FALSIFIED obligations also block closure. Empirical support never upgrades to Formal.
    closure_ok = bool(receipt["accepted"]) and not falsified and open_count == 0
    if any(
        o.status is PredStatus.EMPIRICALLY_SUPPORTED and is_support(o) is False
        for o in theory.predictive_obligations
    ):
        closure_ok = False


    return {
        "format": "heck-theory-evaluation-v1",
        "theory_id": theory.id,
        "theory_digest": digest_obj(theory.to_dict()),
        "compose_receipt": receipt,
        "predictive_statuses": statuses,
        "open_predictive_count": open_count,
        "falsified": falsified,
        "scientific_closure": closure_ok,
        "non_claims": [
            "scientific_closure_is_not_formal_truth",
            "empirical_support_is_not_formal_proof",
            "open_obligations_block_closure",
            "no_production_pcs_authority",
        ],
    }
