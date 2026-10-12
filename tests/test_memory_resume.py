"""Actual Lean-labelled training interrupted at an epoch boundary and resumed."""
import copy,gzip,hashlib,json
from pathlib import Path
import pytest,torch
from pcs.experimental.prover.memory_cli import load as load_model
from pcs.experimental.prover.memory_environment import MemoryEnvironment
from pcs.experimental.prover.memory_resume import save,load
from pcs.experimental.prover.model import imitate
from pcs.experimental.prover.data import replay_receipt

ROOT=Path(__file__).resolve().parents[1]
def test_exact_cpu_adam_rng_resume_on_actual_multistep_Lean_labels(tmp_path):
    folder=ROOT/'research/verified-memory-v1';_,_,library,original=load_model(folder)
    record=json.loads(gzip.decompress((ROOT/'research/verified-memory-demonstration/checked-feedback.json.gz').read_bytes()))
    env=MemoryEnvironment(library,timeout=30)
    try:
        replay_receipt(env,record['goal'],record['result']['receipt'])
        assert len(record['result']['receipt']['actions'])==6
        uninterrupted=copy.deepcopy(original);split=copy.deepcopy(original)
        full=imitate(uninterrupted,[record],epochs=2,seed=89,candidate_provider=env.candidates)
        optimizer=torch.optim.Adam(split.parameters(),lr=.008)
        imitate(split,[record],epochs=1,seed=89,candidate_provider=env.candidates,optimizer=optimizer)
        identity=save(split,optimizer,tmp_path/'resume',{'dataset_sha256':record['id'],'completed_epochs':1,'production_authority':False})
        resumed,restored,metadata=load(tmp_path/'resume',identity)
        assert metadata['completed_epochs']==1
        imitate(resumed,[record],epochs=1,candidate_provider=env.candidates,optimizer=restored,resume=True)
        assert full['changed_parameters']
        assert all(torch.equal(value,resumed.state_dict()[key]) for key,value in uninterrupted.state_dict().items())
        source=tmp_path/'resume'/'optimizer.json';packet=json.loads(source.read_text());packet['state']['0']['exp_avg_sq']=[-1]
        raw=json.dumps(packet).encode();source.write_bytes(raw)
        with pytest.raises(ValueError,match='tensor'):load(tmp_path/'resume',hashlib.sha256(raw).hexdigest())
        with pytest.raises(ValueError,match='integrity'):load(tmp_path/'resume',identity)
    finally:env.close()
