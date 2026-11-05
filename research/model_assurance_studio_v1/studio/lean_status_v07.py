"""Qualified kernel check of trusted generated source, with exact named axiom audits.

Not an ONNX/parser/IEEE/host proof, independently administered root, or sandbox.
The original v0.7 source artifacts remain historical and are never overwritten.
"""
from __future__ import annotations
import hashlib,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
LEAN_SHA256='3e0d0d3d801675359f2d4cf9815bfdb417b20b92fdd9d48b3b14c95bbae28bbf'
LAKE_SHA256='a608ff084d7e2af228b92a29d7c2fd083ba0580e46889175ec74a81678c98359'
MATHLIB_REV='8f9d9cff6bd728b17a24e163c9402775d9e6a365'
ALLOWED={'certified_relation','certified_update_drift','bounded_update_composition'}

def _sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def _source(raw):
    text=raw.decode('utf-8')
    if len(raw)>250000 or re.search(r'\b(sorry|admit|axiom|unsafe|native_decide)\b|#(?:eval|print|check)',text):
        raise ValueError('Unapproved proof escape or command')
    if re.findall(r'^import\s+(.+)$',text,re.M)!=['Mathlib'] or not text.startswith('import Mathlib\n'):
        raise ValueError('Qualified import-first Mathlib export required')
    names=re.findall(r'^theorem\s+(\w+)\b',text,re.M)
    if len(names)!=len(set(names)) or set(names) not in [{'certified_relation','bounded_update_composition'},{'certified_update_drift','bounded_update_composition'}]:
        raise ValueError('Exact generated theorem set required')
    return text,names

def check_proof(path,project_dir=None,timeout=120):
    result={'schema':'pcs-lean-kernel-check-v0.14','source_file':str(path),'status':'NOT_RUN','kernel_checked':False,
            'pcs_authority':False,'onnx_semantics_verified':False,'runtime_conformance_established':False,
            'scope':'Abstract polytope hypotheses entail the named inequality. CSV/ONNX binding, inference and scientific truth are not proved.'}
    try:
        source=Path(path).resolve();raw=source.read_bytes();text,names=_source(raw);result['source_sha256']=_sha(source)
        selected=shutil.which('lean')
        if not selected:raise ValueError('Qualified Lean unavailable')
        lean=Path(selected).resolve();lake=lean.with_name('lake')
        if _sha(lean)!=LEAN_SHA256 or _sha(lake)!=LAKE_SHA256:raise ValueError('Unqualified Lean/Lake binary bytes')
        project=Path(project_dir or '.').resolve();lock=json.loads((project/'lake-manifest.json').read_text())
        pkg=next(p for p in lock['packages'] if p['name']=='mathlib')
        actual=subprocess.check_output(['git','-C',str(project/'.lake/packages/mathlib'),'rev-parse','HEAD'],text=True).strip()
        if pkg['rev']!=MATHLIB_REV or actual!=MATHLIB_REV:raise ValueError('Mathlib revision differs')
        version=subprocess.check_output([str(lean),'--version'],text=True).strip()
        if not version.startswith('Lean (version 4.28.0,'):raise ValueError('Lean version differs')
        query=subprocess.run([str(lake),'env','printenv','LEAN_PATH'],cwd=project,capture_output=True,text=True,timeout=timeout,check=True)
        env={**os.environ,'LEAN_PATH':query.stdout.strip().splitlines()[-1]}
        exact=subprocess.run([str(lean),str(source)],cwd=project,env=env,capture_output=True,text=True,timeout=timeout)
        if exact.returncode!=0:return dict(result,status='REJECTED',exit_code=exact.returncode,compiler_output_last_1000=(exact.stdout+exact.stderr)[-1000:])
        with tempfile.TemporaryDirectory(prefix='pcs-studio-lean-') as tmp:
            audit=Path(tmp)/'Audited.lean';audit.write_text(text+'\n'+'\n'.join('#print axioms PCSModelAssurance.'+n for n in names)+'\n')
            run=subprocess.run([str(lean),str(audit)],cwd=project,env=env,capture_output=True,text=True,timeout=timeout)
        if run.returncode!=0 or 'sorry' in run.stdout+run.stderr:raise ValueError('Axiom audit compilation failed')
        found={}
        for line in run.stdout.splitlines():
            m=re.fullmatch(r"'PCSModelAssurance\.([^']+)' (?:does not depend on any axioms|depends on axioms: \[([^\]]+)\])",line)
            if m:
                deps=[] if m[2] is None else m[2].split(', ')
                if m[1] in found or not set(deps)<={'propext','Classical.choice','Quot.sound'}:raise ValueError('Unexpected axiom dependency')
                found[m[1]]=deps
        if set(found)!=set(names) or _sha(source)!=result['source_sha256'] or _sha(lean)!=LEAN_SHA256 or _sha(lake)!=LAKE_SHA256:raise ValueError('Source/tool binding or exact theorem audit differs')
        return dict(result,status='KERNEL_CHECKED',kernel_checked=True,exit_code=0,compiler_sha256=LEAN_SHA256,lake_sha256=LAKE_SHA256,
                    mathlib_revision=MATHLIB_REV,version=version,axiom_audits=found,host_and_compiled_libraries_trusted=True)
    except (ValueError,OSError,KeyError,StopIteration,subprocess.SubprocessError,UnicodeError) as exc:
        return dict(result,reason=type(exc).__name__+': '+str(exc)[:350])

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('lean_file');p.add_argument('--project-dir');p.add_argument('--timeout',type=int,default=120)
    a=p.parse_args();v=check_proof(a.lean_file,a.project_dir,a.timeout);print(json.dumps(v,indent=2));return 0 if v['kernel_checked'] else 2
if __name__=='__main__':raise SystemExit(main())
