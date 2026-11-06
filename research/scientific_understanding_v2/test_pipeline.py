import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import pytest
from .pipeline import run,replay
from research.scientific_intake_v1.intake import canonical


def fixture(tmp_path):
    p=tmp_path/'input';p.mkdir();(p/'paper.md').write_text('Measured concentration: 2.0 ± 0.1 mM.\nThe treatment causes a cure.\ndC/dt = k*C\n')
    (p/'untrusted.py').write_text('raise RuntimeError("IMPORTED CODE MUST NOT EXECUTE")')
    return p


def resign(out,names):
    m=json.loads((out/'manifest.json').read_text())
    for name in names:m['files'][name]=hashlib.sha256((out/name).read_bytes()).hexdigest()
    (out/'manifest.json').write_bytes(canonical(m))


def test_real_intake_interpretation_and_replay(tmp_path):
    summary=run(fixture(tmp_path),tmp_path/'e',check=True)
    assert summary['scientific_claims_certified']==summary['training_examples_admitted']==0
    assert summary['quantities']>0 and summary['unresolved']>0
    assert replay(tmp_path/'e')['status']=='REPLAYED'


@pytest.mark.parametrize('target',['interpretations.json','checks.json','summary.json','review.html'])
def test_rehashed_semantic_or_result_tampering_is_rejected(tmp_path,target):
    out=tmp_path/'e';run(fixture(tmp_path),out,check=True)
    if target=='review.html':(out/target).write_text('PCS certified a cure.')
    else:
        value=json.loads((out/target).read_text())
        if target=='checks.json':value=[]
        elif target=='summary.json':value['scientific_claims_certified']=99
        else:value['claims'][0]['meaning_status']='CERTIFIED'
        (out/target).write_bytes(canonical(value))
    resign(out,[target])
    with pytest.raises(ValueError):replay(out)


def test_unsafe_upload_never_executes_and_missing_units_abstain(tmp_path):
    source=fixture(tmp_path);marker=tmp_path/'EXECUTED'
    (source/'evil.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').touch()')
    summary=run(source,tmp_path/'e',check=True)
    assert not marker.exists() and summary['checks']['UNKNOWN']>0


def test_cache_context_and_replay_are_independent(tmp_path):
    source=fixture(tmp_path);a=run(source,tmp_path/'a',check=True,cache_dir=tmp_path/'cache');b=run(source,tmp_path/'b',check=True,cache_dir=tmp_path/'cache')
    assert a['checks']==b['checks']
    assert replay(tmp_path/'b')['cache_used'] is False


def test_source_snapshot_tampering_rejected(tmp_path):
    out=tmp_path/'e';run(fixture(tmp_path),out)
    obj=next((out/'intake/objects').iterdir());obj.write_bytes(b'forged')
    with pytest.raises(ValueError):replay(out)


def test_concrete_lean_rejects_false_nullspace_certificate():
    from .concrete_lean import verify_certificate
    good=verify_certificate({'matrix':[['-1'],['1']],'weights':[1,1]})
    assert good['status']=='KERNEL_CHECKED_FINITE_INTEGER_CONSERVATION'
    with pytest.raises(ValueError):verify_certificate({'matrix':[['-1'],['2']],'weights':[1,1]})

def test_noncanonical_model_boolean_fails_closed():
    from .model_checks import SBMLModel
    raw=Path(__file__).with_name('fixtures').joinpath('upstream/tyson1991.sbml').read_bytes()
    with pytest.raises(ValueError):SBMLModel(raw.replace(b'boundaryCondition="true"',b'boundaryCondition="1"',1))


def test_foreign_mathml_operator_fails_closed():
    from .model_checks import SBMLModel
    raw=Path(__file__).with_name('fixtures').joinpath('upstream/tyson1991.sbml').read_bytes()
    with pytest.raises(ValueError):SBMLModel(raw.replace(b'<times/>',b'<evil:times xmlns:evil="urn:fake"/>',1))

def test_unsupported_export_preserves_independently_completed_model_evidence(tmp_path):
    source=tmp_path/'input';source.mkdir();upstream=Path(__file__).with_name('fixtures')/'upstream'
    (source/'model.sbml').write_bytes((upstream/'tyson1991.sbml').read_bytes())
    code=(upstream/'tyson1991.m').read_text().replace('compartment_cell=1.0;','system("untrusted call must never run");\ncompartment_cell=1.0;',1)
    (source/'export.m').write_text(code)
    summary=run(source,tmp_path/'e',check=True)
    checks=json.loads((tmp_path/'e/checks.json').read_text());model=next(r for r in checks if r['checker']=='model_assurance')
    assert model['status']=='UNKNOWN'
    assert model['evidence']['author_export']['status']=='UNKNOWN'
    assert model['evidence']['numerical']['status']=='REPRODUCED_NUMERICALLY'
    assert model['evidence']['kernel_certificates'][0]['status']=='KERNEL_CHECKED_FINITE_INTEGER_CONSERVATION'
    assert replay(tmp_path/'e')['status']=='REPLAYED'
