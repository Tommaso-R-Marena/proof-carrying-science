"""Untrusted attractor synthesis and strict replay; no Python PASS grants authority."""
from __future__ import annotations
from hashlib import sha256
from itertools import product
from pcs.action_shield_v1 import load_model, ActionShieldError
from pcs.jsonio import strict_json_loads
from pcs.canonical_json import canonicalize_jcs_bytes

FORMAT = 'pcs-progress-supervisor-certificate-v1'
MAX_BYTES = 2*1024*1024

def sha(raw): return sha256(raw).hexdigest()
def encode(value): return canonicalize_jcs_bytes(value)
def _nat(value):
    if type(value) is not int or not 0 <= value < 65536: raise ActionShieldError('exact bounded natural required')
    return value

def _ids(values, domain):
    if type(values) is not list or len(values)>32: raise ActionShieldError('bounded goal list required')
    if any(_nat(x) not in domain for x in values) or values != sorted(set(values)): raise ActionShieldError('sorted unique safe goal IDs required')
    return values

def groups(model):
    out={}
    for e in model['transitions']: out.setdefault((e['source'],e['action']),[]).append(e['target'])
    return out

def propose(model_raw:bytes, goals:list[int]):
    model=load_model(model_raw);_ids(goals,model['safe']);out=groups(model)
    ranks={s:0 for s in goals};layer=0
    while True:
        layer+=1
        added=[s for s in model['safe'] if s not in ranks and any(
            src==s and a not in model['forbidden'] and all(t in ranks for t in targets)
            for (src,a),targets in out.items())]
        if not added: break
        ranks.update({s:layer for s in added})
    allowed=[[s,a] for (s,a),ts in sorted(out.items()) if s in ranks and s not in goals
             and a not in model['forbidden'] and all(t in ranks and ranks[t]<ranks[s] for t in ts)]
    return dict(format=FORMAT,model_sha256=sha(model_raw),goals=list(goals),ranks=[list(p) for p in sorted(ranks.items())],allowed=allowed)

def load_certificate(model_raw:bytes,cert_raw:bytes):
    model=load_model(model_raw)
    if type(cert_raw) is not bytes or len(cert_raw)>MAX_BYTES: raise ActionShieldError('bounded certificate bytes required')
    c=strict_json_loads(cert_raw.decode('utf-8',errors='strict'))
    if type(c) is not dict or set(c)!={'format','model_sha256','goals','ranks','allowed'}: raise ActionShieldError('exact progress certificate schema required')
    if c['format']!=FORMAT or c['model_sha256']!=sha(model_raw): raise ActionShieldError('certificate identity mismatch')
    _ids(c['goals'],model['safe'])
    ranks=c['ranks']
    if type(ranks) is not list or len(ranks)>32: raise ActionShieldError('bounded rank map required')
    for p in ranks:
        if type(p) is not list or len(p)!=2 or _nat(p[0]) not in model['safe'] or type(p[1]) is not int or not 0<=p[1]<len(model['states']): raise ActionShieldError('invalid rank pair')
    if ranks!=sorted(ranks) or len({p[0] for p in ranks})!=len(ranks): raise ActionShieldError('ranks must have sorted unique state IDs')
    allowed=c['allowed'];out=groups(model)
    if type(allowed) is not list or len(allowed)>512: raise ActionShieldError('bounded allowed pairs required')
    for p in allowed:
        if type(p) is not list or len(p)!=2 or (_nat(p[0]),_nat(p[1])) not in out: raise ActionShieldError('unknown/empty action pair')
    if allowed!=sorted(allowed) or len({tuple(p) for p in allowed})!=len(allowed): raise ActionShieldError('sorted unique action pairs required')
    return model,c

