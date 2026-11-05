"""Adversarial conflation-attack suite for HECK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .canonical import digest_obj
from .compose import CompositeClaim, EvidenceAtom, accept, achieved_level, compose_receipt
from .levels import Level
from .predictive import Observation, PredStatus, PredictiveObligation, discharge, discharge_sticky, is_support


@dataclass(frozen=True)
class AttackCase:
    name: str
    description: str
    run: Callable[[], dict[str, Any]]


def _digest(label: str) -> str:
    return digest_obj({"label": label})


def attack_empirical_as_formal() -> dict[str, Any]:
    """Producer claims Formal from a single Empirical leaf — must reject."""
    atom = EvidenceAtom(
        id="e1",
        level=Level.EMPIRICAL,
        supported=True,
        claim_id="c1",
        evidence_sha256=_digest("emp"),
    )
    claim = CompositeClaim(id="atk1", required_level=Level.FORMAL, leaf_ids=("e1",))
    receipt = compose_receipt([atom], claim)
    return {
        "name": "empirical_as_formal",
        "expected_accepted": False,
        "accepted": receipt["accepted"],
        "caught": receipt["accepted"] is False,
        "receipt": receipt,
    }


def attack_heterogeneous_promotion() -> dict[str, Any]:
    """Formal + Empirical stacked, producer demands Formal — must reject."""
    atoms = [
        EvidenceAtom("f1", Level.FORMAL, True, "cf", _digest("f")),
        EvidenceAtom("e1", Level.EMPIRICAL, True, "ce", _digest("e")),
    ]
    claim = CompositeClaim(id="atk2", required_level=Level.FORMAL, leaf_ids=("f1", "e1"))
    receipt = compose_receipt(atoms, claim)
    return {
        "name": "heterogeneous_promotion",
        "expected_accepted": False,
        "accepted": receipt["accepted"],
        "achieved_level": receipt["achieved_level"],
        "caught": receipt["accepted"] is False
        and receipt["achieved_level"] == Level.EMPIRICAL.value,
        "receipt": receipt,
    }


def attack_unsupported_leaf() -> dict[str, Any]:
    atom = EvidenceAtom("f1", Level.FORMAL, False, "cf", _digest("bad"))
    claim = CompositeClaim(id="atk3", required_level=Level.FORMAL, leaf_ids=("f1",))
    receipt = compose_receipt([atom], claim)
    return {
        "name": "unsupported_leaf",
        "expected_accepted": False,
        "accepted": receipt["accepted"],
        "caught": receipt["accepted"] is False,
        "receipt": receipt,
    }


def attack_missing_leaf() -> dict[str, Any]:
    atom = EvidenceAtom("f1", Level.FORMAL, True, "cf", _digest("f"))
    claim = CompositeClaim(id="atk4", required_level=Level.FORMAL, leaf_ids=("missing",))
    receipt = compose_receipt([atom], claim)
    return {
        "name": "missing_leaf",
        "expected_accepted": False,
        "accepted": receipt["accepted"],
        "caught": receipt["accepted"] is False,
        "receipt": receipt,
    }


def attack_empty_composite() -> dict[str, Any]:
    claim = CompositeClaim(id="atk5", required_level=Level.FORMAL, leaf_ids=())
    receipt = compose_receipt([], claim)
    return {
        "name": "empty_composite",
        "expected_accepted": False,
        "accepted": receipt["accepted"],
        "caught": receipt["accepted"] is False,
        "receipt": receipt,
    }


def attack_predictive_unfalsify() -> dict[str, Any]:
    """After falsification, a matching observation must not restore support."""
    obl = PredictiveObligation.from_prediction(
        id="p1", theory_id="t1", prediction={"y": 1.0}
    )
    falsified = discharge(obl, Observation.contradict(obl.prediction_key))
    restored = discharge_sticky(falsified, Observation.match(obl.prediction_key))
    return {
        "name": "predictive_unfalsify",
        "expected_accepted": False,
        "status": restored.status.value,
        "is_support": is_support(restored),
        "caught": restored.status is PredStatus.FALSIFIED and not is_support(restored),
    }


def attack_provenance_as_formal() -> dict[str, Any]:
    atom = EvidenceAtom("p1", Level.PROVENANCE, True, "cp", _digest("prov"))
    claim = CompositeClaim(id="atk7", required_level=Level.FORMAL, leaf_ids=("p1",))
    receipt = compose_receipt([atom], claim)
    return {
        "name": "provenance_as_formal",
        "expected_accepted": False,
        "accepted": receipt["accepted"],
        "caught": receipt["accepted"] is False,
        "receipt": receipt,
    }


def attack_computational_as_formal() -> dict[str, Any]:
    atom = EvidenceAtom("c1", Level.COMPUTATIONAL, True, "cc", _digest("comp"))
    claim = CompositeClaim(id="atk8", required_level=Level.FORMAL, leaf_ids=("c1",))
    ok = accept([atom], claim)
    return {
        "name": "computational_as_formal",
        "expected_accepted": False,
        "accepted": ok,
        "caught": ok is False,
        "achieved_level": achieved_level([atom], claim).value,
    }


ATTACKS: list[AttackCase] = [
    AttackCase("empirical_as_formal", "Empirical leaf claimed as Formal", attack_empirical_as_formal),
    AttackCase(
        "heterogeneous_promotion",
        "Formal+Empirical meet promoted to Formal",
        attack_heterogeneous_promotion,
    ),
    AttackCase("unsupported_leaf", "Unsupported formal leaf", attack_unsupported_leaf),
    AttackCase("missing_leaf", "Referenced leaf absent", attack_missing_leaf),
    AttackCase("empty_composite", "Empty leaf set", attack_empty_composite),
    AttackCase(
        "predictive_unfalsify",
        "Sticky falsification under rematch",
        attack_predictive_unfalsify,
    ),
    AttackCase("provenance_as_formal", "Provenance claimed as Formal", attack_provenance_as_formal),
    AttackCase(
        "computational_as_formal",
        "Computational leaf claimed as Formal",
        attack_computational_as_formal,
    ),
]


def run_attack_campaign() -> dict[str, Any]:
    results = [case.run() for case in ATTACKS]
    caught = sum(1 for r in results if r.get("caught"))
    missed = [r["name"] for r in results if not r.get("caught")]
    return {
        "format": "heck-conflation-campaign-v1",
        "attacks": len(results),
        "caught": caught,
        "missed": missed,
        "catch_rate": caught / len(results) if results else 0.0,
        "results": results,
        "non_claims": [
            "suite_specific_catch_rate_is_not_a_security_proof",
            "no_production_pcs_authority",
        ],
    }
