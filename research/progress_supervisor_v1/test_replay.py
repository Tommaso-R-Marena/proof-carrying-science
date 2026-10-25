"""Actual process/capture controls; no fake positive verification responses."""
import json,os,sqlite3,subprocess,sys
from pathlib import Path
import pytest
from .__main__ import execute
from .certificate import encode
from .broker import Broker
from .trace import certify_path


def test_actual_capture_and_fresh_process_replay(tmp_path):
    result=execute(tmp_path/'capture');assert result['captured_path_kernel_checked']
    command=[sys.executable,'-m','research.progress_supervisor_v1','replay',str(tmp_path/'capture/capture.json'),str(tmp_path/'replayed')]
    run=subprocess.run(command,text=True,capture_output=True,timeout=300)
    assert run.returncode==0,run.stderr
    assert json.loads(run.stdout)['replayed']
    before=json.loads((tmp_path/'capture/result.json').read_text());after=json.loads((tmp_path/'replayed/result.json').read_text())
    assert before['final']==after['final'];assert before['captured_path_proof']['proof_sha256']==after['captured_path_proof']['proof_sha256']
    assert before['captured_wire_proof']['proof_sha256']==after['captured_wire_proof']['proof_sha256']
    capture=json.loads((tmp_path/'capture/capture.json').read_text());capture['sources']['Progress.lean']='0'*64
    with pytest.raises(ValueError,match='different implementation'):execute(tmp_path/'bad-source',capture=capture)
    capture=json.loads((tmp_path/'capture/capture.json').read_text());capture['samples'][0]['record']['action']=5
    with pytest.raises(ValueError,match='disagrees'):execute(tmp_path/'fake-receipt',capture=capture)


def test_receipt_corruption_effect_substitution_and_unsafe_proof_labels(tmp_path):
    with Broker(tmp_path/'db',tmp_path/'native') as b:
        b.step(b'{"action":0}','one')
        b._db.execute('INSERT INTO public VALUES(?)',('UNAUTHORIZED',))
        with pytest.raises(ValueError,match='effects disagree'):b.snapshot()
        with pytest.raises(ValueError,match='safe fixed proof label'):certify_path(b._authority,[],label='../../outside')


def test_real_process_crash_after_commit_refuses_unanchored_restart(tmp_path):
    db=tmp_path/'crash.sqlite';build=tmp_path/'crash-native'
    code=r'''
import os,sys
from research.progress_supervisor_v1.broker import Broker
b=Broker(sys.argv[1],sys.argv[2]);actual=b._db
class CrashAfterRealCommit:
 def __getattr__(self,n):return getattr(actual,n)
 def execute(self,sql,*args):
  result=actual.execute(sql,*args)
  if sql=='COMMIT':os._exit(73)
  return result
b._db=CrashAfterRealCommit()
b.step(b'{"action":0}','committed-before-crash')
'''
    run=subprocess.run([sys.executable,'-c',code,str(db),str(build)],capture_output=True,timeout=300)
    assert run.returncode==73,run.stderr
    with sqlite3.connect(db) as sql:
        assert sql.execute('SELECT state,generation FROM meta').fetchone()==(1,1)
        assert sql.execute('SELECT COUNT(*) FROM events').fetchone()==(1,)
        assert sql.execute('SELECT COUNT(*) FROM public').fetchone()==(0,)
    with pytest.raises(FileExistsError,match='external restart anchor'):Broker(db,tmp_path/'no-restart')
