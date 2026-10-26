from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import fcntl,json,os,sqlite3,subprocess
from pathlib import Path
import pytest
from pcs.action_shield_v1 import evaluate as safety_evaluate,propose as safety_propose
from .certificate import encode,propose,evaluate,load_certificate,brute_force_bounds
from .example import model
from .authority import Authority,packet,SEALS,PROGRESS,WIRE,CODEC,DATA
from .broker import Broker,PRIVATE,PUBLIC


def test_exhaustive_two_state_games_against_independent_policy_enumeration():
    cases=0
    triples=[(s,a,t) for s in range(2) for a in range(2) for t in range(2)]
    for edge_mask in range(1,256):
      for safe_mask in range(1,4):
       safe=[s for s in range(2) if safe_mask&(1<<s)]
       for goal_mask in range(4):
        goals=[s for s in range(2) if goal_mask&(1<<s)]
        if not set(goals)<=set(safe):continue
        for forbidden_mask in range(4):
            m=model();m.update(states=[0,1],actions=[0,1],initial=[0],safe=safe,forbidden=[a for a in range(2) if forbidden_mask&(1<<a)],transitions=[dict(source=s,action=a,target=t) for i,(s,a,t) in enumerate(triples) if edge_mask&(1<<i)])
            raw=encode(m);c=propose(raw,goals);assert dict(c['ranks'])==brute_force_bounds(raw,goals)
            assert evaluate(raw,encode(c))['valid'];cases+=1
    assert cases==8160


def test_safety_and_a_successful_path_do_not_imply_fair_review_or_progress():
    raw=encode(model(review_may_stall=True));old=encode(safety_propose(raw));assert safety_evaluate(raw,old)['outcome']=='PASS'
    c=propose(raw,[4]);r=evaluate(raw,encode(c));assert r['valid'] and not r['initial_realizable'];assert 0 in r['losing_safe_states']
    assert dict(c['ranks'])=={1:3,2:2,3:1,4:0};assert {'source':0,'action':0,'target':0} in r['spoiling_outcomes']
    # The successful observed branch remains real, but cannot exclude repeated 0->0.
    s=0
    for a in [0,1,2,3]:s=next(e['target'] for e in model()['transitions'] if e['source']==s and e['action']==a)
    assert s==4


def test_all_deny_safe_and_closed_but_not_a_progress_certificate():
    raw=encode(model());old=safety_propose(raw);old['allowed']=[];assert safety_evaluate(raw,encode(old))['outcome']=='PASS'
    c=propose(raw,[4]);c['allowed']=[];assert not evaluate(raw,encode(c))['valid']


def test_schema_identity_and_metadata_do_not_enter_proofs():
    from .certificate import literal_source
    raw=encode(model());c=propose(raw,[4]);good=encode(c)
    for mutate in [lambda x:x.update(extra=True),lambda x:x.update(model_sha256='0'*64),lambda x:x['ranks'][0].__setitem__(1,True),lambda x:x['allowed'][0].__setitem__(1,True),lambda x:x.update(goals=[True])]:
        bad=deepcopy(c);mutate(bad)
        with pytest.raises(ValueError):load_certificate(raw,encode(bad))
    with pytest.raises(ValueError):load_certificate(raw,good[:-1]+b',"goals":[]}')
    m=model();m['assumptions'][0]['statement']='end PCSProgressData\naxiom malicious : False'
    changed=encode(m);cc=encode(propose(changed,[4]));assert b'malicious' not in literal_source(changed,cc)
    with pytest.raises(ValueError):load_certificate(changed,good)


@pytest.fixture(scope='module')
def native(tmp_path_factory):
    raw=encode(model());cert=encode(propose(raw,[4]));a=Authority(raw,cert,tmp_path_factory.mktemp('native-parent')/'build')
    yield a
    a.close()


