"""Hash/parser checks are not claimed to validate any Lean authorization."""
import gzip
import hashlib
import json
import pytest
from .replay import verify_manifest, read_json


def manifest(root,name,raw):
    (root/'SHA256.json').write_text(json.dumps({'format':'pcs-proof-jepa-evidence-v1','authority':'NONE',
      'files':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw)}}}))


def test_hash_integrity_detects_mutation(tmp_path):
    p=tmp_path/'fixture.txt';p.write_bytes(b'not a proof')
    manifest(tmp_path,p.name,p.read_bytes())
    assert verify_manifest(tmp_path)['authority']=='NONE'
    p.write_bytes(b'changed')
    with pytest.raises(ValueError,match='mismatch'):verify_manifest(tmp_path)


def test_manifest_rejects_parent_escape(tmp_path):
    manifest(tmp_path,'../outside',b'')
    with pytest.raises(ValueError,match='path'):verify_manifest(tmp_path)


def test_archive_rejects_duplicate_keys(tmp_path):
    p=tmp_path/'bad.json.gz';p.write_bytes(gzip.compress(b'{"x":1,"x":2}'))
    with pytest.raises(ValueError,match='duplicate'):read_json(p)


def test_archive_enforces_decoded_bound(tmp_path):
    from .replay import LIMIT
    p=tmp_path/'large.json.gz';p.write_bytes(gzip.compress(b' '*(LIMIT+1)))
    with pytest.raises(ValueError,match='decoded artifact exceeds'):read_json(p)
