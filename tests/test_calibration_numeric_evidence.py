"""The public numerical gate must reject substituted proof/data before Lean."""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

ROOT=Path(__file__).resolve().parents[1]


def verifier():
    spec=importlib.util.spec_from_file_location('calibration_numeric_gate',ROOT/'scripts/verify_calibration_numeric_evidence.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('attack',['source_hash','data_prefix','primary_statement','extra_import',
    'missing_helper','project_axiom','failed_report','case_data'])
def test_numeric_gate_refuses_substitution_before_proof_execution(attack,tmp_path,monkeypatch):
    module=verifier();portable=tmp_path/'proof';shutil.copytree(module.PORTABLE,portable)
    monkeypatch.setattr(module,'PORTABLE',portable)
    report=json.loads((portable/'REPORT.json').read_bytes())
    target=portable/'PCSCalibrationNumericRow00.lean'
    if attack=='source_hash':target.write_text(target.read_text()+'\n')
    if attack=='data_prefix':
        target=portable/'PCSCalibrationNumericData.lean';target.write_text(target.read_text()+'\n-- substituted data prefix\n')
    if attack=='primary_statement':
        target=portable/'PCSCalibrationNumericPortable.lean'
        target.write_text(target.read_text().replace('∀ h d, lsLoss h d = lsSSE h d','True',1))
    if attack=='extra_import':target.write_text('import Mathlib\n'+target.read_text())
    if attack=='missing_helper':
        target.write_text('\n'.join(l for l in target.read_text().splitlines() if not l.startswith('theorem least_squares_row_00'))+'\n')
    if attack=='project_axiom':target.write_text(target.read_text()+'\naxiom forged : False\n')
    if attack=='failed_report':report['passed']=False
    if attack not in ['source_hash','failed_report','case_data']:
        report['source_sha256'][target.name]=module.receiver.sha(target.read_bytes())
    (portable/'REPORT.json').write_text(json.dumps(report))
    if attack=='case_data':
        qualified=tmp_path/'qualified';(qualified/'numeric').mkdir(parents=True)
        for name in ['NumericComparisons.lean','REPORT.json','INPUTS.json']:
            shutil.copyfile(module.QUALIFIED/'numeric'/name,qualified/'numeric'/name)
        (qualified/'study/hull-00').mkdir(parents=True)
        (qualified/'study/hull-00/data.csv').write_bytes(b'x,y\n0,999\n')
        monkeypatch.setattr(module,'QUALIFIED',qualified)
    monkeypatch.setattr(module.receiver.infrastructure,'_environment',lambda *a,**k:pytest.fail('substituted source reached Lean'))
    monkeypatch.setattr('sys.argv',['verify','--output',str(tmp_path/'must-not-exist.json')])
    with pytest.raises(ValueError):module.main()
    assert not (tmp_path/'must-not-exist.json').exists()
