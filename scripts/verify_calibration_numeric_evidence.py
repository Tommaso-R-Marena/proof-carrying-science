"""Recompile the retained experiment's exact numerical proof capsule.

The frozen experiment identity and the current execution identity remain distinct.
This gate grants no empirical or physical authority.
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audit_lean_source import audit,active_code
from pcs import calibration_kernel_v1 as receiver

QUALIFIED=ROOT/'research/experimental-calibration-v1/local-qualification-42f53a6'
NAMES=['PCSExperimentalCalibration.'+n for n in [
    'all_heldout_least_squares_scores_exact','all_heldout_minimax_scores_exact',
    'pooled_least_squares_scores_exact','pooled_minimax_scores_exact',
    'all_minimax_gains_bounded_by_least_squares','every_minimax_heldout_score_below_least_squares',
    'degree_2_heldout_win_count_exact','degree_3_heldout_win_count_exact',
    'every_full_data_class_exceeds_epsilon_0_01_budget']]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    if a.output.exists():raise ValueError('new numeric audit output required')
    folder=QUALIFIED/'numeric';path=folder/'NumericComparisons.lean'
    report=receiver.load_json((folder/'REPORT.json').read_bytes())
    inputs=receiver.load_json((folder/'INPUTS.json').read_bytes())
    if report['passed'] is not True or report['proof_sha256']!=receiver.sha(path.read_bytes()):
        raise ValueError('numeric proof identity mismatch')
    if report['source_head']!=inputs['source_head'] or inputs['source_head']!='42f53a634ab70ffa9994a496b1c3027d683874a3':
        raise ValueError('frozen experiment identity mismatch')
    rows=inputs['case_sources']
    if len(rows)!=22 or {r['case'] for r in rows}!={f'hull-{k:02}' for k in range(22)}:
        raise ValueError('complete frozen case identities required')
    for row in rows:
        base=QUALIFIED/'study'/row['case']
        for filename,key in [('data.csv','data_sha256'),('certificate.json','certificate_sha256'),
                ('receiving/report.json','receiving_report_sha256'),('receiving/Replay.lean','literal_proof_sha256')]:
            if receiver.sha((base/filename).read_bytes())!=row[key]:
                raise ValueError('numeric/case evidence handoff mismatch')
    if findings:=audit([path]):raise ValueError(str(findings))
    declared=['PCSExperimentalCalibration.'+m[1] for m in re.finditer(r'(?m)^theorem (\S+)',active_code(path.read_text()))]
    if len(declared)!=len(NAMES) or set(declared)!=set(NAMES):
        raise ValueError('complete exact nine-name numeric inventory required')
    allowed={'Mathlib.Data.Rat.BigOperators','Mathlib.Data.Fintype.Fin'}
    if set(re.findall(r'(?m)^import (\S+)',path.read_text()))!=allowed:
        raise ValueError('fixed numeric proof imports required')
    before=receiver.sha(path.read_bytes());lean,env,version=receiver.infrastructure._environment(30)
    r=subprocess.run([lean,'-j1','-M2048','-D','Elab.async=false',str(path)],
        cwd=ROOT,env=env,capture_output=True,text=True,timeout=180)
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    if before!=receiver.sha(path.read_bytes()):raise ValueError('numeric source changed during replay')
    inventory=receiver.inventory(r.stdout,NAMES)
    if inventory!=report['kernel_theorems']:raise ValueError('numeric axiom inventory changed')
    current=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    result={'format':'pcs-calibration-numeric-replay-v1','executed_source_head':current,
        'source_tree_dirty':dirty,
        'frozen_experiment_source_head':report['source_head'],'proof_sha256':before,'lean_version':version,
        'kernel_theorems':inventory,'returncode':0,'scientific_acceptance':False,
        'physical_model_validity':'OPEN'}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'kernel_theorems':len(inventory),'executed_source_head':current,'scientific_acceptance':False}))


if __name__=='__main__':main()
