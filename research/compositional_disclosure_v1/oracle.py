"""Independent Python set oracle, never used to grant runtime authority."""
from itertools import product

def worlds(k):return {w for w in range(16) if k&(1<<w)}
def encode(s):return sum(1<<w for w in s)
def answer(q,w):return (q&w).bit_count()
def ambiguous(s):return {w&1 for w in s}=={0,1}
def safe(s,q):return all(ambiguous({x for x in s if answer(q,x)==v}) for v in {answer(q,x) for x in s})
def step(s,w,q):
    if safe(s,q):
        a=answer(q,w);return {x for x in s if answer(q,x)==a},a
    return s,None

def exhaustive(out):
    import json,time
    from pathlib import Path
    start=time.monotonic();prior={w for w in range(16) if w.bit_count()==2}
    # Reach every reachable ledger state, not just hand-picked successful traces.
    todo=[prior];seen={encode(prior)};transitions=[]
    while todo:
        s=todo.pop()
        for q in range(16):
            for w in sorted(s):
                t,a=step(s,w,q);key=encode(t)
                assert w in t and ambiguous(t)
                transitions.append((encode(s),w,q,key,a))
                if key not in seen:seen.add(key);todo.append(t)
    # Reproduce composition failure for every actual world and query permutation.
    from itertools import permutations
    attacks=[]
    for w,qs in product(sorted(prior),permutations((2,4,8))):
        assert all(safe(prior,q) for q in qs)
        leaked={x for x in prior if all(answer(q,x)==answer(q,w) for q in qs)}
        assert leaked=={w}
        s=prior
        for q in qs:s,_=step(s,w,q)
        assert ambiguous(s)
        attacks.append(dict(world=w,queries=qs,stateless_candidates=sorted(leaked),ledger_candidates=sorted(s)))
    d=dict(reachable_states=len(seen),transitions=len(transitions),composition_attacks=len(attacks),all_stateless_attacks_reconstruct_world=True,all_ledger_traces_ambiguous=True,attacks=attacks,seconds=time.monotonic()-start)
    Path(out).write_text(json.dumps(d,indent=2)+'\n');return transitions,d
