"""Disposable, same-admin distinct-UID witness qualification; no production deployment."""
from pathlib import Path
import os,json,subprocess,sys,time,hashlib,shutil,tempfile
from datetime import datetime,timedelta,timezone
from dataclasses import asdict
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa,ed25519
from cryptography.x509.oid import NameOID

ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from research.scientific_history_v1.test_receiver import real_config,FIXTURES
from research.scientific_receiver_v1.host import operator_config_for_lean
from research.scientific_history_v1.receiver import POLICY,checker_identity
from research.authorization_history_v1 import history
from research.scientific_authority_v2.demo import sign_intent

OUT=Path(sys.argv[1]).resolve();OUT.mkdir(exist_ok=False);os.chmod(OUT,0o755)
private=OUT/'private';public=OUT/'public';producer=OUT/'producer'
for p in [private,public,producer]:p.mkdir();os.chmod(p,0o755)
namespace='pcs-v2-b-'+str(os.getpid());env=os.environ.copy()
for k in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(k,None)
D=['docker','--host=unix:///var/run/docker.sock']
def docker(*args,timeout=60,check=True):
 r=subprocess.run([*D,*map(str,args)],env=env,capture_output=True,text=True,timeout=timeout)
 if check and r.returncode:
  (OUT/'docker-error.txt').write_text(r.stderr)
  raise RuntimeError('Docker command failed: '+r.stderr[:2000])
 return r
build=OUT/'scratch-image';build.mkdir()
(build/'Dockerfile').write_text('FROM scratch\nLABEL org.opencontainers.image.title="PCS disposable distinct-principal research probe"\n')
built=docker('build','--network=none','--iidfile',str(build/'image-id'),str(build))
(OUT/'image-build.log').write_text(built.stdout+built.stderr)
image=(build/'image-id').read_text().strip()
PYTHON=Path(sys.executable);python_root=Path(sys.base_prefix)
base=real_config();lean=Path(base.command[0]);main=ROOT/'research/scientific_receiver_v1/formal/Main.lean'
leanpaths=dict(base.environment)['LEAN_PATH']
sources=tuple(sorted(main.parent.glob('*.lean')))+tuple(sorted((main.parent/'PCSScientificReceiver').glob('*.lean')))
sources+=tuple(p for package in ['scientific_receiver_v1','authorization_history_v1','scientific_history_v1','scientific_history_v2','scientific_witness_v1','scientific_authority_v2'] for p in sorted((ROOT/'research'/package).glob('*.py')))
deps=tuple(Path(p.path) for p in base.pins if p.kind=='dependency')
config=operator_config_for_lean(executable=lean,main=main,cwd=main.parent,lean_path=leanpaths,source_files=sources,dependency_files=deps,toolchain='Lean4.28.0; distinct-UID/container research probe; partial dependency inventory, not full loader attestation')
configuration=asdict(config);configuration['environment']=dict(config.environment)
(public/'config.json').write_text(json.dumps(configuration));config_path=public/'config.json'
first,second,witness=[ed25519.Ed25519PrivateKey.generate() for _ in range(3)]
root=history.Root(first.public_key().public_bytes_raw(),second.public_key().public_bytes_raw(),POLICY,checker_identity(config),b'profile-b-genesis',(FIXTURES/'zero-step.wire').read_bytes())
(public/'root.json').write_bytes(root.encode());(public/'witness-public.hex').write_text(witness.public_key().public_bytes_raw().hex())
key=private/'witness.key';key.write_bytes(witness.private_bytes_raw());os.chmod(key,0o600)
raw=sign_intent(root,history.initial(root),first,second,(FIXTURES/'one-step.wire').read_bytes(),b'profile-b-actual')
(public/'positive.wire').write_bytes(raw)
next_anchor=history._advance(root,history.initial(root),history.Envelope.decode(raw),set())
(public/'false-science.wire').write_bytes(sign_intent(root,next_anchor,first,second,(FIXTURES/'wrong-total.wire').read_bytes(),b'profile-b-false'))
tlskey=rsa.generate_private_key(public_exponent=65537,key_size=2048);name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,namespace)])
now=datetime.now(timezone.utc)
cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(tlskey.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName(namespace)]),critical=False).add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).sign(tlskey,hashes.SHA256()))
(public/'ca.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM));(private/'tls.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM));(private/'tls.key').write_bytes(tlskey.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));os.chmod(private/'tls.key',0o600)
paths=[ROOT,python_root,PYTHON.parent.parent,lean.parent.parent,Path('/usr/lib/x86_64-linux-gnu'),Path('/usr/lib64')]
for p in leanpaths.split(os.pathsep):
 p=Path(p)
 if p.is_dir():paths.append(p)
