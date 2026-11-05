"""Exact-scope composition attacks and actual engine/runtime observations."""
from dataclasses import asdict, replace
from fractions import Fraction
import hashlib
import os
from pathlib import Path

import pytest

from research.scientific_receiver_v1 import producer
from research.scientific_receiver_v1.assurance import (
    AssuranceError, ScientificAssumption, SyntheticObservation, compose, prediction_key,
)

HERE = Path(__file__).resolve().parents[1]
RAW = (HERE / "fixtures/multi-step-nonsingleton.wire").read_bytes()
SHA = hashlib.sha256(RAW).hexdigest()


def assumption(name="closed", subject=SHA):
    return ScientificAssumption(name, subject, "The declared compartment is closed.", "closed_compartment", True)


def observation(a, value):
    return SyntheticObservation(a.subject_sha256, a.id, prediction_key(a), value)


def build(*, raw=RAW, assumptions=None, observations=()):
    return compose(raw, expected_raw_sha256=hashlib.sha256(raw).hexdigest(),
                   assumptions=assumptions if assumptions is not None else (assumption(),), observations=observations)


def test_exact_replay_is_scoped_and_does_not_claim_fresh_lean_or_empiricism():
    report = build()
    assert report["subject_sha256"] == SHA
    dims = report["dimensions"]
    assert dims["computational_reproducibility"]["result"]["finalA"] == [13, 2]
    assert dims["computational_reproducibility"]["result"]["finalB"] == [7, 2]
    assert dims["computational_reproducibility"]["result"]["lowerB"] == [2, 1]
    assert dims["computational_reproducibility"]["result"]["upperB"] == [5, 1]
    assert dims["executable_correspondence"]["actual_replay"]["status"] == "NOT_RUN"
    assert dims["formal_mathematics"]["fresh_kernel_audit_in_this_composition"] is False
    assert dims["empirical_validation"]["status"] == "NOT_ESTABLISHED"
    assert dims["authenticated_history"]["status"] == "NOT_ESTABLISHED"
    assert dims["cryptographic_authentication"]["status"] == "NOT_ESTABLISHED"
    assert all(report[k] is False for k in ("scientific_acceptance", "production_authority", "promotion_authority"))
    assert build() == report  # No timestamps or host-path instability in computation-only reports.


def test_real_heck_falsifier_reopens_real_reverse_cone_but_retains_mathematics_and_computation():
    a, unrelated = assumption(), assumption("other")
    before = build(assumptions=(a, unrelated))
    after = build(assumptions=(a, unrelated), observations=(observation(a, False),))
    assert after["observations"][0]["heck_internal_status"] == "falsified"
    assert after["reopened"] == ["assumption:closed", "prediction:closed", "scientific:applicability"]
    assert after["dimensions"]["formal_mathematics"] == before["dimensions"]["formal_mathematics"]
    assert after["dimensions"]["computational_reproducibility"] == before["dimensions"]["computational_reproducibility"]
    graph = after["obligation_graph"]["nodes"]
    assert graph["prediction:closed"]["status"] == "OPEN"
    assert graph["prediction:other"]["status"] == "CONDITIONAL"
    assert graph["computation:" + SHA]["status"] == "COMPUTATIONALLY_TESTED"
    assert after["dimensions"]["scientific_applicability"]["status"] == "REOPENED_BY_SYNTHETIC_FALSIFIER"
    assert after["dimensions"]["empirical_validation"]["status"] == "NOT_ESTABLISHED"


def test_repeated_falsification_and_later_matching_observation_cannot_restore_support():
    a = assumption()
    report = build(observations=(observation(a, False), observation(a, False), observation(a, True)))
    assert [o["heck_internal_status"] for o in report["observations"]] == ["falsified"] * 3
    assert report["dimensions"]["scientific_applicability"]["falsified_predictions"] == [a.id]
    assert report["obligation_graph"]["nodes"]["scientific:applicability"]["status"] == "OPEN"
    assert report["scientific_acceptance"] is False


def test_internal_synthetic_match_label_does_not_promote_empirical_class():
    a = assumption()
    report = build(observations=(observation(a, True),))
    # Existing HECK label is exposed honestly, with no adapter equivalence claim.
    assert report["observations"][0]["heck_internal_status"] == "empirically_supported"
    assert report["observations"][0]["empirical_validation_granted"] is False
    assert report["dimensions"]["empirical_validation"]["status"] == "NOT_ESTABLISHED"
    assert report["dimensions"]["scientific_applicability"]["status"] == "CONDITIONAL_UNVALIDATED"


def test_semantic_assumption_change_prevents_old_observation_replay():
    old = assumption()
    changed = replace(old, statement="A different scientific assumption.")
    assert prediction_key(old) != prediction_key(changed)
    with pytest.raises(AssuranceError, match="prediction scope"):
        build(assumptions=(changed,), observations=(observation(old, False),))


