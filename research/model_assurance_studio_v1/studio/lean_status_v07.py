"""Run the real Lean kernel when installed; never infer success from source generation.

Use inside a separately reviewed Lean 4.28.0 + Mathlib lake project.
Lean is not a safe sandbox for malicious source; run only this locally generated
and reviewed file in a trusted environment.
"""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess


def check_proof(path,project_dir=None,timeout=120):
    result={'schema':'pcs-lean-kernel-check-v0.7','source_file':str(path),
            'status':'NOT_RUN','kernel_checked':False}
    lake=shutil.which('lake')
    lean=shutil.which('lean')
    if not lake and not lean:return dict(result,reason='Neither lake nor Lean executable is installed')
    cmd=([lake,'env','lean',str(Path(path).resolve())] if lake else [lean,str(Path(path).resolve())])
    try:
        tool=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,timeout=timeout,cwd=project_dir)
        result['status']='KERNEL_CHECKED' if tool.returncode==0 else 'REJECTED'
        result['kernel_checked']=tool.returncode==0
        result['exit_code']=tool.returncode
        result['compiler_output_last_1000']=tool.stdout[-1000:]
        return result
    except (OSError,subprocess.TimeoutExpired) as exc:
        return dict(result,reason=type(exc).__name__)


def main():
    import argparse
    p=argparse.ArgumentParser(description='Actually compile generated Lean evidence under installed toolchain')
    p.add_argument('lean_file');p.add_argument('--project-dir');p.add_argument('--timeout',type=int,default=120)
    a=p.parse_args()
    v=check_proof(a.lean_file,a.project_dir,a.timeout)
    print(json.dumps(v,indent=2))
    return 0 if v['kernel_checked'] else 2

if __name__=='__main__':raise SystemExit(main())