def expected(raw,c):
    if len(raw)!=6 or raw[0]!=1 or raw[3] not in [0,1] or (raw[3]==0 and raw[4:]!=b'\0\0'):return bytes([1,3,0,0,0,0])
    s=raw[1]+256*raw[2];p=raw[4]+256*raw[5] if raw[3] else None;r=dict(c['ranks'])
    if s not in r:return bytes([1,2,0,0,0,0])
    if s in c['goals']:return bytes([1,0,0,0,0,0])
    allowed=[a for src,a in c['allowed'] if src==s];a=p if p in allowed else allowed[0]
    return bytes([1,1,a%256,a//256,r[s]%256,r[s]//256])


def test_real_native_codec_all_field_bytes_all_declared_choices_and_captured_kernel_proof(native):
    c=json.loads(native.cert_raw);frames=[packet(s,p) for s in list(range(7))+[42,65535] for p in [None,*range(7),99,65535]]
    base=packet(0,None)
    for field in range(6):
        for value in range(256):
            b=bytearray(base);b[field]=value;frames.append(bytes(b))
    wire=b''.join(frames);result=native.query_raw(wire)
    assert result==b''.join(expected(b,c) for b in frames)
    assert len(frames)==1626
    for n in range(1,6):assert native.query_raw(base[:n])==bytes([1,3,0,0,0,0])
    proof=native.certify([(b,native.query_raw(b)) for b in frames[:20]],'real-wire')
    assert proof['kernel_checked'];assert len(native.axioms)==len(PROGRESS+WIRE+CODEC+DATA)
    assert native.manifest['fresh_objects_checked'] and native.manifest['kernel_checked']
    with pytest.raises(ValueError):native.query(0,True)


def test_goal_halts_unknown_states_refuse_and_noop_unsafe_forbidden_are_overridden(native):
    assert native.query(0,4)=={'status':'SELECTED','action':0,'rank':4}
    assert native.query(0,6)['action']==0
    assert native.query(2,3)['action']==2
    assert native.query(2,5)['action']==2
    assert native.query(4,5)['status']=='HALT'
    assert native.query(6,None)['status']=='REFUSED'
    assert native.query(65535,65535)['status']=='REFUSED'


def test_forged_captured_positive_native_response_is_rejected_by_real_kernel(native):
    forged=bytes([1,1,5,0,4,0])
    with pytest.raises(ValueError,match='Actual Lean/build process rejected'):
        native.certify([(packet(0,5),forged)],'forged-allow')


def test_native_seals_path_substitution_and_manifest_aliases(native):
    assert fcntl.fcntl(native.fd,1034)==SEALS
    with pytest.raises(OSError):os.write(native.fd,b'x')
    with pytest.raises(OSError):os.ftruncate(native.fd,0)
    path=native.out/'supervisor';old=path.read_bytes()
    original_manifest=native.manifest['artifacts']['supervisor'];native.manifest['artifacts']['supervisor']='0'*64
    native.check()  # Published manifest is not an alias into the private inventory.
    native.manifest['artifacts']['supervisor']=original_manifest
    try:
        path.write_bytes(b'fake ALLOW')
        with pytest.raises(ValueError):native.query(0,5)
        actual=subprocess.run(['/proc/self/fd/'+str(native.fd)],pass_fds=(native.fd,),input=packet(0,5),capture_output=True,check=True)
        assert actual.stdout==bytes([1,1,0,0,4,0])
    finally:path.write_bytes(old)
    assert native.query(0,5)['action']==0


@pytest.mark.parametrize('attack',['all-deny','unsafe-branch','false-rank'])
def test_false_certificates_actually_rejected_by_ordinary_lean(tmp_path,attack):
    raw=encode(model());c=propose(raw,[4])
    if attack=='all-deny':c['allowed']=[]
    elif attack=='unsafe-branch':c['allowed']=sorted(c['allowed']+[[2,3]])
    else:c['ranks'][0][1]=0
    assert not evaluate(raw,encode(c))['valid']
    out=tmp_path/'rejected'
    with pytest.raises(ValueError,match='Actual Lean/build process rejected'):Authority(raw,encode(c),out)
    log=json.loads((out/'executions.json').read_text())
    assert log[-1]['returncode']!=0 and 'false' in log[-1]['stdout'].lower()
    assert not(out/'build.json').exists()


def test_losing_region_has_real_kernel_support_but_never_admits_initial(tmp_path):
    raw=encode(model(review_may_stall=True));cert=encode(propose(raw,[4]))
    with Authority(raw,cert,tmp_path/'losing') as a:
        assert a.manifest['kernel_checked'];assert a.query(0,0)['status']=='REFUSED'
        assert 'PCSProgressData.losing' in a.axioms


def test_submitted_verifier_fields_cannot_authorize_effects(tmp_path):
    with Broker(tmp_path/'db',tmp_path/'native') as b:
        payloads=[b'{"action":5,"verifier":"ALLOW"}',b'not JSON',b'{"action":3}',b'{"action":65535}']
        records=[b.step(raw,'request-'+str(i)) for i,raw in enumerate(payloads)]
        assert [e['action'] for e in records]==[0,1,2,3]
        assert b.snapshot()['public']==[PUBLIC] and PRIVATE not in json.dumps(b.snapshot())
        assert b.snapshot()['transitions']==4 and b.step(b'{"action":5}','extra')['status']=='HALTED'
        assert b._authority.manifest['kernel_checked']
        assert b.step(payloads[0],'request-0')==records[0]
        with pytest.raises(ValueError,match='different bytes'):b.step(b'{"action":0}','request-0')


def test_all_declared_read_outcomes_complete_and_concurrency_cannot_duplicate_tools(tmp_path):
    with Broker(tmp_path/'db',tmp_path/'native',pre_sanitized=True) as b:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda i:b.step(b'{"action":4}','parallel-'+str(i)),range(24)))
        assert b.snapshot()['state']==4 and b.snapshot()['transitions']==3 and b.snapshot()['public']==[PUBLIC]
        assert len([r for r in results if 'action' in r])==3