def test_cross_artifact_replay_rejected_even_when_both_contracts_are_valid():
    new_raw = producer.encode(producer.build(Fraction(10), Fraction(0), (Fraction(1),)))
    new_sha = hashlib.sha256(new_raw).hexdigest()
    old = assumption()
    with pytest.raises(AssuranceError, match="artifact scope"):
        build(raw=new_raw, assumptions=(old,))
    with pytest.raises(AssuranceError, match="prediction scope"):
        build(raw=new_raw, assumptions=(assumption(subject=new_sha),), observations=(observation(old, False),))


@pytest.mark.parametrize("change", [lambda raw: raw + b"\n", lambda raw: raw.replace(b"V1", b"V2"), lambda raw: raw + b"|PASS"])
def test_malformed_or_substituted_bytes_never_become_evidence(change):
    with pytest.raises(AssuranceError):
        compose(change(RAW), expected_raw_sha256=SHA, assumptions=(assumption(),))


@pytest.mark.parametrize("flag", ["scientific_acceptance", "production_authority", "formal_status", "accepted", "rank"])
def test_sender_flags_cannot_enter_assumption_or_observation_schema(flag):
    a = assumption()
    with pytest.raises(AssuranceError, match="exact declared schema"):
        ScientificAssumption.from_dict({**asdict(a), flag: True})
    with pytest.raises(AssuranceError, match="exact declared schema"):
        SyntheticObservation.from_dict({**asdict(observation(a, True)), flag: True})


@pytest.mark.parametrize("value", [1, 0, 1.0, "true", None])
def test_boolean_prediction_coercion_is_rejected(value):
    with pytest.raises(AssuranceError):
        replace(assumption(), expected=value)
    with pytest.raises(AssuranceError):
        replace(observation(assumption(), True), value=value)


def test_non_synthetic_observation_cannot_claim_empirical_validation():
    with pytest.raises(AssuranceError, match="synthetic"):
        replace(observation(assumption(), True), synthetic=False)


def test_wrong_prediction_unknown_assumption_and_duplicate_ids_fail_closed():
    a = assumption()
    for changed in (replace(observation(a, False), prediction_key="00" * 32),
                    replace(observation(a, False), assumption_id="unknown")):
        with pytest.raises(AssuranceError):
            build(observations=(changed,))
    with pytest.raises(AssuranceError, match="duplicate"):
        build(assumptions=(a, a))
    with pytest.raises(AssuranceError, match="required"):
        build(assumptions=())
    with pytest.raises(AssuranceError, match="64"):
        build(observations=(observation(a, False),) * 65)


def test_wrong_model_evidence_with_rebound_identity_still_rejects():
    raw = (HERE / "fixtures/wrong-environment.wire").read_bytes()
    subject = hashlib.sha256(raw).hexdigest()
    with pytest.raises(AssuranceError, match="exact replay rejected"):
        compose(raw, expected_raw_sha256=subject, assumptions=(assumption(subject=subject),))


def test_mutable_artifact_input_cannot_become_a_verified_snapshot():
    with pytest.raises(AssuranceError, match="immutable raw bytes"):
        compose(bytearray(RAW), expected_raw_sha256=SHA, assumptions=(assumption(),))


def test_no_caller_verdict_substitution_interface():
    with pytest.raises(TypeError):
        compose(RAW, expected_raw_sha256=SHA, assumptions=(assumption(),), verifier=lambda _: True)
    with pytest.raises(TypeError):
        compose(RAW, expected_raw_sha256=SHA, assumptions=(assumption(),), lean_verdict={"accepted": True})


def test_actual_compiled_lean_replay_remains_true_after_synthetic_falsification():
    names = ("PCS_SCIENTIFIC_LEAN", "PCS_SCIENTIFIC_MAIN", "PCS_SCIENTIFIC_CWD")
    if any(not os.environ.get(name) for name in names):
        pytest.fail("Actual Lean assurance test requires " + ", ".join(names) + " and qualified LEAN_PATH")
    a = assumption()
    report = compose(RAW, expected_raw_sha256=SHA, assumptions=(a,),
                     observations=(observation(a, False), observation(a, True)),
                     checker=Path(os.environ[names[0]]), checker_args=("--run", os.environ[names[1]]),
                     checker_cwd=Path(os.environ[names[2]]))
    actual = report["dimensions"]["executable_correspondence"]["actual_replay"]
    assert actual["acceptance"] is True
    assert actual["response"]["raw_hex"] == RAW.hex()
    assert report["dimensions"]["formal_mathematics"]["invalidated_by_observation"] is False
    assert report["dimensions"]["scientific_applicability"]["status"] == "REOPENED_BY_SYNTHETIC_FALSIFIER"
    assert report["scientific_acceptance"] is False
