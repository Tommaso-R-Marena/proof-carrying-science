"""Independent Python checks of the *data* in PCS V5 release fixtures.

Not a Lean proof or substitute for Lean runtime. Uses direct integer arithmetic
and a different set of breakpoints than the exported Lean checker.
"""
from pathlib import Path
import csv, hashlib, json, re
from fractions import Fraction
from itertools import product
ROOT=Path(__file__).resolve().parents[2]/'formal'
PGSI1=re.compile(rb'PGSI1\|([RL])\|(-?(?:0|[1-9]\d*))\|(-?(?:0|[1-9]\d*))\Z')


def parse_pgsi2(raw: str):
    fields=raw.split('|')
    if fields[0]!='PGSI2-WIDE' or len(fields)<2 or (len(fields)-2)%3: raise ValueError('bad PGSI2 fields')
    if any(not re.fullmatch(r'-?(?:0|[1-9]\d*)',f) or f=='-0' for f in fields[1:]):raise ValueError('bad integer')
    params=list(map(int, fields[1:]));return (params[0],tuple(tuple(params[i:i+3]) for i in range(1,len(params),3)))


def predict(net,x):
    bias, units=net
    return bias+sum(out*max(0,w*x+b) for w,b,out in units)


def cuts(*nets):
    acc=set()
    for net in nets:
        for w,b,out in net[1]:
            if w>0:acc.add((-b)//w)
            elif w<0:acc.add(-((b)//w)-1)
    return sorted(acc)


def maximum_error(f,t,L,U):
    if L>U:return (0,None)
    points={L,U}
    for c in cuts(f,t):
        if L<=c<=U: points.add(c)
        if L<=c+1<=U: points.add(c+1)
    score=max(abs(predict(f,x)-predict(t,x)) for x in points)
    return score, sorted(x for x in points if abs(predict(f,x)-predict(t,x))==score)[0]


def forget(old,new,target):
    bps=cuts(old,new,target)
    cells=[]
    prev=None
    for c in bps:cells.append((prev,c));prev=c+1
    cells.append((prev,None))
    for lo,hi in cells:
        ref=lo if lo is not None else hi if hi is not None else 0
        # local affine relation via closed-form parameters and signs
        def affine(net,x):
            slope=0;offset=net[0]
            for w,b,out in net[1]:
                if w*x+b>0:
                    slope+=w*out;offset+=b*out
            return slope,offset
        oa,ob=affine(old,ref);ta,tb=affine(target,ref);na,nb=affine(new,ref)
        a,b=oa-ta,ob-tb
        candidates=[]
        if a==0 and b==0:
            if na==ta and nb==tb:continue
            if lo is not None:candidates=[lo,lo+1]
            elif hi is not None:candidates=[hi,hi-1]
            else:candidates=[0,1]
        elif a!=0 and (-b)%a==0:candidates=[(-b)//a]
        for x in candidates:
            if (lo is None or lo<=x) and (hi is None or x<=hi) and predict(old,x)==predict(target,x) and predict(new,x)!=predict(target,x):return x
    return None


def run():
    stats={}
    pg=ROOT/'fixtures/proof_gated'
    raw=(pg/'pgsi1_canonical.tsv').read_bytes().splitlines()
    seen=set()
    for row in raw:
        fields=row.split(b'\t');assert len(fields)==4,fields
        mode,wt,bs,artifact=fields
        assert PGSI1.fullmatch(artifact),artifact
        w,b=int(wt),int(bs)
        assert -32<=w<=32 and -32<=b<=32
        assert artifact==b'PGSI1|'+mode+b'|'+str(w).encode()+b'|'+str(b).encode()
        seen.add((mode,w,b))
    assert len(raw)==len(seen)==2*65*65
    assert seen==set(product((b'R',b'L'),range(-32,33),range(-32,33)))
    stats['pgsi1_canonical_vectors']=len(raw)
    negatives=list((pg/'pgsi1_negative').glob('*.txt'))
    for p in negatives:
        b=p.read_bytes()
        m=PGSI1.fullmatch(b)
        assert not m or any(abs(int(x))>32 or x==b'-0' for x in m.groups()[1:]),(p,b)
    stats['pgsi1_malformed_rejected']=len(negatives)
    robust_rows=list(csv.DictReader((pg/'robust_vectors.tsv').open(),delimiter='\t'))
    for r in robust_rows:
        f=parse_pgsi2(r['f']);t=parse_pgsi2(r['t']);L=int(r['lo']);U=int(r['hi'])
        got,x=maximum_error(f,t,L,U)
        assert got==int(r['maxAbsErr']),(r['name'],got,r['maxAbsErr'])
        if L<=U and U-L<=200:
            brute=max(abs(predict(f,z)-predict(t,z)) for z in range(L,U+1))
            assert brute==got,(r['name'],'brute',brute,got)
        if r['witness_at_max_minus_1']!='none':
            z=int(r['witness_at_max_minus_1'])
            assert L<=z<=U and abs(predict(f,z)-predict(t,z))>got-1,(r['name'],'bad witness')
        else:assert got==0 or L>U,(r['name'],'missing witness')
        assert int(r['probes'])<=3*(len(f[1])+len(t[1]))+2
    stats['robust_exact_rows']=len(robust_rows)
    strong=list(csv.DictReader((pg/'strong_gate_cases.tsv').open(),delimiter='\t'))
    target=parse_pgsi2('PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2')
    corpus=list(range(-4,5))
    def valid(model):return len(model[1])<=8 and all(-32<=v<=32 for u in model[1] for v in u) and -32<=model[0]<=32
    for r in strong:
        old=parse_pgsi2(r['incumbent']);new=parse_pgsi2(r['candidate']);L=int(r['lo']);U=int(r['hi'])
        oldcorr={x for x in corpus if predict(old,x)==predict(target,x)}
        newcorr={x for x in corpus if predict(new,x)==predict(target,x)}
        oloss=sum(abs(predict(old,x)-predict(target,x)) for x in corpus)
        nloss=sum(abs(predict(new,x)-predict(target,x)) for x in corpus)
        progress=valid(old) and valid(new) and oldcorr<=newcorr and oldcorr!=newcorr and nloss<oloss
        fw=forget(old,new,target)
        nf=fw is None
        om,_=maximum_error(old,target,L,U);nm,_=maximum_error(new,target,L,U)
        robust=nm<=om
        for key,v in [('A_progress',progress),('B_noForget',nf),('C_robust',robust),('accept',progress and nf and robust)]:
            assert str(v).lower()==r[key],(r['name'],key,v,r[key])
        if r['forget_witness']!='none':
            x=int(r['forget_witness']);assert predict(old,x)==predict(target,x) and predict(new,x)!=predict(target,x)
        if r['robust_witness']!='none':
            x=int(r['robust_witness']);assert L<=x<=U and abs(predict(new,x)-predict(target,x))>om
    stats['strong_gate_rows']=len(strong)
    stats['independent_python_fixture_validation']='PASS'
    return stats

if __name__=='__main__':print(json.dumps(run(),indent=2))
