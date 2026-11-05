"""Preserve every parent blob/mode; additions only in this isolated phase."""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
PARENT="dda1beb58df270e7a7265188dd8052cdf1f23545"
CORE="fabc704efdbda4c8822881366e4db3d3e31f066a"
PREFIX=b"research/real_model_execution_v2/"
WORKFLOW=b".github/workflows/pcs-model-execution.yml"


def check():
    def git(*args):return subprocess.check_output(["git",*args],cwd=ROOT)
    def tree(ref):return {line.split(b"\t",1)[1]:line.split(b"\t",1)[0]
                          for line in git("ls-tree","-rz",ref).split(b"\0") if line}
    old,core,new=tree(PARENT),tree(CORE),tree("HEAD")
    if any(new.get(n)!=v for n,v in old.items()) or any(new.get(n)!=v for n,v in core.items()):
        raise ValueError("parent/core blob or mode changed")
    names=git("diff","--name-only","-z",PARENT).split(b"\0")
    if any(n and (n in old or not(n.startswith(PREFIX) or n==WORKFLOW)) for n in names):
        raise ValueError("change outside additions-only execution phase")
    return dict(parent=PARENT,parent_files_preserved=len(old),protected_core_files_preserved=len(core),
                existing_files_modified=0,production_authority_changed=False)


if __name__=="__main__":print(json.dumps(check()))