# Keep paths unchanged for exact source/profile identity. Bind only required trees.
mounts=[]
for p in sorted(set(paths),key=lambda p:len(str(p))):
 if any(p.is_relative_to(parent) for parent in mounts):continue
 mounts.append(p)
common=['--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--tmpfs','/tmp:rw,nosuid,nodev,size=128m','--workdir',str(ROOT),'--env','PYTHONPATH='+str(ROOT),'--env','PYTHONDONTWRITEBYTECODE=1']
for p in mounts:common+=['--mount',f'type=bind,src={p},dst={p},readonly']
# glibc expects these standard loader locations in the otherwise empty image.
common+=['--mount','type=bind,src=/usr/lib/x86_64-linux-gnu,dst=/lib/x86_64-linux-gnu,readonly','--mount','type=bind,src=/usr/lib64,dst=/lib64,readonly','--mount',f'type=bind,src={public},dst=/public,readonly']
producer_script=r'''
from pathlib import Path
import json,os,sys,time
from research.scientific_history_v2.cli import load_root
from research.scientific_receiver_v1.host import OperatorConfig
from research.scientific_witness_v1.client import WitnessClient
from research.scientific_witness_v1.protocol import verify_statement,digest,decode_anchor
p=Path('/public');root=load_root((p/'root.json').read_bytes());config=OperatorConfig.load(p/'config.json')
key=bytes.fromhex((p/'witness-public.hex').read_text())
client=WitnessClient(sys.argv[1],root,config,key,ca_file=str(p/'ca.pem'))
start=time.monotonic()
while True:
 try:client.checkpoint();break
 except ValueError:
  if time.monotonic()-start>60:raise
  time.sleep(.1)
intent=(p/'positive.wire').read_bytes()
prepared=client.prepare(intent);checked=verify_statement(prepared['receipt'],key,root,config,kind='prepared')
assert checked['intent_sha256']==digest(intent)
finalized=client.finalize(digest(intent));verify_statement(finalized['receipt'],key,root,config,kind='finalized')
evidence=client.checkpoint_evidence();view=evidence['statement']['payload']
assert decode_anchor(view['anchor']).generation==1 and view['pending'] is None
before=view['anchor']
try:client.prepare((p/'false-science.wire').read_bytes());raise AssertionError('false science accepted')
except ValueError:pass
assert client.checkpoint()['anchor']==before and client.checkpoint()['pending'] is None
assert not Path('/var/run/docker.sock').exists()
try:Path('/witness-private/witness.key').read_bytes();raise AssertionError('private key exposed')
except FileNotFoundError:pass
try:Path(__file__).write_bytes(b'substitution');raise AssertionError('source writable')
except OSError as e:assert e.errno==30
value={'profile':'B:same-admin-distinct-UID-containers','scope':'Producer-to-witness authorization boundary; full local-coordinator crash path remains separately tested under Profile A','uid':os.getuid(),'gid':os.getgid(),'capabilities':[s for s in Path('/proc/self/status').read_text().splitlines() if s.startswith('CapEff:')],'actual_lean_authorized_generation':1,'checked_prepared':prepared,'checked_finalized':finalized,'signed_checkpoint':evidence,'export':client.export(),'false_science_rejected':True,'witness_key_not_mounted':True,'docker_control_socket_not_mounted':True,'application_mount_readonly':True,'independent_administration':False,'empirical_validity':'UNVERIFIED','production_authority':False}
print(json.dumps(value))
'''
(public/'producer.py').write_text(producer_script)
# The producer gets hash-identical PUBLIC sources/dependencies with public read
# modes in a copy. No permissions on original source or dependency caches change.
client_source=public/'client-source';client_source.mkdir()
for name in ['pcs','research']:
 directory=ROOT/name
 if name=='pcs':shutil.copytree(directory,client_source/name,ignore=shutil.ignore_patterns('__pycache__'))
 else:
  for package in ['scientific_receiver_v1','authorization_history_v1','scientific_history_v1','scientific_history_v2','scientific_witness_v1','scientific_authority_v2']:
   dest=client_source/name/package;dest.mkdir(parents=True)
   for source in (directory/package).glob('*.py'):shutil.copyfile(source,dest/source.name)
client_env=public/'client-env';(client_env/'bin').mkdir(parents=True)
(client_env/'bin/python').symlink_to(Path(sys.executable).resolve())
shutil.copyfile(PYTHON.parent.parent/'pyvenv.cfg',client_env/'pyvenv.cfg')
site=PYTHON.parent.parent/'lib/python3.12/site-packages'
client_site=client_env/'lib/python3.12/site-packages';client_site.mkdir(parents=True)
for pattern in ['cryptography','cffi','pycparser','_cffi_backend*.so']:
 for source in site.glob(pattern):
  target=client_site/source.name
  if source.is_dir():shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__'))
  else:shutil.copyfile(source,target)
