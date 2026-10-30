"""Keep every protected predecessor blob/mode unchanged; additions only."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[2]
BASE='fabc704efdbda4c8822881366e4db3d3e31f066a'
ALLOWED=('research/progress_supervisor_v1/','.github/workflows/pcs-progress-supervisor.yml')

def check():
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
    def tree(ref):return {line.split(b'\t',1)[1]:line.split(b'\t',1)[0] for line in git('ls-tree','-rz',ref).split(b'\0') if line}
    old,new=tree(BASE),tree('HEAD')
    if any(new.get(n)!=v for n,v in old.items()):raise ValueError('predecessor blob/mode changed')
    names=git('diff','--name-only',BASE).decode().splitlines()
    if any(not n.startswith(ALLOWED) for n in names):raise ValueError('change outside isolated research boundary')
    return dict(baseline=BASE,predecessor_files_preserved=len(old),production_authority_changed=False)
if __name__=='__main__':print(json.dumps(check()))
