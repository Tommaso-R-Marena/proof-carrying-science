"""Compile captured finite-vector/trace proofs; pin actual compiler/checker bytes."""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
import subprocess,time
from pcs import transport_kernel_v1 as host
from pcs import transport_trace_kernel_v1 as trace

ROOT=Path(__file__).resolve().parents[2]
TOOLS={'lean':'3e0d0d3d801675359f2d4cf9815bfdb417b20b92fdd9d48b3b14c95bbae28bbf',
       'leanchecker':'cb6cee24e93aa1d72ad0314906c51918f7c96947e18790a0273c837c25e79025'}
VECTOR=['PCSTraceLab.'+n for n in ('at_left','at_right','elsewhere','amount_shift','quadratic_shift','energy_iff','bounds_shift','trace_reject','feasible_shift')]
PAIR=['PCSFluxForge.'+n for n in ('amount','energy_delta','energy_interval','bounds_interval','feasible_interval','nonzero_changes')]
SOURCES={'PCSReal/Transport':ROOT/'formal/real/PCSReal/Transport.lean',
 'PCSReal/TransportTrace':ROOT/'formal/real/PCSReal/TransportTrace.lean',
 'Transfer':ROOT/'research/flux_forge_v1/Transfer.lean','Vector':Path(__file__).with_name('Vector.lean')}
INVENTORIES={'PCSReal/Transport':host.GENERAL_THEOREMS,'PCSReal/TransportTrace':trace.GENERAL,'Transfer':PAIR,'Vector':VECTOR}

def sha(raw):return hashlib.sha256(raw).hexdigest()
def pinned_tool(name,path):
    digest=sha(Path(path).read_bytes())
    if digest!=TOOLS[name]:raise ValueError('Reviewed Linux x86_64 '+name+' binary bytes required')
    return digest

def audit(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    r=dict(format='pcs-trace-lab-audit-v1',kernel_checked=False,fresh_object_checked=False,pcs_authority=False,scientific_acceptance=False,executions=[],axiom_closures={})
    frozen={n:p.read_bytes() for n,p in SOURCES.items()};r['source_sha256']={n:sha(raw) for n,raw in frozen.items()}
    try:
        lean,env,version=host._environment(30);checker=Path(lean).with_name('leanchecker')
        binaries={'lean':Path(lean),'leanchecker':checker}
        r['tool_sha256']={n:pinned_tool(n,p) for n,p in binaries.items()};r['lean_version']=version
        env=dict(env,LEAN_PATH=str(out)+os.pathsep+env['LEAN_PATH'])
        def run(cmd,timeout):
            p=subprocess.run(list(map(str,cmd)),cwd=out,env=env,text=True,capture_output=True,timeout=timeout)
            r['executions'].append(dict(command=list(map(str,cmd)),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
            if p.returncode:raise ValueError('Actual proof compilation or object replay rejected')
            return p.stdout
        objects={}
        for name,raw in frozen.items():
            source=out/(name+'.lean');source.parent.mkdir(parents=True,exist_ok=True)
            source.write_bytes(raw+('\n'+'\n'.join('#print axioms '+n for n in INVENTORIES[name])+'\n').encode())
            text=run([lean,'-j1','-M2048','-D','Elab.async=false','--root='+str(out),'-o',source.with_suffix('.olean'),source],120)
            r['axiom_closures'].update(host._inventory(text,INVENTORIES[name]));objects[name]=sha(source.with_suffix('.olean').read_bytes())
        run([checker,'--fresh','Vector'],300)
        if frozen!={n:p.read_bytes() for n,p in SOURCES.items()}:raise ValueError('Source changed during audit')
        if objects!={n:sha((out/(n+'.olean')).read_bytes()) for n in objects}:raise ValueError('Object changed during replay')
        if r['tool_sha256']!={n:pinned_tool(n,p) for n,p in binaries.items()}:raise ValueError('Compiler or checker changed')
        r.update(kernel_checked=True,fresh_object_checked=True,object_sha256=objects,sources_stable=True)
    except (OSError,ValueError,subprocess.SubprocessError) as error:r['error']=f'{type(error).__name__}: {error}'
    r['wall_seconds']=time.monotonic()-started;(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args();r=audit(args.out)
    print(json.dumps({k:r.get(k) for k in ('kernel_checked','fresh_object_checked','wall_seconds','error','pcs_authority')}))
    raise SystemExit(0 if r['kernel_checked'] and r['fresh_object_checked'] else 1)

if __name__=='__main__':main()
