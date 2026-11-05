from pcs_next_v1.core.canonical import canonicalize, canonical_hash, loads_strict, CanonicalError
import pytest

def test_key_order_utf16():
    a = canonicalize({"b": 1, "a": 2})
    assert a == b'{"a":2,"b":1}'

def test_reject_nan():
    with pytest.raises(CanonicalError):
        canonicalize(float("nan"))

def test_duplicate_keys():
    with pytest.raises(CanonicalError):
        loads_strict('{"a":1,"a":2}')

def test_hash_stable():
    assert canonical_hash({"x": [1, 2]}) == canonical_hash({"x": [1, 2]})
