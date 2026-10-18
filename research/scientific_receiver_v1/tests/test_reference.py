"""Behavioral boundaries of the independent parser/replay and JSON adapter."""
from dataclasses import replace
from fractions import Fraction as F
import json
from pathlib import Path

import pytest

from research.scientific_receiver_v1 import producer, reference

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.mark.parametrize("case", json.loads((FIXTURES / "index.json").read_text())["cases"])
def test_frozen_fixtures(case):
    raw = (FIXTURES / case["wire"]).read_bytes()
    decision = reference.assess(raw)
    assert decision.accepted is case["accepted"], decision.reason
    if case["accepted"]:
        assert decision.result == case["result"]
        assert producer.encode(producer.from_json((FIXTURES / case["json"]).read_bytes())) == raw


def sample(**kwargs):
    return producer.build(F(10), F(1), (F(1, 3), F(2, 3)), **kwargs)


def mutate(raw, index, value):
    fields = raw.split(b"|")
    fields[index] = value
    return b"|".join(fields)


@pytest.mark.parametrize("token", [b"", b"+1", b"01", b"-0", b"1.0", b"1e0", b" 1",
                                     b"1\n", b"1\r", b"--1", b"-", b"\xff", b"0_1",
                                     b"1000000000000000001", b"1" * 21])
def test_integer_grammar_rejects(token):
    assert not reference.assess(mutate(producer.encode(sample()), 1, token)).accepted


@pytest.mark.parametrize("index", [1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14])
def test_fixed_declarations(index):
    assert not reference.assess(mutate(producer.encode(sample()), index, b"2")).accepted


@pytest.mark.parametrize("index", [11, 12])
def test_boolean_only(index):
    assert not reference.assess(mutate(producer.encode(sample()), index, b"2")).accepted


@pytest.mark.parametrize("index,value", [(10,b"65"), (10,b"-1"), (31,b"65"), (31,b"-1"),
                                        (16,b"0"), (16,b"-1"), (15,b"20"),
                                        (15,b"0"), (16,b"2")])
def test_bounds_and_reduced_rationals(index, value):
    raw = producer.encode(sample())
    if index == 15 and value == b"20":
        raw = mutate(raw, 16, b"2")
    if index == 15 and value == b"0":
        raw = mutate(raw, 16, b"2")
    assert not reference.assess(mutate(raw, index, value)).accepted


@pytest.mark.parametrize("change", [lambda raw: raw+b"|0", lambda raw: raw+b"\n",
                                     lambda raw: raw[:-1], lambda raw: b"\xef\xbb\xbf"+raw,
                                     lambda raw: raw.replace(b"V1",b"V2"),
                                     lambda raw: raw.replace(b"|",b"||",1),
                                     lambda raw: b"x"*8193])
def test_raw_framing_rejects(change):
    assert not reference.assess(change(producer.encode(sample()))).accepted


@pytest.mark.parametrize("changes", [
    {"referenceStep": 0}, {"envValue": F(0)}, {"declaredTotal": F(0)},
    {"initialA": F(11)}, {"firings": (F(2), F(3))},
    {"boxLo": F(10)}, {"boxHi": F(8)}, {"lower": F(10)}, {"upper": F(8)},
])
def test_scientific_binding_rejects(changes):
    raw = producer.encode(replace(sample(), **changes))
    assert not reference.assess(raw).accepted


def test_changed_schedule_with_consistent_new_evidence_accepts():
    changed = producer.build(F(10), F(1), (F(2), F(3)), box=(F(4),F(6)), claim=(F(3),F(7)))
    result = reference.receive(producer.encode(changed))
    assert result["finalA"] == [5,1]
    assert result["lowerB"] == [4,1]
    assert result["upperB"] == [8,1]


@pytest.mark.parametrize("a,b,firings", [(F(-1),F(2),()), (F(2),F(-1),()),
                                         (F(2),F(1),(F(-1),)),
                                         (F(2),F(0),(F(3),F(-2)))])
def test_physical_checks_all_states_and_firings(a,b,firings):
    algebraic = producer.build(a,b,firings)
    assert reference.assess(producer.encode(algebraic)).accepted
    assert not reference.assess(producer.encode(replace(algebraic,physical=True))).accepted


def test_max_steps_and_operand_edges():
    witness = producer.build(F(10**18),F(-10**18), (F(0),)*64,
                             box=(F(10**18-1), F(10**18)))
    assert reference.assess(producer.encode(witness)).accepted
    assert reference.assess(producer.encode(producer.build(F(1,10**18),F(0),()))).accepted
    with pytest.raises(ValueError):
        producer.build(F(10**18+1),F(0),())
    with pytest.raises(ValueError):
        producer.build(F(0),F(0),(F(0),)*65)


def json_sample():
    return producer.to_json(sample())


@pytest.mark.parametrize("change", [
    lambda raw: raw.replace('"referenceStep": 2', '"referenceStep": 2, "referenceStep": 2'),
    lambda raw: raw.replace('"referenceStep": 2', '"referenceStep": -0'),
    lambda raw: raw.replace('"referenceStep": 2', '"referenceStep": 2.0'),
    lambda raw: raw.replace('"referenceStep": 2', '"referenceStep": true'),
    lambda raw: raw.replace('"unitCode": false', '"unitCode": 0'),
    lambda raw: raw.replace('"initialA": "10/1"', '"initialA": "20/2"'),
    lambda raw: raw.replace('"initialA": "10/1"', '"initialA": "010/1"'),
    lambda raw: raw.replace('"initialA": "10/1"', '"initialA": "-0/1"'),
    lambda raw: raw.replace('"initialA": "10/1"', '"initialA": "10/-1"'),
    lambda raw: raw.replace('"initialA": "10/1"', '"initialA": 10'),
    lambda raw: raw.replace('"initialA": "10/1"', '"initialA": NaN'),
    lambda raw: raw.replace('"initialA": "10/1"', '"initialA": [10,1]'),
    lambda raw: raw.replace('"protocol": "PCS-SCI-BOUND-V1"', '"protocol": "PCS-SCI-BOUND-V2"'),
    lambda raw: raw[:-2]+', "PASS": true}',
])
def test_strict_json_rejects(change):
    with pytest.raises((ValueError, TypeError)):
        producer.from_json(change(json_sample()))


def test_json_has_exact_fields():
    obj = json.loads(json_sample())
    for name in tuple(obj):
        missing = dict(obj)
        del missing[name]
        with pytest.raises(ValueError):
            producer.from_json(json.dumps(missing))
    with pytest.raises(ValueError):
        producer.from_json(json.dumps({**obj, "proof": "sorry"}))
