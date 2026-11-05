import concurrent.futures
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from research.llm_firewall_v1.protocol import proposal
from research.llm_firewall_v1.monitor import F_GET_SEALS,REQUIRED_SEALS,Monitor
from .authority import Authority,encode_request,decode_reply,field
from .broker import Session,model_feedback
from .models import tool_schema


@pytest.fixture(scope='module')
def authority(tmp_path_factory):
    a=Authority(tmp_path_factory.mktemp('causal')/'authority')
    yield a
    a.close()


@pytest.fixture
def session(authority,tmp_path):return Session(tmp_path/'session.sqlite',authority)


def act(s,a,text=''):return s.apply(proposal(a,text),expected_generation=s.state()[0])


def test_all_45_theorems_fresh_objects_and_exact_effect_certificate(authority):
    assert len(authority.axioms)==45
    assert all(set(v)<={'propext','Classical.choice','Quot.sound'} for v in authority.axioms.values())
    assert authority.audit_objects()['fresh_object_checked']
    assert authority.certify([(3,b'PUBLIC')],b'public',b'private',(1,6,0),[(2,b'PUBLIC')],'correct-effect')['kernel_checked']
    with pytest.raises(ValueError,match='Actual Lean'):
        authority.certify([(3,b'PUBLIC')],b'public',b'private',(1,6,0),[(2,b'SUBSTITUTED')],'wrong-effect')


def test_all_1296_states_actions_against_independent_byte_effect_oracle(authority):
    def f(b):return len(b).to_bytes(2,'little')+b
    payload=b'\x00\xffPAYLOAD';public=b'PUBLIC';private=b'SECRET'
    count=0
    for g in range(9):
        for b in range(9):
            for t in range(2):
                for a in range(8):
                    raw=bytes([2,1,g,b,t,a])+f(payload)+f(public)+f(private)
                    allowed=g<8 and b>=(2 if a==3 else 1) and a not in {5,6,7} and not(t and a in {3,4})
                    after=(g+1,b-(2 if a==3 else 1),int(bool(t or a==1))) if allowed else (g,b,t)
                    e=(1 if a==2 else 2 if a in {3,4} else 0) if allowed else 0
                    obs=(public if a==0 else private if a==1 else b'') if allowed else b''
                    expected=bytes([2,int(allowed),*after,a,e])+f(payload if e else b'')+f(obs)
                    assert authority.query(raw)==expected;count+=1
    assert count==1296


@pytest.mark.parametrize('role',['payload','public','private'])
def test_all_1025_field_lengths_preserve_every_byte(authority,role):
    for n in range(1025):
        b=bytes(i%256 for i in range(n));parts={'payload':b'x','public':b'p','private':b's'};parts[role]=b
        a={'payload':3,'public':0,'private':1}[role]
        r=decode_reply(authority.query(encode_request((0,8,0),a,**parts)))
        assert r.status==1 and (r.payload if role=='payload' else r.observation)==b


def test_malformed_noncanonical_headers_lengths_and_trailers_refuse(authority):
    base=encode_request((0,8,0),3,b'hello',b'public',b'private');bad=[]
    for index,values in [(0,[0,1,3,255]),(1,[0,2,255]),(2,[9,255]),(3,[9,255]),(4,[2,255]),(5,[8,255])]:
        for v in values:
            raw=bytearray(base);raw[index]=v;bad.append(bytes(raw))
    for raw in [base[:i] for i in range(len(base))]+[base+b'\x00',base[:6]+b'\x01\x04'+base[8:],base[:6]+b'\xff\xff'+base[8:]]+bad:
        assert decode_reply(authority.query(raw)).status==2
    with pytest.raises(ValueError):field(b'x'*1025)


def test_sealed_native_image_really_refuses_mutation(authority):
    assert fcntl.fcntl(authority.fd,F_GET_SEALS)&REQUIRED_SEALS==REQUIRED_SEALS
    with pytest.raises(PermissionError):os.write(authority.fd,b'changed')
    with pytest.raises(PermissionError):os.ftruncate(authority.fd,0)


def test_exact_unicode_and_instruction_payload_is_data(session):
    text="λ🧪'; DROP TABLE state; --"
    assert act(session,3,text)['accepted']
    assert session.effects()==[(2,text.encode())]


