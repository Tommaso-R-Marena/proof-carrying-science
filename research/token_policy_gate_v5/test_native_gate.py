"""Actual fixed Lean checking of positive and adversarial pair certificates."""
from pathlib import Path
import pytest
from .receiver import Checker


@pytest.fixture(scope='module')
def checker(tmp_path_factory):return Checker(tmp_path_factory.mktemp('pair-native')/'checker')


def pair(state,action,selected):
    from research.structured_action_lab_v4.codec import PAYLOADS
    return dict(state=state,tokens=[4913,1311,788,15+action,92,151645],raw_hex=PAYLOADS[action].hex(),selected=selected)


def test_actual_lean_corrects_unsafe_publication_and_checks_all_theorems(checker):
    report=checker.certify([pair(2,3,2)],'safe-correction')
    assert report['kernel_checked'] is True and report['pcs_authority'] is False
    assert len(report['general_axiom_closures'])==16
    assert all(set(v)<={'propext','Quot.sound','Classical.choice'} for v in report['general_axiom_closures'].values())


@pytest.mark.parametrize('fault',['unsafe_selected','forbidden_selected','mismatched_bytes','missing_eos'])
def test_actual_lean_rejects_forged_positive_pair_verdict(checker,fault):
    row=pair(2,3,2)
    if fault=='unsafe_selected':row['selected']=3
    elif fault=='forbidden_selected':row=pair(0,5,5)
    elif fault=='mismatched_bytes':row['raw_hex']=b'{"action":5}'.hex()
    else:row['tokens']=row['tokens'][:-1]
    with pytest.raises(ValueError):checker.certify([row],fault.replace('_','-'))
    assert checker.logs[-1]['returncode']!=0


def test_genuine_kernel_checked_rejection_does_not_authorize_execution(checker):
    from .receiver import require_execution_rows
    row=pair(2,3,None);row['raw_hex']=b'{"action":5}'.hex()
    report=checker.certify([row],'verified-rejection')
    assert report['kernel_checked'] is True  # Real proof that the gate rejects.
    with pytest.raises(ValueError,match='selected action before effects'):
        require_execution_rows([row])
