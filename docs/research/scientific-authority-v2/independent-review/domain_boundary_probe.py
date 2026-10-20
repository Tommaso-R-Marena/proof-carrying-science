"""Canonical signed-intent domain check only; no mathematical verdict is mocked."""
import sys,json,hashlib,importlib.util,argparse
from pathlib import Path
sys.dont_write_bytecode=True
WITNESS=Path('/workspace/pcs-independent-witness-v1');AUDITOR=Path('/workspace/pcs-historical-scientific-replay-v1')
sys.path[:0]=[str(WITNESS),str(AUDITOR)]
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from research.authorization_history_v1 import history
from research.scientific_history_v1.receiver import POLICY,checker_identity
from research.scientific_history_v1.test_receiver import real_config,FIXTURES
from research.scientific_history_v2 import audit
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
source=WITNESS/'research/scientific_witness_v1/protocol.py'
raw=source.read_bytes();snapshot=out/'protocol-domain-review-snapshot.py';snapshot.write_bytes(raw)
spec=importlib.util.spec_from_file_location('review_protocol_snapshot',snapshot);p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
config=real_config();a,w=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()
genesis=(FIXTURES/'zero-step.wire').read_bytes();candidate=(FIXTURES/'one-step.wire').read_bytes()
root=history.Root(a.public_key().public_bytes_raw(),w.public_key().public_bytes_raw(),POLICY,checker_identity(config),b'genesis',genesis)
base=history.initial(root);payload=history.proposed_payload(root,base,event_id=b'x'*257,candidate=candidate,certificate=b'')
envelope=history.Envelope(payload,a.sign(payload.signing_bytes()),w.sign(payload.signing_bytes()));wire=envelope.encode()
report={'source_sha256':hashlib.sha256(raw).hexdigest(),'audit_sha256':hashlib.sha256(Path(audit.__file__).read_bytes()).hexdigest(),'event_id_bytes':len(payload.event_id),'wire_bytes':len(wire),'scope':'Signed canonical envelope/authentication-domain comparison; no actual mathematical verification or committed transition is claimed.'}
try:p.checked_intent(wire);report['witness_preflight']='ACCEPTED'
except Exception as e:report['witness_preflight']=type(e).__name__+': '+str(e)
next_anchor=history._advance(root,base,envelope,set())
try:audit.authenticate_material(root,next_anchor,(wire,),config);report['auditor_authentication']='ACCEPTED'
except Exception as e:report['auditor_authentication']=type(e).__name__+': '+str(e)
report['wider_witness_domain_reproduced']=report['witness_preflight']=='ACCEPTED' and report['auditor_authentication']!='ACCEPTED'
print(json.dumps(report,indent=2))
