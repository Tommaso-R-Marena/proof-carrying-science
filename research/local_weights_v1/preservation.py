"""Freeze every predecessor blob/mode; permit only isolated local-weight additions."""
import json
from pathlib import Path
import subprocess

BASE='68702256fe646a235e67416dd957d7af09186e8f'
ROOT=Path(__file__).resolve().parents[2]


def check():
    def tree(ref):
        raw=subprocess.check_output(['git','ls-tree','-rz','-r',ref],cwd=ROOT)
        return {r.split(b'\t',1)[1]:r.split(b'\t',1)[0] for r in raw.split(b'\0') if r}
    old,new=tree(BASE),tree('HEAD')
    if any(new.get(p)!=v for p,v in old.items()):raise ValueError('Predecessor blob or mode changed')
    if any(not(p.startswith(b'research/local_weights_v1/') or p==b'.github/workflows/pcs-local-weights-v1.yml') for p in new.keys()-old.keys()):
        raise ValueError('Unrelated addition')
    return dict(passed=True,base=BASE,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                previous_files_preserved=len(old),new_files=len(new)-len(old),production_authority=False)


if __name__=='__main__':print(json.dumps(check(),indent=2))
