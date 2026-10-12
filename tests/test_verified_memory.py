"""Real primitive audits, proposal screening, failure costs and learned utility."""
import copy,os,shutil
import pytest
from pcs.experimental.prover.memory_environment import MemoryEnvironment,structural_rank,replay_memory_receipt
from pcs.experimental.prover.memory_cost import MeasuredInductionEnvironment
from pcs.experimental.prover.memory_falsify import falsify,check_witness,witness_term
from pcs.experimental.prover.memory_discovery import anti_unify,choose_memory
from pcs.experimental.prover.memory_search import state_identity,memory_search
from pcs.experimental.prover.induction_language import formalize
from pcs.experimental.prover.induction_ir import digest
from pcs.experimental.prover.environment import act,search
from pcs.experimental.prover.library import FORMAT

@pytest.fixture(scope='module')
def env():
    if not shutil.which('lean'):
        if os.environ.get('PCS_REQUIRE_PROVER')=='1':pytest.fail('Required Lean missing')
        pytest.skip('Lean unavailable')
    e=MemoryEnvironment(timeout=30)
    try:yield e
    finally:e.close()

def goal(s):return formalize(s)['candidates'][0]['ir']

def test_real_primitive_catalog_audits_actual_types(env):
    assert len(env.catalog)==13
    for entry in env.catalog:
        assert entry['source_name'] and entry['license']=='Apache-2.0'
        assert set(entry['kernel']['axioms'])<={'propext','Classical.choice','Quot.sound'}
    g=goal('For all natural numbers a and b, if the successor of a equals the successor of b then a equals b.')
    r=search(env,g,structural_rank,budget=48,beam=4)
    assert r['status']=='verified' and any(a['argument']=='PCSKnownL2' for a in r['receipt']['actions'])
    assert r['receipt']['primitive_catalog_sha256']==env.primitive_catalog_sha256

def test_forged_memory_receipt_and_goal_do_not_replay(env):
    g=env.primitives[0]['goal'];receipt=env.verify(g,[act('apply','PCSKnownL0')])
    altered=copy.deepcopy(receipt);altered['primitive_catalog_sha256']='0'*64
    with pytest.raises(ValueError,match='binding'):replay_memory_receipt(g,altered)
    changed=goal('For all natural numbers n, the successor of n equals n.')
    with pytest.raises(ValueError,match='goal'):replay_memory_receipt(changed,receipt)
    with pytest.raises(RuntimeError):env.verify(changed,[act('apply','PCSKnownL0')])

def test_immutable_negative_claim_requires_actual_kernel_counterexample(env):
    g=goal('For all natural numbers n, the successor of n equals n.')
    r=falsify(env,g);assert r['status']=='verified_counterexample'
    fresh=check_witness(env,g,r['receipt']['witness'])
    assert fresh['kernel']['axioms']==[] and fresh['original_goal_sha256']==digest(g)
    assert fresh['pcs_authority'] is False
    true=goal('For all natural numbers n, n + 0 equals n.')
    assert falsify(env,true)['status']=='not_refuted_in_bound'
    with pytest.raises(RuntimeError):check_witness(env,true,{'n':0})
    for t,v in [('Nat',True),('NatList',[False]),('NatFn','fun x => sorry')]:
        with pytest.raises(ValueError):witness_term(t,v)

def test_typed_anti_unification_is_not_automatic_truth(env):
    a=goal('For all natural numbers n, n equals 0.')
    b=goal('For all natural numbers n, n equals 1.')
    generalized=anti_unify(a,b)
    assert len(generalized['binders'])==2
    assert falsify(env,generalized)['status']=='verified_counterexample'
    with pytest.raises(ValueError):anti_unify(a,goal('For all lists of natural numbers xs, xs equals the empty list.'))

