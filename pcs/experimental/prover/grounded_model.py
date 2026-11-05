"""Binding-aware goal/action graphs and a learned checker-response head.

Local and bound references link to their declarations. The action head sees the
actual selected premise, not just its name token. All outputs remain proposals.
"""
import hashlib
import json
from pathlib import Path

import torch
from torch import nn

from .reuse_model import ReuseNetwork
from .model import token
from .environment import reference_expression, premise_matches


def binding_graph(state):
    nodes, edges = [token("state")], []
    def link(a,b): edges.extend([(a,b),(b,a)])
    def visit(expr,parent,local_ids,bound=()):
        index=len(nodes);kind=expr["kind"]
        value="" if kind in {"local","goal","forall","lambda"} else expr["value"]
        nodes.append(token(kind+":"+value));link(parent,index)
        if kind=="local" and expr["value"] in local_ids: link(index,local_ids[expr["value"]])
        if kind=="bound" and int(expr["value"])<len(bound): link(index,bound[-1-int(expr["value"])])
        for i,child in enumerate(expr["children"]):
            visit(child,index,local_ids,(*bound,index) if kind in {"forall","lambda"} and i==1 else bound)
    for goal in state["goals"]:
        target=len(nodes);nodes.append(token("target"));link(0,target)
        local_ids={}
        for local in goal["locals"]:
            local_ids[local["id"]]=len(nodes);nodes.append(token("hypothesis"));link(target,len(nodes)-1)
        visit(goal["expression"],target,local_ids)
        for local in goal["locals"]:visit(local["expression"],local_ids[local["id"]],local_ids)
    if len(nodes)>4096:raise ValueError("state graph exceeds bound")
    return nodes,edges


class GroundedNetwork(ReuseNetwork):
    def __init__(self,width=24,architecture="graph"):
        super().__init__(width,architecture)
        self.local_query=nn.Linear(width,width,bias=False)
        self.local_key=nn.Linear(width,width,bias=False)
        self.local_policy=nn.Linear(width*3+3,1)
        self.proposal_validity=nn.Linear(width*3+3,1)

    def encode(self,state):
        nodes,edges=binding_graph(state);device=self.tokens.weight.device
        h=self.tokens(torch.tensor(nodes,device=device))
        if self.architecture=="graph":
            source=torch.tensor([a for a,b in edges],device=device);target=torch.tensor([b for a,b in edges],device=device)
            for _ in range(2):
                messages=self.message(h[source]);aggregated=torch.zeros_like(h);aggregated.index_add_(0,target,messages)
                counts=torch.zeros(len(nodes),device=device);counts.index_add_(0,target,torch.ones(len(target),device=device))
                h=torch.tanh(self.update(torch.cat([h,aggregated/counts.clamp_min(1).unsqueeze(1)],dim=1)))
        return h.mean(0)

    def action_inputs(self,state,options):
        goal=self.encode(state);inputs=[]
        catalog={e["name"]:e["expression"] for e in state.get("available_lemmas",[])}
        target=state["goals"][0]["expression"] if state["goals"] else None
        for action in options:
            reference=str(action["argument"] or "").split()[0] if action["argument"] is not None else ""
            premise=catalog.get(reference) or (reference_expression(state,reference) if state["goals"] else None)
            if premise is not None:
                p=self.encode({"goals":[{"expression":premise,"target":"selected premise","locals":state["goals"][0]["locals"]}]})
            else:p=goal.new_zeros(goal.shape)
            flags=goal.new_tensor([float(premise is not None),float(bool(target) and premise_matches(target,premise)),float(action["kind"].startswith("induct"))])
            inputs.append(torch.cat([self.local_query(goal),self.local_key(p),goal*p,flags]))
        return torch.stack(inputs) if inputs else goal.new_empty((0,self.width*3+3))

    def forward(self,state,options):
        logits,value,uncertainty=super().forward(state,options)
        inputs=self.action_inputs(state,options)
        if options:
            logits=logits+self.local_policy(inputs).squeeze(1)+nn.functional.logsigmoid(self.proposal_validity(inputs).squeeze(1))
        return logits,value,uncertainty

    def save(self,path,metadata):
        payload={"format":"pcs-grounded-network-v1","width":self.width,"architecture":self.architecture,"metadata":metadata,
                 "weights":{k:v.detach().cpu().tolist() for k,v in self.state_dict().items()}}
        Path(path).write_text(json.dumps(payload,sort_keys=True,separators=(",", ":"))+"\n")
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @classmethod
    def load(cls,path,expected_sha):
        raw=Path(path).read_bytes()
        if len(raw)>2_000_000 or hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError("checkpoint integrity failure")
        p=json.loads(raw)
        if set(p)!={"format","width","architecture","metadata","weights"} or p["format"]!="pcs-grounded-network-v1" or p["width"]!=24:raise ValueError("unsupported grounded checkpoint")
        m=cls(p["width"],p["architecture"]);state={k:torch.tensor(v) for k,v in p["weights"].items()}
        if any(not torch.isfinite(v).all() for v in state.values()):raise ValueError("nonfinite checkpoint")
        m.load_state_dict(state,strict=True);return m


def train_validity(model,trajectories,epochs=4,seed=17):
    torch.manual_seed(seed);examples=[]
    for episode in trajectories:
        if episode["split"]!="train":raise ValueError("evaluation firewall")
        for attempt in episode["result"].get("attempts",[]):
            if "state" in attempt and attempt["status"] in {"open","closed","invalid"}:
                examples.append((attempt["state"],attempt["action"],float(attempt["status"]!="invalid")))
    optimizer=torch.optim.Adam(model.parameters(),lr=.003)
    before=model.proposal_validity.weight.detach().clone()
    for _ in range(epochs):
        for i in torch.randperm(len(examples)).tolist():
            state,action,valid=examples[i];inputs=model.action_inputs(state,[action]);logit=model.proposal_validity(inputs).squeeze()
            loss=nn.functional.binary_cross_entropy_with_logits(logit,logit.new_tensor(valid))
            optimizer.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
    return {"examples":len(examples),"invalid_examples":sum(not x[2] for x in examples),"epochs":epochs,
            "validity_head_changed":not torch.equal(before,model.proposal_validity.weight)}
