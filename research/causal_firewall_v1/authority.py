"""Compile the proved byte-effect function; never accept a submitted authority."""
from __future__ import annotations

from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from pcs.transport_kernel_v1 import _inventory
from research.llm_firewall_v1.monitor import Monitor,THEOREMS as OLD_THEOREMS,digest,F_ADD_SEALS,F_GET_SEALS,REQUIRED_SEALS

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'llm_firewall_v1'
NAMES=('execute_refines','execute_forbidden','execute_budget','execute_exact_private','execute_exact_public',
       'execute_private_read','execute_tainted_no_public','execute_taint_persists','execute_secret_independent',
       'drive_tainted_empty','causal_public_noninterference','runEffects_refines',
       'untracked_initial_memory_counterexample','private_feedback_can_distinguish_secrets',
       'field_roundtrip','request_roundtrip','malformed_request_refuses','wire_effect_sound','wire_public_payload_bound')
THEOREMS=['PCSCausalFirewall.'+n for n in NAMES]


def field(b):
    if type(b) is not bytes or len(b)>1024:raise ValueError('Bounded exact bytes required')
    return len(b).to_bytes(2,'little')+b


def encode_request(state,action,payload,public,private):
    from research.llm_firewall_v1.broker import encode
    return b'\x02'+encode(state,action)+field(payload)+field(public)+field(private)


@dataclass(frozen=True)
class Plan:
    status:int
    after:tuple[int,int,int]
    action:int
    effect:int
    payload:bytes
    observation:bytes


def decode_reply(raw):
    if type(raw) is not bytes or not 11<=len(raw)<=2059 or raw[0]!=2 or raw[1] not in {0,1,2}:
        raise ValueError('Invalid native effect reply')
    g,b,t,a,e=raw[2:7]
    if g>8 or b>8 or t>1 or a>7 or e>2:raise ValueError('Invalid native effect header')
    rest=raw[7:];parts=[]
    for _ in range(2):
        if len(rest)<2:raise ValueError('Truncated effect field')
        n=int.from_bytes(rest[:2],'little')
        if n>1024 or len(rest)<2+n:raise ValueError('Invalid effect field length')
        parts.append(rest[2:2+n]);rest=rest[2+n:]
    if rest:raise ValueError('Trailing effect bytes')
    if (e==0 and parts[0]) or (raw[1]!=1 and (e!=0 or any(parts))):
        raise ValueError('Inconsistent denied/empty effect')
    return Plan(raw[1],(g,b,t),a,e,*parts)


