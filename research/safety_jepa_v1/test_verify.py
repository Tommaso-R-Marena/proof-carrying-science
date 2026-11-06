import hashlib,json
import pytest
from .verify import verify


def test_integrity_census_and_changed_bytes(tmp_path):
    path=tmp_path/'data.txt';path.write_bytes(b'ordinary data, not a proof')
    records={'data.txt':{'size':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}
    (tmp_path/'SHA256.json').write_text(json.dumps({'format':'pcs-safety-jepa-evidence-v1','authority':'NONE','files':records}))
    assert verify(tmp_path)['files_verified']==1
    path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='digest'):verify(tmp_path)


def test_missing_artifact_cannot_pass_integrity_check(tmp_path):
    (tmp_path/'SHA256.json').write_text(json.dumps({'format':'pcs-safety-jepa-evidence-v1','authority':'NONE','files':{'missing':{'size':0,'sha256':'0'*64}}}))
    with pytest.raises(ValueError,match='census'):verify(tmp_path)
