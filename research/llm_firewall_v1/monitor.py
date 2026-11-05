"""Build and execute the proved Lean monitor; never accept a submitted verifier."""
from __future__ import annotations

from hashlib import sha256
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from research.trace_lab_v1.audit import pinned_tool
from pcs.transport_kernel_v1 import _inventory

HERE=Path(__file__).resolve().parent
LEANC_SHA256='871b10499518fd713bb1088dd98ca2833efdc0c6342cf972b056ef2224b4057d'
# Linux UAPI values (linux/fcntl.h); some Python builds omit the named constants.
F_ADD_SEALS=1033
F_GET_SEALS=1034
REQUIRED_SEALS=1|2|4|8  # SEAL_SEAL, SEAL_SHRINK, SEAL_GROW, SEAL_WRITE.
THEOREMS=['PCSLLMFirewall.'+n for n in (
    'step_facts','step_valid','step_budget','step_generation','step_forbidden',
    'step_taint','step_private','step_no_public','history_forbidden','history_budget',
    'history_generation','history_valid','initial_history_bound','history_taint','history_no_public','private_blocks_suffix',
    'initial_publish_permitted','tainted_publish_refuses',
    'action_roundtrip','decode_encode','malformed_refuses','process_decoded',
    'process_accepts','process_sound','wire_forbidden','run_sound')]


def digest(b):return sha256(b).hexdigest()


