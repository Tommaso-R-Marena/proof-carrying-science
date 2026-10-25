"""Fixed-source native Lean supervisor. Linux host/compiler/stdlib remain trusted."""
from __future__ import annotations
import fcntl,json,os,re,shutil,subprocess,time
from pathlib import Path
from pcs.transport_kernel_v1 import _inventory
from .certificate import literal_source,sha,load_certificate

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TOOLS={'lean':'3e0d0d3d801675359f2d4cf9815bfdb417b20b92fdd9d48b3b14c95bbae28bbf',
 'leanchecker':'cb6cee24e93aa1d72ad0314906c51918f7c96947e18790a0273c837c25e79025',
 'leanc':'871b10499518fd713bb1088dd98ca2833efdc0c6342cf972b056ef2224b4057d'}
PROGRESS=['PCSProgress.'+n for n in ('check_iff','force_succ','force_mono','winning_can_force','force_implies_winning','losing_no_finite_bound','pick_sound','pick_exists','choose_sound','choose_available','chosen_step_progresses','path_bound','completion_at_bound','preserves_existing_safety','goals_halt')]
WIRE=['PCSProgressWire.'+n for n in ('selected_from_choose','selected_all_outcomes','halt_is_goal','malformed_refuses')]
DATA=['PCSProgressData.'+n for n in ('certificate_checked','winning','losing')]
SEALS=15

