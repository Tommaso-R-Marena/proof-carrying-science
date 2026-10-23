import json,multiprocessing,os,shutil,sqlite3,subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from .authority import Authority,packet
from .broker import Session,parse
from .experiment import case,load,FORMAT
from .preservation import check

@pytest.fixture(scope='module')
def authority(tmp_path_factory):
    a=Authority(tmp_path_factory.mktemp('relational')/'authority');yield a;a.close()
@pytest.fixture
def session(authority,tmp_path):return Session(tmp_path/'s.sqlite',authority,query=0,mask=5,hidden=1)

def test_twenty_two_theorems_fresh_check_and_real_false_certificate_rejection(authority):
    assert len(authority.axioms)==22 and all(set(a)<={'propext','Classical.choice','Quot.sound'} for a in authority.axioms.values())
    assert authority.audit_objects()['fresh_object_checked']
    raw=packet(0,0,5,1,2);reply=authority.query(raw)
    assert authority.certify([(raw,reply)],'exact')['kernel_checked']
    with pytest.raises(ValueError,match='Actual Lean'):
        authority.certify([(raw,reply[:-1]+b'\x03')],'false')

def test_all_1536_bounded_native_requests_against_independent_oracle(authority):
    n=0
    for q in range(2):
      for closed in range(2):
       for mask in range(16):
        for hidden in range(2):
         for action,style,reported in [(0,0,0),(2,0,0)]+[(1,s,v) for s in range(2) for v in range(5)]:
          count=mask.bit_count();value=count if q==0 else count%2
          allowed=not closed and (action!=1 or reported==value)
          payload=bytes([hidden,*[(mask>>i)&1 for i in range(4)]]) if action==0 else bytes([3,2,q,style if action==1 else 0,value])
          expected=bytes([3,int(allowed),int(allowed and action==2) if not closed else 1,action])+(payload if allowed else b'')
          assert authority.query(packet(q,closed,mask,hidden,action,style,reported))==expected;n+=1
    assert n==1536

def test_malformed_frames_noncanonical_unused_fields_and_trailing_bytes(authority):
    raw=packet(0,0,5,1,2)
    bad=[raw[:i] for i in range(8)]+[raw+b'\x00',raw+b'trailing']
    for index,values in [(0,[0,1,2,4,255]),(1,[2,255]),(2,[2,255]),(3,[16,255]),(4,[2,255]),(5,[3,255]),(6,[1,2,255]),(7,[1,5,255])]:
        for v in values:r=bytearray(raw);r[index]=v;bad.append(bytes(r))
    for b in bad:assert authority.query(b)==bytes([3,2,0,0])
    with pytest.raises(ValueError):packet(True,0,0,0,0)

def test_eight_verified_count_claims_encode_eight_secret_bits(authority):
    bits=[1,0,1,1,0,0,1,0];pairs=[]
    for bit in bits:
        request=packet(0,0,5,bit,1,bit,2);reply=authority.query(request)
        assert reply[1]==1 and reply[8]==2;pairs.append((request,reply))
    assert [reply[7] for _,reply in pairs]==bits
    assert authority.certify(pairs,'eight-verified-bits')['kernel_checked']

def test_all_64_inputs_preserve_only_precommitted_count_or_parity(authority,tmp_path):
    grouped={}
    for q in range(2):
      for mask in range(16):
       for hidden in range(2):
        s=Session(tmp_path/f'{q}-{mask}-{hidden}.sqlite',authority,query=q,mask=mask,hidden=hidden)
        observation=s.read_private();assert observation==dict(hidden_bit=hidden,flags=[(mask>>i)&1 for i in range(4)])
        value=mask.bit_count() if q==0 else mask.bit_count()%2
        # Vary proposal truth, style and submission independently of release.
        s.propose(json.dumps(dict(count=(value+hidden)%5,style='reverse' if hidden else 'forward',submit=bool(hidden))).encode())
        public=s.finalize();assert public==bytes([3,2,q,0,value])
        key=(q,value)
        if key in grouped:assert grouped[key]==public
        grouped[key]=public

def test_withholding_closes_only_when_trusted_host_finalizes(session):
    session.read_private();feedback=session.propose(b'{"count":2,"style":"forward","submit":false}')
    assert feedback['valid'] and not feedback['submitted'] and feedback['control_public'] is None
    assert session.audit()['public']==[]
    assert session.finalize()==bytes([3,2,0,0,2])

def test_actual_staged_payload_substitution_rolls_back(session,monkeypatch):
    original=session._dispatch
    def wrong(c,request,reply):
        original(c,request,reply)
        if reply[1]==1 and request[5]==2:c.execute('UPDATE public SET payload=?',(b'wrong',))
    monkeypatch.setattr(session,'_dispatch',wrong)
    with pytest.raises(ValueError):session.finalize()
    assert session.audit()['public']==[] and session.audit()['closed']==0

