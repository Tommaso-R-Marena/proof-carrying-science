"""Real process exits, not exceptions standing in for SQLite crash recovery."""
import multiprocessing,os,sqlite3
import pytest
from ..test_ledger import authority
from ..ledger import Ledger

@pytest.mark.parametrize('stage',['after-public-stage','before-commit'])
def test_real_child_exit_rolls_back_uncommitted_public_effect(authority,tmp_path,stage):
    ledger=Ledger(tmp_path/'crash.sqlite',authority,world=3)
    def crash():
        if stage=='before-commit':ledger._commit=lambda _:os._exit(23)
        else:
            original=ledger._dispatch
            def staged(c,g,q,r):original(c,g,q,r);os._exit(23)
            ledger._dispatch=staged
        ledger.query(2,expected_generation=0)
        os._exit(99)
    child=multiprocessing.get_context('fork').Process(target=crash)
    child.start();child.join(30)
    if child.is_alive():child.kill();child.join();pytest.fail('Crash control did not exit')
    assert child.exitcode==23
    assert ledger.audit()['public']==[] and ledger.audit()['generation']==0
    # A fresh real authority reply can still be committed after SQLite recovery.
    assert ledger.query(2,expected_generation=0)['answer']==1


def test_real_child_exit_after_commit_requires_refusing_unanchored_restart(authority,tmp_path):
    path=tmp_path/'committed.sqlite'
    def commit_then_exit():
        ledger=Ledger(path,authority,world=3)
        assert ledger.query(2,expected_generation=0)['accepted']
        os._exit(24)
    child=multiprocessing.get_context('fork').Process(target=commit_then_exit)
    child.start();child.join(30)
    if child.is_alive():child.kill();child.join();pytest.fail('Committed crash control did not exit')
    assert child.exitcode==24
    with sqlite3.connect(path) as c:
        assert c.execute('SELECT generation FROM state').fetchone()==(1,)
        assert c.execute('SELECT query,status,answer FROM public').fetchall()==[(2,1,1)]
    with pytest.raises(ValueError,match='Fresh trusted namespace'):Ledger(path,authority,world=3)
