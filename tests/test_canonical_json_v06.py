from __future__ import annotations

import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from pcs.canonical_json import (
    CanonicalJSONError,
    canonicalize_jcs,
    canonicalize_jcs_text,
    parse_jcs_json,
)


ROOT = Path(__file__).resolve().parents[1]
VECTORS = json.loads(
    (ROOT / "tests/canonical_json_vectors.json").read_text(encoding="utf-8")
)


def test_frozen_jcs_vectors():
    for vector in VECTORS["vectors"]:
        got = canonicalize_jcs_text(vector["input_json"])
        assert got.decode("utf-8") == vector["canonical"], vector["name"]
        assert hashlib.sha256(got).hexdigest() == vector["sha256"], vector["name"]


_RFC8785_NUMBER_VECTORS = [
    ("0000000000000000", "0"),
    ("8000000000000000", "0"),
    ("0000000000000001", "5e-324"),
    ("8000000000000001", "-5e-324"),
    ("7fefffffffffffff", "1.7976931348623157e+308"),
    ("ffefffffffffffff", "-1.7976931348623157e+308"),
    ("4340000000000000", "9007199254740992"),
    ("c340000000000000", "-9007199254740992"),
    ("4430000000000000", "295147905179352830000"),
    ("44b52d02c7e14af5", "9.999999999999997e+22"),
    ("44b52d02c7e14af6", "1e+23"),
    ("44b52d02c7e14af7", "1.0000000000000001e+23"),
    ("444b1ae4d6e2ef4e", "999999999999999700000"),
    ("444b1ae4d6e2ef4f", "999999999999999900000"),
    ("444b1ae4d6e2ef50", "1e+21"),
    ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"),
    ("3eb0c6f7a0b5ed8d", "0.000001"),
    ("41b3de4355555553", "333333333.3333332"),
    ("41b3de4355555554", "333333333.33333325"),
    ("41b3de4355555555", "333333333.3333333"),
    ("41b3de4355555556", "333333333.3333334"),
    ("41b3de4355555557", "333333333.33333343"),
    ("becbf647612f3696", "-0.0000033333333333333333"),
    ("43143ff3c1cb0959", "1424953923781206.2"),
]


@pytest.mark.parametrize(("bits", "expected"), _RFC8785_NUMBER_VECTORS)
def test_rfc8785_appendix_b_number_serialization(bits: str, expected: str):
    value = struct.unpack(">d", bytes.fromhex(bits))[0]
    assert canonicalize_jcs(value) == expected


def test_duplicate_object_names_rejected():
    with pytest.raises(CanonicalJSONError, match="duplicate JSON object key"):
        parse_jcs_json('{"a":1,"a":2}')


@pytest.mark.parametrize("text", ["NaN", "Infinity", "-Infinity", "1e400"])
def test_non_finite_numbers_rejected(text: str):
    with pytest.raises(CanonicalJSONError):
        canonicalize_jcs_text(text)


def test_lone_surrogate_and_noncharacter_rejected():
    with pytest.raises(CanonicalJSONError):
        canonicalize_jcs("\ud800")
    with pytest.raises(CanonicalJSONError):
        canonicalize_jcs("\ufdd0")


def test_unicode_normalization_is_not_applied():
    assert canonicalize_jcs("é") != canonicalize_jcs("e\u0301")


def test_cross_language_node_vectors_when_node_available():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    proc = subprocess.run(
        [node, str(ROOT / "scripts/check_jcs_cross_language.mjs")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
