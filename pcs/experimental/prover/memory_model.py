"""Verifier-cost-conditioned graph policy; weights propose, never certify.

The symbolic prior reserves introduction/closure priorities. A bounded learned
residual and a learned lemma-utility head choose between grounded proposals.
Utility supervision comes from actual paired bounded searches, not supplied
scores or predicted proof success. Baselines can disable the learned residual.
"""
import hashlib,json
from pathlib import Path
import torch
from torch import nn
from .grounded_model import GroundedNetwork
from .memory_environment import structural_rank

class MemoryNetwork(GroundedNetwork):
    def __init__(self,width=24,architecture='graph'):
        super().__init__(width,architecture)
        self.verifier_cost=nn.Sequential(nn.Linear(width*3+3,24),nn.Tanh(),nn.Linear(24,1))

    def forward(self,state,options):
        logits,value,uncertainty=super().forward(state,options)
        if options:
            cost=self.verifier_cost(self.action_inputs(state,options)).squeeze(1)
            prior=logits.new_tensor(structural_rank(state,options))
            logits=prior+3.*torch.tanh(logits/3.)+2.*torch.tanh(cost)
        return logits,value,uncertainty

    def save(self,path,metadata):
        p={'format':'pcs-verifier-cost-network-v1','width':self.width,'architecture':self.architecture,
           'metadata':metadata,'weights':{k:v.detach().cpu().tolist() for k,v in self.state_dict().items()}}
        raw=(json.dumps(p,sort_keys=True,separators=(',',':'))+'\n').encode();Path(path).write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def load(cls,path,expected_sha):
        raw=Path(path).read_bytes()
        if len(raw)>2_000_000 or hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError('memory checkpoint integrity')
        p=json.loads(raw)
        if set(p)!={'format','width','architecture','metadata','weights'} or p['format']!='pcs-verifier-cost-network-v1' or p['width']!=24 or p['architecture'] not in {'graph','bag'}:
            raise ValueError('unsupported memory checkpoint')
        m=cls(p['width'],p['architecture']);weights={k:torch.tensor(v) for k,v in p['weights'].items()}
        if any(not torch.isfinite(v).all() for v in weights.values()):raise ValueError('nonfinite memory weights')
        m.load_state_dict(weights,strict=True);return m

def fit_utility(model,examples,*,epochs=10,seed=17):
    if any(e['split']!='utility' or e.get('label_source')!='paired_actual_Lean_search' for e in examples):
        raise ValueError('utility data firewall/provenance')
    torch.manual_seed(seed);optimizer=torch.optim.Adam(model.parameters(),lr=.002)
    before={k:v.detach().clone() for k,v in model.state_dict().items()};losses=[]
    for _ in range(epochs):
        total=0.
        for i in torch.randperm(len(examples)).tolist():
            e=examples[i];features=model.action_inputs(e['state'],[e['action']])
            predicted=model.verifier_cost(features).squeeze()
            # This is measured utility under the frozen budget, with unsolved
            # searches censored. It is not a true minimum proof-cost label.
            target=max(-2.,min(2.,e['solve_delta']+e['calls_saved']/96.))
            loss=nn.functional.smooth_l1_loss(predicted,predicted.new_tensor(target))
            optimizer.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
            total+=float(loss.detach())
        losses.append(total/max(1,len(examples)))
    return {'examples':len(examples),'epochs':epochs,'losses':losses,
            'changed_parameters':[k for k,v in model.state_dict().items() if not torch.equal(v,before[k])],
            'target':'observed bounded-search solve difference and Lean calls saved; not optimal proof cost'}
