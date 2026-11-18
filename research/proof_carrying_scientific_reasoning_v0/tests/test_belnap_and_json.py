"""Belnap truth table + JSON hardening + WF correspondence tests."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "independent_checker"))

from scientific_reasoning.belnap import ALL, EXPECTED, TV, band, designated
import check_certificate_v1 as v1


def test_belnap_all_16():
    for a in ALL:
        for b in ALL:
            assert band(a, b) == EXPECTED[(a, b)], (a, b, band(a, b))


def test_both_and_onlyFalse():
    assert band(TV.both, TV.onlyFalse) == TV.onlyFalse


def test_designated_and_iff():
    for a in ALL:
        for b in ALL:
            d = designated(band(a, b))
            assert d == (designated(a) and designated(b))


def test_schema_version_bool_rejected():
    text = '{"schema_version": true, "premises": [], "steps": [], "conclusion_step": 0}'
    try:
        v1.check(v1.parse_certificate_json(text))
        assert False
    except v1.CheckError:
        pass


def test_duplicate_json_key_rejected():
    text = '{"schema_version": 1, "schema_version": 1, "premises": [], "steps": [], "conclusion_step": 0}'
    try:
        v1.parse_certificate_json(text)
        assert False
    except v1.CheckError as e:
        assert "duplicate" in str(e)


def test_unknown_field_rejected():
    cert = {
        "schema_version": 1,
        "premises": [{"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"}],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": 0}],
        "conclusion_step": 0,
        "evil": 1,
    }
    try:
        v1.check(cert)
        assert False
    except v1.CheckError as e:
        assert "unknown" in str(e)


def test_claimed_support_bool_rejected():
    cert = {
        "schema_version": 1,
        "premises": [{"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"}],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": 0, "support": [True]}],
        "conclusion_step": 0,
    }
    try:
        v1.check(cert)
        assert False
    except v1.CheckError:
        pass


def test_claim_math_established_rejected():
    cert = {
        "schema_version": 1,
        "premises": [{"id": 0, "formula": ["atom", 0], "declared_authority": "mathVerified"}],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": 0, "math_established": True}],
        "conclusion_step": 0,
    }
    try:
        v1.check(cert)
        assert False
    except v1.CheckError:
        pass


def test_duplicate_premise_ids_rejected():
    cert = {
        "schema_version": 1,
        "premises": [
            {"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"},
            {"id": 0, "formula": ["atom", 1], "declared_authority": "mathVerified"},
        ],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": 0}],
        "conclusion_step": 0,
    }
    try:
        v1.check(cert)
        assert False
    except v1.CheckError as e:
        assert "duplicate" in str(e)


def test_external_conclusion_compared_to_reconstruction():
    cert = {
        "schema_version": 1,
        "premises": [{"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"}],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": 0}],
        "conclusion_step": 0,
        "conclusion": ["atom", 99],
    }
    try:
        v1.check(cert)
        assert False
    except v1.CheckError as e:
        assert "conclusion" in str(e)