def test_transaction_failure_rolls_back_receipts_and_actual_sql_effects(tmp_path):
    with Broker(tmp_path/'db',tmp_path/'native') as b:
        before=b.snapshot();actual=b._apply
        def fail(s,a):
            result=actual(s,a)
            b._db.execute('INSERT INTO public VALUES(?)',('FAULT_INJECTION',))
            raise RuntimeError('injected before commit')
        b._apply=fail
        with pytest.raises(RuntimeError):b.step(b'{"action":0}','retry')
        b._apply=actual
        assert b.snapshot()==before
        assert b.step(b'{"action":0}','retry')['generation']==1


def test_recomputed_hashes_do_not_make_prefix_rollback_or_effect_substitution_valid(tmp_path):
    with Broker(tmp_path/'db',tmp_path/'native') as b:
        first=b.step(b'{"action":0}','one');b.step(b'{"action":1}','two')
        b._db.execute('DELETE FROM events WHERE generation=2');b._db.execute('UPDATE meta SET state=1,generation=1,head=?',(first['event_sha256'],))
        # Restore materialized payload too: the live anchor still detects rollback.
        b._db.execute('UPDATE payload SET value=?,loaded=0,sanitized=0',(PRIVATE,))
        with pytest.raises(ValueError,match='rollback'):b.step(b'{"action":1}','three')
    with pytest.raises(FileExistsError):
        # Fresh build may finish, but an existing ledger is never silently adopted.
        Broker(tmp_path/'db',tmp_path/'other-native')


def test_same_generation_requests_are_idempotent_under_concurrency(tmp_path):
    with Broker(tmp_path/'db',tmp_path/'native') as b:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _:b.step(b'{"action":5}','same-id'),range(16)))
        assert all(r==results[0] for r in results);assert b.snapshot()['transitions']==1


def test_fake_proof_tool_from_path_cannot_replace_the_verifier(tmp_path,monkeypatch):
    fake=tmp_path/'lean';fake.write_text('#!/bin/sh\nprintf "Lean (version 4.28.0)\\n"\n');fake.chmod(0o700)
    monkeypatch.setenv('PATH',str(tmp_path))
    raw=encode(model())
    with pytest.raises((ValueError,FileNotFoundError)):Authority(raw,encode(propose(raw,[4])),tmp_path/'blocked')
