import json,shutil,sqlite3,subprocess
from concurrent.futures import ThreadPoolExecutor
import pytest
from .authority import Authority,packet
from .ledger import Ledger,INITIAL,parse
from .oracle import worlds,encode,answer,ambiguous,safe,step,exhaustive

@pytest.fixture(scope='module')
def authority(tmp_path_factory):
    a=Authority(tmp_path_factory.mktemp('composition')/'authority')
    yield a
    a.close()
@pytest.fixture
def ledger(tmp_path,authority):return Ledger(tmp_path/'ledger.sqlite',authority,world=3)

def test_kernel_audit_and_reject_false_native_certificate(authority):
    assert len(authority.axioms)==22
    assert all(set(v)<={'propext','Classical.choice','Quot.sound'} for v in authority.axioms.values())
    assert authority.audit_objects()['fresh_object_checked']
    r=packet(INITIAL,3,2);v=authority.query(r)
    assert authority.certify([(r,v)],'true')['kernel_checked']
    with pytest.raises(ValueError,match='Actual Lean'):authority.certify([(r,v[:-1]+b'\x00')],'false')

def test_exhaustive_every_reachable_native_transition_and_composition_attack(authority,tmp_path):
    transitions,d=exhaustive(tmp_path/'exhaustive.json')
    assert d['reachable_states']==7 and d['transitions']==384 and d['composition_attacks']==36
    requests=b''.join(packet(k,w,q) for k,w,q,t,a in transitions)
    replies=authority.query(requests)
    for i,(k,w,q,t,a) in enumerate(transitions):
        assert replies[5*i:5*i+5]==bytes((4,int(a is not None),t%256,t//256,255 if a is None else a))
    for i in range(0,len(transitions),32):
        pairs=[(packet(k,w,q),replies[j*5:j*5+5]) for j,(k,w,q,t,a) in enumerate(transitions[i:i+32],i)]
        assert authority.certify(pairs,f'exhaustive-{i}')['kernel_checked']

def test_all_65536_prior_encodings_native_decode_encode_and_private_validity(authority):
    # q=0 is constant, hence preserves exactly every valid ambiguous prior.
    for base in range(0,65536,4096):
        rs=[];expected=[]
        for k in range(base,base+4096):
            s=worlds(k);w=min(s) if s else 0;rs.append(packet(k,w,0))
            expected.append(bytes((4,1,k%256,k//256,0)) if ambiguous(s) else bytes((4,2,0,0,255)))
        assert authority.query(b''.join(rs))==b''.join(expected)

def test_all_queries_all_full_domain_actual_worlds_against_set_oracle(authority):
    pairs=[];expected=[]
    for w in range(16):
      for q in range(16):
        s,a=step(set(range(16)),w,q);k=encode(s)
        pairs.append(packet(65535,w,q));expected.append(bytes((4,int(a is not None),k%256,k//256,255 if a is None else a)))
    assert authority.query(b''.join(pairs))==b''.join(expected)

def test_actual_shared_ledger_blocks_cross_caller_composition(ledger):
    # Three callers share the same dataset ledger, rather than resetting its prior.
    r=[ledger.query(q,expected_generation=i) for i,q in enumerate((2,4,8))]
    assert [v['answer'] for v in r]==[1,None,None]
    assert ledger.audit()['candidates']==encode({3,6,10})
    assert ledger.certify('shared-callers')['kernel_checked']

def test_unsafe_actual_cell_only_gate_would_leak_denial(authority):
    # q=6 has both safe and unsafe answer cells. Only checking actual cell leaks.
    prior=worlds(INITIAL)
    cells={answer(6,w):{x for x in prior if answer(6,x)==answer(6,w)} for w in prior}
    assert any(ambiguous(s) for s in cells.values()) and any(not ambiguous(s) for s in cells.values())
    assert all(authority.query(packet(INITIAL,w,6))[1]==0 for w in prior)

@pytest.mark.parametrize('attack',['state','public','receipt','contract','rollback'])
def test_tamper_and_live_rollback_fail_closed(ledger,tmp_path,attack):
    old=tmp_path/'old.sqlite';shutil.copyfile(ledger.path,old)
    ledger.query(2,expected_generation=0)
    if attack=='rollback':shutil.copyfile(old,ledger.path)
    else:
        with ledger.connection() as c:
            c.execute({'state':'UPDATE state SET candidates=65535','public':'UPDATE public SET answer=0','receipt':"UPDATE receipts SET sha='fake'",'contract':'UPDATE contract SET world=5'}[attack])
    with pytest.raises(ValueError):ledger.query(4,expected_generation=1)

def test_staged_substitution_rolls_back(ledger,monkeypatch):
    orig=ledger._dispatch
    def wrong(c,g,q,r):orig(c,g,q,r);c.execute('UPDATE public SET answer=99')
    monkeypatch.setattr(ledger,'_dispatch',wrong)
    with pytest.raises(ValueError):ledger.query(2,expected_generation=0)
    assert ledger.audit()['public']==[]

def test_real_verifier_failure_never_gets_positive_fallback(ledger,monkeypatch):
    def fail(_):raise subprocess.TimeoutExpired('actual failure injection',3)
    with monkeypatch.context() as m:
        m.setattr(ledger.authority,'query',fail)
        with pytest.raises(subprocess.TimeoutExpired):ledger.query(2,expected_generation=0)
    assert ledger.audit()['public']==[]

def test_concurrent_generation_cas_accepts_exactly_one(ledger):
    def apply(q):
        try:return ledger.query(q,expected_generation=0)
        except ValueError:return None
    with ThreadPoolExecutor(max_workers=8) as pool:r=list(pool.map(apply,[2,4,8,2,4,8,2,4]))
    assert sum(x is not None for x in r)==1 and ledger.audit()['generation']==1

def test_stale_generation_rejected_without_extra_disclosure(ledger):
    ledger.query(2,expected_generation=0)
    with pytest.raises(ValueError):ledger.query(4,expected_generation=0)
    assert ledger.audit()['generation']==1

def test_crash_before_commit_rolls_back(ledger,monkeypatch):
    def crash(_):raise OSError('injected crash before transaction commitment')
    monkeypatch.setattr(ledger,'_commit',crash)
    with pytest.raises(OSError):ledger.query(2,expected_generation=0)
    assert ledger.audit()['public']==[]

def test_host_namespace_reset_is_a_negative_control(authority,tmp_path):
    # A malicious host can evade a ledger by creating independent namespaces.
    # This is an explicit trust limitation, not an approved client interface.
    answers=[]
    for i,q in enumerate((2,4,8)):
        s=Ledger(tmp_path/f'reset-{i}.sqlite',authority,world=3)
        answers.append(s.query(q,expected_generation=0)['answer'])
    assert answers==[1,0,0]
    assert {w for w in worlds(INITIAL) if [answer(q,w) for q in (2,4,8)]==answers}=={3}

@pytest.mark.parametrize('raw',[b'{"query":true}',b'{"query":2.0}',b'{"query":2,"query":4}',b'{"query":2,"verified":true}',b'{"query":16}',b'null',b'\xff',b'{"query":-1}'])
def test_strict_public_proposal_parser(raw):
    with pytest.raises((ValueError,UnicodeError)):parse(raw)

def test_invalid_priors_actual_not_present_and_noncanonical_frames(authority,tmp_path):
    for k,w in [(0,0),(1,0),(2,0),(INITIAL,0)]:
        with pytest.raises(ValueError):Ledger(tmp_path/f'invalid-{k}-{w}.sqlite',authority,world=w,prior=k)
    r=packet(INITIAL,3,2)
    for n in range(1,5):assert authority.query(r[:n])==bytes((4,2,0,0,255))
    for index,values in [(0,[0,1,3,5,255]),(3,[16,255]),(4,[16,255])]:
        for value in values:
            b=bytearray(r);b[index]=value;assert authority.query(bytes(b))==bytes((4,2,0,0,255))
    with pytest.raises(ValueError):packet(True,3,2)

def test_commit_then_storage_rollback_keeps_pending_live_anchor(ledger,tmp_path,monkeypatch):
    old=tmp_path/'precommit.sqlite';shutil.copyfile(ledger.path,old)
    def rollback(c):c.commit();shutil.copyfile(old,ledger.path)
    monkeypatch.setattr(ledger,'_commit',rollback)
    assert ledger.query(2,expected_generation=0)['accepted']
    with pytest.raises(ValueError):ledger.query(4,expected_generation=1)

def test_missing_database_does_not_recreate_an_empty_prior(ledger):
    ledger.path.unlink()
    with pytest.raises(sqlite3.OperationalError):ledger.query(2,expected_generation=0)
    assert not ledger.path.exists()

def test_no_unanchored_restart_or_caller_verifier_substitution(authority,tmp_path):
    p=tmp_path/'fixed.sqlite';Ledger(p,authority,world=3)
    with pytest.raises(ValueError):Ledger(p,authority,world=3)
    with pytest.raises(ValueError):Ledger(tmp_path/'fake.sqlite',object(),world=3)

def test_predecessor_blobs_preserved():
    from .preservation import check
    assert check()['previous_files_preserved']==6431

def test_actual_weight_capture_replay(tmp_path):
    import os
    from pathlib import Path
    from .experiment import replay
    p=Path(__file__).parent/'evidence/adaptive-v1.json'
    if not p.exists():
        if os.environ.get('PCS_REQUIRE_DISCLOSURE_CAPTURE')=='1':pytest.fail('Real-weight fixture required')
        pytest.skip('Registered real-weight capture not supplied yet')
    out=Path(os.environ.get('PCS_DISCLOSURE_REPLAY_OUT',str(tmp_path/'replay')))
    r=replay(p,out)
    assert r['replayed'] and r['episodes']==24 and r['requests']==96 and r['ledger_all_ambiguous']
