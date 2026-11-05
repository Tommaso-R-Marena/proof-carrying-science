"""Preserve every pre-game source and allow only reviewed lab UI/workflow edits."""
import json
from pathlib import Path
import subprocess
from research.flux_forge_v1.preservation import check as prior_check
ROOT=Path(__file__).resolve().parents[2]
BASE='a84b485a4b7b84a6eb69e05a3ee7bcc26d5bf71b'
ALLOW={'.github/workflows/pcs-flux-detective-v1.yml',*(f'research/flux_detective_v1/{n}' for n in ('README.md','app.mjs','index.html','style.css','test_browser.mjs'))}

def check():
    previous=prior_check()
    def tree(ref):
        raw=subprocess.check_output(['git','ls-tree','-rz','-r',ref],cwd=ROOT)
        return {x.split(b'\t',1)[1].decode():x.split(b'\t',1)[0] for x in raw.split(b'\0') if x}
    old,new=tree(BASE),tree('HEAD');changed=[p for p in old if old[p]!=new.get(p)]
    if set(changed)-ALLOW or any(p not in new for p in old):raise ValueError('Unexpected predecessor change or deletion')
    return dict(base=BASE,head=previous['head'],passed=True,pre_game_files_preserved=previous['predecessor_files_preserved'],previous_files_preserved=len(old)-len(changed),allowed_ui_workflow_changes=sorted(changed),new_files=len(new)-len(old),production_authority=False)

if __name__=='__main__':print(json.dumps(check(),indent=2))