def evaluate(model_raw:bytes,cert_raw:bytes):
    """Independent certificate criteria, NOT the synthesis algorithm or authority."""
    m,c=load_certificate(model_raw,cert_raw);r=dict(c['ranks']);out=groups(m);issues=[];spoilers=[]
    for s,k in r.items():
        if (k==0)!=(s in c['goals']): issues.append(['zero_goal',s])
        if s not in c['goals'] and not any(p[0]==s for p in c['allowed']): issues.append(['deadlock',s])
    for g in c['goals']:
        if g not in r: issues.append(['missing_goal',g])
    for s,a in c['allowed']:
        if s not in r or a in m['forbidden']: issues.append(['pair',s,a])
        for t in out[s,a]:
            if t not in r or s not in r or r[t]>=r[s]: issues.append(['nonprogress_outcome',s,a,t])
    for s in m['safe']:
        if s in r: continue
        for (src,a),ts in out.items():
            if src!=s or a in m['forbidden']: continue
            bad=next((t for t in ts if t not in r),None)
            if bad is None: issues.append(['incomplete_winning_region',s,a])
            else: spoilers.append(dict(source=s,action=a,target=bad))
    return dict(format='pcs-progress-supervisor-analysis-v1',valid=not issues,issues=issues,
        winning_states=sorted(r),losing_safe_states=[s for s in m['safe'] if s not in r],
        initial_realizable=all(s in r for s in m['initial']),completion_upper_bounds=c['ranks'],
        spoiling_outcomes=spoilers,kernel_checked=False,pcs_authority=False,
        liveness_scope='Finite worst-case tool-transition bound; no wall-clock, scheduler or tool-termination guarantee',
        assumptions=m['assumptions'])

def literal_source(model_raw:bytes,cert_raw:bytes):
    m,c=load_certificate(model_raw,cert_raw)
    nums=lambda a:'['+','.join(map(str,a))+']'
    edges='['+','.join('⟨'+','.join(str(e[k]) for k in ['source','action','target'])+'⟩' for e in m['transitions'])+']'
    pairs=lambda a:'['+','.join('('+str(s)+','+str(v)+')' for s,v in a)+']'
    return (f'import Codec\nnamespace PCSProgressData\ndef spec : PCSProgress.Spec := ⟨⟨{nums(m["initial"])},{nums(m["safe"])},{edges},{pairs(c["allowed"])},{nums(m["forbidden"])}⟩,{nums(c["goals"])},{pairs(c["ranks"])}⟩\n'
        'theorem certificate_checked : PCSProgress.check spec = true := by decide\n'
        'theorem winning : ∀ s ∈ PCSProgress.region spec, PCSProgress.CanForce spec.base spec.goals (PCSProgress.rank spec s) s := PCSProgress.winning_can_force certificate_checked\n'
        'theorem losing {s : Nat} (h : s ∉ PCSProgress.region spec) : ∀ n, ¬ PCSProgress.CanForce spec.base spec.goals n s := PCSProgress.losing_no_finite_bound certificate_checked h\n'
        'theorem wire_bounds : PCSProgressCodec.FitsWire spec := by decide\n'
        'end PCSProgressData\n').encode()

def brute_force_bounds(model_raw:bytes,goals:list[int]):
    """Independent small-model oracle: enumerate policies and reject non-goal cycles.

    Does not use attractor iteration or submitted ranks. Intended for <=4 states.
    """
    m=load_model(model_raw)
    if len(m['states'])>4: raise ValueError('brute-force oracle limited to four states')
    out=groups(m);states=[s for s in m['safe'] if s not in goals];best={g:0 for g in goals}
    choices=[[a for (src,a) in out if src==s and a not in m['forbidden']]+[None] for s in states]
    for actions in product(*choices):
        policy=dict(zip(states,actions))
        def depth(s,ancestors):
            if s not in m['safe']: return None
            if s in goals:return 0
            if s in ancestors or policy.get(s) is None:return None
            tails=[depth(t,ancestors|{s}) for t in out[s,policy[s]]]
            return None if any(t is None for t in tails) else 1+max(tails)
        for s in states:
            d=depth(s,set())
            if d is not None:best[s]=min(best.get(s,d),d)
    return best
