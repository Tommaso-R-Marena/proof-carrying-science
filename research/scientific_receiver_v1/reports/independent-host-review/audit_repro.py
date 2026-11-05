"""Read-only historical/fixed host containment review; diagnostic children reject only."""
import hashlib,importlib.util,json,os,signal,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path('/workspace/pcs-scientific-receiver-v1')
OUT=Path('/workspace/pcs-review-evidence/receiver-host-audit')
BASE='7a48fa34441641b0cd28dad3753c72ccf9dceabc'
REL='research/scientific_receiver_v1/host.py'
from research.scientific_receiver_v1 import host as current
historical=subprocess.check_output(['git','show',BASE+':'+REL],cwd=ROOT)
file=OUT/'host-historical-7a48fa3.py';file.write_bytes(historical)
name='research.scientific_receiver_v1._historical_review_host'
spec=importlib.util.spec_from_file_location(name,file)
baseline=importlib.util.module_from_spec(spec);sys.modules[name]=baseline;spec.loader.exec_module(baseline)
raw=(ROOT/'research/scientific_receiver_v1/fixtures/one-step.wire').read_bytes()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def service(module,code,timeout):
 tmp=Path(tempfile.mkdtemp(prefix='pcs-readonly-audit-'));script=tmp/'negative.py';script.write_text(code)
 exe=Path(sys.executable).resolve()
 pins=(module.Pin('source',str(script),sha(script)),module.Pin('dependency',str(ROOT/'research/scientific_receiver_v1/reference.py'),sha(ROOT/'research/scientific_receiver_v1/reference.py')))
 cfg=module.OperatorConfig((str(exe),str(script)),sha(exe),pins,str(tmp),(),'negative review diagnostic only',timeout_seconds=timeout)
 return module.ReceiverService(cfg)
def deep(module):
 svc=service(module,'print("["*12000+"0"+"]"*12000)\n',2)
 try:
  envelope=svc.verify_bytes(raw)
  return {'signed_rejection':envelope['receipt']['accepted'] is False and module.replay_signed_receipt(envelope,svc.public_key_hex),'errors':envelope['receipt']['errors']}
 except Exception as e:return {'escaped_exception':type(e).__name__,'message':str(e)}
def descendant(module):
 pidfile=Path(tempfile.mkdtemp(prefix='pcs-audit-pid-'))/'child.pid'
 code='import subprocess,sys\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\nPath('+repr(str(pidfile))+').write_text(str(p.pid))\nprint("{}")\n'
 svc=service(module,code,.3);env=svc.verify_bytes(raw);pid=int(pidfile.read_text())
 try:
  time.sleep(.5)
  try:state=Path(f'/proc/{pid}/stat').read_text().split()[2]
  except FileNotFoundError:state='absent'
  return {'accepted':env['receipt']['accepted'],'descendant_state_after_deadline':state,'descendant_running':state not in ('Z','absent'),'signed_rejection':module.replay_signed_receipt(env,svc.public_key_hex)}
 finally:
  try:os.kill(pid,signal.SIGKILL)
  except ProcessLookupError:pass
report={'format':'pcs-readonly-host-containment-review-v1','baseline_commit':BASE,'baseline_host_sha256':hashlib.sha256(historical).hexdigest(),'current_host_sha256':sha(ROOT/REL),'historical':{'deep_json':deep(baseline),'descendant':descendant(baseline)},'working_tree_fixed':{'deep_json':deep(current),'descendant':descendant(current)},'scope':'Negative diagnostic subprocesses only; no positive verifier substitute; mathematical codec not independently re-reviewed by its author.'}
(OUT/'findings-and-retest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
