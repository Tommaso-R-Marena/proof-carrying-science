"""Grammar/invertible scheduling controls; actual Mathlib execution has a CI CLI."""
import pytest
from pcs.experimental.prover.mathlib_environment_v4 import MathlibEnvironmentV4,same_kernel_type

def boundary():
    env=MathlibEnvironmentV4.__new__(MathlibEnvironmentV4)
    env.by_name={'Eq.trans':{'module':'Init'},'Nat.add_zero':{'module':'Init'}}
    env.excluded_names={'Nat.add_zero'};env.excluded_modules=set()
    return env

@pytest.mark.parametrize('action',[
 {'kind':'apply_lemma','argument':'sorry'}, {'kind':'apply_lemma','argument':'Nat.add_zero'},
 {'kind':'exact_local','argument':'h0; sorry'}, {'kind':'intro','argument':'h0\naxiom bad : False'},
 {'kind':'rewrite_lemma','argument':{'name':'Eq.trans','direction':'forward','occurrence':True}},
 {'kind':'rewrite_lemma','argument':{'name':'Eq.trans','direction':'sideways','occurrence':1}},
 {'kind':'simp','argument':None}, {'kind':'import','argument':'Mathlib'},
 {'kind':'apply_lemma','argument':'Eq.trans','statement':'False'},
])
def test_untrusted_actions_cannot_escape_receiver(action):
    with pytest.raises(ValueError):boundary().render(action)

def test_exact_catalog_membership_and_occurrence_rendering():
    env=boundary();assert env.render({'kind':'apply_lemma','argument':'Eq.trans'})=='apply Eq.trans'
    assert env.render({'kind':'rewrite_lemma','argument':{'name':'Eq.trans','direction':'backward','occurrence':2}})=='conv => lhs; rw (occs := .pos [2]) [← Eq.trans]'

@pytest.mark.parametrize('source',['True := by trivial','False -- comment','by sorry','axiom bad : False','True\n#eval 1'])
def test_declaration_injection_rejected(source):
    with pytest.raises(ValueError):MathlibEnvironmentV4._statement(source)

def test_ranker_cannot_supply_a_proof_or_reward():
    env=boundary();assert not hasattr(env,'accepted_reward')
    with pytest.raises(ValueError):env.render({'kind':'verified','argument':{'reward':1,'proof':'sorry'}})

def test_kernel_comparison_is_alpha_faithful_and_rejects_changed_domain():
    node=lambda k,v,c=[]:{'kind':k,'value':v,'children':c}
    first={'format':'pcs-lean-kernel-v1','axioms':[], 'expression':node('forall','a',[node('constant','Nat:[]'),node('bound','0')])}
    renamed={'format':'pcs-lean-kernel-v1','axioms':[], 'expression':node('forall','a._hyg.123',[node('constant','Nat:[]'),node('bound','0')])}
    assert same_kernel_type(first,renamed)
    changed={'format':'pcs-lean-kernel-v1','axioms':[], 'expression':node('forall','a',[node('constant','Int:[]'),node('bound','0')])}
    assert not same_kernel_type(first,changed)
    forged={**renamed,'axioms':['badAxiom']}
    assert not same_kernel_type(first,forged)
