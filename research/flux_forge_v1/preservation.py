"""Pin all existing source except an explicit research UI/workflow allowlist."""
import json
from pathlib import Path
import subprocess
from research.flux_detective_v1.preservation import check as prior_check

ROOT=Path(__file__).resolve().parents[2]
BASE='31290f7ac90fde96193e0f21d6fc9f0ef2bcc4ec'
ALLOW={'.github/workflows/pcs-flux-detective-v1.yml',*(f'research/flux_detective_v1/{name}' for name in ('README.md','app.mjs','index.html','style.css','test_browser.mjs'))}


def check():
    prior=prior_check()
    def tree(ref):
        raw=subprocess.check_output(['git','ls-tree','-rz','-r',ref],cwd=ROOT)
        return {e.split(b'\t',1)[1].decode():e.split(b'\t',1)[0] for e in raw.split(b'\0') if e}
    old,new=tree(BASE),tree('HEAD')
    changes=[name for name in old if old[name]!=new.get(name)]
    if set(changes)-ALLOW:raise ValueError('Change outside reviewed research UI/workflow boundary')
    if any(name not in new for name in old):raise ValueError('Predecessor deletion forbidden')
    return dict(base=BASE,head=prior['head'],predecessor_files_preserved=prior['predecessor_files_and_modes_preserved'],
      previous_ui_files_preserved=len(old)-len(changes),allowed_ui_workflow_changes=sorted(changes),new_files=len(new)-len(old),passed=True,production_authority=False)


if __name__=='__main__':print(json.dumps(check(),indent=2))
