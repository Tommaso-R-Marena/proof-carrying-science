from __future__ import annotations

import json
from pathlib import Path

from pcs.adapters.pkpd import check_peak_concentration_file
from pcs.check_registry_v06 import formal_target_for_check_v06
from pcs.replay_v06 import replay_evidence_item_v06


MODEL = {
    "model_type": "one_compartment_iv_bolus",
    "dose": {"value": 100.0, "unit": "mg"},
    "volume": {"value": 10.0, "unit": "L"},
    "clearance": {"value": 1.0, "unit": "L/h"},
    "time_unit": "h",
    "concentration_unit": "mg/L",
    "pd": {
        "model_type": "direct_emax",
        "e0": {"value": 0.0, "unit": "1"},
        "emax": {"value": 100.0, "unit": "1"},
        "ec50": {"value": 2.0, "unit": "mg/L"},
        "effect_unit": "1",
    },
}


def _write_fixture(root: Path, *, first: str = "10") -> tuple[Path, Path]:
    model = root / "model.json"
    output = root / "predictions.csv"
    model.write_text(json.dumps(MODEL), encoding="utf-8")
    output.write_text(
        "time,concentration,effect\n"
        f"0,{first},83.3\n"
        "1,9.0,81.8\n"
        "2,8.1,80.2\n",
        encoding="utf-8",
    )
    return model, output


def _evidence() -> dict:
    predicate = {
        "type": "pkpd_peak_concentration_threshold",
        "model_artifact": "A_MODEL",
        "output_artifact": "A_OUTPUT",
        "concentration_column": "concentration",
        "upper_bound": "12",
        "unit": "mg/L",
    }
    return {
        "id": "E_PEAK",
        "kind": "computational_test",
        "claim_ids": ["C_PEAK"],
        "outcome": "UNVERIFIED",
        "checker": "pcs-python-kernel/0.6.0",
        "predicate": predicate,
        "artifact_ids": ["A_MODEL", "A_OUTPUT"],
        "check_spec": dict(predicate),
    }


def test_peak_threshold_accepts_all_committed_rows_below_bound(tmp_path: Path):
    model, output = _write_fixture(tmp_path)
    ok, details = check_peak_concentration_file(
        model,
        output,
        concentration_column="concentration",
        upper_bound="12",
        unit="mg/L",
    )
    assert ok is True
    assert details["maximum_reported_concentration"] == "10"
    assert "committed prediction rows only" in details["scope"]


def test_peak_threshold_rejects_exceeding_row(tmp_path: Path):
    model, output = _write_fixture(tmp_path, first="12.0001")
    ok, details = check_peak_concentration_file(
        model,
        output,
        concentration_column="concentration",
        upper_bound="12",
        unit="mg/L",
    )
    assert ok is False
    assert details["first_exceeding_row"] == 2
    assert details["first_exceeding_value"] == "12.0001"


def test_peak_threshold_rejects_unit_not_declared_by_model(tmp_path: Path):
    model, output = _write_fixture(tmp_path)
    ok, details = check_peak_concentration_file(
        model,
        output,
        concentration_column="concentration",
        upper_bound="12",
        unit="ug/mL",
    )
    assert ok is False
    assert "must exactly match model concentration_unit" in details["message"]


def test_peak_threshold_rejects_non_strict_or_negative_cells(tmp_path: Path):
    model, output = _write_fixture(tmp_path, first="-1")
    ok, details = check_peak_concentration_file(
        model,
        output,
        concentration_column="concentration",
        upper_bound="12",
        unit="mg/L",
    )
    assert ok is False
    assert "non-negative" in details["message"]

    output.write_text(
        "time,concentration,effect\n0, 10,83.3\n",
        encoding="utf-8",
    )
    ok, details = check_peak_concentration_file(
        model,
        output,
        concentration_column="concentration",
        upper_bound="12",
        unit="mg/L",
    )
    assert ok is False
    assert "strict decimal subset" in details["message"]


def test_peak_threshold_replay_and_formal_target(tmp_path: Path):
    model, output = _write_fixture(tmp_path)
    replayed = replay_evidence_item_v06(
        _evidence(),
        {"A_MODEL": model, "A_OUTPUT": output},
    )
    assert replayed["outcome"] == "PASS"
    assert replayed["kind"] == "computational_test"

    target = formal_target_for_check_v06(
        "pkpd_peak_concentration_threshold"
    )
    assert target is not None
    assert target["checker"] == "PCS.V2.Checkers.pkpdPeakChecker"
    assert target["soundness_theorem"] == "PCS.V2.PKPDCheck.pkpdPeakRun_sound"
    assert target["semantic_proposition"] == "PCS.V2.PKPDCheck.PkpdPeakHolds"
    assert target["proof_level"] == "LEAN_KERNEL"
