"""Independent semantic oracles, replay tampering, and bounded execution."""
from copy import deepcopy
import itertools
import json
import random
import subprocess
import sys
import pytest
from pcs.experimental.conditional import check, digest, evaluate, from_text, parse_formula, validate, verify


def oracle(f, a):
    op = f['op']
    if op == 'atom': return a[f['symbol']]
    if op == 'true': return True
    if op == 'false': return False
    if op == 'not': return not oracle(f['body'], a)
    x, y = oracle(f['left'], a), oracle(f['right'], a)
    return {'and':x and y, 'or':x or y, 'implies':(not x) or y}[op]


def formula(rng, depth):
    if depth == 0 or rng.random() < .28:
        return {'op':'atom','symbol':rng.choice(list('ABCDEF')),'args':[]} if rng.random()<.8 else {'op':rng.choice(['true','false'])}
    op = rng.choice(['not','and','or','implies'])
    return {'op':op,'body':formula(rng,depth-1)} if op=='not' else {'op':op,'left':formula(rng,depth-1),'right':formula(rng,depth-1)}


def worlds(names):
    return [dict(zip(names, bits)) for bits in itertools.product([False, True], repeat=len(names))]


@pytest.mark.parametrize('seed',range(160))
def test_against_independent_exhaustive_semantics(seed):
    rng=random.Random(seed)
    t={'format':'pcs-conditional-boolean-task-v1','variables':list('ABCDEF'),'source':formula(rng,3),'candidate':formula(rng,3),'assumptions':[formula(rng,2) for _ in range(rng.randrange(4))]}
    r=check(t); assert verify(r)==r['decision']
    allowed=[w for w in worlds(t['variables']) if all(oracle(f,w) for f in t['assumptions'])]
    bad=[w for w in allowed if oracle(t['source'],w)!=oracle(t['candidate'],w)]
    assert r['decision']==('inconsistent_assumptions' if not allowed else 'counterexample' if bad else 'equivalent_under_assumptions')
    if allowed: assert r['context_example']==allowed[0]
    if bad: assert r['counterexample']['assignment']==bad[0]
    if not allowed:
        core=r['unsat_core'];assert core
        assert not any(all(oracle(t['assumptions'][i],w) for i in core) for w in worlds(t['variables']))
        for witness in r['core_necessity_witnesses']:
            i=witness['removed_assumption'];w=witness['assignment']
            assert all(oracle(t['assumptions'][j],w) for j in core if j!=i)
            assert not oracle(t['assumptions'][i],w)
    nodes=r['diagram']['nodes'];assert len({tuple(n) for n in nodes})==len(nodes)
    for id,(v,lo,hi) in enumerate(nodes,2):
        assert lo!=hi and 0<=lo<id and 0<=hi<id
        assert all(nodes[child-2][0]>v for child in (lo,hi) if child>=2)


def test_context_is_used_and_contradictions_never_accept():
    assert check(from_text('TRUE','B','A\nA -> B'))['decision']=='equivalent_under_assumptions'
    assert check(from_text('TRUE','B','A -> B'))['decision']=='counterexample'
    assert check(from_text('A AND B','A OR B'))['decision']=='counterexample'
    assert check(from_text('A AND B','A OR B','A\nB'))['decision']=='equivalent_under_assumptions'
    r=check(from_text('A AND B','A OR B','A\nNOT A\nB'))
    assert r['decision']=='inconsistent_assumptions' and r['unsat_core']==[0,1]
    assert r['diagram']['source'] is None and r['diagram']['candidate'] is None


def test_constants_zero_variables_and_balanced_large_formula():
    assert check(from_text('TRUE','FALSE'))['counterexample']['assignment']=={}
    assert check(from_text('TRUE','TRUE'))['decision']=='equivalent_under_assumptions'
    names=['V'+str(i).zfill(2) for i in range(24)]
    t=from_text('NOT ('+' OR '.join(names)+')',' AND '.join('NOT '+n for n in names))
    r=check(t);assert r['decision']=='equivalent_under_assumptions'
    assert r['work']['bdd_nodes']<200 and r['work']['apply_calls']<1000
    assert len(t['variables'])==24


