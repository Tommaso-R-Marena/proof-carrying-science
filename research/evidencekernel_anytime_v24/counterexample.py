"""Exact false-discovery attack when the physical propensity contradicts registration.

This is an ASSUMPTION VIOLATION, not a bypass of a correctly operated design.
Under true p=9/10, but a false uniform registration p=1/2, a researcher who
observes an all-null binary experiment with Y(0)=Y(1)=1 can obtain apparently
strong positive evidence through a wrong inverse-propensity correction.
"""
from __future__ import annotations
from fractions import Fraction
from math import comb
from .kernel import taylor_lower

def evaluate():
    n=64
    p_actual=Fraction(9,10)
    p_claimed=Fraction(1,2)
    alpha=Fraction(1,20)
    c=Fraction(3)
    lam=Fraction(1,8)
    assert taylor_lower(c,16)*alpha>=1
    w=1/p_claimed+1/(1-p_claimed)
    B=c/lam+lam*n*w*w/8
    # For all-null, Y_i(1)=Y_i(0)=1. A fixed sum of k treated allocations
    # yields registered HT=2k-2(n-k)=4k-2n. Its legitimate ATE is exactly 0.
    bad_counts=[k for k in range(n+1) if Fraction(4*k-2*n)>B]
    exact_failure=sum((Fraction(comb(n,k))*p_actual**k*(1-p_actual)**(n-k)
                       for k in bad_counts),Fraction(0))
    assert bad_counts==list(range(43,n+1))
    # Under the actual correct p, mathematical validity of the anytime
    # confidence sequence follows from the martingale theorem, not this attack.
    return {'nominal_alpha':str(alpha),'actual_treatment_probability':str(p_actual),
            'falsely_claimed_treatment_probability':str(p_claimed),
            'n':n,'exact_false_positive_probability':str(exact_failure),
            'approx_false_positive_probability':float(exact_failure),
            'rejected_treated_counts':bad_counts,
            'invalid_assumption':'recorded propensities disagree with physical randomization'}

if __name__=='__main__':
    import json
    print(json.dumps(evaluate(),indent=2))
