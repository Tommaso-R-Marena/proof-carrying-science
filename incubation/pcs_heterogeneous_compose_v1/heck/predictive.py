"""Predictive obligations — Popperian closure for HECK."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .canonical import digest_obj
from .levels import Level


class PredStatus(str, Enum):
    OPEN = "open"
    EMPIRICALLY_SUPPORTED = "empirically_supported"
    FALSIFIED = "falsified"

    def to_level(self) -> Level:
        if self is PredStatus.EMPIRICALLY_SUPPORTED:
            return Level.EMPIRICAL
        return Level.OPEN


class ObservationKind(str, Enum):
    MATCH = "match"
    CONTRADICT = "contradict"
    UNRELATED = "unrelated"


@dataclass(frozen=True)
class Observation:
    kind: ObservationKind
    prediction_key: str | None = None

    @classmethod
    def match(cls, prediction_key: str) -> "Observation":
        return cls(ObservationKind.MATCH, prediction_key)

    @classmethod
    def contradict(cls, prediction_key: str) -> "Observation":
        return cls(ObservationKind.CONTRADICT, prediction_key)

    @classmethod
    def unrelated(cls) -> "Observation":
        return cls(ObservationKind.UNRELATED, None)


@dataclass(frozen=True)
class PredictiveObligation:
    id: str
    theory_id: str
    prediction_key: str
    status: PredStatus
    prediction: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "heck-predictive-obligation-v1",
            "id": self.id,
            "theory_id": self.theory_id,
            "prediction_key": self.prediction_key,
            "status": self.status.value,
            "prediction": dict(self.prediction),
        }

    @classmethod
    def from_prediction(
        cls,
        *,
        id: str,
        theory_id: str,
        prediction: Mapping[str, Any],
        status: PredStatus = PredStatus.OPEN,
    ) -> "PredictiveObligation":
        key = digest_obj({"theory_id": theory_id, "prediction": dict(prediction)})
        return cls(
            id=id,
            theory_id=theory_id,
            prediction_key=key,
            status=status,
            prediction=dict(prediction),
        )


def is_support(o: PredictiveObligation) -> bool:
    return o.status is PredStatus.EMPIRICALLY_SUPPORTED


def discharge(o: PredictiveObligation, obs: Observation) -> PredictiveObligation:
    if obs.kind is ObservationKind.MATCH and obs.prediction_key == o.prediction_key:
        return PredictiveObligation(
            id=o.id,
            theory_id=o.theory_id,
            prediction_key=o.prediction_key,
            status=PredStatus.EMPIRICALLY_SUPPORTED,
            prediction=o.prediction,
        )
    if obs.kind is ObservationKind.CONTRADICT and obs.prediction_key == o.prediction_key:
        return PredictiveObligation(
            id=o.id,
            theory_id=o.theory_id,
            prediction_key=o.prediction_key,
            status=PredStatus.FALSIFIED,
            prediction=o.prediction,
        )
    return o


def discharge_sticky(o: PredictiveObligation, obs: Observation) -> PredictiveObligation:
    if o.status is PredStatus.FALSIFIED:
        return o
    return discharge(o, obs)


def observe_against_prediction(
    obligation: PredictiveObligation,
    observed: Mapping[str, Any],
    *,
    tolerance: float = 0.0,
) -> Observation:
    """Compare a numeric/string prediction payload to an observation dict.

    Exact key-set match required. Numeric values may use absolute tolerance.
    A structural mismatch or out-of-tolerance numeric difference contradicts.
    """
    pred = obligation.prediction
    if set(pred) != set(observed):
        return Observation.contradict(obligation.prediction_key)
    for key, expected in pred.items():
        actual = observed[key]
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            if abs(float(expected) - float(actual)) > tolerance:
                return Observation.contradict(obligation.prediction_key)
        elif expected != actual:
            return Observation.contradict(obligation.prediction_key)
    return Observation.match(obligation.prediction_key)