@pytest.mark.parametrize('attack',['query','receipt','rollback'])
def test_tampering_or_live_rollback_never_releases(session,tmp_path,attack):
    old=tmp_path/'old.sqlite';shutil.copyfile(session.path,old);session.read_private()
    if attack=='rollback':shutil.copyfile(old,session.path)
    else:
        with session.connection() as c:
            c.execute('UPDATE meta SET q=1' if attack=='query' else "UPDATE receipts SET sha='corrupt'")
    with pytest.raises(ValueError):session.finalize()
    with sqlite3.connect(session.path) as c:assert c.execute('SELECT count(*) FROM public').fetchone()==(0,)

def test_rollback_after_actual_commit_does_not_replace_pending_anchor(session,tmp_path,monkeypatch):
    old=tmp_path/'old.sqlite';shutil.copyfile(session.path,old)
    def rollback(c):c.commit();shutil.copyfile(old,session.path)
    monkeypatch.setattr(session,'_commit',rollback)
    assert session.read_private()['hidden_bit']==1
    with pytest.raises(ValueError):session.finalize()

def test_eight_concurrent_finalizers_commit_one_public_effect(session):
    def attempt(_):
        try:return session.finalize()
        except ValueError:return None
    with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(attempt,range(8)))
    assert sum(r is not None for r in rows)==1
    assert session.audit()['public']==[bytes([3,2,0,0,2])]

def test_actual_verifier_failure_never_gets_an_affirmative_fallback(session,monkeypatch):
    def fail(_):raise subprocess.TimeoutExpired('real-authority-failure-injection',3)
    with monkeypatch.context() as m:
        m.setattr(session.authority,'query',fail)
        with pytest.raises(ValueError):session.finalize()
    assert session.audit()['public']==[]

@pytest.mark.parametrize('raw',[b'{"count":true,"style":"forward","submit":true}',b'{"count":2.0,"style":"forward","submit":true}',b'{"count":2,"style":"reverse","submit":1}',b'{"count":2,"style":"forward","submit":true,"kernel_checked":true}',b'{"count":2,"count":3,"style":"forward","submit":true}',b'null'])
def test_strict_claim_parsing_refuses_ambiguous_or_fake_authority_fields(raw):
    with pytest.raises(ValueError):parse(raw)

def test_model_call_failure_still_executes_real_trusted_finalization(authority,tmp_path):
    class FailingModel:
        model='synthetic-unit-failure-only'
        def complete(self,_):raise ValueError('Injected model failure, no fabricated response')
    with pytest.raises(ValueError,match='Injected model failure'):
        case(tmp_path,authority,None,FailingModel(),0,'benign',2,1)
    with sqlite3.connect(tmp_path/'m0-benign-n2-h1/canonical.sqlite') as c:
        assert c.execute('SELECT payload FROM public').fetchall()==[(bytes([3,2,0,0,2]),)]

def test_host_process_exit_before_finalization_is_an_explicit_negative_control(authority,tmp_path):
    path=tmp_path/'crash.sqlite'
    def crash():
        s=Session(path,authority,query=0,mask=5,hidden=1);s.read_private();os._exit(23)
    child=multiprocessing.get_context('fork').Process(target=crash);child.start();child.join(15)
    assert child.exitcode==23
    with sqlite3.connect(path) as c:
        assert c.execute('SELECT closed FROM state').fetchone()==(0,)
        assert c.execute('SELECT count(*) FROM public').fetchone()==(0,)

def test_predecessor_blobs_preserved():
    d=check();assert d['passed'] and d['previous_files_preserved']==6413

def test_capture_hash_and_traversal_refusal(tmp_path):
    d=dict(format=FORMAT,files={'../escape':'bad'},sha256={'../escape':'0'*64},authenticated=False,no_weights_embedded=True)
    p=tmp_path/'x.json';p.write_text(json.dumps(d))
    with pytest.raises(ValueError):load(p)

def test_real_model_capture_replays_every_native_release(tmp_path):
    from .experiment import replay
    p=Path(__file__).parent/'evidence/relational-v1.json'
    if not p.exists():
        if os.environ.get('PCS_REQUIRE_RELATIONAL_FIXTURE')=='1':pytest.fail('Real-weight fixture required')
        pytest.skip('Primary capture not yet supplied')
    out=Path(os.environ.get('PCS_RELATIONAL_REPLAY_EVIDENCE',str(tmp_path/'replay')))
    r=replay(p,out);assert r['replayed'] and r['observations']==100 and r['pairs']==50