def test_memory_selection_rejects_final_labels_and_negative_utility():
    entry={'goal':goal('For all natural numbers n, n + 0 equals n.'),'actions':[act('intro','h0'),act('simp')],'license':'Apache-2.0','source_revision':'unit-test'}
    pool=[{'entry':entry,'identity':'a'}]
    library,chosen=choose_memory(pool,{'a':[{'split':'utility','solve_delta':0,'calls_saved':-3}]})
    assert not chosen and library=={'format':FORMAT,'entries':[]}
    with pytest.raises(ValueError,match='labels'):choose_memory(pool,{'a':[{'split':'final','solve_delta':1,'calls_saved':10}]})

def test_failed_compiler_attempts_are_counted():
    e=MeasuredInductionEnvironment(timeout=30)
    try:
        before=e.actual_calls
        with pytest.raises(RuntimeError):e._source('theorem failed : False := by trivial\n#pcs_audit failed\n','PCS_KERNEL:')
        assert e.actual_calls==before+1 and e.compiler_elapsed>0
    finally:e.close()

def test_hypothesis_preserving_induction_is_a_real_action_sequence(env):
    g=goal('For all predicates on natural numbers P, if (P(0) and (∀ (k : Nat), P(k) implies P(the successor of k))) then (∀ (n : Nat), P(n)).')
    path=[act('intro','h0'),act('intro','h1'),act('intro','h2'),act('induct_nat','h2 h3 h4'),act('apply','h1.2'),act('exact','h4'),act('exact','h1.1')]
    for i,a in enumerate(path):assert a in env.candidates(env.observe(g,path[:i])['states'][-1])
    assert len(env.observe(g,path[:4])['states'][-1]['goals'])==2
    receipt=env.verify(g,path);assert receipt['goal_sha256']==digest(g)

def test_checked_successor_search_and_typed_loop_identity(env):
    g=env.primitives[2]['goal'];r=memory_search(env,g,budget=32,beam=4)
    assert r['status']=='verified' and r['expansions']<=32
    state=env.observe(g,[act('intro','h0')])['states'][-1];other=copy.deepcopy(state)
    mapping={l['id']:'renamed'+str(i) for i,l in enumerate(other['goals'][0]['locals'])}
    def rename(e):
        if e['kind']=='local':e['value']=mapping.get(e['value'],e['value'])
        for c in e['children']:rename(c)
    for g in other['goals']:
        rename(g['expression'])
        for l in g['locals']:rename(l['expression']);l['id']=mapping[l['id']]
    assert state_identity(state)==state_identity(other)

def test_actual_utility_gradients_change_graph_and_safe_checkpoint(env,tmp_path):
    torch=pytest.importorskip('torch')
    from pcs.experimental.prover.memory_model import MemoryNetwork,fit_utility
    # Genuine paired executions with different budgets; the target records the
    # measured outcome, never a supplied policy reward or self-declared score.
    g=env.primitives[0]['goal'];before=search(env,g,budget=1,beam=1);after=search(env,g,budget=8,beam=4)
    state=env.observe(g,[])['states'][-1]
    sample={'split':'utility','label_source':'paired_actual_Lean_search','state':state,
            'action':act('apply','PCSKnownL0'),
            'solve_delta':int(after['status']=='verified')-int(before['status']=='verified'),
            'calls_saved':before['lean_invocations']-after['lean_invocations']}
    torch.manual_seed(17);m=MemoryNetwork();report=fit_utility(m,[sample],epochs=2)
    assert 'message.weight' in report['changed_parameters']
    assert any(x.startswith('verifier_cost.') for x in report['changed_parameters'])
    path=tmp_path/'checkpoint.json';sha=m.save(path,{'experimental':True})
    loaded=MemoryNetwork.load(path,sha);opts=env.candidates(state)
    assert loaded.rank(state,opts)==m.rank(state,opts)
    path.write_text(path.read_text()+' ')
    with pytest.raises(ValueError,match='integrity'):MemoryNetwork.load(path,sha)
