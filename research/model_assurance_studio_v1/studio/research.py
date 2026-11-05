"""Non-authoritative, bounded research checks for PCS Model Assurance Studio.

These operations do not execute user code or invoke submitted model runtimes.
Scalar ONNX candidates use exact rational *idealized* arithmetic, which is not
by itself a reproduction in ONNX Runtime or a proof about IEEE-754 execution.
Stoichiometric invariants use exact rational row reduction, with a deliberately
strict abstention policy on SBML features outside simple reaction-only models.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import product
from math import gcd, lcm, isfinite
import struct

MAX_WITNESS_TRIALS = 1024
MAX_MATRIX_DIM = 32
MAX_FRACTION_BITS = 512
SUPPORTED_SCALAR = {'Identity','Neg','Relu','Abs','Add','Sub','Mul','Div'}


def value_shape(proto, wire_fields):
    """Read a concrete scalar/length-one tensor shape or return None (unknown)."""
    present = False
    shape = None
    for f,w,v in wire_fields(proto,2):
        if f != 2 or w != 2:
            continue
        for tf,tw,tv in wire_fields(v,3):
            if tf != 1 or tw != 2:
                continue
            for ef,ew,ev in wire_fields(tv,4):
                if ef != 2 or ew != 2:
                    continue
                present = True
                dims=[]
                for df,dw,dv in wire_fields(ev,5):
                    if df != 1 or dw != 2:
                        continue
                    n=None
                    for a,b,c in wire_fields(dv,6):
                        if a == 1 and b == 0:
                            n = c
                        elif a == 2 and b == 2:
                            n = None
                    if n is None or n>1:
                        return None
                    dims.append(n)
                shape = tuple(dims)
    return shape if present and (shape == () or shape == (1,)) else None


def _sample_points(lo, hi, dtype):
    """Small deterministic finite candidate set, rounding to declared f32/f64."""
    grid = [-8,-4,-2,-1,-.75,-.5,-.25,-.125,0,.125,.25,.5,.75,1,2,4,8]
    grid += [lo, hi, (lo+hi)/2]
    values=set()
    for v in grid:
        try:
            vv = struct.unpack('<f',struct.pack('<f',v))[0] if dtype==1 else float(v)
            if isfinite(vv) and lo <= vv <= hi:
                values.add(vv)
        except (OverflowError, ValueError, struct.error):
            continue
    return sorted(values, key=lambda x:(-abs(x),x))


def find_scalar_witness(nodes, inputs, outputs, initializers, types, shapes, policy):
    """Candidate violating input for an exceptionally narrow scalar ONNX subset.

    Returns (candidate, reason). Candidate is explicitly not runtime-validated.
    """
    if len(nodes)>512:
        return None,'Scalar candidate search has a strict 512-node budget'
    if not inputs or len(inputs)>3 or not outputs or len(outputs)>8:
        return None, 'Only 1–3 graph inputs and 1–8 outputs supported'
    if not all(types.get(n) in (1,11) and shapes.get(n) in ((),(1,)) for n in inputs+outputs):
        return None, 'Requires explicit scalar or [1] floating-point input/output shapes'
    for ins, outs, op, domain, nested in nodes:
        if op not in SUPPORTED_SCALAR or domain not in ('','ai.onnx') or nested or len(outs)!=1 or not outs[0] or len([x for x in ins if x]) not in (1,2):
            return None, 'Unsupported operator, optional input or non-scalar operation'
    constants={}
    for name, bounds in initializers.items():
        if bounds is None or bounds[0]!=bounds[1]:
            return None, 'Initializer values are not uniquely available as scalar constants'
        constants[name]=Fraction.from_float(float(bounds[0]))
    points = [ _sample_points(policy['input_min'],policy['input_max'],types[n]) for n in inputs ]
    if any(not p for p in points):
        return None, 'No representable scalar candidate within assumed input interval'
    tested=0
    for samples in product(*points):
        if tested>=MAX_WITNESS_TRIALS:break
        tested+=1
        env=constants | {name:Fraction.from_float(x) for name,x in zip(inputs,samples)}
        valid=True
        for ins,outs,op,_,_ in nodes:
            a=[env.get(k) for k in ins if k]
            if not a or any(v is None for v in a):valid=False;break
            if op in ('Identity','Neg','Relu','Abs') and len(a)!=1:valid=False;break
            if op in ('Add','Sub','Mul','Div') and len(a)!=2:valid=False;break
            if op=='Div' and a[1]==0:valid=False;break
            try:
                val = {'Identity':lambda: a[0], 'Neg':lambda: -a[0],
                       'Relu':lambda: max(Fraction(0),a[0]), 'Abs':lambda: abs(a[0]),
                       'Add':lambda: a[0]+a[1], 'Sub':lambda: a[0]-a[1],
                       'Mul':lambda: a[0]*a[1], 'Div':lambda: a[0]/a[1]}[op]()
            except (ArithmeticError,OverflowError,ValueError):valid=False;break
            if val.numerator.bit_length()>MAX_FRACTION_BITS or val.denominator.bit_length()>MAX_FRACTION_BITS:
                valid=False;break
            env[outs[0]]=val
        if not valid or any(o not in env for o in outputs):continue
        violations=[o for o in outputs if env[o] < Fraction(str(policy['output_min'])) or env[o] > Fraction(str(policy['output_max']))]
        if violations:
            return {
                'status':'CANDIDATE_UNREPLAYED','semantics':'idealized rational elementwise scalar arithmetic',
                'model_execution':False,'inputs':dict(zip(inputs,samples)),
                'outputs':{o:float(env[o]) for o in outputs},
                'exact_output_fractions':{o:str(env[o]) for o in outputs},
                'violating_outputs':violations,'samples_tested':tested,
                'assumptions':{'input_interval':[policy['input_min'],policy['input_max']],
                               'required_output_interval':[policy['output_min'],policy['output_max']]},
                'reproduction_needed':'Reproduce against pinned ONNX Runtime in an isolated environment, then independently review the policy.'
            }, None
    return None, f'No idealized scalar counterexample in {tested} deterministic candidate inputs (not evidence of safety)'


def _rref_nullspace(a, ncols):
    """Nullspace basis for A over rationals; A has ncols columns."""
    a=[row[:] for row in a]
    nrows=len(a);piv=[];k=0
    for j in range(ncols):
        q=next((i for i in range(k,nrows) if a[i][j]),None)
        if q is None:continue
        a[k],a[q]=a[q],a[k]
        scale=a[k][j];a[k]=[x/scale for x in a[k]]
        for i in range(nrows):
            if i!=k and a[i][j]:
                m=a[i][j];a[i]=[v-m*u for v,u in zip(a[i],a[k])]
        piv.append(j);k+=1
        if k==nrows:break
    free=[j for j in range(ncols) if j not in piv]
    vecs=[]
    for f in free:
        vec=[Fraction(0) for _ in range(ncols)];vec[f]=Fraction(1)
        for i,j in enumerate(piv):vec[j]=-a[i][f]
        mul=lcm(*(x.denominator for x in vec))
        vi=[int(x*mul) for x in vec]
        common=gcd(*vi)
        if common:vi=[v//abs(common) for v in vi]
        if next((x for x in vi if x),1)<0:vi=[-x for x in vi]
        vecs.append(vi)
    return len(piv),vecs


def sbml_conservation(model, species, reactions, tag):
    """Exact linear invariants of a reaction-only SBML stoichiometric matrix.

    Never infer physical mass conservation; abstain on rules, events,
    boundary species, alternative stoichiometry or conversions.
    """
    if not species or not reactions:
        return None,'Requires at least one species and one reaction'
    if len(species)>MAX_MATRIX_DIM or len(reactions)>MAX_MATRIX_DIM:
        return None,'Species/reaction matrix exceeds 32 × 32 research cap'
    if any(not x.get('id') for x in species) or len({x.get('id') for x in species})!=len(species):
        return None,'Unknown or duplicate species identifiers'
    if any(x.get('boundaryCondition','false').lower()=='true' or x.get('constant','false').lower()=='true' or x.get('conversionFactor') for x in species):
        return None,'Boundary/constant/conversion-factor species require dedicated semantics'
    if model.get('conversionFactor') or any(tag(x) in ('event','assignmentRule','rateRule','algebraicRule','initialAssignment') for x in model.iter()):
        return None,'Event, rule, conversion factor or initial assignment requires a richer dynamical model'
    if any(x.get('fast','false').lower()=='true' for x in reactions):
        return None,'Fast reaction semantics not covered'
    ids=[s.get('id') for s in species]
    rows=[ [Fraction(0) for _ in reactions] for _ in species]
    ix={x:i for i,x in enumerate(ids)}
    try:
        for j,r in enumerate(reactions):
            for group in r:
                kind=tag(group)
                if kind not in ('listOfReactants','listOfProducts'):continue
                sign=-1 if kind=='listOfReactants' else 1
                for ref in group:
                    if tag(ref)!='speciesReference':continue
                    name=ref.get('species')
                    if name not in ix:return None, f'Unknown species in reaction: {name}'
                    if any(tag(c)=='stoichiometryMath' for c in ref):
                        return None,'Dynamic stoichiometryMath not covered'
                    st=Fraction(ref.get('stoichiometry','1'))
                    if st<0 or st.numerator.bit_length()>MAX_FRACTION_BITS or st.denominator.bit_length()>MAX_FRACTION_BITS:
                        return None,'Negative or oversized stoichiometric coefficient'
                    rows[ix[name]][j]+=sign*st
        rank,basis=_rref_nullspace([[rows[i][j] for i in range(len(species))] for j in range(len(reactions))],len(species))
        if any(any(sum(b[i]*rows[i][j] for i in range(len(species)))!=0 for j in range(len(reactions))) for b in basis):
            return None,'Internal invariant calculation did not replay'
        if any(abs(x).bit_length()>MAX_FRACTION_BITS for b in basis for x in b):
            return None,'Invariant coefficients exceed output budget'
    except (ZeroDivisionError, ValueError, ArithmeticError, TypeError):
        return None,'Non-constant or invalid stoichiometric coefficient'
    return {'stoichiometric_rank':rank,'linear_invariant_count':len(basis),
            'conservation_basis':[{ids[i]:v for i,v in enumerate(b) if v} for b in basis],
            'matrix_shape':[len(species),len(reactions)],
            'meaning':'Exact left-nullspace of the reaction-only stoichiometric matrix; assumes d(amount)/dt = N·v with no additional species-changing effects.',
            'not_established':'Physical mass conservation, full SBML semantics, kinetic stability, or biological realism'},None

# Chemical formulas are never guessed from arbitrary SBML species IDs.
_ELEMENT_NAMES = set('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og'.split())

def formula_elements(formula):
    """Conservative elemental formula grammar (no parentheses/isotopes/charges)."""
    import re
    if not isinstance(formula,str) or len(formula)>160:return None
    counts={}; pos=0
    for m in re.finditer(r'([A-Z][a-z]?)([1-9][0-9]{0,5})?',formula):
        if m.start()!=pos or m.group(1) not in _ELEMENT_NAMES:return None
        pos=m.end()
        elem=m.group(1);counts[elem]=counts.get(elem,0)+int(m.group(2) or '1')
    return counts if pos==len(formula) and counts else None


def sbml_element_balance(species,reactions,tag):
    """Formula-based per-reaction balance with exact coefficients, if formula supplied."""
    formulas={}
    for s in species:
        raw = next((value for key,value in s.attrib.items() if key.rsplit('}',1)[-1]=='chemicalFormula'),None)
        formulas[s.get('id')]=formula_elements(raw)
    if not any(v is not None for v in formulas.values()):
        return None,'No recognized explicit fbc:chemicalFormula annotations; cannot infer formulas from names'
    balanced=0;unsupported=0;violations=[]
    for r in reactions:
        amount={}
        missing=False
        for group in r:
            kind=tag(group)
            if kind not in ('listOfReactants','listOfProducts'):continue
            sign=-1 if kind=='listOfReactants' else 1
            for ref in group:
                if tag(ref)!='speciesReference':continue
                form=formulas.get(ref.get('species'))
                if form is None or any(tag(e)=='stoichiometryMath' for e in ref):
                    missing=True;break
                try:coeff=Fraction(ref.get('stoichiometry','1'))
                except (ValueError,TypeError):missing=True;break
                if coeff<0 or coeff.numerator.bit_length()>MAX_FRACTION_BITS or coeff.denominator.bit_length()>MAX_FRACTION_BITS:
                    missing=True;break
                for elem,cnt in form.items():amount[elem]=amount.get(elem,Fraction(0))+sign*coeff*cnt
        if missing:
            unsupported+=1;continue
        bad={x:str(n) for x,n in sorted(amount.items()) if n}
        if bad:
            if len(violations)<12:violations.append({'reaction':r.get('id') or '(unnamed)','element_imbalance':bad})
        else:balanced+=1
    return {'reaction_count':len(reactions),'balanced_reactions':balanced,
            'unresolved_reactions':unsupported,'imbalanced_reactions_sample':violations,
            'imbalanced_reactions_at_least':len(violations),
            'scope':'Formal stoichiometric consistency of explicitly annotated elemental formulas; charge, chemistry, reactions and kinetics not otherwise certified'},None


def sbml_charge_balance(species, reactions, tag):
    """Exact charge bookkeeping where explicit integer fbc:charge tags are provided.

    Charge annotations are accepted as declared, not independently validated.
    Boundary reservoirs or unmodeled electron exchange can change interpretation.
    """
    charges={}
    for sp in species:
        v=next((val for key,val in sp.attrib.items() if key.rsplit('}',1)[-1]=='charge'),None)
        if v is not None:
            try:
                z=int(v)
                if str(z)!=v.strip() or abs(z)>100000:raise ValueError('invalid charge')
            except (TypeError,ValueError):
                return None, 'An explicit fbc:charge value is not a bounded integer'
            charges[sp.get('id')]=z
    if not charges:
        return None,'No explicitly annotated fbc:charge values; charges are never guessed from species names'
    unbalanced=[];balanced=unresolved=0
    for r in reactions:
        imbalance=Fraction(0);valid=True
        for group in r:
            direction=tag(group)
            if direction not in ('listOfReactants','listOfProducts'):continue
            sign=-1 if direction=='listOfReactants' else 1
            for ref in group:
                if tag(ref)!='speciesReference':continue
                sp=ref.get('species')
                if sp not in charges or any(tag(x)=='stoichiometryMath' for x in ref):
                    valid=False;break
                try:
                    coeff=Fraction(ref.get('stoichiometry','1'))
                    if coeff<0 or max(coeff.numerator.bit_length(),coeff.denominator.bit_length())>MAX_FRACTION_BITS:
                        valid=False;break
                    imbalance+=sign*coeff*charges[sp]
                except (TypeError,ValueError,ArithmeticError):valid=False;break
            if not valid:break
        if not valid:unresolved+=1
        elif imbalance:
            if len(unbalanced)<12:unbalanced.append({'reaction':r.get('id') or '(unnamed)', 'signed_charge_imbalance':str(imbalance)})
        else:balanced+=1
    return {'balanced_reactions':balanced,'imbalanced_reactions_at_least':len(unbalanced),
            'unresolved_reactions':unresolved,'unbalanced_sample':unbalanced,
            'scope':'Stoichiometric bookkeeping of annotated charges only; electron reservoirs, redox environment and species annotations unverified'},None
