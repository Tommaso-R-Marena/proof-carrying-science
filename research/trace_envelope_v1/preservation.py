"""This successor may add research files; every PR172 blob and mode is frozen."""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
BASE='c49308fa958703e8d90d8662232995ec6460a5cd'


def check():
    def tree(ref):
        raw=subprocess.check_output(['git','ls-tree','-rz','-r',ref],cwd=ROOT)
        return {x.split(b'\t',1)[1]:x.split(b'\t',1)[0] for x in raw.split(b'\0') if x}
    old,new=tree(BASE),tree('HEAD')
    if any(new.get(p)!=mode for p,mode in old.items()):
        raise ValueError('Every predecessor blob and mode must remain unchanged')
    allowed=lambda p: p.startswith(b'research/trace_envelope_v1/') or p==b'.github/workflows/pcs-trace-envelope-v1.yml'
    if any(not allowed(p) for p in new.keys()-old.keys()):
        raise ValueError('Only isolated envelope research additions allowed')
    return dict(base=BASE,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                passed=True,previous_files_preserved=len(old),new_files=len(new)-len(old),production_authority=False)


if __name__=='__main__':print(json.dumps(check(),indent=2))
