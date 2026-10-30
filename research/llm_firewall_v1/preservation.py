"""Additions only; freeze every predecessor blob and file mode, including PGSI."""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
BASE='6d7ef2a23bbe674813ed8ee38fdc46b21068e404'


def check():
    def tree(ref):
        raw=subprocess.check_output(['git','ls-tree','-rz','-r',ref],cwd=ROOT)
        return {x.split(b'\t',1)[1]:x.split(b'\t',1)[0] for x in raw.split(b'\0') if x}
    old,new=tree(BASE),tree('HEAD')
    if any(new.get(p)!=v for p,v in old.items()):raise ValueError('Predecessor source/mode changed or deleted')
    for p in new.keys()-old.keys():
        if not(p.startswith(b'research/llm_firewall_v1/') or p==b'.github/workflows/pcs-llm-firewall-v1.yml'):
            raise ValueError('Only isolated firewall research additions permitted')
    return dict(base=BASE,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                passed=True,previous_files_preserved=len(old),new_files=len(new)-len(old),production_authority=False)


if __name__=='__main__':print(json.dumps(check(),indent=2))
