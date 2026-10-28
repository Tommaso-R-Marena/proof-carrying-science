"""Actual native Lean/SQL checks; no verifier substitutes or positive mocks."""
from research.live_agent_lab_v3.protocol import standard_plan
from .experiment import run,replay
from .intake import parse


def test_real_control_execution_and_receiving_replay(tmp_path):
    p=standard_plan();p['cases']=[dict(id='control',title='Control',task='Control',pre_sanitized=False,mode='always_publish')]
    frozen=run(None,None,tmp_path/'live',p,mode='trie',progress=lambda _:None)
    assert len(frozen.episodes)==1 and parse(frozen.episodes[0].capture_json)['final']['state']==4
    received=replay(tmp_path/'live',None,tmp_path/'received')
    assert received.sha256==frozen.sha256


def test_real_replay_uses_frozen_bytes_after_submitted_files_change(tmp_path,monkeypatch):
    from . import experiment
    p=standard_plan();p['cases']=[dict(id='control',title='Control',task='Control',pre_sanitized=True,mode='oracle')]
    original=run(None,None,tmp_path/'source',p,mode='raw',progress=lambda _:None)
    prepare=experiment.prepare
    def freeze_then_replace(root,oracle):
        frozen=prepare(root,oracle)
        for path in (root/'suite.json',root/'control/capture.json',root/'control/result.json'):path.write_bytes(b'replaced')
        return frozen
    monkeypatch.setattr(experiment,'prepare',freeze_then_replace)
    result=experiment.replay(tmp_path/'source',None,tmp_path/'received')
    assert result.sha256==original.sha256
    assert (tmp_path/'received/control/capture.json').read_bytes()==original.episodes[0].capture_json