@pytest.mark.parametrize('limits',[{'nodes':1,'operations':100000},{'nodes':4096,'operations':1}])
def test_resource_exhaustion_fails_closed(limits):
    r=check(from_text('A AND B','A OR B'),limits)
    assert r['decision']=='resource_limit' and r['diagram'] is None and r['counterexample'] is None
    assert r['work']['bdd_nodes']<=limits['nodes'] and r['work']['apply_calls']<=limits['operations']
    assert verify(r)=='resource_limit'


@pytest.mark.parametrize('field',['decision','counterexample','diagram','limits','work','pcs_authority','lean_kernel_checked','extra'])
def test_resigned_forgery_rejected(field):
    r=deepcopy(check(from_text('A AND B','A OR B')))
    if field=='decision':r[field]='equivalent_under_assumptions'
    elif field=='counterexample':r[field]['assignment']['A']=True
    elif field=='diagram':r[field]['difference']=0
    elif field=='limits':r[field]['nodes']=1
    elif field=='work':r[field]['apply_calls']+=1
    elif field=='extra':r[field]='unreviewed'
    else:r[field]=True
    r['receipt_sha256']=digest({k:v for k,v in r.items() if k!='receipt_sha256'})
    with pytest.raises(ValueError):verify(r)


@pytest.mark.parametrize('text',['A B','A ->','A + B','A()','a','AND','A OR','('*34+'A'+')'*34,'A\ufeff'])
def test_invalid_formula_grammar(text):
    with pytest.raises(ValueError):from_text(text,'A')


def test_precedence_right_implication_and_unicode_whitespace():
    t=from_text('A OR B AND C','A -> B -> C','A\u2028B')
    assert t['source']['op']=='or' and t['source']['right']['op']=='and'
    assert t['candidate']['op']=='implies' and t['candidate']['right']['op']=='implies'
    assert len(t['assumptions'])==2
    assert parse_formula('A\u0085AND B')['op']=='and'


def test_strict_types_boundaries_and_no_mutation():
    t=from_text('A AND B','A OR B');original=deepcopy(t);check(t);assert t==original
    for mutate in [lambda t:t['source'].update(op=[]),lambda t:t['source'].update(unknown=1),lambda t:t['variables'].append('A'),lambda t:t.update(assumptions=[{'op':'true'}]*9)]:
        bad=deepcopy(t);mutate(bad)
        with pytest.raises(ValueError):validate(bad)
    for limits in [{'nodes':True,'operations':10},{'nodes':4097,'operations':10},{'nodes':10,'operations':100001}]:
        with pytest.raises(ValueError):check(t,limits)
    with pytest.raises(ValueError):from_text(' AND '.join('V'+str(i) for i in range(25)),'TRUE')


def test_actual_cli_outcomes_and_exclusive_output(tmp_path):
    t=tmp_path/'task.json';out=tmp_path/'receipt.json';t.write_text(json.dumps(from_text('A AND B','A OR B')))
    command=[sys.executable,'-m','pcs.cli','conditional']
    r=subprocess.run(command+['check',str(t),'--output',str(out)],capture_output=True,text=True)
    assert r.returncode==1 and json.loads(out.read_text())['decision']=='counterexample'
    assert subprocess.run(command+['verify',str(out)],capture_output=True).returncode==0
    before=out.read_bytes();assert subprocess.run(command+['check',str(t),'--output',str(out)],capture_output=True).returncode==4;assert out.read_bytes()==before
    for raw in ['{"format":1,"format":2}', '{"format":NaN}', ' '*262145]:
        t.write_text(raw);assert subprocess.run(command+['check',str(t)],capture_output=True).returncode==4
