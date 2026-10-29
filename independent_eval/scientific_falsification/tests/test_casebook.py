"""Task 7 — scientific casebook: certify/verify via black-box PCS CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_harness.hashing import verify_hashes  # noqa: E402
from python_harness.paths import CASEBOOK, HASH_MANIFEST, ROOT as SF_ROOT  # noqa: E402
from python_harness.pcs_cli import certify, load_json, verify_certificate  # noqa: E402


def _cases() -> list[Path]:
    index = load_json(CASEBOOK / "CASEBOOK_INDEX.json")
    return [CASEBOOK / "cases" / cid for cid in index["cases"]]


def test_casebook_has_at_least_six_cases():
    cases = _cases()
    assert len(cases) >= 6
    for case in cases:
        assert (case / "CASE.md").is_file()
        assert (case / "manifest.json").is_file()
        assert (case / "license.json").is_file()
        lic = load_json(case / "license.json")
        assert lic["spdx"] == "CC0-1.0"


@pytest.mark.parametrize("case_id", [
    "01_pkpd_one_compartment",
    "02_pkpd_with_peak_threshold_note",
    "03_mass_action_reaction_balance",
    "04_unit_compatible_concentration",
    "05_csv_disjoint_cohorts",
    "06_scientific_workflow_composite",
    "07_pkpd_alt_parameters",
])
def test_case_certify_and_verify(case_id, tmp_path):
    case = CASEBOOK / "cases" / case_id
    out = tmp_path / "evidence"
    c = certify(case / "manifest.json", out)
    assert c.ok, c.combined()
    cert = load_json(out / "certificate.json")
    for claim in cert["claims"]:
        assert claim["assessment"]["status"] == "COMPUTATIONALLY_SUPPORTED", claim
    v = verify_certificate(out / "certificate.json")
    assert v.ok, v.combined()


def test_pkpd_negative_control_fails_reference_match(tmp_path):
    case = CASEBOOK / "cases" / "01_pkpd_one_compartment"
    # Build a bad manifest pointing at tampered predictions.
    manifest = load_json(case / "manifest.json")
    work = tmp_path / "neg"
    work.mkdir()
    for name in ("model.json", "manifest.json"):
        (work / name).write_bytes((case / name).read_bytes())
    (work / "predictions.csv").write_bytes(
        (case / "negative_controls" / "tampered_predictions.csv").read_bytes()
    )
    out = tmp_path / "evidence"
    c = certify(work / "manifest.json", out)
    assert c.ok, c.combined()  # certify still emits a certificate
    cert = load_json(out / "certificate.json")
    statuses = {cl["id"]: cl["assessment"]["status"] for cl in cert["claims"]}
    assert statuses["C_PK_REPLAY"] != "COMPUTATIONALLY_SUPPORTED"


def test_fixture_hashes_immutable():
    assert HASH_MANIFEST.is_file()
    manifest = load_json(HASH_MANIFEST)
    errors = verify_hashes(manifest["files"], SF_ROOT, relative_to=SF_ROOT)
    assert errors == [], errors