def packet(state,proposal):
 if type(state) is not int or not 0<=state<65536:raise ValueError('exact state ID required')
 if proposal is not None and (type(proposal) is not int or not 0<=proposal<65536):raise ValueError('exact optional action ID required')
 a=0 if proposal is None else proposal
 return bytes([1,state%256,state//256,int(proposal is not None),a%256,a//256])

class Authority:
 """No caller-selected verifier/binary/source. This is NOT an immutable host root."""
 def __init__(self,model_raw,cert_raw,out):
  load_certificate(model_raw,cert_raw)
  self.out=Path(out).resolve();self.out.mkdir(parents=True,exist_ok=False);self.fd=None;self.executions=[]
  self.model_raw=bytes(model_raw);self.cert_raw=bytes(cert_raw)
  self.sources={'PCSActionShield.lean':(ROOT/'formal/PCSActionShield.lean').read_bytes(),
    **{n:(HERE/n).read_bytes() for n in ['Progress.lean','Wire.lean','Main.lean']},'Data.lean':literal_source(model_raw,cert_raw)}
  lean=shutil.which('lean')
  if lean is None:raise ValueError('Lean 4.28.0 required; no substitute')
  self.tools={n:Path(lean).with_name(n) for n in TOOLS};self._check_tools()
  self.env={'PATH':str(Path(lean).parent)+':/usr/bin:/bin','LANG':'C.UTF-8','LEAN_PATH':str(self.out)}
  self.host_sources={n:sha((HERE/n).read_bytes()) for n in ['authority.py','certificate.py','broker.py','example.py']}
  self.axioms={};started=time.monotonic()
  try:
   for n in ['PCSActionShield.lean','Progress.lean','Wire.lean','Data.lean','Main.lean']:
    names=PROGRESS if n=='Progress.lean' else WIRE if n=='Wire.lean' else DATA if n=='Data.lean' else []
    raw=self.sources[n]+('\n'+'\n'.join('#print axioms '+t for t in names)+'\n').encode()
    (self.out/n).write_bytes(raw)
    log=self._run([self.tools['lean'],'-j1','-M2048','-D','Elab.async=false','--root='+str(self.out),'-o',n[:-5]+'.olean','-c',n[:-5]+'.c',n],90)
    if (self.out/n).read_bytes()!=raw:raise ValueError('staged source changed')
    if names:self.axioms.update(_inventory(log,names))
   self._run([self.tools['leanchecker'],'--fresh','Main'],180)
   self._run([self.tools['leanc'],'-O2','-o','supervisor',*[n+'.c' for n in ['Main','Data','Wire','Progress','PCSActionShield']]],90)
   self.artifacts={p.name:sha(p.read_bytes()) for p in self.out.iterdir() if p.is_file()}
   image=(self.out/'supervisor').read_bytes();self.binary_sha256=sha(image)
   self.fd=os.memfd_create('pcs-progress-supervisor',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
   view=memoryview(image)
   while view:view=view[os.write(self.fd,view):]
   fcntl.fcntl(self.fd,1033,SEALS);self.check()
   self.manifest=dict(format='pcs-progress-supervisor-build-v1',model_sha256=sha(model_raw),certificate_sha256=sha(cert_raw),
      sources={n:sha(b) for n,b in self.sources.items()},host_sources=dict(self.host_sources),tools=dict(TOOLS),artifacts=dict(self.artifacts),axiom_closures=json.loads(json.dumps(self.axioms)),
      fresh_objects_checked=True,kernel_checked=True,compiled_implementation_correspondence='TRUSTED_NOT_PROVED',
      executable_image='Linux sealed memfd; host/shared libraries/compiler remain trusted',pcs_authority=False,
      build_seconds=round(time.monotonic()-started,6))
   (self.out/'build.json').write_text(json.dumps(self.manifest,indent=2)+'\n');self._write_log()
  except BaseException:self._write_log();self.close();raise
 def _run(self,cmd,timeout):
  p=subprocess.run(list(map(str,cmd)),cwd=self.out,env=self.env,capture_output=True,text=True,timeout=timeout)
  self.executions.append(dict(command=list(map(str,cmd)),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
  if p.returncode:raise ValueError('Actual Lean/build process rejected: '+(p.stdout+p.stderr)[-2000:])
  return p.stdout
 def _write_log(self):
  (self.out/'executions.json').write_text(json.dumps(self.executions,indent=2)+'\n')
 def _check_tools(self):
  if {n:sha(p.read_bytes()) for n,p in self.tools.items()}!=TOOLS:raise ValueError('reviewed proof/compiler tool bytes required')
 def check(self):
  self._check_tools()
  if {n:sha((HERE/n).read_bytes()) for n in self.host_sources}!=self.host_sources:raise ValueError('host adapter source changed')
  actual={'PCSActionShield.lean':(ROOT/'formal/PCSActionShield.lean').read_bytes(),**{n:(HERE/n).read_bytes() for n in ['Progress.lean','Wire.lean','Main.lean']},'Data.lean':literal_source(self.model_raw,self.cert_raw)}
  if actual!=self.sources:raise ValueError('source/model identity changed')
  if {n:sha((self.out/n).read_bytes()) for n in self.artifacts}!=self.artifacts:raise ValueError('compiled artifact identity changed')
  if self.fd is None or fcntl.fcntl(self.fd,1034)!=SEALS:raise ValueError('native image seals missing')
 def query_raw(self,raw):
  if type(raw) is not bytes or len(raw)>32768:raise ValueError('bounded request bytes required')
  self.check()
  p=subprocess.run(['/proc/self/fd/'+str(self.fd)],pass_fds=(self.fd,),input=raw,capture_output=True,cwd=self.out,env=self.env,timeout=15)
  self.check()
  if p.returncode or p.stderr or len(p.stdout)!=6*((len(raw)+5)//6):raise ValueError('native process failed or malformed; no effect authorized')
  return p.stdout
 def query(self,state,proposal):
  r=self.query_raw(packet(state,proposal))
  if len(r)!=6 or r[0]!=1 or r[1] not in [0,1,2,3]:raise ValueError('native protocol failure')
  if r[1]!=1 and r[2:]!=bytes(4):raise ValueError('noncanonical native refusal')
  return dict(status=['HALT','SELECTED','REFUSED','MALFORMED'][r[1]],action=r[2]+256*r[3] if r[1]==1 else None,rank=r[4]+256*r[5])
 def certify(self,pairs,label='capture'):
  if not re.fullmatch('[a-z0-9_-]{1,40}',label) or not 1<=len(pairs)<=100:raise ValueError('bounded fresh capture required')
  def nums(raw):
   if type(raw) is not bytes or len(raw)>32768:raise ValueError('bounded captured bytes required')
   return '['+','.join(map(str,raw))+']'
  ins='['+','.join(nums(a) for a,b in pairs)+']';outs='['+','.join(nums(b) for a,b in pairs)+']'
  source=f'import Data\nimport Wire\nnamespace Capture\ntheorem actual : ({ins} : List (List Nat)).map (PCSProgressWire.batch PCSProgressData.spec) = {outs} := by decide\nend Capture\n#print axioms Capture.actual\n'
  p=self.out/('Capture-'+label+'.lean')
  with p.open('x') as f:f.write(source)
  self.check();log=self._run([self.tools['lean'],'-j1','-M2048','-D','maxHeartbeats=8000000','--root='+str(self.out),p],90)
  if p.read_text()!=source:raise ValueError('capture source changed')
  self.check();self._write_log();return dict(kernel_checked=True,proof_sha256=sha(source.encode()),axioms=_inventory(log,['Capture.actual']),pcs_authority=False)
 def close(self):
  if self.fd is not None:os.close(self.fd);self.fd=None
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
