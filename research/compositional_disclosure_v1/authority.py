"""Fixed pinned-tool Lean byte authority; no caller-selected verifier."""
import fcntl,json,os,re,shutil,subprocess
from pathlib import Path
from pcs.transport_kernel_v1 import _inventory
from research.llm_firewall_v1.monitor import Monitor,digest,F_ADD_SEALS,F_GET_SEALS,REQUIRED_SEALS

HERE=Path(__file__).resolve().parent
NAMES=('actual_retained', 'safe_all_cells', 'step_preserves_ambiguity', 'arbitrary_history_preserves_actual', 'arbitrary_history_preserves_ambiguity', 'ambiguity_has_two_witnesses', 'cannot_determine_protected_bit', 'denial_independent_of_actual', 'accepted_answer_exact', 'denied_changes_nothing', 'step_candidate_exact', 'same_output_same_posterior', 'posterior_exact', 'all_three_individually_safe', 'stateless_composition_discloses', 'ledger_blocks_composition', 'initial_ambiguous', 'malformed_refuses', 'adaptive_retains_actual', 'adaptive_preserves_ambiguity', 'adaptive_posterior_exact', 'adaptive_public_transcript_has_both_secrets')
THEOREMS=["PCSDisclosure."+n for n in NAMES]

def packet(k,w,q):
    if any(type(v) is not int or not 0<=v<=bound for v,bound in zip((k,w,q),(65535,15,15))):raise ValueError("Exact bounded request")
    return bytes((4,k%256,k//256,w,q))

class Authority(Monitor):
    def __init__(self,out):
        self.out=Path(out).resolve();self.out.mkdir(parents=True,exist_ok=False);self.executions=[];self.fd=None
        self.sources={n:(HERE/n).read_bytes() for n in ['Ledger.lean','Main.lean']}
        lean=shutil.which('lean')
        if lean is None:raise ValueError('Pinned Lean4.28 required')
        self.tools={n:Path(lean).with_name(n) for n in ['lean','leanchecker','leanc']};self.tool_hashes=self._tools()
        self.env={'PATH':str(Path(lean).parent)+':/usr/bin:/bin','LANG':'C.UTF-8','LEAN_PATH':str(self.out)}
        try:
            for n,raw in self.sources.items():
                if n=='Ledger.lean':raw+=('\n'+'\n'.join('#print axioms '+t for t in THEOREMS)+'\n').encode()
                (self.out/n).write_bytes(raw)
                log=self._run([self.tools['lean'],'-j1','-M2048','-D','Elab.async=false','--root='+str(self.out),'-o',Path(n).with_suffix('.olean'),'-c',Path(n).with_suffix('.c'),n],60)
                if (self.out/n).read_bytes()!=raw:raise ValueError('Staged source changed')
                if n=='Ledger.lean':self.axioms=_inventory(log,THEOREMS)
            self._run([self.tools['leanc'],'-O2','-o','authority','Main.c','Ledger.c'],60)
            self.binary=self.out/'authority';image=self.binary.read_bytes()
            self.fd=os.memfd_create('pcs-disclosure-ledger',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
            view=memoryview(image)
            while view:view=view[os.write(self.fd,view):]
            fcntl.fcntl(self.fd,F_ADD_SEALS,REQUIRED_SEALS)
            self.artifacts={p.name:digest(p.read_bytes()) for p in self.out.iterdir() if p.is_file()};self.check()
            (self.out/'build.json').write_text(json.dumps(dict(artifacts=self.artifacts,source_sha256={n:digest(b) for n,b in self.sources.items()},tool_sha256=self.tool_hashes,axiom_closures=self.axioms,seals=REQUIRED_SEALS,host_refinement_proved=False),indent=2)+'\n')
        except BaseException:self.close();raise
    def check(self):
        if self.sources!={n:(HERE/n).read_bytes() for n in self.sources}:raise ValueError('Reviewed ledger sources changed')
        if self.tool_hashes!=self._tools():raise ValueError('Proof tools changed')
        if self.artifacts!={n:digest((self.out/n).read_bytes()) for n in self.artifacts}:raise ValueError('Native release artifacts changed')
    def query(self,request):
        if type(request) is not bytes or not 1<=len(request)<=327680:raise ValueError('Bounded native packet batch required')
        self.check()
        if fcntl.fcntl(self.fd,F_GET_SEALS)!=REQUIRED_SEALS:raise ValueError('Native image seals absent')
        p=subprocess.run(['/proc/self/fd/'+str(self.fd)],pass_fds=(self.fd,),input=request,capture_output=True,cwd=self.out,env=self.env,timeout=30)
        self.check();r=p.stdout
        if p.returncode or p.stderr or len(r)!=5*((len(request)+4)//5):raise ValueError('Actual native authority refused/malformed')
        for i in range(0,len(r),5):
            if r[i]!=4 or r[i+1] not in {0,1,2} or (r[i+1]!=1 and r[i+4]!=255) or (r[i+1]==1 and r[i+4]>4):raise ValueError('Invalid native reply')
        return r
    def audit_objects(self):
        self.check();self._run([self.tools['leanchecker'],'--fresh','Ledger'],180);self.check()
        d=dict(fresh_object_checked=True,axiom_closures=self.axioms,tool_sha256=self.tool_hashes,executions=self.executions)
        (self.out/'audit.json').write_text(json.dumps(d,indent=2)+'\n');return d
    def certify(self,pairs,label):
        if not re.fullmatch('[a-z0-9_-]{1,80}',label) or not 1<=len(pairs)<=64:raise ValueError('Bounded fresh proof required')
        def bs(b):
            if type(b) is not bytes or len(b)>65536:raise ValueError('Bounded literal bytes required')
            return '['+','.join(map(str,b))+']'
        ins='['+','.join(bs(a) for a,b in pairs)+']';outs='['+','.join(bs(b) for a,b in pairs)+']'
        raw=f'import Ledger\nopen PCSDisclosure\ntheorem actual : ({ins} : List (List UInt8)).map process = {outs} := by decide\n#print axioms actual\n'
        p=self.out/('Capture-'+label+'.lean')
        if p.exists():raise ValueError('Fresh proof name required')
        p.write_text(raw);self.check()
        log=self._run([self.tools['lean'],'-j1','-M2048','-D','Elab.async=false','--root='+str(self.out),p],60)
        if p.read_text()!=raw:raise ValueError('Concrete proof changed')
        self.check();d=dict(kernel_checked=True,proof_sha256=digest(raw.encode()),axiom_closures=_inventory(log,['actual']))
        (self.out/'executions.json').write_text(json.dumps(self.executions,indent=2)+'\n');return d