for basepath in [public]:
 for here,dirs,files in os.walk(basepath):
  os.chmod(here,0o755)
  for name in files:
   f=Path(here)/name
   if not f.is_symlink():os.chmod(f,0o644)
private.chmod(0o700)
pcommon=['--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--tmpfs','/tmp:rw,nosuid,nodev,size=64m','--workdir',str(ROOT),'--env','PYTHONPATH='+str(ROOT),'--env','PYTHONDONTWRITEBYTECODE=1']
for src,dst in [(client_source,ROOT),(client_env,PYTHON.parent.parent),(python_root,python_root),(Path('/usr/lib/x86_64-linux-gnu'),Path('/lib/x86_64-linux-gnu')),(Path('/usr/lib64'),Path('/lib64')),(public,Path('/public'))]:
 pcommon+=['--mount',f'type=bind,src={src},dst={dst},readonly']
# The daemon/control plane remains trusted same-admin operator infrastructure.
containers=[];created_network=False
record={'format':'pcs-authority-v2-distinct-principal-replay-v1','started_utc':now.isoformat(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'image_id':image,'witness_uid':1000,'producer_uid':65534,'same_administrator':True,'independent_administration':False,'fixture_dependency_profile':'Explicit partial dependency inventory; full Profile A qualified separately','source_before':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'operator_config_sha256':root.checker.hex(),'no_production_credentials_or_deployment':True}
(OUT/'preregistration.json').write_text(json.dumps(record,indent=2))
try:
 private_mount=['--mount',f'type=bind,src={private},dst=/witness-private']
 flags=['--db','/witness-private/witness.sqlite','--root','/public/root.json','--config','/public/config.json','--key','/witness-private/witness.key']
 initialized=docker('run','--rm','--network=none',*common,*private_mount,'--user=1000:1000',image,str(PYTHON),'-m','research.scientific_witness_v1.server','init',*flags)
 (OUT/'init.log').write_text(initialized.stdout+initialized.stderr)
 docker('network','create','--internal',namespace);created_network=True
 docker('run','--detach','--name',namespace,'--network',namespace,'--network-alias',namespace,*common,*private_mount,'--user=1000:1000',image,str(PYTHON),'-m','research.scientific_witness_v1.server','serve',*flags,'--bind','0.0.0.0','--port','8443','--cert','/witness-private/tls.pem','--tls-key','/witness-private/tls.key');containers.append(namespace)
 metadata=docker('exec',namespace,str(PYTHON),'-c',"import os,json;from pathlib import Path;p=Path('/witness-private/witness.key');s=p.stat();print(json.dumps({'uid':os.getuid(),'gid':os.getgid(),'key_uid':s.st_uid,'key_mode':oct(s.st_mode&0o777),'docker_socket_present':Path('/var/run/docker.sock').exists(),'capabilities':[x for x in Path('/proc/self/status').read_text().splitlines() if x.startswith('CapEff:')]}))")
 record['witness_principal']=json.loads(metadata.stdout)
 # The producer UID cannot read the private key even if administratively
 # granted a path inside the witness mount; this tests DAC, not host-admin safety.
 denied=docker('exec','--workdir','/','--user=65534:65534',namespace,str(PYTHON.resolve()),'-c',"from pathlib import Path;Path('/witness-private/witness.key').read_bytes()",check=False)
 (OUT/'key-access-refusal.txt').write_text(denied.stderr)
 assert denied.returncode!=0 and 'PermissionError' in denied.stderr
 record['producer_uid_same_mount_key_read_denied']=True
 command=['run','--rm','--name',namespace+'-producer','--network',namespace,*pcommon,'--env','NO_PROXY='+namespace,'--env','no_proxy='+namespace,'--user=65534:65534',image,str(PYTHON),'/public/producer.py','https://'+namespace+':8443']
 execution=docker(*command,timeout=180,check=False)
 (OUT/'producer.log').write_text(execution.stdout+execution.stderr)
 if execution.returncode:raise RuntimeError('Producer failed; see retained producer.log')
 record['producer']=json.loads(execution.stdout)
 record['source_after']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources};assert record['source_after']==record['source_before']
 record['passed']=True
finally:
 for name in containers:
  logs=docker('logs',name,check=False);(OUT/'witness.log').write_text(logs.stdout+logs.stderr)
  docker('rm','--force',name,check=False)
 if created_network:docker('network','rm',namespace,check=False)
 # Delete only this probe's disposable witness secrets/state; no historical evidence.
 for f in private.iterdir():f.unlink()
 docker('image','rm',image,check=False)
 record['finished_utc']=datetime.now(timezone.utc).isoformat();(OUT/'result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'passed':record.get('passed',False),'profile':'B:same-admin-distinct-UID-containers','independently_administered':False,'out':str(OUT)}))
