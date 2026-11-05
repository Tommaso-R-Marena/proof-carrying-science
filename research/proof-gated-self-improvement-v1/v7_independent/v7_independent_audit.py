#!/usr/bin/env python3
"""Independent, exact-integer V7 wire and semantic reference auditor.

Not Lean; never grants production authority. Release fixtures only (unless --fixtures).
Policy and certificate parsers are strict/canonical; all network arithmetic uses unbounded
Python integers. Universal scalar ReLU properties checked by finite affine-cell analysis.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, random, time
from dataclasses import dataclass
from typing import Optional

class BadWire(ValueError): pass


def tagged_ints(raw: bytes, tag: str) -> list[int]:
    try: text = raw.decode('ascii')
    except UnicodeDecodeError: raise BadWire('non ASCII')
    parts = text.split('|')
    if parts[0] != tag or any(not p for p in parts[1:]):
        raise BadWire('bad tag or field')
    out=[]
    for x in parts[1:]:
        try: number=int(x)
        except ValueError: raise BadWire('non-integer field')
        if x != str(number) or x == '-0' or x.startswith('+'):
            raise BadWire('noncanonical signed decimal')
        out.append(number)
    return out

def encode(tag: str, fields) -> bytes:
    return (tag+'|'+ '|'.join(map(str, fields))).encode('ascii')

class Reader:
    def __init__(self, nums): self.a=nums;self.i=0
    def int(self):
        if self.i>=len(self.a):raise BadWire('truncated')
        v=self.a[self.i];self.i+=1;return v
    def nat(self):
        v=self.int()
        if v<0:raise BadWire('negative length/nat')
        return v
    def block(self):
        n=self.nat()
        if n>len(self.a)-self.i:raise BadWire('truncated block')
        out=self.a[self.i:self.i+n];self.i+=n;return out
    def bytes(self):
        xs=self.block()
        if any(x<0 or x>255 for x in xs):raise BadWire('invalid byte')
        return bytes(xs)
    def finish(self):
        if self.i!=len(self.a):raise BadWire('trailing fields')

@dataclass(frozen=True)
class Unit:
    w:int;b:int;o:int
@dataclass(frozen=True)
class Net:
    bias:int
    units:tuple[Unit,...]

def decode_net_ints(xs:list[int]) -> Net:
    if not xs or (len(xs)-1)%3:raise BadWire('invalid network field count')
    return Net(xs[0],tuple(Unit(*xs[i:i+3]) for i in range(1,len(xs),3)))
def net_ints(n): return [n.bias]+[x for u in n.units for x in (u.w,u.b,u.o)]
def model(raw:bytes,maxwidth=None,bound=None):
    n=decode_net_ints(tagged_ints(raw,'PGSI2-WIDE'))
    if maxwidth is not None and (len(n.units)>maxwidth or any(abs(v)>bound for v in net_ints(n))):
        raise BadWire('model violates architecture')
    return n

def pred(n:Net,x:int)->int:
    return n.bias+sum(u.o*max(0,u.w*x+u.b) for u in n.units)

def split(u:Unit)->int:
    if u.w>0:return (-u.b)//u.w
    if u.w<0:return (u.b-1)//(-u.w)
    raise ValueError('constant has no split')

def cutpoints(*nets:Net)->list[int]:
    return sorted({split(u)+1 for n in nets for u in n.units if u.w})

def affine(n:Net,x:int)->tuple[int,int]:
    slope=0;intercept=n.bias
    for u in n.units:
        if u.w*x+u.b>0:
            slope+=u.o*u.w;intercept+=u.o*u.b
    return slope,intercept

def cells(*nets):
    """Inclusive integer intervals, None = unbounded side. Cuts change act. at cut."""
    cuts=cutpoints(*nets)
    if not cuts:yield (None,None)
    else:
        yield(None,cuts[0]-1)
        for a,b in zip(cuts,cuts[1:]):yield(a,b-1)
        yield(cuts[-1],None)

def representative(lo,hi):
    return lo if lo is not None else (hi if hi is not None else 0)

def affine_error(n,t,x):
    a,b=affine(n,x);c,d=affine(t,x);return a-c,b-d

def noforget(old:Net,new:Net,target:Net)->tuple[bool,Optional[int]]:
    """Decide ∀ integer x: old(x)=target(x) ⇒ new(x)=target(x) exactly.
    On each affine cell solve old-target=0 in integer arithmetic.
    """
    for lo,hi in cells(old,new,target):
        x=representative(lo,hi)
        oa,ob=affine_error(old,target,x); na,nb=affine_error(new,target,x)
        if oa==0:
            if ob:continue
            # Every integer in cell is incumbent-correct. Candidate must vanish.
            if na==0 and nb==0:continue
            if lo is not None and hi is not None and lo==hi:
                if na*lo+nb: return False,lo
                continue
            for probe in ((lo,lo+1) if lo is not None else ((hi,hi-1) if hi is not None else (0,1))):
                if na*probe+nb:return False,probe
        elif (-ob)%oa==0:
            root=(-ob)//oa
            if (lo is None or lo<=root) and (hi is None or root<=hi):
                if na*root+nb:return False,root
    return True,None

def max_error(n:Net,t:Net,L:int,U:int)->tuple[int,Optional[int]]:
    if L>U:return 0,None
    best=(-1,None)
    for a,b in cells(n,t):
        a=max(a,L) if a is not None else L
        b=min(b,U) if b is not None else U
        if a>b:continue
        for x in (a,b):
            err=abs(pred(n,x)-pred(t,x))
            if err>best[0]:best=(err,x)
    return best

@dataclass(frozen=True)
class Policy:
    version:int;checker:int;predicate:int;width:int;bound:int;lo:int;hi:int
    corpus:tuple[int,...];target:Net

def parse_policy(raw:bytes)->Policy:
    r=Reader(tagged_ints(raw,'PGPOL7'))
    v,c,p,w,b=r.nat(),r.nat(),r.nat(),r.nat(),r.nat()
    lo,hi=r.int(),r.int()
    corpus=tuple(r.block());target=decode_net_ints(r.block());r.finish()
    pol=Policy(v,c,p,w,b,lo,hi,corpus,target)
    if policy_wire(pol)!=raw:raise BadWire('policy not canonical')
    return pol

def policy_wire(p:Policy):
    return encode('PGPOL7',[p.version,p.checker,p.predicate,p.width,p.bound,p.lo,p.hi,
        len(p.corpus),*p.corpus,len(net_ints(p.target)),*net_ints(p.target)])

@dataclass(frozen=True)
class Cert:
    version:int;predicate:int;width:int;bound:int;generation:int;lo:int;hi:int
    gain:int;inc_loss:int;cand_loss:int;err_witness:int;err_level:int
    corpus:tuple[int,...];target:Net;old:bytes;new:bytes
    order:Optional[tuple[tuple[int,int,int,int,int],...]]=None

def parse_cert(raw:bytes)->Cert:
    tag=raw.split(b'|',1)[0].decode('ascii','replace')
    if tag not in ('PGSC6','PGSC7'):raise BadWire('bad certificate tag')
    r=Reader(tagged_ints(raw,tag))
    order=None
    if tag=='PGSC7':
        ol=r.block()
        if len(ol)%5:raise BadWire('bad sweep width')
        order=tuple(tuple(ol[i:i+5]) for i in range(0,len(ol),5))
    version,predid,w,b,g=r.nat(),r.nat(),r.nat(),r.nat(),r.nat()
    L,U,gain,oloss,nloss,ew,elevel=r.int(),r.int(),r.int(),r.nat(),r.nat(),r.int(),r.nat()
    corpus=tuple(r.block());t=decode_net_ints(r.block());old=r.bytes();new=r.bytes();r.finish()
    c=Cert(version,predid,w,b,g,L,U,gain,oloss,nloss,ew,elevel,corpus,t,old,new,order)
    if cert_wire(c)!=raw:raise BadWire('certificate not canonical')
    return c

def cert_fields(c):
    base=[c.version,c.predicate,c.width,c.bound,c.generation,c.lo,c.hi,c.gain,c.inc_loss,
        c.cand_loss,c.err_witness,c.err_level]
    for block in (c.corpus,net_ints(c.target),c.old,c.new):
        base.extend([len(block),*block])
    return base

def cert_wire(c):
    base=cert_fields(c)
    if c.order is None:return encode('PGSC6',base)
    order=[v for tu in c.order for v in tu]
    return encode('PGSC7',[len(order),*order,*base])

def sweep_order(old,new,t):
    units=([(u.w,u.b,u.o,1,0) for u in old.units] +
      [(u.w,u.b,u.o,0,1) for u in new.units] +
      [(u.w,u.b,u.o,-1,-1) for u in t.units])
    return collections.Counter(u for u in units if u[0]!=0)

def check_cert_semantics(p:Policy,g:int,active:bytes,wire:bytes)->tuple[Optional[bytes],str]:
    if (p.version,p.predicate) != (7,1) or p.checker not in (6,7):return None,'unsupported policy'
    try: c=parse_cert(wire)
    except BadWire as e:return None,'malformed certificate: '+str(e)
    if p.checker==6 and c.order is not None:return None,'unexpected PGSC7'
    if p.checker==7 and c.order is None:return None,'unexpected PGSC6'
    if c.version!=p.checker or c.predicate!=p.predicate:return None,'certificate version/predicate mismatch'
    if (c.width,c.bound,c.lo,c.hi,c.corpus,c.target)!=(p.width,p.bound,p.lo,p.hi,p.corpus,p.target):
        return None,'configuration mismatch'
    if c.generation!=g or c.old!=active:return None,'generation / incumbent mismatch'
    try:old=model(c.old,p.width,p.bound);new=model(c.new,p.width,p.bound)
    except BadWire as e:return None,'noncanonical/invalid model: '+str(e)
    T=p.target
    if c.gain not in p.corpus or pred(old,c.gain)==pred(T,c.gain) or pred(new,c.gain)!=pred(T,c.gain):
        return None,'gain witness invalid'
    oldloss=sum(abs(pred(old,x)-pred(T,x)) for x in p.corpus)
    newloss=sum(abs(pred(new,x)-pred(T,x)) for x in p.corpus)
    if (oldloss,newloss)!=(c.inc_loss,c.cand_loss) or newloss>=oldloss:
        return None,'loss witness invalid'
    if p.lo<=p.hi:
        if not(p.lo<=c.err_witness<=p.hi) or abs(pred(old,c.err_witness)-pred(T,c.err_witness))!=c.err_level:
            return None,'incumbent error witness invalid'
        # Witness must be actual incumbent maximum for soundness of C relative to old.
        # The Lean witness checker needs only a level at one point; it separately bounds
        # candidate at this level, which suffices for candidate <= incumbent max.
        if max_error(new,T,p.lo,p.hi)[0] > c.err_level:
            return None,'candidate bound invalid'
    nf,witness=noforget(old,new,T)
    if not nf:return None,'forgetting at '+str(witness)
    if c.order is not None:
        if collections.Counter(c.order)!=sweep_order(old,new,T):return None,'sweep permutation wrong'
        if any(split(Unit(*a[:3]))>split(Unit(*b[:3])) for a,b in zip(c.order,c.order[1:])):
            return None,'sweep unsorted'
    return c.new,'accepted by independent strong-semantic oracle'

@dataclass(frozen=True)
class Receipt:
    version:int;old_gen:int;expected_gen:int;accepted:bool;new_gen:int
    policy:bytes;old:bytes;candidate:bytes;certificate:bytes;new:bytes

def receipt_wire(rc:Receipt):
    fields=[rc.version,rc.old_gen,rc.expected_gen,int(rc.accepted),rc.new_gen]
    for b in [rc.policy,rc.old,rc.candidate,rc.certificate,rc.new]:fields.extend([len(b),*b])
    return encode('PGSR7',fields)

def parse_receipt(wire:bytes)->Receipt:
    r=Reader(tagged_ints(wire,'PGSR7'))
    version,g,eg,yes,ng=r.nat(),r.nat(),r.nat(),r.int(),r.nat()
    if yes not in (0,1):raise BadWire('invalid boolean')
    pol,old,cand,cert,new=(r.bytes() for _ in range(5));r.finish()
    rc=Receipt(version,g,eg,bool(yes),ng,pol,old,cand,cert,new)
    if receipt_wire(rc)!=wire:raise BadWire('receipt not canonical')
    return rc

def receipt_verdict(rc:Receipt,pinned:bytes)->tuple[bool,str]:
    if rc.version!=7 or rc.policy!=pinned or rc.old_gen!=rc.expected_gen:
        return False,'receipt header mismatch'
    try: policy=parse_policy(pinned)
    except BadWire as e:return False,'bad pinned policy: '+str(e)
    cand,reason=check_cert_semantics(policy,rc.old_gen,rc.old,rc.certificate)
    if rc.accepted:
        if cand is None:return False,'false positive: '+reason
        if rc.candidate!=cand or rc.new!=cand or rc.new_gen!=rc.old_gen+1:
            return False,'accepted transition misbound'
    else:
        if cand is not None:return False,'false negative: oracle accepts'
        if rc.candidate or rc.new!=rc.old or rc.new_gen!=rc.old_gen:
            return False,'rejection changed state'
    return True,'semantics consistent'

def run(fixtures:pathlib.Path,seed:int=7317,mutations:int=20000):
    start=time.time();counts=collections.Counter();detail=[]
    p=(fixtures/'policies'/'pinned0.pgpol7').read_bytes()
    assert policy_wire(parse_policy(p))==p
    all_files=[]
    for dirname,ext,parse,serialize in [
        ('policies','.pgpol7',parse_policy,policy_wire),
        ('certs','.pgsc7',parse_cert,cert_wire),
        ('receipts','.pgsr7',parse_receipt,receipt_wire)]:
        for path in sorted((fixtures/dirname).glob('*'+ext)):
            b=path.read_bytes();assert serialize(parse(b))==b,(path,'roundtrip')
            all_files.append((path,b,parse));counts[dirname+'_canonical']+=1
    state_gen=0;state= b'PGSI2-WIDE|0'
    for path in sorted((fixtures/'receipts').glob('*.pgsr7'),key=lambda x:int(x.stem.split('_')[1])):
        rc=parse_receipt(path.read_bytes())
        ok,reason=receipt_verdict(rc,p)
        if not ok:raise AssertionError((path,reason))
        if rc.old_gen!=state_gen or rc.old!=state:raise AssertionError((path,'broken chain'))
        state_gen,state=rc.new_gen,rc.new
        counts['receipts_replayed']+=1
        counts['accepted' if rc.accepted else 'rejected']+=1
    assert state_gen==3
    assert state == b'PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2',state
    # Independent oracle tests on actual fixed fixtures and V7 acceptance versions.
    pol=parse_policy(p)
    for path in sorted((fixtures/'certs').glob('*.pgsc7')):
        c=parse_cert(path.read_bytes())
        pc=Policy(pol.version,7,pol.predicate,pol.width,pol.bound,pol.lo,pol.hi,pol.corpus,pol.target)
        cand,msg=check_cert_semantics(pc,c.generation,c.old,path.read_bytes())
        if cand!=c.new:raise AssertionError((path,msg))
        counts['pgsc7_semantic_accept']+=1
    # Verify no forgetting + max bound against brute force on bounded randomized models.
    rng=random.Random(seed)
    for i in range(6000):
        nets=[Net(rng.randint(-5,5),tuple(Unit(rng.randint(-5,5),rng.randint(-7,7),rng.randint(-4,4)) for _ in range(rng.randint(0,5)))) for _ in range(3)]
        old,new,t=nets
        ours,w=noforget(old,new,t)
        brute=all(pred(old,x)!=pred(t,x) or pred(new,x)==pred(t,x) for x in range(-100,101))
        if ours!=brute:raise AssertionError(('noforget',i,ours,brute,nets,w))
        L=rng.randint(-25,5);U=rng.randint(5,25)
        exact=max_error(new,t,L,U)[0]
        slow=max(abs(pred(new,x)-pred(t,x)) for x in range(L,U+1))
        if exact!=slow:raise AssertionError(('max',i,exact,slow,nets))
        counts['random_semantics']+=1
    # Deliberately adversarial distant-error construction. A three-ReLU integer
    # impulse at N is invisible in all nearby tests but breaks universal no-forgetting.
    def impulse(n:int)->tuple[Unit,...]:
        return (Unit(1,1-n,1),Unit(1,-n,-2),Unit(1,-1-n,1))
    for n in (1000,10**6,10**12):
        target=Net(0,impulse(0))
        old=Net(0,())
        new=Net(0,impulse(0)+impulse(n))
        assert all(pred(new,x)==pred(target,x) for x in range(-100,101))
        assert sum(abs(pred(new,x)-pred(target,x)) for x in (-4,-3,-2,-1,0,1,2,3,4)) == 0
        assert sum(abs(pred(old,x)-pred(target,x)) for x in (-4,-3,-2,-1,0,1,2,3,4)) == 1
        assert max_error(new,target,-100,100)[0] == 0
        good,witness=noforget(old,new,target)
        if good or witness != n:raise AssertionError(('far-tail witness missed',n,witness))
        counts['distant_regressions_detected']+=1
    # Canonicality checks on arbitrary single-byte corruptions. A changed byte may
    # legitimately produce a DIFFERENT canonical object, so re-encode is the condition.
    for i in range(mutations):
        path,raw,parse=rng.choice(all_files)
        mutable=bytearray(raw)
        typ=rng.choice(['replace','insert','delete','append'])
        idx=rng.randrange(len(mutable))
        byte=rng.choice([0,1,31,43,45,46,48,49,55,57,58,124,127,128,255])
        if typ=='replace':mutable[idx]=byte
        elif typ=='insert':mutable.insert(idx,byte)
        elif typ=='delete':del mutable[idx]
        else:mutable.append(byte)
        corrupt=bytes(mutable)
        try:
            out=parse(corrupt)
            ser= policy_wire if path.suffix=='.pgpol7' else cert_wire if path.suffix=='.pgsc7' else receipt_wire
            if ser(out)!=corrupt:raise AssertionError(('noncanonical accepted',path,corrupt))
            counts['canonical_mutation_valid_other']+=1
        except BadWire:counts['canonical_mutation_rejected']+=1
    # Adversarial permutations and semantic mutations on the complete receipt stream.
    chain=[parse_receipt(x.read_bytes()) for x in sorted((fixtures/'receipts').glob('*.pgsr7'),key=lambda x:int(x.stem.split('_')[1]))]
    for i,rc in enumerate(chain):
        altered=[
            Receipt(rc.version,rc.old_gen+1,rc.expected_gen,rc.accepted,rc.new_gen,rc.policy,rc.old,rc.candidate,rc.certificate,rc.new),
            Receipt(rc.version,rc.old_gen,rc.expected_gen,not rc.accepted,rc.new_gen,rc.policy,rc.old,rc.candidate,rc.certificate,rc.new),
            Receipt(rc.version,rc.old_gen,rc.expected_gen,rc.accepted,rc.new_gen,rc.policy,rc.old+b'x',rc.candidate,rc.certificate,rc.new),
            Receipt(rc.version,rc.old_gen,rc.expected_gen,rc.accepted,rc.new_gen,rc.policy,rc.old,rc.candidate,rc.certificate+b'!',rc.new),
            Receipt(rc.version,rc.old_gen,rc.expected_gen,rc.accepted,rc.new_gen,rc.policy,rc.old,rc.candidate,rc.certificate,rc.new+b'x'),
            Receipt(rc.version,rc.old_gen,rc.expected_gen,rc.accepted,rc.new_gen,rc.policy+b'!',rc.old,rc.candidate,rc.certificate,rc.new),
        ]
        for alt in altered:
            ok,reason=receipt_verdict(alt,p)
            if ok:
                if alt.certificate == rc.certificate or rc.accepted:
                    raise AssertionError(('unsafe mutation accepted',i,reason,alt))
                # A new invalid certificate may generate an equally valid *rejected* receipt.
                # V7 does not promise signatures/nonrepudiation; preserve this negative finding.
                counts['rejected_receipt_certificate_malleability']+=1
            else:
                counts['semantic_receipt_mutations_rejected']+=1
    # Two existentially valid forks can share gen; index alone cannot authenticate.
    summary=dict(counts)
    return dict(result='PASS',release_sha256='e98448c4d9493c54b88c876ea715c4c66d653565bf60d553c9627b14b7a5f8f8',
        fixture_root=str(fixtures),seed=seed,counts=summary,final_generation=state_gen,
        final_artifact_hex=state.hex(),elapsed_seconds=round(time.time()-start,3),
        caveats=['independent Python finite affine-cell oracle; not a Lean kernel check',
          'receipt checks are exact mathematical semantics and witness-structure checks, not an independent proof of the complete V7 sweep checker implementation',
          'No authentication, real monotonic storage, OS isolation or production security verified',
          'Random differential oracle scans [-100,100]; exact affine cell algorithm itself covers all integers by construction, but its Python correctness is unverified'])

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--fixtures',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent/'fixtures'/'proof_gated'/'v7')
    ap.add_argument('--mutations',type=int,default=20000)
    a=ap.parse_args()
    result=run(a.fixtures,mutations=a.mutations)
    print(json.dumps(result,indent=2))
