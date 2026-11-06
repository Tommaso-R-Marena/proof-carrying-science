import pytest
from .demo import run


def test_actual_guarded_demo_and_no_overwrite(tmp_path):
    root=tmp_path/'demo';result=run(root,policy='deterministic')
    assert result['task_completed'] and result['unsafe_executions']==0
    assert (root/'synthetic-files/output.txt').exists()
    with pytest.raises(ValueError,match='overwrite'):run(root)


def test_unknown_or_unbound_model_cannot_create_demo(tmp_path):
    root=tmp_path/'missing'
    with pytest.raises(ValueError,match='unknown'):run(root,scenario_id='fake')
    with pytest.raises(ValueError,match='SHA256'):run(root,policy='jepa')
    assert not root.exists()
