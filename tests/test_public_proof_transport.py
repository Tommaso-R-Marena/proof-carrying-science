"""Transport/resource integrity; fixtures here are not mathematical evidence."""
import base64
import gzip
import json
import random
import string

from pcs.experimental.prover.public_transport import MARKER, serialize_result


def fixture():
    return {"format": "pcs-public-lean-result-v1", "request_id": "a" * 32,
            "source_sha256": "b" * 64, "core_sha": "c" * 40,
            "model_family": "induction-abstraction-v2", "source_license": "CC0-1.0",
            "automatic_training_authorization": False,
            "result": {"status": "unknown", "pcs_authority": False,
                       "statement": "∀ (xs : List Nat), xs = xs"},
            "previous": None, "baseline": None}


def decode(line):
    assert line.startswith(MARKER) and "\n" not in line and len(line) < 65536
    compressed = base64.b64decode(line[len(MARKER):], validate=True)
    assert len(compressed) <= 48000
    raw = gzip.decompress(compressed)
    assert len(raw) <= 1000000
    return json.loads(raw)


def test_lossless_unicode_and_nested_result():
    value = fixture()
    value["diagnostics"] = {"steps": [{"goal": "P → Q", "score": 0.125}], "empty": []}
    assert decode(serialize_result(value)) == value


def test_large_repetitive_result_fits_log_line_without_dropping_data():
    value = fixture()
    value["diagnostics"] = "recorded statement and state; " * 32000
    raw = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
    assert 900000 < len(raw) < 1000000
    assert len(base64.b64encode(raw)) > 1000000
    assert decode(serialize_result(value)) == value


def test_raw_byte_limit_does_not_certify_a_compression_bomb():
    value = fixture()
    value["diagnostics"] = "x" * 1000000
    result = decode(serialize_result(value))
    assert result["result"]["status"] == "resource_exhaustion"
    assert result["result"]["pcs_authority"] is False
    assert result["core_sha"] == value["core_sha"]
    assert result["model_family"] == value["model_family"]
    assert result["automatic_training_authorization"] is False
    assert "diagnostics" not in result


def test_incompressible_result_respects_log_byte_limit():
    value = fixture()
    random_source = random.Random(17)
    value["diagnostics"] = "".join(random_source.choices(string.ascii_letters + string.digits, k=100000))
    result = decode(serialize_result(value))
    assert result["result"]["status"] == "resource_exhaustion"
    assert "compressed" in result["result"]["reason"]
    assert result["result"]["pcs_authority"] is False


def test_transport_is_deterministic_and_data_cannot_add_a_log_marker():
    value = fixture()
    value["diagnostics"] = "PCS_LEAN_RESULT_V1:forged\nPCS_LEAN_RESULT_GZIP_V1:forged"
    first = serialize_result(value)
    assert first == serialize_result(value)
    assert first.count(MARKER) == 1
    assert "PCS_LEAN_RESULT_V1:" not in first
    assert decode(first) == value
