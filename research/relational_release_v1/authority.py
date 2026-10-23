"""Fixed pinned-tool Lean byte authority; no caller-selected verifier."""
import fcntl,json,os,re,shutil,subprocess
from pathlib import Path
from pcs.transport_kernel_v1 import _inventory
from research.llm_firewall_v1.monitor import Monitor,digest,F_ADD_SEALS,F_GET_SEALS,REQUIRED_SEALS

HERE=Path(__file__).resolve().parent
NAMES=('truth_gate_sound','both_representations_true','representation_channel_decodes_secret',
 'representation_channel_is_verified','representation_counterexample','unbounded_verified_representation_channel',
 'all_encoded_claims_verified','bounded_render_value','withholding_counterexample','adaptive_query_choice_counterexample','proposals_have_no_public_effect',
 'proposals_preserve_state','forced_completion_exact','canonical_depends_only_on_view',
 'scheduled_release_noninterference','post_completion_has_no_effect','finalize_once',
 'malformed_request_refuses','wire_accepted_sound','wire_claim_truth','wire_finalization_exact','closed_request_refuses')
THEOREMS=['PCSRelationalRelease.'+n for n in NAMES]

def packet(q,closed,mask,hidden,action,style=0,reported=0):
    values=(q,closed,mask,hidden,action,style,reported)
    if any(type(v) is not int or not 0<=v<=bound for v,bound in zip(values,(1,1,15,1,2,1,4))):raise ValueError('Exact bounded request required')
    if action!=1 and (style or reported):raise ValueError('Canonical unused fields required')
    return bytes((3,*values))

class Authority(Monitor):
    def __init__(self,out):
        self.out=Path(out).resolve();self.out.mkdir(parents=True,exist_ok=False);self.executions=[];self.fd=None
        self.sources={n:(HERE/n).read_bytes() for n in ['Release.lean','Main.lean']}
        lean=shutil.which('lean')
        if lean is None:raise ValueError('Pinned Lean4.28 required')
        self.tools={n:Path(lean).with_name(n) for n in ['lean','leanchecker','leanc']};self.tool_hashes=self._tools()
        self.env={'PATH':str(Path(lean).parent)+':/usr/bin:/bin','LANG':'C.UTF-8','LEAN_PATH':str(self.out)}
        try:
            for n,raw in self.sources.items():
                if n=='Release.lean':raw+=('\n'+'\n'.join('#print axioms '+t for t in THEOREMS)+'\n').encode()
                (self.out/n).write_bytes(raw)
                log=self._run([self.tools['lean'],'-j1','-M2048','-D','Elab.async=false','--root='+str(self.out),'-o',Path(n).with_suffix('.olean'),'-c',Path(n).with_suffix('.c'),n],60)
                if (self.out/n).read_bytes()!=raw:raise ValueError('Staged source changed')
                if n=='Release.lean':self.axioms=_inventory(log,THEOREMS)
            self._run([self.tools['leanc'],'-O2','-o','authority','Main.c','Release.c'],60)
            self.binary=self.out/'authority';image=self.binary.read_bytes()
            self.fd=os.memfd_create('pcs-canonical-release',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
            view=memoryview(image)
            while view:view=view[os.write(self.fd,view):]
            fcntl.fcntl(self.fd,F_ADD_SEALS,REQUIRED_SEALS)
            self.artifacts={p.name:digest(p.read_bytes()) for p in self.out.iterdir() if p.is_file()};self.check()
            (self.out/'build.json').write_text(json.dumps(dict(artifacts=self.artifacts,source_sha256={n:digest(b) for n,b in self.sources.items()},tool_sha256=self.tool_hashes,axiom_closures=self.axioms,seals=REQUIRED_SEALS,host_refinement_proved=False),indent=2)+'\n')
        except BaseException:self.close();raise
    def check(self):
        if self.sources!={n:(HERE/n).read_bytes() for n in self.sources}:raise ValueError('Reviewed release sources changed')
        if self.tool_hashes!=self._tools():raise ValueError('Proof tools changed')
        if self.artifacts!={n:digest((self.out/n).read_bytes()) for n in self.artifacts}:raise ValueError('Native release artifacts changed')
    def query(self,request):
        if type(request) is not bytes or len(request)>4096:raise ValueError('Bounded native packet required')
        self.check()
        if fcntl.fcntl(self.fd,F_GET_SEALS)!=REQUIRED_SEALS:raise ValueError('Native image seals absent')
        p=subprocess.run(['/proc/self/fd/'+str(self.fd)],pass_fds=(self.fd,),input=request,capture_output=True,cwd=self.out,env=self.env,timeout=3)
        self.check();r=p.stdout
        if p.returncode or p.stderr or not 4<=len(r)<=9 or r[0]!=3 or r[1] not in {0,1,2} or r[2]>1 or r[3]>2 or (r[1]!=1 and len(r)!=4):raise ValueError('Actual native authority refused/malformed')
        if r[1]==1 and len(r)!=9:raise ValueError('Exact byte payload required')
        return r
    def audit_objects(self):
        self.check();self._run([self.tools['leanchecker'],'--fresh','Release'],180);self.check()
        d=dict(fresh_object_checked=True,axiom_closures=self.axioms,tool_sha256=self.tool_hashes,executions=self.executions)
        (self.out/'audit.json').write_text(json.dumps(d,indent=2)+'\n');return d
    def certify(self,pairs,label):
        if not re.fullmatch('[a-z0-9_-]{1,80}',label) or not 1<=len(pairs)<=8:raise ValueError('Bounded fresh proof required')
        def bs(b):
            if type(b) is not bytes or len(b)>64:raise ValueError('Bounded literal bytes required')
            return '['+','.join(map(str,b))+']'
        ins='['+','.join(bs(a) for a,b in pairs)+']';outs='['+','.join(bs(b) for a,b in pairs)+']'
        raw=f'import Release\nopen PCSRelationalRelease\ntheorem actual : ({ins} : List (List UInt8)).map process = {outs} := by decide\n#print axioms actual\n'
        p=self.out/('Capture-'+label+'.lean')
        if p.exists():raise ValueError('Fresh proof name required')
        p.write_text(raw);self.check()
        log=self._run([self.tools['lean'],'-j1','-M2048','-D','Elab.async=false','--root='+str(self.out),p],60)
        if p.read_text()!=raw:raise ValueError('Concrete proof changed')
        self.check();d=dict(kernel_checked=True,proof_sha256=digest(raw.encode()),axiom_closures=_inventory(log,['actual']))
        (self.out/'executions.json').write_text(json.dumps(self.executions,indent=2)+'\n');return d
