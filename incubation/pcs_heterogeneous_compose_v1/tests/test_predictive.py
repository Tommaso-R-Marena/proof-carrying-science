from heck.predictive import (
    Observation,
    PredStatus,
    PredictiveObligation,
    discharge,
    discharge_sticky,
    is_support,
    observe_against_prediction,
)


def test_match_supports_empirically_not_formally():
    obl = PredictiveObligation.from_prediction(
        id="p1", theory_id="t", prediction={"cmax": 1.5}
    )
    updated = discharge(obl, Observation.match(obl.prediction_key))
    assert updated.status is PredStatus.EMPIRICALLY_SUPPORTED
    assert is_support(updated)
    assert updated.status.to_level().value == "empirical"


def test_contradict_falsifies_and_is_sticky():
    obl = PredictiveObligation.from_prediction(
        id="p1", theory_id="t", prediction={"cmax": 1.5}
    )
    falsified = discharge(obl, Observation.contradict(obl.prediction_key))
    assert falsified.status is PredStatus.FALSIFIED
    assert not is_support(falsified)
    rematch = discharge_sticky(falsified, Observation.match(obl.prediction_key))
    assert rematch.status is PredStatus.FALSIFIED


def test_observe_against_prediction_tolerance():
    obl = PredictiveObligation.from_prediction(
        id="p1", theory_id="t", prediction={"y": 1.0, "unit": "mg/L"}
    )
    match = observe_against_prediction(obl, {"y": 1.0, "unit": "mg/L"})
    assert match.kind.value == "match"
    near = observe_against_prediction(
        obl, {"y": 1.05, "unit": "mg/L"}, tolerance=0.1
    )
    assert near.kind.value == "match"
    far = observe_against_prediction(
        obl, {"y": 2.0, "unit": "mg/L"}, tolerance=0.1
    )
    assert far.kind.value == "contradict"


def test_wrong_key_preserves():
    obl = PredictiveObligation.from_prediction(
        id="p1", theory_id="t", prediction={"y": 1}
    )
    assert discharge(obl, Observation.match("deadbeef" * 8)) == obl
    assert discharge(obl, Observation.unrelated()) == obl
