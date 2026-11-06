"""Training firewall checks do not simulate any affirmative Lean verdict."""
from copy import deepcopy
import pytest
from .model import ProofJEPA
from .experiment import fit, configure, write_json
from .data import tasks, receipt_claim_graph

@pytest.mark.parametrize('split',['validation','test',None])
def test_fit_refuses_evaluation_before_optimizer(split):
    with pytest.raises(ValueError,match='evaluation firewall'):
        fit(ProofJEPA(),[{'split':split}],'jepa',seed=17,epochs=1)

def test_fit_refuses_missing_proof_binding():
    with pytest.raises(ValueError,match='provenance'):
        fit(ProofJEPA(),[{'split':'train','kernel_completed':True,'valid':True}],
            'proof_guided',seed=17,epochs=1)

def test_fit_refuses_no_completed_demonstration():
    with pytest.raises(ValueError,match='no kernel-verified'):
        fit(ProofJEPA(),[{'split':'train','kernel_completed':False,'valid':False,'remaining':None}],
            'supervised',seed=17,epochs=1)

def test_deterministic_initialization():
    import torch
    configure(17); a=ProofJEPA()
    configure(17); b=ProofJEPA()
    assert all(torch.equal(a.state_dict()[k],v) for k,v in b.state_dict().items())

def test_bound_claim_is_not_scientific_authority():
    graph=receipt_claim_graph(tasks()[0])
    assert graph

def test_json_rejects_nonfinite_evidence(tmp_path):
    with pytest.raises(ValueError): write_json(tmp_path/'bad.json',{'score':float('nan')})

def test_compressed_evidence_reproducible(tmp_path):
    a,b=tmp_path/'a.json.gz',tmp_path/'b.json.gz'
    assert write_json(a,{'fixture':'ordinary data'})==write_json(b,{'fixture':'ordinary data'})
    assert a.read_bytes()==b.read_bytes()
