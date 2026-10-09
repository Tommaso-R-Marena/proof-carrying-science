"""Compile retained adaptive Boolean repairs and reject a real false target."""
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pcs.experimental.omega.logic import lean_source

def verify(directory):
    directory=Path(directory).resolve()
    source=(directory/'Repairs.lean').read_text()
    names=re.findall(r'^theorem (adaptive_\d+) ',source,re.M)
    if not names or names!=['adaptive_'+str(i) for i in range(len(names))] or len(names)>1024:
        raise ValueError('Expected a nonempty bounded exact theorem inventory')
    version=subprocess.check_output(['lake','env','lean','--version'],cwd=ROOT/'formal',text=True)
    if 'version 4.28.0' not in version:raise ValueError('Lean 4.28.0 is required')
    subprocess.run([sys.executable,str(ROOT/'scripts/audit_lean_source.py'),str(directory/'Repairs.lean')],check=True)
    positive=subprocess.run(['lake','env','lean',str(directory/'Repairs.lean')],cwd=ROOT/'formal',capture_output=True,text=True,timeout=240)
    (directory/'lean-positive.log').write_text(positive.stdout+positive.stderr)
    if positive.returncode:raise ValueError('Actual Lean compilation failed')
    audits=re.findall(r"'([^']+)' does not depend on any axioms",positive.stdout)
    if audits!=names:raise ValueError('Unexpected or incomplete axiom inventory')
    corpus=json.loads((directory/'20261009/corpus.json').read_text())
    original=corpus['records'][0]['task']
    with tempfile.TemporaryDirectory(prefix='pcs-adaptive-negative-',dir='/tmp') as tmp:
        path=Path(tmp)/'Negative.lean';path.write_text(lean_source(original))
        negative=subprocess.run(['lake','env','lean',str(path)],cwd=ROOT/'formal',capture_output=True,text=True,timeout=60)
    (directory/'lean-negative.log').write_text(negative.stdout+negative.stderr)
    if negative.returncode==0 or 'decide' not in negative.stdout or 'error:' not in negative.stdout:
        raise ValueError('False-original control did not fail through the deciding tactic')
    result={'format':'pcs-adaptive-lean-result-v2','lean_version':version.strip(),'positive_theorems':len(names),
        'empty_axiom_inventories':len(audits),'negative_original_rejected':True,'pcs_authority':False,
        'scope':'Generated Boolean equalities only; no Python/JavaScript refinement or scientific grounding theorem'}
    (directory/'lean-result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':print(json.dumps(verify(sys.argv[1]),indent=2))
