import os
from pathlib import Path
import pytest
from .__main__ import execute

def test_real_weight_cooperative_control_replay(tmp_path):
    p=Path(__file__).parents[1]/'evidence/control-v1.json'
    if not p.exists():
        if os.environ.get('PCS_REQUIRE_DISCLOSURE_CAPTURE')=='1':pytest.fail('Real control capture required')
        pytest.skip('Control capture not supplied yet')
    out=Path(os.environ.get('PCS_DISCLOSURE_CONTROL_REPLAY_OUT',str(tmp_path/'replay')))
    r=execute(out,capture=p)
    assert r['replayed'] and r['episodes']==24 and r['requests']==72 and r['ledger_all_ambiguous']
