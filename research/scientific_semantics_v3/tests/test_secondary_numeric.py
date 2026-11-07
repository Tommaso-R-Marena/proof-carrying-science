"""Retained fresh-source computation checks, not new semantic training labels."""
import hashlib
import json
from pathlib import Path

from research.scientific_semantics_v3.numerical import reproduce

ROOT=Path(__file__).parents[1]
SOURCE=ROOT/"fixtures/secondary_numeric"


def test_independently_frozen_source_and_reference_bytes_unchanged():
    raw=(SOURCE/"freeze-manifest.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest()=="8db918d5255b417db7490caf7a7bb4a12eb7fa06b92279bc1281bab02537c8e3"
    for name,row in json.loads(raw)["files"].items():
        data=(SOURCE/name).read_bytes()
        assert len(data)==row["bytes"] and hashlib.sha256(data).hexdigest()==row["sha256"]


def test_new_authentic_ultrasonic_regression_reproduces_published_statistics():
    r=reproduce((SOURCE/"Chwirut2.dat").read_bytes())
    assert r["status"]=="REPRODUCED_ROUNDED_COMPUTATION"
    assert (r["observations"],r["fitted_parameters"],r["degrees_of_freedom"])==(54,3,51)
    # Independently frozen reference tolerances, not checker-owned reward labels.
    assert abs(r["rss_float"]-513.04802941)<=1e-8+1e-6*513.04802941
    assert abs(r["residual_std_recomputed"]-3.1717133040)<=1e-8+1e-6*3.1717133040
    assert r["exact_rational_rounding_enclosure"]["status"]=="UNSUPPORTED"
    assert r["authority"] is False and r["statistical_assumptions_status"]=="NOT_VERIFIED"


def test_independently_predetermined_corrupted_observation_is_refuted():
    r=reproduce((SOURCE/"Chwirut2-corrupt-first-response.dat").read_bytes())
    assert r["status"]=="REFUTED" and r["rss_relative_discrepancy"]>1


def test_no_primary_result_overwritten_by_posthoc_repair():
    expected=json.loads((ROOT/"evidence/primary-index.json").read_text())["files"]
    for name in ["final-primary.json.gz","final-primary-packages.zip","development-primary.json.gz","development-primary-packages.zip"]:
        assert hashlib.sha256((ROOT/"evidence"/name).read_bytes()).hexdigest()==expected[name]["sha256"]
