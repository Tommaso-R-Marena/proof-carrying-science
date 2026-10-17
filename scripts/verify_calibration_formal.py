"""Audit all static calibration theorem identities and source bytes."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audit_lean_source import active_code,audit
from pcs.calibration_kernel_v1 import GENERAL,inventory
from pcs.transport_kernel_v1 import _environment,_inventory,sha

CONTROLS=['PCSReal.CalibrationControls.'+n for n in ['good_normal','wrong_coefficient_rejected',
    'exact_nonzero_residual','good_dual','wrong_dual_rejected','sharp_gain','good_minimax',
    'false_minimax_rejected','smaller_uniform_radius_impossible']]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('new audit output required')
    paths=[ROOT/'formal/real/PCSReal'/n for n in ['Calibration.lean','CalibrationControls.lean','CalibrationAudit.lean']]
    findings=audit(paths)
    if findings:raise ValueError(str(findings))
    names=GENERAL+CONTROLS;declared=[]
    for source,ns in zip(paths[:2],['PCSReal.Calibration','PCSReal.CalibrationControls']):
        declared.extend(ns+'.'+m[1] for m in re.finditer(r'(?m)^theorem (\S+)',active_code(source.read_text())))
    if len(names)!=26 or len(set(declared))!=26 or set(declared)!=set(names):raise ValueError('complete 26-name static inventory required')
    driver='import PCSReal.CalibrationControls\nset_option format.width 1000000\n\n'+''.join('#print axioms '+n+'\n' for n in names)
    if paths[-1].read_text()!=driver:raise ValueError('exact audit driver required')
    hashes={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}
    _environment(30)
    r=subprocess.run(['lake','env','lean','formal/real/PCSReal/CalibrationAudit.lean'],cwd=ROOT,
                     capture_output=True,text=True,timeout=180)
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    checked=inventory(r.stdout,names)
    if hashes!={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}:raise ValueError('sources changed during audit')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump({'format':'pcs-calibration-static-audit-v1',
        'kernel_theorems':checked,'source_sha256':hashes,'returncode':0,'stdout':r.stdout,
        'scientific_acceptance':False,'physical_model_validity':'OPEN'},f,indent=2);f.write('\n')
    print(json.dumps({'kernel_theorems':len(checked),'scientific_acceptance':False}))


if __name__=='__main__':main()
