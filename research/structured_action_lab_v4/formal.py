"""Fresh fixed-source Lean audit and independent Python/Lean codec differential."""
import json,os,shutil,subprocess
from pathlib import Path
from research.progress_supervisor_v1.authority import TOOLS
from research.progress_supervisor_v1.certificate import sha
from pcs.transport_kernel_v1 import _inventory
from .protocol import HERE
from .codec import PAYLOADS,decode

NAMES=tuple('PCSActionFormat.'+n for n in ('roundtrip','injective','decode_sound','canonical_iff','all_octets','bypass_remains_representable','token_roundtrip','token_injective','token_decode_sound','token_byte_agreement','fixed_token_bound'))


def qualify(output):
    lean=shutil.which('lean')
    if not lean:raise ValueError('Exact Lean 4.28.0 required')
    tools={n:Path(lean).with_name(n) for n in TOOLS}
    if {n:sha(p.read_bytes()) for n,p in tools.items()}!=TOOLS:raise ValueError('Pinned tool bytes required')
    sources={n:(HERE/n).read_bytes() for n in ('ActionCodec.lean','CodecRunner.lean')}
    output.mkdir(parents=True,exist_ok=False)
    for n,raw in sources.items():(output/n).write_bytes(raw)
    env=dict(os.environ,LEAN_PATH=str(output));logs=[]
    def call(args,input=None):
        r=subprocess.run(list(map(str,args)),cwd=output,env=env,input=input,capture_output=True,text=True,timeout=180)
        logs.append(dict(command=list(map(str,args)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        (output/'executions.json').write_text(json.dumps(logs,indent=2)+'\n')
        if r.returncode:raise ValueError('Actual Lean process rejected; inspect executions.json')
        return r.stdout
    log=call([tools['lean'],'-j1','--root='+str(output),'-o','ActionCodec.olean','ActionCodec.lean'])
    inventory=_inventory(log,list(NAMES))
    if any(set(v)-{'propext'} for v in inventory.values()):raise ValueError('Unexpected codec proof assumptions')
    call([tools['leanchecker'],'--fresh','ActionCodec'])
    call([tools['lean'],'-j1','--root='+str(output),'-o','CodecRunner.olean','CodecRunner.lean'])
    call([tools['leanchecker'],'--fresh','CodecRunner'])
    # Exhaustive single-octet substitutions, every insertion/deletion, and fixed
    # adversarial encodings. This is finite differential evidence, not a proof
    # of the Rust tokenizer or Python implementation.
    variants=set(PAYLOADS)
    for p in PAYLOADS:
        for i in range(len(p)):
            variants.add(p[:i]+p[i+1:])
            for b in range(256):variants.add(p[:i]+bytes([b])+p[i+1:])
        for i in range(len(p)+1):
            for b in range(256):variants.add(p[:i]+bytes([b])+p[i:])
    variants.update((b'',b'{"action":-0}',b'{"action":00}',b'{"action":0.0}',b'{"action":true}',b'{"action":null}',b'{"action":0}\n',b'```json\n{"action":0}\n```','{"action":０}'.encode()))
    rows=sorted(variants);wire=''.join(json.dumps(list(p),separators=(',',':'))+'\n' for p in rows)
    result=call([tools['lean'],'--run','CodecRunner.lean'],wire).splitlines()
    expected=['none' if decode(p) is None else str(decode(p)) for p in rows]
    if result!=expected:raise ValueError('Python/Lean canonical codec disagreement')
    if any((HERE/n).read_bytes()!=raw or (output/n).read_bytes()!=raw for n,raw in sources.items()):raise ValueError('Formal source changed during audit')
    report=dict(format='pcs-action-format-audit-v1',kernel_checked=True,axiom_closures=inventory,differential_cases=len(rows),mismatches=0,source_sha256={n:sha(raw) for n,raw in sources.items()},pcs_authority=False,scope='Finite format codec; no theorem about neural reasoning, Python/Rust/compiler/SQL correctness or policy safety')
    (output/'audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