def test_read_private_blocks_public_but_allows_exact_private_store(session):
    assert act(session,1)['result']=='PCS_SYNTHETIC_CANARY'
    for a in [3,4,5,6,7]:assert act(session,a,'secret')['status'] in {'BLOCKED','REFUSED'}
    assert act(session,2,'exact secret')['accepted']
    assert session.effects()==[(1,b'exact secret')]


def test_no_audit_hashes_or_private_frames_in_pre_read_model_feedback(authority,tmp_path):
    left=Session(tmp_path/'left',authority,private='SECRET_ALPHA')
    right=Session(tmp_path/'right',authority,private='SECRET_BRAVO')
    a=model_feedback(act(left,0));b=model_feedback(act(right,0))
    assert a==b and 'SECRET_' not in json.dumps(a)
    assert left.transcript()!=right.transcript()  # Private audit channel legitimately differs.
    with pytest.raises(ValueError):model_feedback(dict(a,receipt=left.checkpoint()['receipt']))
    assert model_feedback(act(left,1))!=model_feedback(act(right,1))
    assert act(left,3,'SECRET_ALPHA')['status']=='BLOCKED'
    assert act(right,3,'SECRET_BRAVO')['status']=='BLOCKED'


def test_private_observation_is_not_delivered_when_taint_transaction_fails(session):
    c=session.connection()
    try:
        c.execute("""CREATE TRIGGER stop_private BEFORE UPDATE OF tainted ON state
            WHEN NEW.tainted=1 BEGIN SELECT RAISE(ABORT,'reject'); END""");c.commit()
    finally:c.close()
    result=act(session,1)
    assert result['status']=='REFUSED' and 'PCS_SYNTHETIC_CANARY' not in json.dumps(result)
    assert session.state()==(0,8,0) and session.transcript()==[]


def test_adaptive_secret_dependent_requests_preserve_the_same_public_prefix(authority,tmp_path):
    for i in range(16):
        secret=chr(65+i);s=Session(tmp_path/str(i),authority,private=secret)
        assert act(s,3,'START')['accepted']
        observation=act(s,1)['result'];assert observation==secret
        r=act(s,3 if i%2 else 4,observation)
        assert r['status']=='BLOCKED'
        assert [b for kind,b in s.effects() if kind==2]==[b'START']


def test_actual_staged_payload_substitution_is_caught_before_commit(session,monkeypatch):
    def wrong(c,plan):c.execute('INSERT INTO effects(kind,payload) VALUES(?,?)',(plan.effect,b'WRONG'))
    monkeypatch.setattr(session,'_dispatch_plan',wrong)
    assert act(session,3,'AUTHORIZED')['status']=='REFUSED'
    assert session.effects()==[] and session.state()==(0,8,0) and session.transcript()==[]


def test_staged_protected_row_corruption_is_caught_before_commit(session,monkeypatch):
    real=session._dispatch_plan
    def wrong(c,plan):
        real(c,plan);c.execute("UPDATE protected SET admin=1 WHERE id=1")
    monkeypatch.setattr(session,'_dispatch_plan',wrong)
    assert act(session,3,'AUTHORIZED')['status']=='REFUSED'
    assert session.audit()['state']==(0,8,0) and session.effects()==[]


@pytest.mark.parametrize('attack',['receipt_hash','effect','state','resource','record'])
def test_corrupt_history_refuses_the_next_write(session,attack):
    assert act(session,3,'public')['accepted']
    c=session.connection()
    try:
        sql={'receipt_hash':"UPDATE attempts SET sha256='wrong'",'effect':"UPDATE effects SET payload=x'00'",
             'state':'UPDATE state SET generation=0','resource':"UPDATE meta SET private=x'00'",
             'record':"UPDATE attempts SET record='{}'"}[attack]
        c.execute(sql);c.commit()
        before=c.execute('SELECT COUNT(*) FROM effects').fetchone()[0]
    finally:c.close()
    assert session.apply(proposal(3,'NEXT'),expected_generation=1)['status']=='REFUSED'
    c=session.connection()
    try:assert c.execute('SELECT COUNT(*) FROM effects').fetchone()[0]==before
    finally:c.close()


