"""Real-authority regressions for rollback of an active broker database."""
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from research.llm_firewall_v1.protocol import proposal
from ..authority import Authority
from ..broker import Session as BaseSession
from . import Session


@pytest.fixture(scope='module')
def authority(tmp_path_factory):
    a=Authority(tmp_path_factory.mktemp('live-checkpoint')/'authority')
    yield a
    a.close()


def act(s,a,text='',generation=None):
    return s.apply(proposal(a,text),expected_generation=s.state()[0] if generation is None else generation)


def snapshot(s,path):
    shutil.copyfile(s.path,path)
    return path


def test_real_active_database_rollback_counterexample_and_guard(authority,tmp_path):
    for cls,name in [(BaseSession,'unanchored'),(Session,'retained')]:
        s=cls(tmp_path/(name+'.sqlite'),authority,private='PCS_SYNTHETIC_ROLLBACK')
        old=snapshot(s,tmp_path/(name+'-old.sqlite'))
        read=act(s,1);assert read['accepted']
        shutil.copyfile(old,s.path)
        # A correctly retained generation refuses in both implementations.
        assert not act(s,3,read['result'],generation=1)['accepted']
        # Trusting the rolled-back DB generation permits an actual leak in the
        # frozen baseline. The retained-prefix wrapper still refuses it.
        r=act(s,3,read['result'],generation=0)
        assert r['accepted']==(cls is BaseSession)
        if cls is Session:
            with pytest.raises(ValueError,match='rolled back or forked'):s.audit()
            with sqlite3.connect(s.path) as c:assert c.execute('SELECT count(*) FROM effects').fetchone()==(0,)
        else:assert s.effects()==[(2,b'PCS_SYNTHETIC_ROLLBACK')]


def test_denied_receipt_rollback_is_detected_even_without_generation_change(authority,tmp_path):
    s=Session(tmp_path/'s.sqlite',authority);old=snapshot(s,tmp_path/'old.sqlite')
    r=act(s,6,'SYNTHETIC');assert r['status']=='BLOCKED' and s.state()==(0,8,0)
    shutil.copyfile(old,s.path)
    assert act(s,3,'PUBLIC',generation=0)['status']=='REFUSED'
    with pytest.raises(ValueError,match='rolled back or forked'):s.checkpoint()


def test_failed_private_transaction_does_not_advance_live_anchor(authority,tmp_path):
    s=Session(tmp_path/'s.sqlite',authority);before=s.checkpoint()
    with s.connection() as c:c.execute("CREATE TRIGGER stop_private BEFORE UPDATE ON state BEGIN SELECT RAISE(ABORT,'synthetic'); END")
    r=act(s,1,generation=0)
    assert not r['accepted'] and 'PCS_SYNTHETIC_CANARY' not in str(r)
    assert s.checkpoint()==before
    with s.connection() as c:c.execute('DROP TRIGGER stop_private')
    assert act(s,3,'PUBLIC')['accepted']
    assert act(s,1)['accepted']
    assert not act(s,3,'PRIVATE')['accepted']


def test_concurrent_compare_and_swap_and_checkpoint_reopen(authority,tmp_path):
    s=Session(tmp_path/'s.sqlite',authority)
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows=list(pool.map(lambda i:act(s,3,str(i),generation=0),range(8)))
    assert sum(r['accepted'] for r in rows)==1
    checkpoint=s.checkpoint();r=Session.reopen(s.path,authority,checkpoint)
    assert r.checkpoint()==checkpoint
    assert act(r,2,'PRIVATE')['accepted']
    # A separately opened writer can append a valid descendant. Observation
    # advances s's retained prefix, after which rollback to checkpoint refuses.
    assert s.state()[0]==2
    assert act(s,0)['accepted']


def test_rollback_both_storage_and_external_checkpoint_remains_a_negative_control(authority,tmp_path):
    s=Session(tmp_path/'s.sqlite',authority);old=snapshot(s,tmp_path/'old.sqlite');initial=s.checkpoint()
    assert act(s,1)['accepted'];new=s.checkpoint()
    shutil.copyfile(old,s.path)
    with pytest.raises(ValueError):Session.reopen(s.path,authority,new)
    old_root=Session.reopen(s.path,authority,initial)
    assert act(old_root,3,'OLD_ROOT')['accepted']


def test_descendant_observation_prevents_later_rollback(authority,tmp_path):
    s=Session(tmp_path/'s.sqlite',authority);old=snapshot(s,tmp_path/'old.sqlite')
    other=Session.reopen(s.path,authority,s.checkpoint())
    assert act(other,1)['accepted']
    assert s.state()==(1,7,1)
    shutil.copyfile(old,s.path)
    assert act(s,3,'SYNTHETIC',generation=0)['status']=='REFUSED'


def test_rollback_after_real_commit_cannot_replace_the_pending_memory_anchor(authority,tmp_path,monkeypatch):
    s=Session(tmp_path/'s.sqlite',authority);old=snapshot(s,tmp_path/'old.sqlite')
    actual_apply=BaseSession.apply
    def rollback_after_actual_commit(self,raw,*,expected_generation):
        result=actual_apply(self,raw,expected_generation=expected_generation)
        assert result['accepted'] and result['action']==1
        shutil.copyfile(old,self.path)
        return result
    with monkeypatch.context() as m:
        m.setattr(BaseSession,'apply',rollback_after_actual_commit)
        read=act(s,1,generation=0)
    assert read['accepted'] and read['result']=='PCS_SYNTHETIC_CANARY'
    # The private-read receipt was captured while staged, rather than adopting
    # the attacker-restored database after the real commit returned.
    assert act(s,3,read['result'],generation=0)['status']=='REFUSED'
