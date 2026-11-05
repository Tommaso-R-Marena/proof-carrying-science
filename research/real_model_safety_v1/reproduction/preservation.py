"""Additions-only phase boundary protecting every PR #185 and core blob/mode.

The preceding supervisor phase's narrower directory policy remains unchanged.
This phase adds a separate experiment; no existing file may change.
"""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
PARENT="d9fc04c9cf77162bf1130d0c6c9d5d4e53d13733"
CORE="fabc704efdbda4c8822881366e4db3d3e31f066a"
WORKFLOW=b".github/workflows/pcs-real-model-safety.yml"
PREFIX=b"research/real_model_safety_v1/"


def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT)


def tree(ref):
    return {line.split(b"\t",1)[1]:line.split(b"\t",1)[0]
            for line in git("ls-tree","-rz",ref).split(b"\0") if line}


def check():
    parent,core,head=tree(PARENT),tree(CORE),tree("HEAD")
    if any(head.get(n)!=v for n,v in parent.items()):
        raise ValueError("parent blob/mode changed")
    if any(head.get(n)!=v for n,v in core.items()):
        raise ValueError("protected core blob/mode changed")
    # git diff <parent> includes staged/unstaged edits as well as commits.
    # Any preexisting pathname is forbidden, even if it falls under a new prefix.
    names=git("diff","--name-only","-z",PARENT).split(b"\0")
    if any(n and (n in parent or not (n.startswith(PREFIX) or n==WORKFLOW)) for n in names):
        raise ValueError("change outside additions-only experiment boundary")
    return dict(parent=PARENT,parent_files_preserved=len(parent),core=CORE,
                protected_core_files_preserved=len(core),existing_files_modified=0,
                production_authority_changed=False)


if __name__=="__main__":
    print(json.dumps(check()))
