"""Keep all parent artifacts/code intact; this phase adds a separate live lab."""
from pathlib import Path
import json
import subprocess

ROOT=Path(__file__).resolve().parents[2]
PARENT="98b358b0305e6c10e0935de307cd927d85c4c612"
CORE="fabc704efdbda4c8822881366e4db3d3e31f066a"
PREFIX=b"research/live_agent_lab_v3/"
WORKFLOW=b".github/workflows/pcs-live-agent-lab.yml"


def check():
    def git(*a):return subprocess.check_output(["git",*a],cwd=ROOT)
    def tree(ref):return {l.split(b"\t",1)[1]:l.split(b"\t",1)[0] for l in git("ls-tree","-rz",ref).split(b"\0") if l}
    old,core,new=tree(PARENT),tree(CORE),tree("HEAD")
    if any(new.get(n)!=v for n,v in old.items()) or any(new.get(n)!=v for n,v in core.items()):raise ValueError("Parent/core blob or mode changed")
    if any(n and (n in old or not(n.startswith(PREFIX) or n==WORKFLOW)) for n in git("diff","--name-only","-z",PARENT).split(b"\0")):
        raise ValueError("Change outside additions-only lab boundary")
    return dict(parent=PARENT,parent_files_preserved=len(old),core_files_preserved=len(core),existing_files_modified=0,production_authority_changed=False)


if __name__=="__main__":print(json.dumps(check()))
