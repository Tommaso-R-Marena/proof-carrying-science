"""Independent finite operational model, deliberately separate from SQLite code.

A successful enumeration proves only this finite abstract model under its rules;
it is NOT a theorem about all Python executions, SQLite, real providers, or LLMs.
"""
from collections import deque
from dataclasses import dataclass, replace
import json

EMPTY, RESERVED, IN_FLIGHT, APPLIED, NO_EFFECT, ABANDONED = range(6)
NAMES = {EMPTY:'none', RESERVED:'reserved', IN_FLIGHT:'in_flight', APPLIED:'applied',
         NO_EFFECT:'no_effect', ABANDONED:'abandoned'}

@dataclass(frozen=True)
class State:
    gate_epoch: int = 0
    sink_epoch: int = 0
    pending: bool = False
    a: int = EMPTY
    b: int = EMPTY
    a_epoch: int = -1
    b_epoch: int = -1
    a_calls: int = 0
    b_calls: int = 0
    a_effects: int = 0
    b_effects: int = 0
    # calls are capped by each attempt's two possible delivery/retry actions


def next_states(s:State, *, broken_idempotency=False):
    # one logical intention, up to two separate approvals and effect reservations
    if s.gate_epoch == s.sink_epoch and not s.pending:
        if s.a == EMPTY:
            yield 'reserve first',replace(s,a=RESERVED,a_epoch=s.gate_epoch)
        if s.b == EMPTY and s.a in (NO_EFFECT,ABANDONED):
            yield 'reserve successor',replace(s,b=RESERVED,b_epoch=s.gate_epoch)
    for prefix in ('a','b'):
        status=getattr(s,prefix)
        issued_epoch=getattr(s,prefix+'_epoch')
        calls=getattr(s,prefix+'_calls')
        effects=getattr(s,prefix+'_effects')
        if status == RESERVED and issued_epoch == s.gate_epoch and not s.pending:
            yield f'issue {prefix}',replace(s,**{prefix:IN_FLIGHT})
        if status == RESERVED and issued_epoch < s.gate_epoch and not s.pending and s.sink_epoch == s.gate_epoch:
            yield f'abandon {prefix}',replace(s,**{prefix:ABANDONED})
        if status == IN_FLIGHT and calls < 2 and issued_epoch == s.sink_epoch:
            yield f'deliver/retry {prefix}',replace(s,**{
                prefix+'_calls':calls+1,
                prefix+'_effects': effects+1 if broken_idempotency else min(1,effects+1)})
        if status == IN_FLIGHT and effects:
            yield f'ack {prefix}',replace(s,**{prefix:APPLIED})
        if status == IN_FLIGHT and s.sink_epoch > issued_epoch and effects == 0:
            yield f'certified no-effect {prefix}',replace(s,**{prefix:NO_EFFECT})
    if s.gate_epoch < 2 and not s.pending and s.gate_epoch == s.sink_epoch:
        yield 'revoke locally',replace(s,gate_epoch=s.gate_epoch+1,pending=True)
    if s.pending and s.sink_epoch < s.gate_epoch:
        yield 'sink fence and signed receipt',replace(s,sink_epoch=s.gate_epoch,pending=False)


def invariant(s:State):
    if s.a_effects>1 or s.b_effects>1: return 'duplicate effect for same permit'
    if s.a_effects+s.b_effects>1: return 'two committed effects for same intent'
    if s.a==NO_EFFECT and s.a_effects: return 'false no-effect A'
    if s.b==NO_EFFECT and s.b_effects: return 'false no-effect B'
    if s.b!=EMPTY and s.a not in (NO_EFFECT,ABANDONED):
        return 'successor authorized while prior intent unsettled'
    if s.sink_epoch>s.gate_epoch: return 'sink future epoch'
    if not s.pending and s.sink_epoch!=s.gate_epoch:return 'unaccounted fence gap'
    return None


def run(*,broken_idempotency=False,max_states=50000):
    initial=State()
    queue=deque([initial])
    paths={initial:()}
    edges=0
    while queue:
        s=queue.popleft()
        why=invariant(s)
        if why:
            return {'safe':False,'reason':why,'trace':paths[s],
                    'states_explored':len(paths),'transitions_explored':edges}
        for label,t in next_states(s,broken_idempotency=broken_idempotency):
            edges+=1
            if t not in paths:
                paths[t]=paths[s]+(label,)
                queue.append(t)
                if len(paths)>max_states:
                    raise RuntimeError('model bound exhausted')
    return {'safe':True,'states_explored':len(paths),'transitions_explored':edges,
            'properties':['at most one provider effect per intent',
                          'no success after certified absence',
                          'no successor while unresolved',
                          'sink fence required for absence']}


def report():
    return {'bounded_idempotent_model':run(),
            'deliberately_broken_no_idempotency':run(broken_idempotency=True)}


if __name__=='__main__':
    print(json.dumps(report(),indent=2))
