"""No predecessor authority, artifact or file-mode changes."""
import json
from pathlib import Path
import subprocess

BASE='5a0dad902c89917298179c269680954ddb5e22b8'
ROOT=Path(__file__).resolve().parents[2]
def check():
    def tree(ref):
        raw=subprocess.check_output(['git','ls-tree','-rz','-r',ref],cwd=ROOT)
        return {x.split(b'\t',1)[1]:x.split(b'\t',1)[0] for x in raw.split(b'\0') if x}
    old,new=tree(BASE),tree('HEAD')
    if any(new.get(p)!=v for p,v in old.items()):raise ValueError('Predecessor blob/mode changed')
    if any(not(p.startswith(b'research/causal_firewall_v1/') or p==b'.github/workflows/pcs-causal-firewall-v1.yml') for p in new.keys()-old.keys()):raise ValueError('Unrelated addition')
    return dict(passed=True,base=BASE,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                previous_files_preserved=len(old),new_files=len(new)-len(old),production_authority=False)
if __name__=='__main__':print(json.dumps(check(),indent=2))
