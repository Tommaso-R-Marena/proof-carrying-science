"""Adversarial structural proposal tests; synthetic Expr fixtures are NOT proofs."""
from copy import deepcopy
import pytest
from pcs.experimental.prover.abstraction_v4 import propose,source_pattern
from pcs.experimental.prover.induction_ir import digest

def node(kind,value='',children=()):return {'kind':kind,'value':value,'children':list(children)}
def apply(head,*args):
 for arg in args:head=node('application',children=[head,arg])
 return head

def fixture(identity,domain='Nat',context='Nat.succ'):
 d=node('constant',domain+':[]');var=lambda n:node('local',n)
 image=lambda n:apply(node('constant',context+':[]'),var(n))
 eq=lambda a,b:apply(node('constant','Eq:[1]'),d,a,b)
 locals_=[{'name':'h'+str(i),'id':n,'type':domain,'expression':d} for i,n in enumerate(['x','y','z'])]
 locals_.extend([{'name':'h3','id':'hab','type':'fixture equality','expression':eq(image('x'),image('y'))},{'name':'h4','id':'hbc','type':'fixture equality','expression':eq(image('y'),image('z'))}])
 statement='synthetic structural fixture '+identity;kernel={'format':'pcs-lean-kernel-v1','axioms':[]}
 return {'id':identity,'statement':statement,'state':{'goals':[{'target':'fixture target','expression':eq(var('x'),var('z')),'locals':locals_}]},'receipt':{'goal_sha256':digest(statement),'kernel':kernel,'independent_kernel':deepcopy(kernel),'pcs_authority':False}}

def test_cross_type_context_abstraction_is_proposal_only():
 result=propose([fixture('first'),fixture('second','List Nat','List.cons')])
 assert result['semantically_certified'] is False
 assert result['missing_premise_candidate']=='Function.Injective f'
 assert result['novel_mathematics_claim'] is False
 assert len(result['source_patterns'])==2

def test_alpha_copies_and_one_source_do_not_count_as_cross_type_abstraction():
 with pytest.raises(ValueError):propose([fixture('first')])
 with pytest.raises(ValueError):propose([fixture('first'),fixture('first')])
 with pytest.raises(ValueError):propose([fixture('first'),fixture('second')])

@pytest.mark.parametrize('mutation',[lambda s:s['receipt'].update(goal_sha256='0'*64),lambda s:s['receipt'].update(pcs_authority=True),lambda s:s['receipt']['independent_kernel'].update(axioms=['sorryAx']),lambda s:s['state']['goals'][0]['locals'][1].update(expression=node('constant','Int:[]')),lambda s:s['state']['goals'][0]['locals'][4].update(expression=s['state']['goals'][0]['locals'][3]['expression']),lambda s:s['state']['goals'][0]['expression'].update(kind='goal')])
def test_unbound_or_ill_typed_patterns_are_rejected(mutation):
 source=fixture('bad');mutation(source)
 with pytest.raises(ValueError):source_pattern(source)


def test_counterexample_proposals_preserve_screening_and_need_kernel_check():
 from pcs.experimental.prover.abstraction_v4 import counterexample_search
 result=counterexample_search()
 assert result['certified'] is False
 assert len(result['trials'])==10
 assert result['witness']['endpoints']==[0,0,1]
 assert result['witness']['premises'] and not result['witness']['conclusion']
 assert 'Nat.noConfusion' in result['proof']
