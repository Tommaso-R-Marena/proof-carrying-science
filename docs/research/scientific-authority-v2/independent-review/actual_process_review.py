"""Independent real-process controls. No affirmative verdict is synthesized.

All stores/keys are fresh research fixtures in a temporary directory; no
production credentials or target-worktree source files are modified.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
from pathlib import Path
W=Path('/workspace/pcs-independent-witness-v1');A=Path('/workspace/pcs-historical-scientific-replay-v1');C=Path('/workspace/pcs-scientific-authority-v2')
sys.path[:0]=[str(W),str(A),str(C)]
from dataclasses import replace,asdict
from datetime import datetime,timezone
import os,json,hashlib,tempfile,time,subprocess,shutil,atexit
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from research.authorization_history_v1 import history
from research.scientific_history_v1.test_receiver import real_config,FIXTURES
from research.scientific_history_v1.receiver import POLICY,checker_identity
from research.scientific_receiver_v1 import host
from research.scientific_witness_v1.store import WitnessStore
from research.scientific_witness_v1.client import WitnessClient
from research.scientific_witness_v1 import protocol as p
from research.scientific_history_v2 import audit
from research.scientific_authority_v2 import coordinator

OUT=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
files=[*(W/'research/scientific_witness_v1'/name for name in ('__init__.py','protocol.py','store.py','client.py','server.py')),
       *(A/'research/scientific_history_v2'/name for name in ('__init__.py','audit.py')),
       *(C/'research/scientific_authority_v2'/name for name in ('__init__.py','coordinator.py'))]
def identities():return {str(path):sha(path.read_bytes()) for path in files}
report={'format':'pcs-authority-v2-independent-actual-process-review-v1','started_utc':datetime.now(timezone.utc).isoformat(),'preregistration_sha256':sha((OUT/'PREREGISTERED_CONTROLS.json').read_bytes()),'source_before':identities(),'controls':[],'receipts':[],'profile':'A: separate real server process and keys on one underlying host/admin','no_positive_mocks':True,'external_empirical_validation':False}
start=time.monotonic()
def retain_partial():
 if not (OUT/'actual-process-results.json').exists():
  report['completed']=False;report['wall_seconds']=time.monotonic()-start
  (OUT/'actual-process-incomplete.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
atexit.register(retain_partial)
def record(name,passed,**values):
 row={'id':name,'passed':bool(passed),**values};report['controls'].append(row)
 if not passed:raise AssertionError(row)
def refusal(name,fn):
 try:fn()
 except Exception as exc:
  record(name,True,outcome=type(exc).__name__+': '+str(exc));return
 record(name,False,outcome='unexpected_acceptance')

with tempfile.TemporaryDirectory(prefix='pcs-v2-independent-') as td:
 td=Path(td);config=real_config();pins={pin.path:pin for pin in config.pins}
 for path in files:
  pins[str(path)]=host.Pin('source',str(path),sha(path.read_bytes()))
 config=replace(config,pins=tuple(pins[path] for path in sorted(pins)))
 issuer,cosigner,witnesskey=[Ed25519PrivateKey.generate() for _ in range(3)]
 expectedpk=witnesskey.public_key().public_bytes_raw()
 root=history.Root(issuer.public_key().public_bytes_raw(),cosigner.public_key().public_bytes_raw(),POLICY,checker_identity(config),b'independent-genesis',(FIXTURES/'zero-step.wire').read_bytes())
 base=history.initial(root);producer=td/'producer.sqlite';wdb=td/'witness.sqlite'
 history.History.create(producer,root);producer_genesis=producer.read_bytes()
 store=WitnessStore.create(wdb,root,config,witnesskey);witness_genesis=wdb.read_bytes()
 rootpath=td/'root.json';rootpath.write_bytes(root.encode())
 keypath=td/'witness-key';keypath.write_bytes(witnesskey.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption()));os.chmod(keypath,0o600)
 configpath=td/'operator.json';configuration=asdict(config);configuration['environment']=dict(config.environment);configpath.write_bytes(p.canonical(configuration))
 report['root']=json.loads(root.encode());report['witness_public_key']=expectedpk.hex();report['operator_config_identity']=config.identity()
 processes=[]
 def launch(label):
  ready=td/('ready-'+label+'.json');errors=(td/('server-'+label+'.stderr')).open('wb')
  env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'PYTHONPATH':os.pathsep.join(map(str,[W,A,C])),'PYTHONDONTWRITEBYTECODE':'1'}
  process=subprocess.Popen([sys.executable,'-m','research.scientific_witness_v1.server','serve','--db',str(wdb),'--root',str(rootpath),'--config',str(configpath),'--key',str(keypath),'--ready-file',str(ready)],cwd=W,env=env,stdout=subprocess.DEVNULL,stderr=errors)
  processes.append((process,errors));deadline=time.monotonic()+75
  while not ready.exists():
   if process.poll() is not None:raise RuntimeError('Witness startup failed: '+(td/('server-'+label+'.stderr')).read_text())
   if time.monotonic()>deadline:raise TimeoutError('Witness readiness deadline')
   time.sleep(.05)
  bootstrap=json.loads(ready.read_bytes());assert bootstrap['witness_key']==expectedpk.hex()
  client=WitnessClient('http://127.0.0.1:'+str(bootstrap['port']),root,config,expectedpk)
  return process,client
 def stop(process):
  process.terminate();process.wait(timeout=10)
 def signed(raw,anchor,event_id):
  payload=history.proposed_payload(root,anchor,event_id=event_id,candidate=raw,certificate=b'')
  return history.Envelope(payload,issuer.sign(payload.signing_bytes()),cosigner.sign(payload.signing_bytes())).encode()
 try:
  process,client=launch('original');authority=coordinator.ScientificAuthority(producer,root,base,config,client)
  genesisview=client.checkpoint();record('actual_genesis_server_and_authority_open',p.decode_anchor(genesisview['anchor'])==base)
  candidate=(FIXTURES/'multi-step-nonsingleton.wire').read_bytes();intent=signed(candidate,base,b'accepted')
  prepared=client.prepare(intent);report['receipts'].append(prepared)
  refusal('prepared_only_not_eligible',authority.current)
  conflict=signed(candidate,base,b'conflicting-reservation')
  refusal('conflicting_pending_request_refused',lambda:client.prepare(conflict))
  finalized=client.finalize(p.digest(intent));report['receipts'].append(finalized)
  after=p.decode_anchor(client.checkpoint()['anchor']);record('witness_can_finalize_own_commit_without_claiming_remote_local_commit',after.generation==1 and history.History(producer,root,base).snapshot().anchor==base)
  refusal('witness_finalized_local_old_not_eligible',authority.current)
  recovered=coordinator.recover(producer,root,config,client)
  record('exact_witness_material_recovery',recovered.anchor==after and not recovered.new_authorization_created and recovered.audit.historically_authenticated_verification=='UNVERIFIED')
  authority=coordinator.ScientificAuthority(producer,root,after,config,client);snapshot=authority.current()
  record('recovered_result_has_exact_checked_candidate',snapshot.artifact.raw==candidate and snapshot.artifact.result.final_a.numerator==13 and snapshot.artifact.result.final_a.denominator==2)
  before=wdb.read_bytes();bad=(FIXTURES/'wrong-environment.wire').read_bytes()
  refusal('cosigned_false_science_refused',lambda:client.prepare(signed(bad,after,b'false-science')))
  record('false_science_does_not_advance_or_reserve_witness',wdb.read_bytes()==before and client.checkpoint()['pending'] is None and p.decode_anchor(client.checkpoint()['anchor'])==after)
  producer.write_bytes(producer_genesis)
  refusal('whole_producer_rollback_refused_live_authority',authority.current)
  refusal('whole_producer_rollback_refused_reopened_authority',lambda:coordinator.ScientificAuthority(producer,root,base,config,client))
  recovered=coordinator.recover(producer,root,config,client)
  record('whole_producer_rollback_reconstructs_exact_witness_history',recovered.anchor==after and not recovered.new_authorization_created)
  wrongkey=Ed25519PrivateKey.generate().public_key().public_bytes_raw()
  refusal('wrong_receiver_pinned_witness_key_refused',lambda:WitnessClient(client._url,root,config,wrongkey).checkpoint())
  otherroot=replace(root,genesis_id=b'foreign-root')
  refusal('cross_root_checkpoint_transplant_refused',lambda:WitnessClient(client._url,otherroot,config,expectedpk).checkpoint())
  nonce=os.urandom(32);view=store.checkpoint(nonce)
  refusal('nonce_replayed_checkpoint_refused',lambda:p.verify(view,root,expectedpk,kind='checkpoint',nonce=os.urandom(32)))
  refusal('checkpoint_role_confusion_refused',lambda:p.verify(view,root,expectedpk,kind='export',nonce=nonce))
  stop(process);wdb.write_bytes(witness_genesis)
  process,rolled=launch('witness-rollback');old=p.decode_anchor(rolled.checkpoint()['anchor'])
  record('witness_store_rollback_counterexample',old==base,counterexample=True,scope='Both trusted witness durability/monotonic continuity and retained latest checkpoint are lost; same pinned key/root alone authenticate a fresh old head. This is outside producer-only rollback protection.')
  producer.write_bytes(producer_genesis)
  reopened=coordinator.ScientificAuthority(producer,root,base,config,rolled)
  record('both_stores_rollback_counterexample',reopened.current().anchor==base,counterexample=True,scope='Simultaneously rolling back producer and trusted witness stores with no retained monotonic checkpoint is observationally accepted; not an unconditional rollback-resistance guarantee.')
  stop(process)
 finally:
  for process,errors in processes:
   if process.poll() is None:
    process.terminate()
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
   errors.close()
report['source_after']=identities();report['sources_stable']=report['source_after']==report['source_before'];report['wall_seconds']=time.monotonic()-start;report['finished_utc']=datetime.now(timezone.utc).isoformat();report['passed']=report['sources_stable'] and all(r['passed'] for r in report['controls'])
(OUT/'actual-process-results.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'controls':len(report['controls']),'expected_counterexamples':sum(r.get('counterexample',False) for r in report['controls']),'sources_stable':report['sources_stable'],'wall_seconds':report['wall_seconds'],'passed':report['passed']}))
if not report['passed']:raise SystemExit(1)
