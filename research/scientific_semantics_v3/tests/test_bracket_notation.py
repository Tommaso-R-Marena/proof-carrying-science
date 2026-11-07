"""Authored post-hoc tests; these are not fresh scientific evaluation cases."""
import pytest
from research.scientific_semantics_v3 import semantics as s

def parse(expression,**kwargs):
    return s.parse_statistical_expression(expression,**kwargs)


def test_exp_brackets_become_function_not_array():
    result=parse('2*(1-exp[-b2*x])+e')
    ir=result['rhs']
    assert s._symbols(ir)==['b2','e','x']
    assert result['notation']['bracket_functions']==['exp']
    assert result['notation']['assumptions']
    assert ir==parse('2*(1-exp(-b2*x))+e')['rhs']


def test_nested_brackets_and_domains():
    result=parse('exp[log[1.25e-4*x]]')
    assert result['notation']['bracket_functions']==['exp','log']
    assert result['rhs']==parse('exp(log(1.25e-4*x))')['rhs']
    assert result['notation']['domain_obligations']==[{'relation':'positive','expression':{'op':'mul','args':[{'op':'number','value':'1.25e-4'},{'op':'symbol','name':'x'}]}}]


def test_scientific_literal_is_not_rounded():
    result=parse('exp[-0.1000000000000000000001e-30*x]')
    number=result['rhs']['args'][0]['args'][0]['arg']
    assert number=={'op':'number','value':'0.1000000000000000000001e-30'}


def test_parenthesized_math_unchanged():
    result=parse('b1*(1-exp(-b2*x))+e')
    assert result['notation']=={'bracket_functions':[],'assumptions':[],'domain_obligations':[]}
    assert result['rhs']==s.previous.parse_expression('b1*(1-exp(-b2*x))+e')


@pytest.mark.parametrize('expression',[
    'x[0]', 'data[i]', 'Exp[x]', 'sqrt[x]', 'exp[x][0]',
    'exp[0:2]', 'exp[x,y]', 'exp[(x,y)]', 'exp[[x]]',
    'exp[x[0]]', 'exp[lambda: x]', 'np.exp[x]', 'sum(x,axis=1)',
    '__import__("os").system("echo unsafe")', '__import__["os"]',
])
def test_unsupported_or_unsafe_indexing_abstains(expression):
    with pytest.raises(s.previous.Unsupported):
        parse(expression)


@pytest.mark.parametrize('expression',['exp[x]','exp(x)','log[x]','log(x)'])
def test_declared_variable_function_name_ambiguity_abstains(expression):
    name='exp' if expression.startswith('exp') else 'log'
    with pytest.raises(s.previous.Unsupported,match='ambiguous'):
        parse(expression,declared_symbols=[name,'x'])


@pytest.mark.parametrize('expression',['exp[x]+exp','exp[exp+x]','log[x]+log'])
def test_bare_variable_function_collision_abstains(expression):
    with pytest.raises(s.previous.Unsupported,match='ambiguous'):
        parse(expression)


def test_bare_exp_identifier_does_not_turn_into_function():
    result=parse('exp+x',declared_symbols=['exp','x'])
    assert result['rhs']=={'op':'add','args':[{'op':'symbol','name':'exp'},{'op':'symbol','name':'x'}]}
    assert result['notation']['bracket_functions']==[]


def test_variable_symbols_do_not_collide_case_insensitively():
    result=parse('exp[Exp+x]',declared_symbols=['Exp','x'])
    assert s._symbols(result['rhs'])==['Exp','x']


def test_unknown_payload_never_executes(tmp_path):
    marker=tmp_path/'executed'
    with pytest.raises(s.previous.Unsupported):
        parse(f'__import__("pathlib").Path({str(marker)!r}).touch()')
    assert not marker.exists()


def test_resource_budgets():
    with pytest.raises(s.previous.Unsupported):
        parse('exp['*100+'x'+']'*100)
    with pytest.raises(s.previous.Unsupported):
        parse('exp[x]',declared_symbols=['x']*1025)


def test_original_source_bytes_and_assumptions_are_preserved(tmp_path):
    raw='NIST\nProcedure: Nonlinear Least Squares Regression\nModel:\n y=b1*(1-exp[-b2*x])+e\n'
    (tmp_path/'authored.dat').write_text(raw)
    result=s.interpret_project(tmp_path)
    claim=next(c for c in result['claims'] if c['kind']=='equation')
    assert claim['source']['quote']==' y=b1*(1-exp[-b2*x])+e\n'
    assert s.verify_grounding(claim,tmp_path)
    assert claim['notation']['bracket_functions']==['exp']
    assert any('source meaning requires review' in assumption for assumption in claim['assumptions'])
    assert 'exp' not in claim['symbols']
    assert claim['authority'] is False


def test_document_declared_function_symbol_rejects_ambiguous_equation(tmp_path):
    (tmp_path/'authored.dat').write_text('NIST\nexp = 5\n y=exp[x]+e\n')
    result=s.interpret_project(tmp_path)
    assert not [c for c in result['claims'] if c['kind']=='equation']
    assert any('Unsupported NIST regression expression' in u['reason'] for u in result['unresolved'])


def test_log_domain_is_obligation_not_truth(tmp_path):
    (tmp_path/'authored.dat').write_text('NIST\n y=log[x]+e\n')
    result=s.interpret_project(tmp_path)
    claim=next(c for c in result['claims'] if c['kind']=='equation')
    assert claim['domain']['required_positive']==[{'relation':'positive','expression':{'op':'symbol','name':'x'}}]
    assert any('not proved by parsing' in a for a in claim['assumptions'])
    assert not claim['authority']
