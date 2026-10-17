"""Untrusted exact-arithmetic candidate producer, outside verification authority."""
import csv
from fractions import Fraction
import hashlib
import io
import json
from itertools import combinations

from pcs.canonical_json import canonicalize_jcs_bytes as encode


def solve(matrix,rhs):
    n=len(rhs);a=[[Fraction(v) for v in row]+[Fraction(y)] for row,y in zip(matrix,rhs)]
    for j in range(n):
        pivot=next((i for i in range(j,n) if a[i][j]),None)
        if pivot is None:raise ValueError('singular design')
        a[j],a[pivot]=a[pivot],a[j];scale=a[j][j]
        a[j]=[v/scale for v in a[j]]
        for i in range(n):
            if i!=j:
                scale=a[i][j];a[i]=[v-scale*w for v,w in zip(a[i],a[j])]
    return [row[-1] for row in a]


def minimax(design,features):
    n=len(design);p=len(features);best=None
    for support in combinations(range(n),p):
        selected=[design[i] for i in support]
        values=solve([[row[j] for row in selected] for j in range(p)],features)
        weights=[Fraction(0) for _ in range(n)]
        for i,v in zip(support,values):weights[i]=v
        gain=sum(map(abs,weights))
        dual=solve(selected,[Fraction(1) if v>=0 else Fraction(-1) for v in values])
        if (all(abs(sum(a*b for a,b in zip(row,dual)))<=1 for row in design)
                and sum(a*b for a,b in zip(features,dual))==gain):
            if best is None or gain<best[0]:best=(gain,weights,dual)
    if best is None:raise ValueError('no exact primal/dual minimax certificate found')
    gain,weights,dual=best
    return {'weights':list(map(str,weights)),'dual':list(map(str,dual)),'gain':str(gain)}


def propose(data_raw,contract_raw):
    contract=json.loads(contract_raw)
    reader=csv.DictReader(io.StringIO(data_raw.decode()))
    rows=[(Fraction(r['x']),Fraction(r['y'])) for r in reader]
    models=[]
    for spec in contract['models']:
        p=spec['degree']+1;selected=[rows[i] for i in spec['fit_rows']]
        design=[[x**j for j in range(p)] for x,_ in selected];y=[v for _,v in selected]
        gram=[[sum(row[j]*row[k] for row in design) for k in range(p)] for j in range(p)]
        rhs=[sum(row[j]*v for row,v in zip(design,y)) for j in range(p)]
        b=solve(gram,rhs)
        sse=sum((v-sum(a*c for a,c in zip(row,b)))**2 for row,v in zip(design,y))
        queries=[]
        for q in spec['queries']:
            features=[Fraction(q)**j for j in range(p)];dual=solve(gram,features)
            weights=[sum(a*c for a,c in zip(row,dual)) for row in design]
            queries.append({'dual':list(map(str,dual)),'weights':list(map(str,weights)),
                            'gain':str(sum(map(abs,weights))),'minimax':minimax(design,features)})
        models.append({'coefficients':list(map(str,b)),'sse':str(sse),'queries':queries})
    return encode({'format':contract['format'],'contract_sha256':hashlib.sha256(contract_raw).hexdigest(),'models':models})
