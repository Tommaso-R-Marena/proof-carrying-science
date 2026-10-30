"""The public study adds files only; all existing PR189 bytes and modes remain."""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
PARENT='1e165ba06b4833a0e3fbcca2f654b581837acb68'
ALLOWED=('research/public_study_validation_v1/','research/public_study_validation_v1_results/',
         '.github/workflows/pcs-public-study-validation.yml')


def check():
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
    def tree(ref):return {line.split(b'\t',1)[1]:line.split(b'\t',1)[0] for line in git('ls-tree','-rz',ref).split(b'\0') if line}
    old,new=tree(PARENT),tree('HEAD')
    if any(new.get(name)!=identity for name,identity in old.items()):raise ValueError('parent byte/mode changed')
    if any(not name.startswith(ALLOWED) for name in git('diff','--name-only',PARENT).decode().splitlines()):
        raise ValueError('change outside additive study boundary')
    return dict(parent=PARENT,parent_files_preserved=len(old),production_authority_changed=False)


if __name__=='__main__':print(json.dumps(check()))