class Authority(Monitor):
    """Fixed reviewed sources/tool pins; same-host native runtime remains trusted."""
    def __init__(self,out):
        self.out=Path(out).resolve();self.out.mkdir(parents=True,exist_ok=False)
        self.executions=[];self.fd=None
        self.locations={'Policy.lean':OLD/'Policy.lean','Refinement.lean':HERE/'Refinement.lean','Main.lean':HERE/'Main.lean'}
        self.sources={n:p.read_bytes() for n,p in self.locations.items()}
        lean=shutil.which('lean')
        if lean is None:raise ValueError('Reviewed Lean 4.28.0 required')
        self.tools={n:Path(lean).with_name(n) for n in ['lean','leanchecker','leanc']}
        self.tool_hashes=self._tools()
        self.env={'PATH':str(Path(lean).parent)+':/usr/bin:/bin','LANG':'C.UTF-8','LEAN_PATH':str(self.out)}
        self.axioms={}
        try:
            for name in self.sources:
                names=OLD_THEOREMS if name=='Policy.lean' else THEOREMS if name=='Refinement.lean' else []
                raw=self.sources[name]+('\n'+'\n'.join('#print axioms '+n for n in names)+'\n').encode()
                (self.out/name).write_bytes(raw)
                log=self._run([self.tools['lean'],'-j1','-M2048','-D','Elab.async=false','--root='+str(self.out),
                               '-o',Path(name).with_suffix('.olean'),'-c',Path(name).with_suffix('.c'),name],60)
                if (self.out/name).read_bytes()!=raw:raise ValueError('Staged authority source changed')
                if names:self.axioms.update(_inventory(log,names))
            self._run([self.tools['leanc'],'-O2','-o','authority','Main.c','Refinement.c','Policy.c'],60)
            self.binary=self.out/'authority'
            image=self.binary.read_bytes();self.binary_hash=digest(image)
            self.fd=os.memfd_create('pcs-exact-effect-authority',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
            view=memoryview(image)
            while view:view=view[os.write(self.fd,view):]
            self.seals=REQUIRED_SEALS;fcntl.fcntl(self.fd,F_ADD_SEALS,self.seals)
            self.artifacts={p.name:digest(p.read_bytes()) for p in self.out.iterdir() if p.is_file()}
            self.check()
            (self.out/'build.json').write_text(json.dumps(dict(artifacts=self.artifacts,
                source_sha256={n:digest(b) for n,b in self.sources.items()},tool_sha256=self.tool_hashes,
                axiom_closures=self.axioms,seals=self.seals,compiler_refinement_proved=False,production_authority=False),indent=2)+'\n')
        except BaseException:self.close();raise

    def check(self):
        if self.sources!={n:p.read_bytes() for n,p in self.locations.items()}:raise ValueError('Authority sources changed')
        if self.tool_hashes!=self._tools():raise ValueError('Proof/compiler tools changed')
        if self.artifacts!={n:digest((self.out/n).read_bytes()) for n in self.artifacts}:raise ValueError('Built authority changed')

    def query(self,request):
        if type(request) is not bytes or len(request)>4096:raise ValueError('Bounded native packet required')
        self.check()
        if fcntl.fcntl(self.fd,F_GET_SEALS)&self.seals!=self.seals:raise ValueError('Native authority seals unavailable')
        p=subprocess.run(['/proc/self/fd/'+str(self.fd)],pass_fds=(self.fd,),input=request,capture_output=True,
                         cwd=self.out,env=self.env,timeout=3)
        self.check()
        if p.returncode or p.stderr:raise ValueError('Actual authority failed; no effect permitted')
        decode_reply(p.stdout)
        return p.stdout

    def audit_objects(self):
        self.check();self._run([self.tools['leanchecker'],'--fresh','Refinement'],180);self.check()
        result=dict(fresh_object_checked=True,axiom_closures=self.axioms,tool_sha256=self.tool_hashes,
                    executions=self.executions,production_authority=False)
        (self.out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');return result

    def certify(self,intents,public,private,state,effects,label):
        if not re.fullmatch(r'[a-z0-9_-]{1,80}',label) or len(intents)>8:raise ValueError('Bounded safe proof label/history required')
        if len(effects)!=len(intents) or any(type(a) is not int or not 0<=a<8 for a,_ in intents) or any(
                type(e) is not int or e not in {0,1,2} or (e==0 and b!=b'') for e,b in effects):
            raise ValueError('Exact intent/effect constructors required')
        encode_request(state,0,b'',public,private)
        self.check();names=['readPublic','readPrivate','writePrivate','publish','finish','deleteProtected','network','grantAdmin']
        def bs(b):
            if type(b) is not bytes or len(b)>1024:raise ValueError('Bounded literal bytes required')
            return '['+','.join(map(str,b))+']'
        ins='['+', '.join('⟨Action.'+names[a]+','+bs(b)+'⟩' for a,b in intents)+']'
        es='['+', '.join('Effect.none' if e==0 else '(Effect.'+('privateWrite' if e==1 else 'publicWrite')+' '+bs(b)+')' for e,b in effects)+']'
        g,b,t=state;st=f'⟨{g},{b},{"true" if t else "false"}⟩'
        text=f'''import Refinement
namespace CapturedEffects
open PCSLLMFirewall PCSCausalFirewall
def world : World := ⟨initial,{bs(public)},{bs(private)}⟩
def intents : List Intent := {ins}
theorem executed : runEffects world intents = some ({st},{es}) := by decide
theorem safe : History initial (intents.map Intent.action) {st} := runEffects_refines executed
end CapturedEffects
#print axioms CapturedEffects.executed
#print axioms CapturedEffects.safe
'''
        path=self.out/('Effects-'+label+'.lean')
        if path.exists():raise ValueError('Fresh effect proof required')
        path.write_text(text)
        log=self._run([self.tools['lean'],'-j1','-M2048','-D','Elab.async=false','--root='+str(self.out),path],60)
        if path.read_text()!=text:raise ValueError('Effect proof source changed')
        self.check()
        result=dict(kernel_checked=True,proof_sha256=digest(text.encode()),
                    axiom_closures=_inventory(log,['CapturedEffects.executed','CapturedEffects.safe']),production_authority=False)
        # Persist actual compiler/checker stdout, including every concrete proof.
        (self.out/'executions.json').write_text(json.dumps(self.executions,indent=2)+'\n')
        return result
