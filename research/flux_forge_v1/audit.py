"""Fresh ordinary Lean proof compilation and official same-kernel object replay."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from pcs import transport_kernel_v1 as host

SOURCE=Path(__file__).with_name('Transfer.lean')
NAMES=['PCSFluxForge.'+s for s in ('amount','energy_delta','energy_interval','bounds_interval','feasible_interval','nonzero_changes')]


def audit(out: Path) -> dict:
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    result=dict(format='pcs-flux-forge-axiom-audit-v1',kernel_checked=False,fresh_object_checked=False,pcs_authority=False,scientific_acceptance=False,executions=[])
    def sha(raw):return hashlib.sha256(raw).hexdigest()
    raw=SOURCE.read_bytes();result['source_sha256']=sha(raw)
    try:
        lean,env,version=host._environment(30)
        result.update(lean_version=version,lean_sha256=sha(Path(lean).read_bytes()))
        module=out/'Transfer.lean'
        module.write_bytes(raw+('\n'+'\n'.join('#print axioms '+n for n in NAMES)+'\n').encode())
        env=dict(env,LEAN_PATH=str(out.resolve())+os.pathsep+env['LEAN_PATH'])
        def run(cmd,timeout):
            p=subprocess.run(list(map(str,cmd)),cwd=out,env=env,text=True,capture_output=True,timeout=timeout)
            result['executions'].append(dict(command=list(map(str,cmd)),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
            if p.returncode:raise ValueError('Actual Lean compilation/object replay rejected')
            return p.stdout
        text=run([lean,'-j1','-M2048','-D','Elab.async=false','--root='+str(out.resolve()),'-o',module.with_suffix('.olean'),module],120)
        result['axiom_closures']=host._inventory(text,NAMES)
        result['kernel_checked']=True
        obj=module.with_suffix('.olean');before=sha(obj.read_bytes())
        run([Path(lean).with_name('leanchecker'),'--fresh','Transfer'],300)
        if SOURCE.read_bytes()!=raw or sha(obj.read_bytes())!=before:raise ValueError('Source or object changed')
        result.update(fresh_object_checked=True,object_sha256=before,sources_stable=True)
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        result.update(kernel_checked=False,fresh_object_checked=False,error=f'{type(exc).__name__}: {exc}')
    result['wall_seconds']=time.monotonic()-start
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    result=audit(args.out)
    print(json.dumps({k:result.get(k) for k in ('kernel_checked','fresh_object_checked','wall_seconds','error','pcs_authority')}))
    raise SystemExit(0 if result['kernel_checked'] and result['fresh_object_checked'] else 1)


if __name__=='__main__':main()
