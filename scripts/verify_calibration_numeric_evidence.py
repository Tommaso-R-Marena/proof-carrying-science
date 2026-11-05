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
import os
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_lean_source import audit,active_code
from pcs import calibration_kernel_v1 as receiver

QUALIFIED=ROOT/'research/experimental-calibration-v1/local-qualification-42f53a6'
PORTABLE=ROOT/'research/experimental-calibration-v1/numeric-portability-v1/proof'
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
    folder=QUALIFIED/'numeric';original=folder/'NumericComparisons.lean'
    original_report=receiver.load_json((folder/'REPORT.json').read_bytes())
    report=receiver.load_json((PORTABLE/'REPORT.json').read_bytes())
    inputs=receiver.load_json((folder/'INPUTS.json').read_bytes())
    if (original_report['passed'] is not True or report['passed'] is not True
            or original_report['proof_sha256']!=receiver.sha(original.read_bytes())
            or report['original_proof_sha256']!=original_report['proof_sha256']):
        raise ValueError('numeric proof identity mismatch')
    if (original_report['source_head']!=inputs['source_head']
            or report['frozen_experiment_source_head']!=inputs['source_head']
            or inputs['source_head']!='42f53a634ab70ffa9994a496b1c3027d683874a3'):
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
    modules=['PCSCalibrationNumericData']+[f'PCSCalibrationNumericRow{k:02}' for k in range(22)]+['PCSCalibrationNumericPortable']
    paths=[PORTABLE/(name+'.lean') for name in modules]
    before={path.name:receiver.sha(path.read_bytes()) for path in paths}
    if before!=report['source_sha256']:raise ValueError('portable module identity mismatch')
    prefix=original.read_text().split('theorem all_heldout_least_squares_scores_exact',1)[0]
    if paths[0].read_text()!=prefix+'end PCSExperimentalCalibration\n':
        raise ValueError('original numeric definitions changed')
    statements=lambda text:[line.split(' := by',1)[0] for line in text.splitlines() if line.startswith('theorem ')]
    if statements(original.read_text())!=statements(paths[-1].read_text()):
        raise ValueError('original primary theorem statements changed')
    helpers=['PCSExperimentalCalibration.'+name for k in range(22)
        for name in [f'least_squares_row_{k:02}',f'minimax_row_{k:02}']]
    if report['primary_theorems']!=NAMES or report['supporting_theorems']!=helpers:
        raise ValueError('complete primary/supporting numeric identities required')
    if findings:=audit(paths):raise ValueError(str(findings))
    declared=[]
    for i,path in enumerate(paths):
        declared.extend('PCSExperimentalCalibration.'+m[1] for m in re.finditer(r'(?m)^theorem (\S+)',active_code(path.read_text())))
        allowed=({'Mathlib.Data.Rat.BigOperators','Mathlib.Data.Fintype.Fin'} if i==0 else
            ({'PCSCalibrationNumericData'} if i<23 else set(modules[1:23])|{'Mathlib.Tactic.FinCases'}))
        if set(re.findall(r'(?m)^import (\S+)',path.read_text()))!=allowed:
            raise ValueError('fixed portable proof import graph required')
    if len(declared)!=53 or set(declared)!=set(NAMES+helpers):
        raise ValueError('complete 53-name numeric inventory required')
    start=time.monotonic();deadline=start+180
    lean,env,version=receiver.infrastructure._environment(30)
    inventory={};executions=[]
    with tempfile.TemporaryDirectory(prefix='pcs-calibration-numeric-replay-') as temp:
        private=Path(temp);env['LEAN_PATH']=str(private)+os.pathsep+env['LEAN_PATH']
        for i,path in enumerate(paths):
            target=private/path.name;target.write_bytes(path.read_bytes())
            command=[lean,'-j1','-M2048','-D','Elab.async=false','--root='+str(private),
                     '-o',str(target.with_suffix('.olean')),str(target)]
            remaining=deadline-time.monotonic()
            if remaining<=0:raise subprocess.TimeoutExpired('portable numeric replay',180)
            r=subprocess.run(command,cwd=private,env=env,capture_output=True,text=True,timeout=remaining)
            if r.returncode:raise RuntimeError(r.stdout+r.stderr)
            expected=[] if i==0 else (helpers[2*(i-1):2*i] if i<23 else NAMES)
            inventory.update(receiver.inventory(r.stdout,expected))
            executions.append({'module':path.name,'returncode':0})
    if before!={path.name:receiver.sha(path.read_bytes()) for path in paths}:
        raise ValueError('numeric sources changed during replay')
    if inventory!=report['kernel_theorems']:raise ValueError('numeric axiom inventory changed')
    current=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    result={'format':'pcs-calibration-numeric-replay-v1','executed_source_head':current,
        'source_tree_dirty':dirty,
        'frozen_experiment_source_head':inputs['source_head'],'source_sha256':before,'lean_version':version,
        'original_proof_sha256':original_report['proof_sha256'],'primary_theorems':NAMES,
        'supporting_theorems':helpers,'executions':executions,'elapsed_seconds':round(time.monotonic()-start,6),
        'memory_limit_mb_per_process':2048,'wall_budget_seconds':180,
        'kernel_theorems':inventory,'returncode':0,'scientific_acceptance':False,
        'physical_model_validity':'OPEN'}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'primary_theorems':len(NAMES),'supporting_theorems':len(helpers),
        'kernel_theorems':len(inventory),'executed_source_head':current,'scientific_acceptance':False}))


if __name__=='__main__':main()
