import json,subprocess
from pathlib import Path
BASE='d7ec58d968fae5051daa7fd8d4bad5b2622b02af'
ROOT=Path(__file__).resolve().parents[2]
def check():
    def tree(ref):
        raw=subprocess.check_output(['git','ls-tree','-rz','-r',ref],cwd=ROOT)
        return {x.split(b'\t',1)[1]:x.split(b'\t',1)[0] for x in raw.split(b'\0') if x}
    old,new=tree(BASE),tree('HEAD')
    if any(new.get(p)!=v for p,v in old.items()):raise ValueError('Predecessor blob/mode changed')
    if any(not(p.startswith(b'research/relational_release_v1/') or p==b'.github/workflows/pcs-relational-release-v1.yml') for p in new.keys()-old.keys()):raise ValueError('Unrelated addition')
    return dict(passed=True,base=BASE,previous_files_preserved=len(old),new_files=len(new)-len(old),production_authority=False)
if __name__=='__main__':print(json.dumps(check(),indent=2))
