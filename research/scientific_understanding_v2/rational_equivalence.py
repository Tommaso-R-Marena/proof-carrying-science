"""Bounded exact rational-function comparison, independent of sample equality.

Normal forms are Python computations, not a kernel-certified compiler. Equality
holds on the common defined domain; nonzero denominator obligations remain open.
Budgets cause abstention rather than heuristic equality.
"""
from fractions import Fraction
from .model_checks import fraction,tag

MAX_TERMS=1024
MAX_DEGREE=32


def clean(poly):
    p={m:c for m,c in poly.items() if c}
    if len(p)>MAX_TERMS or any(sum(e for s,e in m)>MAX_DEGREE for m in p) or any(max(c.numerator.bit_length(),c.denominator.bit_length())>8192 for c in p.values()):raise ValueError('symbolic normal form resource bound')
    return p


def add(a,b,sign=1):
    p=dict(a)
    for m,c in b.items():p[m]=p.get(m,Fraction())+sign*c
    return clean(p)


def multiply(a,b):
    if len(a)*len(b)>MAX_TERMS*4:raise ValueError('symbolic product resource bound')
    p={}
    for x,c in a.items():
        for y,d in b.items():
            exponents=dict(x)
            for s,e in y:exponents[s]=exponents.get(s,0)+e
            m=tuple(sorted(exponents.items()));p[m]=p.get(m,Fraction())+c*d
    return clean(p)


def power(a,n):
    p={():Fraction(1)}
    for i in range(n):p=multiply(p,a)
    return p


def normalized(ir,conditions,depth=0):
    if depth>64:raise ValueError('symbolic depth')
    op=ir['op'];one={():Fraction(1)}
    if op=='number':return clean({():fraction(ir['value'])}),one
    if op=='symbol':return {((ir['name'],1),):Fraction(1)},one
    if op=='neg':
        a,b=normalized(ir['arg'],conditions,depth+1);return {m:-v for m,v in a.items()},b
    args=[normalized(a,conditions,depth+1) for a in ir.get('args',[])]
    if op=='pow':
        e=ir['args'][1]
        if e.get('op')!='number':raise ValueError('nonconstant exponent')
        n=fraction(e['value'])
        if n.denominator!=1 or abs(n)>8:raise ValueError('bounded integer exponent')
        a,b=args[0]
        if n<0:a,b=b,a;conditions.append(serialized(b))
        return power(a,abs(int(n))),power(b,abs(int(n)))
    if op=='div' and len(args)==2:
        (a,b),(c,d)=args
        if not c:raise ValueError('identically zero denominator')
        conditions.append(serialized(c));return multiply(a,d),multiply(b,c)
    if op in {'add','sub','mul'}:
        a,b=({},one) if op in {'add','sub'} else (one,one)
        for i,(c,d) in enumerate(args):
            if op=='mul':a,b=multiply(a,c),multiply(b,d)
            else:a,b=add(multiply(a,d),multiply(c,b),-1 if op=='sub' and i else 1),multiply(b,d)
        return a,b
    raise ValueError('outside rational expression fragment')


def serialized(p):return [{'monomial':[[s,e] for s,e in m],'coefficient':str(c)} for m,c in sorted(p.items())]


def direct_ir(node):
    kind=tag(node)
    if kind=='math':return direct_ir(node[0])
    if kind=='cn':
        if len(node):raise ValueError('compound constant')
        return {'op':'number','value':(node.text or '').strip()}
    if kind=='ci':return {'op':'symbol','name':(node.text or '').strip()}
    if kind=='apply':
        op={'plus':'add','minus':'sub','times':'mul','divide':'div','power':'pow'}.get(tag(node[0]))
        if op is None:raise ValueError('nonrational source expression')
        args=[direct_ir(n) for n in list(node)[1:]]
        if op=='sub' and len(args)==1:return {'op':'neg','arg':args[0]}
        return {'op':op,'args':args}
    raise ValueError('unsupported source rational expression')


def compare(a,b):
    conditions=[];(p,q)=normalized(a,conditions);(r,s)=normalized(b,conditions)
    if not q or not s:raise ValueError('undefined rational function')
    left,right=multiply(p,s),multiply(r,q);difference=add(left,right,-1)
    return {'status':'EQUAL_ON_COMMON_DEFINED_DOMAIN' if not difference else 'DISTINCT_RATIONAL_FUNCTIONS',
            'cross_difference':serialized(difference),'source_cross_polynomial':serialized(left),'candidate_cross_polynomial':serialized(right),
            'nonzero_denominator_obligations':conditions,'authority':False,
            'scope':'Exact bounded rational normalization; all original denominators must be nonzero. Python normalization/compiler refinement is unproved.'}