class Monitor:
    """Trusted harness-owned build. No model/API input chooses its executable.

    File/object privacy and hashes do not protect against a malicious same-user
    process, administrator, compiler, shared library or OS.
    """
    def __init__(self,out:Path):
        if sys.platform!='linux':raise ValueError('Reviewed Linux executable/sealing path required')
        self.out=Path(out).resolve();self.out.mkdir(parents=True,exist_ok=False)
        start=time.monotonic();self.executions=[]
        self.sources={n:(HERE/n).read_bytes() for n in ['Policy.lean','Main.lean']}
        lean=shutil.which('lean')
        if lean is None:raise ValueError('Lean4.28.0 must be activated; no automatic substitute')
        self.tools={n:Path(lean).with_name(n) for n in ['lean','leanchecker','leanc']}
        self.tool_hashes=self._tools()
        self.env={k:v for k,v in os.environ.items() if not k.startswith(('LD_','DYLD_'))}
        self.env['LEAN_PATH']=str(self.out)  # Only Std from the pinned distribution.
        self.audited=self.sources['Policy.lean']+('\n'+'\n'.join('#print axioms '+n for n in THEOREMS)+'\n').encode()
        for name,raw in [('Policy.lean',self.audited),('Main.lean',self.sources['Main.lean'])]:
            (self.out/name).write_bytes(raw)
            log=self._run([self.tools['lean'],'-j1','-M2048','-D','Elab.async=false',
                           '--root='+str(self.out),'-o',Path(name).with_suffix('.olean'),
                           '-c',Path(name).with_suffix('.c'),name],60)
            if (self.out/name).read_bytes()!=raw:raise ValueError('Staged Lean source changed')
            if name=='Policy.lean':self.axioms=_inventory(log,THEOREMS)
        self._run([self.tools['leanc'],'-O2','-o','monitor','Main.c','Policy.c'],60)
        self.binary=self.out/'monitor';self.binary_hash=digest(self.binary.read_bytes())
        image=self.binary.read_bytes()
        self.fd=os.memfd_create('pcs-lean-firewall',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
        view=memoryview(image)
        while view:
            view=view[os.write(self.fd,view):]
        self.seals=REQUIRED_SEALS
        fcntl.fcntl(self.fd,F_ADD_SEALS,self.seals)
        self.artifacts={n:digest((self.out/n).read_bytes()) for n in
                        ['Policy.lean','Main.lean','Policy.olean','Main.olean','Policy.c','Main.c','monitor']}
        self.check()
        self.manifest=dict(format='pcs-llm-firewall-build-v1',
            source_sha256={n:digest(b) for n,b in self.sources.items()},tool_sha256=self.tool_hashes,
            artifacts=self.artifacts,axiom_closures=self.axioms,
            kernel_checked=True,compiler_refinement='TRUSTED_NOT_PROVED',
            same_host_not_immutable=True,production_authority=False,
            executable_image='Linux sealed memfd',seals=self.seals,
            build_seconds=round(time.monotonic()-start,6),executions=self.executions)
        (self.out/'build.json').write_text(json.dumps(self.manifest,indent=2)+'\n')

    def _tools(self):
        h={n:pinned_tool(n,self.tools[n]) for n in ['lean','leanchecker']}
        h['leanc']=digest(self.tools['leanc'].read_bytes())
        if h['leanc']!=LEANC_SHA256:raise ValueError('Reviewed Linux x86_64 leanc bytes required')
        return h

    def _run(self,cmd,timeout):
        p=subprocess.run(list(map(str,cmd)),cwd=self.out,env=self.env,text=True,
                         capture_output=True,timeout=timeout)
        self.executions.append(dict(command=list(map(str,cmd)),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
        if p.returncode:raise ValueError('Actual Lean/build process rejected: '+p.stdout[-1500:]+p.stderr[-500:])
        return p.stdout

    def check(self):
        if self.sources!={n:(HERE/n).read_bytes() for n in self.sources}:raise ValueError('Reviewed monitor sources changed')
        if self.tool_hashes!=self._tools():raise ValueError('Tool bytes changed')
        if self.artifacts!={n:digest((self.out/n).read_bytes()) for n in self.artifacts}:raise ValueError('Built monitor artifacts changed')

    def query(self,request:bytes):
        if type(request) is not bytes or len(request)>4096:raise ValueError('Bounded captured request bytes required')
        self.check()
        if fcntl.fcntl(self.fd,F_GET_SEALS)&self.seals!=self.seals:
            raise ValueError('Executable image lost required kernel seals')
        p=subprocess.run(['/proc/self/fd/'+str(self.fd)],pass_fds=(self.fd,),
                         input=request,capture_output=True,timeout=3,cwd=self.out,env=self.env)
        self.check()
        if p.returncode or p.stderr or len(p.stdout)!=6:raise ValueError('Monitor refused/failed; no effect permitted')
        return p.stdout

    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None

    def audit_objects(self):
        self.check();self._run([self.tools['leanchecker'],'--fresh','Policy'],180);self.check()
        result=dict(format='pcs-llm-firewall-audit-v1',kernel_checked=True,
                    fresh_object_checked=True,axiom_closures=self.axioms,
                    tool_sha256=self.tool_hashes,executions=self.executions,production_authority=False)
        (self.out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');return result

    def certify(self,actions:list[int],label:str):
        """Fresh ordinary-kernel proof of a captured accepted-action sequence."""
        if not re.fullmatch(r'[a-z0-9_-]{1,80}',label):raise ValueError('Fixed safe proof label required')
        if len(actions)>8 or any(type(a) is not int or not 0<=a<8 for a in actions):raise ValueError('Bounded action IDs required')
        self.check()
        names=['readPublic','readPrivate','writePrivate','publish','finish','deleteProtected','network','grantAdmin']
        literal='['+', '.join('Action.'+names[a] for a in actions)+']'
        final=f"⟨{len(actions)}, {max(0,8-sum(2 if a==3 else 1 for a in actions))}, {'true' if 1 in actions else 'false'}⟩"
        text=f'''import Policy
namespace CapturedRun
open PCSLLMFirewall
def actions : List Action := {literal}
theorem accepted : run initial actions = some {final} := by decide
theorem safe : ∃ s, History initial actions s ∧
    (∀ a ∈ actions, forbidden a = false) ∧
    s.remaining + (actions.map cost).sum = 8 := by
  have hh := run_sound accepted
  exact ⟨_,hh,history_forbidden hh,history_budget hh⟩
end CapturedRun
#print axioms CapturedRun.accepted
#print axioms CapturedRun.safe
'''
        path=self.out/('Trace-'+label+'.lean')
        if path.exists():raise ValueError('Fresh captured trace proof required')
        path.write_text(text)
        stdout=self._run([self.tools['lean'],'-j1','-M2048','-D','Elab.async=false',
                          '--root='+str(self.out),path],30)
        if path.read_text()!=text:raise ValueError('Captured trace proof changed')
        self.check()
        return dict(kernel_checked=True,actions=actions,proof_sha256=digest(text.encode()),
                    axiom_closures=_inventory(stdout,['CapturedRun.accepted','CapturedRun.safe']),
                    production_authority=False)
