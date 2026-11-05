"""Adversarial and positive controls for the epistemic obligation lattice."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pcs.epistemic_lattice_v1 import (
    EpistemicLatticeError,
    evaluate,
    load_package,
    replay,
    run_campaign,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "research" / "epistemic-lattice-v1" / "fixtures"


def _raw(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_good_empirical_supported():
    receipt = replay(_raw("01_good_empirical.json"))
    assert receipt["claims"][0]["status"] == "supported"
    assert receipt["aggregate"]["all_supported"] is True
    assert receipt["scientific_acceptance"] is False
    assert receipt["pcs_authority"] is False


def test_falsifier_dominates_passing_evidence():
    receipt = replay(_raw("02_falsified.json"))
    assert receipt["claims"][0]["status"] == "refuted"
    assert receipt["aggregate"]["any_refuted"] is True


def test_class_promotion_attack_blocked():
    receipt = replay(_raw("03_class_promotion_attack.json"))
    assert receipt["claims"][0]["status"] == "open"


def test_unfalsifiable_empirical_rejected():
    with pytest.raises(EpistemicLatticeError, match="falsifier"):
        load_package(_raw("04_unfalsifiable_rejected.json"))


def test_composition_supported():
    receipt = replay(_raw("05_composition_supported.json"))
    got = {row["claim_id"]: row["status"] for row in receipt["claims"]}
    assert got == {
        "C_data_ok": "supported",
        "C_model_bound": "supported",
        "C_lemma": "supported",
    }


def test_refutation_reopens_dependents():
    receipt = replay(_raw("06_composition_reopens.json"))
    got = {row["claim_id"]: row["status"] for row in receipt["claims"]}
    assert got == {
        "C_data_ok": "refuted",
        "C_model_bound": "open",
        "C_lemma": "open",
    }


def test_self_dependency_rejected():
    payload = {
        "format": "pcs-epistemic-lattice-v1",
        "claims": [{
            "id": "C1",
            "class": "formal",
            "dependencies": ["C1"],
            "falsifiers": [],
            "support_requires": [],
        }],
        "evidence": [],
        "observations": {"atoms": {}},
    }
    with pytest.raises(EpistemicLatticeError, match="self-dependency"):
        load_package(json.dumps(payload).encode())


def test_duplicate_claim_ids_rejected():
    payload = {
        "format": "pcs-epistemic-lattice-v1",
        "claims": [
            {
                "id": "C1",
                "class": "formal",
                "dependencies": [],
                "falsifiers": [],
                "support_requires": [],
            },
            {
                "id": "C1",
                "class": "formal",
                "dependencies": [],
                "falsifiers": [],
                "support_requires": [],
            },
        ],
        "evidence": [],
        "observations": {"atoms": {}},
    }
    with pytest.raises(EpistemicLatticeError, match="duplicate claim"):
        load_package(json.dumps(payload).encode())


def test_cycle_marked_unsound():
    package = load_package(json.dumps({
        "format": "pcs-epistemic-lattice-v1",
        "claims": [
            {
                "id": "A",
                "class": "formal",
                "dependencies": ["B"],
                "falsifiers": [],
                "support_requires": [],
            },
            {
                "id": "B",
                "class": "formal",
                "dependencies": ["A"],
                "falsifiers": [],
                "support_requires": [],
            },
        ],
        "evidence": [
            {"claim_id": "A", "class": "formal", "pass": True},
            {"claim_id": "B", "class": "formal", "pass": True},
        ],
        "observations": {"atoms": {}},
    }).encode())
    receipt = evaluate(package)
    assert all(row["status"] == "unsound" for row in receipt["claims"])


def test_defeasibility_under_new_observation():
    base = json.loads(_raw("01_good_empirical.json"))
    assert replay(json.dumps(base).encode())["claims"][0]["status"] == "supported"
    base["observations"]["atoms"]["obs.peak_above_threshold"] = True
    assert replay(json.dumps(base).encode())["claims"][0]["status"] == "refuted"


def test_full_fixture_campaign(tmp_path: Path):
    report = run_campaign(FIXTURES)
    assert report["passed"] is True
    assert len(report["cases"]) == 6
