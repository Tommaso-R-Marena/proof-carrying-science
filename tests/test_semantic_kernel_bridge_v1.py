from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import pytest

from pcs.semantic_kernel_bridge_v1 import canonical_bytes, strict_decode, evaluate, digest

def test_reject_duplicate_keys_and_float():
    with pytest.raises(ValueError):
        strict_decode(b'{"x":1,"x":2}')
    with pytest.raises(ValueError):
        canonical_bytes({"float":1.2})
    with pytest.raises(ValueError):
        canonical_bytes({"float":float("nan")})

def test_canonical_dictionary_is_order_invariant():
    assert canonical_bytes({"b":2,"a":1}) == b'{"a":1,"b":2}'

def setup(tmp_path):
    binary=tmp_path/"checker"
    binary.write_bytes(b"not an actual Lean checker")
    authority=canonical_bytes({"schema":"pcs-semantic-authority-v1"})
    request=canonical_bytes({"schema":"pcs-semantic-translation-v1"})
    kw=dict(binary=binary,binary_sha256=digest(binary.read_bytes()),
            authority_bytes=authority,authority_sha256=digest(authority),request_bytes=request)
    return kw

def test_wrong_binary_digest_fails_closed(tmp_path):
    kw=setup(tmp_path);kw["binary_sha256"]="0"*64
    assert evaluate(**kw)["state"]=="REJECTED"

def test_wrong_authority_digest_fails_closed(tmp_path):
    kw=setup(tmp_path);kw["authority_sha256"]="f"*64
    assert evaluate(**kw)["state"]=="REJECTED"

def test_no_execution_when_claim_mapping_unproved(tmp_path):
    kw=setup(tmp_path)
    kw["claim_ir"]={"format":"pcs-claim-ir-v1","claims":[],"claim_ir_sha256":"bad"}
    assert evaluate(**kw)["state"]=="REJECTED"

def test_noncanonical_json_rejected(tmp_path):
    kw=setup(tmp_path);kw["request_bytes"]=b'{ "schema": "pcs-semantic-translation-v1" }'
    assert evaluate(**kw)["state"]=="REJECTED"

def test_bad_checker_is_never_kernel_proof(tmp_path):
    kw=setup(tmp_path);r=evaluate(**kw)
    assert r["state"]=="REJECTED" and not r["pcs_scientific_authority"]

@pytest.mark.parametrize("val",[b"{}",b"[]",b'{"schema":"unknown"}',b'{"schema":1}'])
def test_unknown_wire_rejected(tmp_path,val):
    kw=setup(tmp_path);kw["request_bytes"]=val
    assert evaluate(**kw)["state"]=="REJECTED"
