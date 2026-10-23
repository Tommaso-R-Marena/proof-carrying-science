import os
from pathlib import Path
import pytest
from .__main__ import execute

def test_fresh_engine_reverse_order_capture_replays(tmp_path):
    p=Path(__file__).parents[1]/'evidence/fresh-pairs-v1.json'
    if not p.exists():
        if os.environ.get('PCS_REQUIRE_RELATIONAL_FIXTURE')=='1':pytest.fail('Actual fresh-engine supplementary capture required')
        pytest.skip('Supplementary capture not yet supplied')
    out=Path(os.environ.get('PCS_RELATIONAL_FRESH_REPLAY_EVIDENCE',str(tmp_path/'replay')))
    d=execute(out,capture=p)
    assert d['complete'] and d['replayed'] and d['requests']==10 and d['canonical_utility']==10
