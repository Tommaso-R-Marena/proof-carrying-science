"""Read-only target review; every positive host response comes from actual Lean."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
TARGET=Path('/workspace/pcs-scientific-history-runtime-v1')
sys.path.insert(0,str(TARGET))
from dataclasses import replace
from datetime import datetime,timezone
from fractions import Fraction
import hashlib,json,sqlite3,time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from research.authorization_history_v1 import history
from research.scientific_receiver_v1 import host
from research.scientific_history_v1.receiver import ScientificReceivingLedger,IntakeRejected,POLICY,checker_identity
from research.scientific_history_v1.test_receiver import real_config,FIXTURES

OUT=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
sources=[TARGET/'research/scientific_history_v1/receiver.py',TARGET/'research/scientific_history_v1/test_receiver.py',TARGET/'research/authorization_history_v1/history.py',TARGET/'research/scientific_receiver_v1/host.py']
identities=lambda:[{'path':str(p),'sha256':sha(p.read_bytes())} for p in sources]
report={'started_utc':datetime.now(timezone.utc).isoformat(),'source_before':identities(),'tests':[],'actual_host_receipts':[],'findings':[]}
clock=time.perf_counter()
config=real_config()
authority,witness=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()
genesis=(FIXTURES/'zero-step.wire').read_bytes();candidate=(FIXTURES/'one-step.wire').read_bytes()
root=history.Root(authority.public_key().public_bytes_raw(),witness.public_key().public_bytes_raw(),POLICY,checker_identity(config),b'genesis',genesis)
path=OUT/'independent.sqlite'
history.History.create(path,root);initial=history.initial(root)
ledger=ScientificReceivingLedger(path,root,initial,config)
original_verify=ledger._service.verify_bytes

def observed_actual(raw):
 start=time.perf_counter();result=original_verify(raw)
 report['actual_host_receipts'].append({'raw_sha256':sha(raw),'wall_seconds':time.perf_counter()-start,'envelope':result})
 return result
ledger._service.verify_bytes=observed_actual

def signed(raw=candidate,anchor=initial,event_id=b'one',**changes):
 payload=replace(history.proposed_payload(root,anchor,event_id=event_id,candidate=raw,certificate=b''),**changes)
 return history.Envelope(payload,authority.sign(payload.signing_bytes()),witness.sign(payload.signing_bytes())).encode()

def expect_reject(name,raw,*,expect_fresh_verifications):
 before=sha(path.read_bytes());calls=len(report['actual_host_receipts']);current=ledger.current();start=time.perf_counter()
 try:
  ledger.submit(raw);outcome='unexpected_success'
 except Exception as exc:
  outcome=type(exc).__name__+': '+str(exc)
 after_current=ledger.current()
 test={'id':name,'outcome':outcome,'wall_seconds':time.perf_counter()-start,
       'fresh_verifications':len(report['actual_host_receipts'])-calls,
       'expected_fresh_verifications':expect_fresh_verifications,
       'db_unchanged':sha(path.read_bytes())==before,'cache_unchanged':after_current==current}
 test['passed']=outcome!='unexpected_success' and test['fresh_verifications']==expect_fresh_verifications and test['db_unchanged'] and test['cache_unchanged']
 report['tests'].append(test)
 if not test['passed']:report['findings'].append(test)

payload=history.proposed_payload(root,initial,event_id=b'unsigned',candidate=candidate,certificate=b'')
unsigned=history.Envelope(payload,bytes(64),bytes(64)).encode()
expect_reject('invalid_signatures_reject_before_science',unsigned,expect_fresh_verifications=0)
expect_reject('reserved_auxiliary_certificate_rejects',signed(certificate=b'not-authority'),expect_fresh_verifications=0)
expect_reject('malformed_envelope_rejects',b'{"unknown":1}',expect_fresh_verifications=0)

start=time.perf_counter();first_signed=signed();accepted=ledger.submit(first_signed)
assert accepted.candidate==candidate and accepted.result.final_a==Fraction(7,2)
assert accepted.result.total==7 and accepted.anchor.generation==1
assert not(accepted.scientific_acceptance or accepted.production_authority or accepted.promotion_authority or accepted.historical_scientific_audit)
report['tests'].append({'id':'actual_valid_candidate_admitted','passed':True,'wall_seconds':time.perf_counter()-start,'raw_sha256':accepted.raw_sha256})

expect_reject('stale_generation_rejects_before_science',signed(anchor=initial,event_id=b'stale'),expect_fresh_verifications=0)
expect_reject('replayed_exact_envelope_rejects_before_science',first_signed,expect_fresh_verifications=0)
expect_reject('reused_event_id_rejects_before_science',signed(anchor=accepted.anchor,event_id=b'one'),expect_fresh_verifications=0)
next_signed=history.Envelope.decode(signed(anchor=accepted.anchor,event_id=b'tamper'))
tampered=replace(next_signed,payload=replace(next_signed.payload,candidate=genesis)).encode()
expect_reject('signed_candidate_tampering_rejects_before_science',tampered,expect_fresh_verifications=0)
expect_reject('validly_cosigned_false_math_cannot_enter',signed((FIXTURES/'wrong-environment.wire').read_bytes(),anchor=accepted.anchor,event_id=b'false-math'),expect_fresh_verifications=1)

# Negative-only write fault, reached after an actual successful mathematical check.
before=sha(path.read_bytes());saved_append=ledger._history.append
ledger._history.append=lambda _:(_ for _ in ()).throw(sqlite3.OperationalError('independent negative write fault'))
try:
 ledger.submit(signed(anchor=accepted.anchor,event_id=b'write-fault'));write_outcome='unexpected_success'
except Exception as exc:write_outcome=type(exc).__name__+': '+str(exc)
finally:ledger._history.append=saved_append
ok=write_outcome.startswith('OperationalError:') and sha(path.read_bytes())==before and ledger.current()==accepted
report['tests'].append({'id':'actual_verified_then_negative_write_fault','passed':ok,'outcome':write_outcome})
if not ok:report['findings'].append(report['tests'][-1])

# A real commit followed by a negative exception must not expose a stale current cache.
postcommit=signed(anchor=accepted.anchor,event_id=b'postcommit-fault')
def append_then_fail(raw):
 saved_append(raw)
 raise sqlite3.OperationalError('independent negative fault after real commit')
ledger._history.append=append_then_fail
try:ledger.submit(postcommit);post_outcome='unexpected_success'
except Exception as exc:post_outcome=type(exc).__name__+': '+str(exc)
finally:ledger._history.append=saved_append
try:ledger.current();current_outcome='unexpected_success'
except Exception as exc:current_outcome=type(exc).__name__+': '+str(exc)
recovered=history.recover(path,root,previous=accepted.anchor,expected_envelope=postcommit)
reopened=ScientificReceivingLedger(path,root,recovered,config)
ok=post_outcome.startswith('OperationalError:') and current_outcome.startswith('IntakeRejected:') and reopened.current().anchor==recovered and recovered.generation==2
report['tests'].append({'id':'postcommit_exception_fails_closed_until_explicit_recovery','passed':ok,'submit_outcome':post_outcome,'current_outcome':current_outcome,'recovered_generation':recovered.generation})
if not ok:report['findings'].append(report['tests'][-1])

# Real Lean timeout; no fake executable, positive callback or fabricated receipt.
short=replace(config,timeout_seconds=.01)
shortroot=replace(root,checker=checker_identity(short))
shortpath=OUT/'timeout.sqlite';history.History.create(shortpath,shortroot)
before=sha(shortpath.read_bytes());start=time.perf_counter()
try:ScientificReceivingLedger(shortpath,shortroot,history.initial(shortroot),short);timeout_outcome='unexpected_success'
except Exception as exc:timeout_outcome=type(exc).__name__+': '+str(exc)
ok=timeout_outcome.startswith('IntakeRejected:') and sha(shortpath.read_bytes())==before
report['tests'].append({'id':'real_lean_timeout_constructor_fails_without_admission','passed':ok,'outcome':timeout_outcome,'wall_seconds':time.perf_counter()-start})
if not ok:report['findings'].append(report['tests'][-1])

report.update({'source_after':identities(),'finished_utc':datetime.now(timezone.utc).isoformat(),'wall_seconds':time.perf_counter()-clock,
               'scope':'Read-only implementation review and finite actual-process fault reproductions; no full-history scientific audit or protected root established.',
               'no_positive_mocks':True})
report['sources_stable']=report['source_before']==report['source_after']
(OUT/'reproductions.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'tests':len(report['tests']),'findings':report['findings'],'sources_stable':report['sources_stable'],'wall_seconds':report['wall_seconds']}))
