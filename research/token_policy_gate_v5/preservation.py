"""Strict additive phase boundary on the fully qualified PR #189 head."""
from pathlib import Path
import json
import subprocess

ROOT=Path(__file__).resolve().parents[2]
PARENT='1e165ba06b4833a0e3fbcca2f654b581837acb68'
ALLOWED=(b'research/token_policy_gate_v5/',b'.github/workflows/pcs-token-policy-gate.yml')


def check():
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
    def tree(ref):return {line.split(b'\t',1)[1]:line.split(b'\t',1)[0]
                          for line in git('ls-tree','-rz',ref).split(b'\0') if line}
    parent,current=tree(PARENT),tree('HEAD')
    if any(current.get(n)!=v for n,v in parent.items()):
        raise ValueError('PR189 parent blob or mode changed')
    names=[n for n in git('diff','--name-only','-z',PARENT).split(b'\0') if n]
    if any(n in parent or not any(n.startswith(prefix) if prefix.endswith(b'/') else n==prefix for prefix in ALLOWED) for n in names):
        raise ValueError('Change outside additions-only token-policy boundary')
    return dict(parent=PARENT,parent_files_preserved=len(parent),
                existing_files_modified=0,production_authority_changed=False)


if __name__=='__main__':print(json.dumps(check()))
