"""Ordinary-kernel proof of the exact recorded abstract path, not SQL correctness."""
import re
from pathlib import Path
from .certificate import sha,load_certificate
from pcs.transport_kernel_v1 import _inventory

def certify_path(authority,records,label='workflow',*,proof_dir=None):
    if type(label) is not str or re.fullmatch('[a-z0-9_-]{1,40}',label) is None:raise ValueError('safe fixed proof label required')
    if not records or len(records)>32:raise ValueError('bounded nonempty captured path required')
    m,c=load_certificate(authority.model_raw,authority.cert_raw)
    edges={(e['source'],e['action'],e['target']) for e in m['transitions']};allowed={tuple(p) for p in c['allowed']}
    start=records[0]['source'];state=start
    if start not in m['initial']:raise ValueError('captured path has no declared initial state')
    for r in records:
        if any(type(r[k]) is not int or not 0<=r[k]<65536 for k in ['source','action','target']):raise ValueError('exact captured IDs required')
        if r['source']!=state or (state,r['action'],r['target']) not in edges or (state,r['action']) not in allowed:raise ValueError('captured path is not admitted')
        state=r['target']
    if state not in c['goals']:raise ValueError('captured path has not completed')
    body='\n'.join(f'  apply Path.cons ⟨{r["source"]},{r["action"]},{r["target"]}⟩ rfl (by decide) (by decide)' for r in records)
    text=f'''import Data
open PCSProgress PCSProgressData
namespace CapturedPath
theorem path : Path spec {len(records)} {start} {state} := by
{body}
  exact Path.nil {state}
theorem bounded : rank spec {state} + {len(records)} ≤ rank spec {start} :=
  (path_bound certificate_checked path (by decide)).2
theorem completed : {state} ∈ spec.goals ∧ {state} ∈ spec.base.safe := by decide
end CapturedPath
#print axioms CapturedPath.path
#print axioms CapturedPath.bounded
#print axioms CapturedPath.completed
'''
    directory=authority.out if proof_dir is None else Path(proof_dir).resolve()
    directory.mkdir(parents=True,exist_ok=True)
    p=directory/('Path-'+label+'.lean')
    with p.open('x') as f:f.write(text)
    authority.check();log=authority._run([authority.tools['lean'],'-j1','-M2048','--root='+str(directory),p],60)
    if p.read_text()!=text:raise ValueError('captured proof changed')
    authority.check();authority._write_log()
    return dict(kernel_checked=True,proof_sha256=sha(text.encode()),axiom_closures=_inventory(log,['CapturedPath.path','CapturedPath.bounded','CapturedPath.completed']),pcs_authority=False)
