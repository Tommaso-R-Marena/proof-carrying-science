from fractions import Fraction
import pytest
from .interpretation import parse_expression
from .rational_equivalence import compare
from .checks import eval_ir


@pytest.mark.parametrize('a,b',[
    ('x*(y+z)','x*y+x*z'),('x/y+z/y','(x+z)/y'),('(x/y)**2','x*x/(y*y)'),('-x+y','y-x'),
    ('(x+1)*(x-1)','x*x-1'),('x**0','1')])
def test_exact_symbolic_equalities(a,b):
    r=compare(parse_expression(a),parse_expression(b));assert r['status']=='EQUAL_ON_COMMON_DEFINED_DOMAIN'
    assert r['authority'] is False


def test_cancellation_keeps_domain_obligation():
    r=compare(parse_expression('x/x'),parse_expression('1'))
    assert r['status']=='EQUAL_ON_COMMON_DEFINED_DOMAIN' and r['nonzero_denominator_obligations']


def test_fixed_sample_aliasing_is_caught_by_normal_form():
    original=parse_expression('x+x*x')
    attack=parse_expression('x+x*x+'+'*'.join(f'(x-{i}/100)' for i in range(1,13)))
    assert all(eval_ir(original,{'x':Fraction(i,100)})==eval_ir(attack,{'x':Fraction(i,100)}) for i in range(1,13))
    r=compare(original,attack);assert r['status']=='DISTINCT_RATIONAL_FUNCTIONS'
    assert eval_ir(original,{'x':Fraction(1,2)})!=eval_ir(attack,{'x':Fraction(1,2)})


def test_resource_and_undefined_fail_closed():
    with pytest.raises(ValueError):compare(parse_expression('1/(x-x)'),parse_expression('1'))
    with pytest.raises(ValueError):compare(parse_expression('x**99'),parse_expression('x'))
