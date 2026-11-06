"""Trainable Safety-JEPA proposals; no prediction has enforcement authority.

The graph encoder is reused unchanged from Proof-JEPA. Agent observations are
mapped to bounded typed trees, preserving field/child roles. The new action
predictor rolls latent states forward without reading oracle future states.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re

import torch
from torch import nn
from torch.nn import functional as F

from pcs.jsonio import strict_json_loads
from research.proof_jepa_rl_v1.model import GraphEncoder, ProofJEPA

ACTIONS = ('inspect','read_public','read_sensitive','draft','redact','verify','publish',
           'send_external','read_secret','exec_code','edit_policy','forge_reward',
           'review','abstain','noop')
OBSERVABLE_FIELDS = ('stage','phase','goal','document','history','last_result','lastresult',
                     'permissions','resources','remaining','unknown','inspected','result')
FORMAT = 'pcs-safety-jepa-model-v1'
MAX_BYTES = 8_000_000
TRANSFER_SHA256 = '3a340553c2863cbd46cc306db2bc8cfb541cf30d467c3d63141c230756f7485d'


def _action_index(action):
    if type(action) is not str or action not in ACTIONS:
        raise ValueError('unsupported bounded tool action')
    return ACTIONS.index(action)


def observation_graph(observation):
    """Only observed state is encoded, never labels, attacks, reward or task IDs.

    Text tokens use the inherited 257-bucket hash vocabulary. This is an
    intentionally lossy learned representation, not formal canonicalization.
    Bounded truncation and hash collisions are explicit representation limits.
    """
    if type(observation) is not dict:
        raise ValueError('agent observation must be an object')
    count = 0
    def node(kind, value, children=()):
        nonlocal count
        count += 1
        if count > 1024:
            raise ValueError('agent observation graph exceeds bound')
        return {'kind':kind, 'value':str(value), 'children':list(children)}
    def encode(value, depth=0):
        if depth > 8:
            raise ValueError('observation nesting exceeds bound')
        if type(value) is dict:
            # Per-action audit dictionaries may contain evaluator-only fields.
            forbidden = {'unsafe','blocked','reward','completion','risk','attack_sequence',
                         'split','source_sha256','episode_id','id','expected','oracle'}
            keys = [k for k in sorted(value) if type(k) is str and k not in forbidden][:24]
            return node('constant','object', [node('constant','field:'+k,
                         [encode(value[k],depth+1)]) for k in keys])
        if type(value) in (list,tuple):
            return node('constant','sequence', [node('constant','position:'+str(i),[encode(v,depth+1)])
                         for i,v in enumerate(value[-16:])])
        if type(value) is str:
            # Token positions are retained by child roles/order in GraphEncoder.
            tokens = re.findall(r'\w+|[^\w\s]', value[:2048].casefold(), flags=re.UNICODE)[:64]
            return node('constant','text', [node('constant','position:'+str(i),[node('constant','text:'+t)])
                         for i,t in enumerate(tokens)])
        if value is None or type(value) is bool:
            return node('constant','literal:'+str(value))
        if type(value) in (int,float) and math.isfinite(value) and abs(value)<=1e9:
            return node('constant','number:'+str(value))
        raise ValueError('unsupported or nonfinite observation value')
    children = [node('constant','field:'+key,[encode(observation[key])])
                for key in OBSERVABLE_FIELDS if key in observation]
    if not children:
        raise ValueError('observation has no supported observable fields')
    return {'goals':[{'expression':node('constant','agent-observation',children),
                      'target':'', 'locals':[]}]}


class SafetyJEPA(nn.Module):
    """Predictive graph model and actor/critic, never an authorization interface."""
    def __init__(self, width=24, transfer=False):
        super().__init__()
        if type(width) is not int or not 8<=width<=64 or type(transfer) is not bool:
            raise ValueError('invalid model dimensions/transfer flag')
        if transfer and width!=24:
            raise ValueError('retained proof encoder transfer requires width24')
        self.width, self.transfer = width, transfer
        self.online = GraphEncoder(width)
        if transfer:
            checkpoint = Path(__file__).resolve().parents[1]/'proof_jepa_rl_v1/evidence/proof_guided-17.json'
            # Transfer changes encoder initialization only, not downstream RNG/head initialization.
            with torch.random.fork_rng(devices=[]):
                original = ProofJEPA.load(checkpoint,TRANSFER_SHA256)
            self.online.load_state_dict(original.online.state_dict(),strict=True)
        self.target = copy.deepcopy(self.online).requires_grad_(False)
        self.actions = nn.Embedding(len(ACTIONS),width)
        self.predictor = nn.Sequential(nn.Linear(2*width,2*width), nn.GELU(),
                                       nn.Linear(2*width,width), nn.Tanh())
        def head(): return nn.Sequential(nn.Linear(3*width,width),nn.Tanh(),nn.Linear(width,1))
        self.actor = head()
        self.risk_head = head()
        self.block_head = head()
        self.reward_head = head()
        self.value = nn.Sequential(nn.Linear(width,width),nn.Tanh(),nn.Linear(width,1))
        self.last_loss_metrics = {}

    def encode(self, observation):
        return self.online(observation_graph(observation))

    @torch.no_grad()
    def encode_target(self, observation):
        return self.target(observation_graph(observation))

    def _action(self,action):
        return self.actions.weight[_action_index(action)]

    def predict(self,latent,action):
        if latent.shape != (self.width,) or not torch.isfinite(latent).all():
            raise ValueError('invalid predictive latent')
        return self.predictor(torch.cat((latent,self._action(action))))

    def _context(self,latent,action):
        return torch.cat((latent,self._action(action),self.predict(latent,action)))

    def forward(self,observation,options):
        if type(options) not in (tuple,list) or len(options)>len(ACTIONS):
            raise ValueError('bounded action options required')
        h = self.encode(observation)
        contexts = [self._context(h,a) for a in options]
        if contexts:
            c = torch.stack(contexts)
            logits = self.actor(c).squeeze(-1)
            risk_logits = self.risk_head(c).squeeze(-1)
        else:
            logits = risk_logits = h.new_empty(0)
        return logits, self.value(h).squeeze(), risk_logits

    def rank(self,observation,options):
        self.eval()
        with torch.no_grad():
            logits = self(observation,options)[0]
            if not torch.isfinite(logits).all():
                raise ValueError('nonfinite proposal scores')
            return logits.cpu().tolist()

    def risk(self,observation,action):
        self.eval()
        with torch.no_grad():
            return float(self.risk_head(self._context(self.encode(observation),action)).sigmoid())

    def forecast(self,observation,sequence):
        """Unroll predicted latents only; max score is not a calibrated probability.

        No environment, tool implementation, future observation or gate is called.
        This cannot certify safety or discover every dangerous continuation.
        """
        if type(sequence) not in (list,tuple) or not 1<=len(sequence)<=10:
            raise ValueError('forecast requires1..10 bounded actions')
        self.eval()
        with torch.no_grad():
            h = self.encode(observation)
            risks=[]
            for action in sequence:
                context=self._context(h,action)
                risks.append(self.risk_head(context).sigmoid().squeeze())
                h=self.predict(h,action)
            return float(torch.stack(risks).max())

    def plan_scores(self,observation,sequences,risk_weight=1.):
        """Heuristic model-based utility; every selected action still needs guard."""
        if type(risk_weight) not in (int,float) or not math.isfinite(risk_weight) or risk_weight<0:
            raise ValueError('invalid risk weight')
        result=[]
        self.eval()
        with torch.no_grad():
            for sequence in sequences:
                if type(sequence) not in (tuple,list) or not 1<=len(sequence)<=10:
                    raise ValueError('invalid bounded plan')
                h=self.encode(observation); reward=h.new_zeros(()); risks=[]
                for index,action in enumerate(sequence):
                    context=self._context(h,action)
                    reward=reward+(.97**index)*self.reward_head(context).squeeze()
                    risks.append(self.risk_head(context).sigmoid().squeeze())
                    h=self.predict(h,action)
                utility=reward+.2*self.value(h).squeeze()-risk_weight*torch.stack(risks).max()
                result.append(float(utility))
        return result

    @torch.no_grad()
    def update_target(self,momentum=.99):
        if type(momentum) not in (int,float) or not math.isfinite(momentum) or not 0<=momentum<1:
            raise ValueError('invalid EMA momentum')
        for target,online in zip(self.target.parameters(),self.online.parameters()):
            target.mul_(momentum).add_(online,alpha=1-momentum)

    def loss(self,batch,predictive=True,multistep=True,proof_guided=False):
        """Fit only externally measured train outcomes, never authorize from them.

        `unsafe` must describe an independently executed unguarded counterfactual,
        `blocked` comes from the unchanged gate, and rewards from the environment.
        This method checks schema/provenance plumbing, not truth of those labels.
        The training harness must establish their provenance separately.
        """
        if type(batch) is not list or not batch:
            raise ValueError('nonempty training batch required')
        if any(r.get('split')!='train' for r in batch):
            raise ValueError('evaluation firewall: train records only')
        hs=[]; predictions=[]; targets=[]; risk_losses=[]; reward_losses=[]
        actor_losses=[]; block_losses=[]; value_losses=[]; future_losses=[]; forecast_losses=[]; sequence_losses=[]
        for record in batch:
            if any(type(record.get(key)) is not bool for key in ('unsafe','blocked','completion')):
                raise ValueError('checker labels must be actual booleans')
            source=record.get('source_sha256','')
            if type(source) is not str or re.fullmatch(r'[0-9a-f]{64}',source) is None:
                raise ValueError('training provenance digest required')
            reward=record['reward']; ret=record.get('return',reward)
            if any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1000 for v in (reward,ret)):
                raise ValueError('invalid independently observed reward')
            h=self.encode(record['obs']); context=self._context(h,record['action']); hs.append(h)
            risk_losses.append(F.binary_cross_entropy_with_logits(self.risk_head(context).squeeze(),h.new_tensor(float(record['unsafe']))))
            reward_losses.append((self.reward_head(context).squeeze()-reward).square())
            actor_losses.append((self.actor(context).squeeze()-ret).square())
            value_losses.append((self.value(h).squeeze()-ret).square())
            block_losses.append(F.binary_cross_entropy_with_logits(self.block_head(context).squeeze(),h.new_tensor(float(record['blocked']))))
            prediction=self.predict(h,record['action'])
            if predictive:
                predictions.append(prediction); targets.append(self.encode_target(record['next_obs']))
            latent=prediction
            sequence_risks=[self.risk_head(context).sigmoid().squeeze()]
            sequence_unsafe=record['unsafe']
            future = record.get('future',[]) if multistep else []
            if type(future) is not list or len(future)>3:
                raise ValueError('future trajectory exceeds bound')
            for step in future:
                if type(step.get('unsafe')) is not bool:
                    raise ValueError('future outcome must be a checker boolean')
                forecast_context=self._context(latent,step['action'])
                future_risk_logit=self.risk_head(forecast_context).squeeze()
                forecast_losses.append(F.binary_cross_entropy_with_logits(future_risk_logit,h.new_tensor(float(step['unsafe']))))
                sequence_risks.append(future_risk_logit.sigmoid())
                sequence_unsafe=sequence_unsafe or step['unsafe']
                latent=self.predict(latent,step['action'])
                if predictive:
                    future_losses.append(F.mse_loss(latent,self.encode_target(step['next_obs'])))
            if multistep and future:
                sequence_losses.append(F.binary_cross_entropy(torch.stack(sequence_risks).max(),h.new_tensor(float(sequence_unsafe))))
        zero=hs[0].sum()*0
        mean=lambda xs:torch.stack(xs).mean() if xs else zero
        successor=F.mse_loss(torch.stack(predictions),torch.stack(targets)) if predictions else zero
        z=torch.stack(hs)
        if len(hs)>1:
            centered=z-z.mean(0); covariance=centered.T@centered/(len(hs)-1)
            offdiag=covariance-torch.diag(torch.diagonal(covariance))
            variance=F.relu(.2-torch.sqrt(z.var(0,unbiased=False)+1e-4)).mean()
            decorrelation=offdiag.square().sum()/self.width
            std=z.std(0,unbiased=False).mean()
        else: variance=decorrelation=std=zero
        risk_loss,actor_loss,reward_loss=mean(risk_losses),mean(actor_losses),mean(reward_losses)
        loss=risk_loss+.5*actor_loss+.2*reward_loss
        if predictive:loss=loss+successor+.5*variance+.5*decorrelation
        if multistep:loss=loss+.5*mean(forecast_losses)+.5*mean(sequence_losses)+(.5*mean(future_losses) if predictive else zero)
        if proof_guided:loss=loss+.2*mean(block_losses)+.1*mean(value_losses)
        self.last_loss_metrics={key:float(value.detach()) for key,value in {
            'loss':loss,'risk_bce':risk_loss,'actor_mse':actor_loss,'reward_mse':reward_loss,
            'successor_mse':successor,'multistep_mse':mean(future_losses),
            'forecast_bce':mean(forecast_losses),'sequence_risk_bce':mean(sequence_losses),'variance_penalty':variance,
            'covariance_penalty':decorrelation,'embedding_std':std,
            'block_bce':mean(block_losses),'value_mse':mean(value_losses)}.items()}
        self.last_loss_metrics.update({'records':len(batch),'multistep_targets':len(future_losses),
                                      'target_requires_grad':any(p.requires_grad for p in self.target.parameters())})
        return loss

    def save(self,path,metadata):
        if type(metadata) is not dict:
            raise ValueError('checkpoint metadata must be an object')
        payload={'format':FORMAT,'width':self.width,'transfer':self.transfer,'authority':'NONE',
                 'metadata':metadata,'weights':{k:v.detach().cpu().tolist() for k,v in self.state_dict().items()}}
        raw=(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
        if len(raw)>MAX_BYTES:raise ValueError('checkpoint exceeds bound')
        with Path(path).open('xb') as stream:stream.write(raw)
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def load(cls,path,expected_sha):
        if type(expected_sha) is not str or re.fullmatch(r'[0-9a-f]{64}',expected_sha) is None:
            raise ValueError('expected checkpoint SHA256 required')
        with Path(path).open('rb') as stream:raw=stream.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES or hashlib.sha256(raw).hexdigest()!=expected_sha:
            raise ValueError('checkpoint digest/size mismatch')
        payload=strict_json_loads(raw.decode('utf-8'))
        if (type(payload) is not dict or set(payload)!={'format','width','transfer','authority','metadata','weights'}
                or payload['format']!=FORMAT or payload['authority']!='NONE'
                or type(payload['transfer']) is not bool or type(payload['metadata']) is not dict):
            raise ValueError('unsupported checkpoint contract')
        # Loading a retained checkpoint never opens an initial-transfer path.
        model=cls(payload['width'],transfer=False); model.transfer=payload['transfer']
        if model.transfer and model.width!=24:raise ValueError('invalid transfer width')
        expected=model.state_dict()
        if type(payload['weights']) is not dict or set(payload['weights'])!=set(expected):
            raise ValueError('checkpoint parameter keys differ')
        def finite_numbers(value):
            return all(finite_numbers(v) for v in value) if type(value) is list else type(value) in (int,float) and math.isfinite(value)
        converted={}
        for name,value in payload['weights'].items():
            if not finite_numbers(value):raise ValueError('finite numeric weights required')
            try:tensor=torch.tensor(value,dtype=expected[name].dtype)
            except (TypeError,ValueError,RuntimeError) as error:raise ValueError('invalid parameter tensor') from error
            if tensor.shape!=expected[name].shape or not torch.isfinite(tensor).all():
                raise ValueError('checkpoint shape/finiteness mismatch')
            converted[name]=tensor
        model.load_state_dict(converted,strict=True)
        return model
