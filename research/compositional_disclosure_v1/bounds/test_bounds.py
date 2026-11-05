from ..test_ledger import authority
from .audit import prove

def test_twelve_maximality_and_quantitative_theorems(authority):
    r=prove(authority)
    assert r['kernel_checked'] and r['fresh_object_checked'] and len(r['axiom_closures'])==12
    assert all(set(v)<={'propext','Classical.choice','Quot.sound'} for v in r['axiom_closures'].values())
