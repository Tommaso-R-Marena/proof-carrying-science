"""Reproduce a sharp-null false-positive increase under uncorrected optional peeking.

Seven-unit independent uniform assignment, *not* a registered v23 policy.
The distinction is explicit: this is a cautionary comparison, not a real trial.
"""
from fractions import Fraction
from .kernel import statistic

def run():
    y=(0,0,0,0,1,0,1)
    Y=tuple((v,v) for v in y)
    tests={}
    for t in range(2,8):
        paths=[tuple((mask>>i)&1 for i in range(t)) for mask in range(1<<t)]
        values=[statistic(Y,p) for p in paths]
        tests[t]=[Fraction(sum(x>=v for x in values),len(paths)) for v in values]
    hits=[]
    for mask in range(1<<7):
        for t in range(2,8):
            if tests[t][mask&((1<<t)-1)]<=Fraction(1,20):
                hits.append((mask,t));break
    return {'crossings':len(hits),'possible_assignments':1<<7,
            'exact_false_positive_fraction':str(Fraction(len(hits),1<<7)),
            'nominal_alpha':'1/20',
            'caution':'The seven-unit peek-on-p-value stop rule is not within the v23 registered-table API.'}
if __name__=='__main__':
    import json
    print(json.dumps(run(),indent=2,sort_keys=True))