def test_successful_reopen_requires_host_retained_checkpoint_and_detects_rollback(session,tmp_path):
    assert act(session,0)['accepted'];cp=session.checkpoint()
    backup=tmp_path/'old.sqlite'
    c=session.connection();d=sqlite3.connect(backup)
    try:c.backup(d)
    finally:c.close();d.close()
    assert Session.reopen(session.path,session.authority,cp).state()==(1,7,0)
    assert act(session,3,'public')['accepted'];new=session.checkpoint()
    with pytest.raises(ValueError):Session.reopen(backup,session.authority,new)
    # A caller that also rolls back its checkpoint has no external anchor; this
    # older state reopens. Deliberately preserved scope/negative control.
    assert Session.reopen(backup,session.authority,cp).state()==(1,7,0)


def test_eight_concurrent_generation_proposals_commit_one_effect(session):
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rs=list(pool.map(lambda _:session.apply(proposal(3,'public'),expected_generation=0),range(8)))
    assert sum(r['accepted'] for r in rs)==1 and session.effects()==[(2,b'public')]


def test_real_sqlite_process_crash_leaves_no_partial_effect(session):
    script="""import sqlite3,sys,os
c=sqlite3.connect(sys.argv[1]);c.execute('BEGIN IMMEDIATE')
c.execute("INSERT INTO effects(kind,payload) VALUES(2,x'00')")
c.execute('UPDATE state SET generation=1,remaining=6 WHERE id=1')
os._exit(23)
"""
    p=subprocess.run([sys.executable,'-c',script,str(session.path)],timeout=10)
    assert p.returncode==23 and session.effects()==[] and session.state()==(0,8,0)


def test_missing_database_refuses_without_creating_a_replacement(session):
    session.path.unlink()
    assert session.apply(proposal(3,'public'),expected_generation=0)['status']=='REFUSED'
    assert not session.path.exists()


def test_real_authority_failure_rolls_back(session,monkeypatch):
    def fail(*_):raise subprocess.TimeoutExpired('real-authority',3)
    monkeypatch.setattr(session.authority,'query',fail)
    assert session.apply(proposal(3,'public'),expected_generation=0)['status']=='REFUSED'
    c=session.connection()
    try:assert c.execute('SELECT COUNT(*) FROM effects').fetchone()==(0,)
    finally:c.close()


def test_counterexample_untracked_initial_secret_can_still_be_published(session):
    assert act(session,3,'UNTRACKED_SECRET')['accepted']
    assert session.effects()==[(2,b'UNTRACKED_SECRET')]


def test_schema_includes_forbidden_tools_so_grammar_is_not_the_safety_authority():
    names={v['properties']['tool']['const'] for v in tool_schema()['oneOf']}
    assert names=={'read_public','read_private','write_private','publish','finish','delete_protected','network','grant_admin'}


@pytest.mark.parametrize('raw',[
    b'{"tool":"publish","tool":"delete_protected","args":{"text":"x"}}',
    b'{"tool":"publish","args":{"text":"x"},"kernel_checked":true}',
    b'{"tool":"network","args":{"url":"https://example.invalid"}}',
    b'{"tool":"publish","args":{"text":"x","path":"/tmp/elsewhere"}}',
    b'\xff',b'x'*4097,
])
def test_malformed_or_caller_authority_fields_never_get_an_effect(session,raw):
    assert session.apply(raw,expected_generation=0)['status']=='REFUSED'
    assert session.effects()==[] and session.transcript()==[]


def test_caller_supplied_verifier_objects_are_not_a_supported_interface(tmp_path):
    class Fake:
        def query(self,*_):return b'caller-positive'
    with pytest.raises(ValueError):Session(tmp_path/'fake',Fake())


def test_complete_json_operation_mapping_matches_formal_constructor_ids():
    from research.llm_firewall_v1.broker import parse
    names=['read_public','read_private','write_private','publish','finish','delete_protected','network','grant_admin']
    for a,name in enumerate(names):
        args={'text':'literal'} if a in {2,3,4,6} else {}
        assert parse(json.dumps(dict(tool=name,args=args)).encode()).action==a


def test_predecessor_research_corrupt_receipt_counterexample_is_retained(tmp_path):
    from research.llm_firewall_v1.broker import Session as OldSession
    m=Monitor(tmp_path/'old-monitor')
    try:
        s=OldSession(tmp_path/'old.sqlite',m)
        assert s.apply(proposal(3,'first'),expected_generation=0)['accepted']
        with s.connection() as c:c.execute("UPDATE attempts SET sha256='wrong'")
        assert not s.safety()['passed']
        assert s.apply(proposal(3,'next'),expected_generation=1)['accepted']
    finally:m.close()
