"""Independent closed scientific computations. Imported code is never executed.

SBML MathML is interpreted directly here, separately from candidate lowering.
The supported MATLAB subset is parsed as scalar arithmetic, never evaluated by
MATLAB/Python eval. Numerical agreement is finite evidence, not program proof.
"""
from __future__ import annotations
import ast
from fractions import Fraction
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET


def tag(node):return node.tag.rsplit('}',1)[-1]
def children(node,name):return [n for n in node if tag(n)==name]
def first(node,name):
    namespace='{http://www.w3.org/1998/Math/MathML}' if name=='math' else node.tag.rsplit('}',1)[0]+'}'
    return next((n for n in node if n.tag==namespace+name),None)
def elements(node,name):
    child=first(node,name)
    return list(child) if child is not None else []


def safe_xml(raw):
    if len(raw)>5*1024*1024 or raw.count(b'<')>50000 or re.search(rb'<!\s*(?:DOCTYPE|ENTITY)',raw,re.I):raise ValueError('XML resources/entities unsupported')
    root=ET.fromstring(raw)
    if sum(1 for n in root.iter())>50000:raise ValueError('XML node bound')
    return root


def fraction(value):
    if not isinstance(value,str) or len(value)>100 or not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',value):raise ValueError('bounded numeric literal required')
    if 'e' in value.lower() and abs(int(value.lower().split('e')[1]))>100:raise ValueError('exponent bound')
    return Fraction(value)


def bounded(value):
    if isinstance(value,Fraction):
        if max(value.numerator.bit_length(),value.denominator.bit_length())>8192:raise ValueError('exact arithmetic bit budget')
    elif isinstance(value,int):
        if value.bit_length()>8192:raise ValueError('integer bit budget')
    elif not math.isfinite(float(value)) or abs(value)>1e100:raise ValueError('nonfinite/oversized numerical value')
    return value


def power(a,b):
    if b!=int(b) or abs(b)>8:raise ValueError('bounded integer power required')
    if isinstance(a,Fraction) and max(a.numerator.bit_length(),a.denominator.bit_length())*abs(int(b))>8192:raise ValueError('power bit budget')
    return bounded(a**int(b))


def mathml(node,values,depth=0):
    if node is None or depth>64:raise ValueError('MathML depth/missing expression')
    if not node.tag.startswith('{http://www.w3.org/1998/Math/MathML}'):raise ValueError('unsupported MathML namespace')
    kind=tag(node)
    if kind=='math':
        if len(node)!=1:raise ValueError('one expression required')
        return mathml(node[0],values,depth+1)
    if kind=='cn':
        if len(node):raise ValueError('compound MathML numeric literal unsupported')
        return fraction((node.text or '').strip())
    if kind=='ci':return values[(node.text or '').strip()]
    if kind!='apply' or len(node)<2:raise ValueError('unsupported MathML')
    if not node[0].tag.startswith('{http://www.w3.org/1998/Math/MathML}'):raise ValueError('unsupported MathML operator namespace')
    op=tag(node[0]);args=[mathml(n,values,depth+1) for n in list(node)[1:]]
    if op=='plus':
        value=0
        for a in args:value=bounded(value+a)
        return value
    if op=='times':
        value=1
        for a in args:value=bounded(value*a)
        return value
    if op=='minus' and len(args) in (1,2):return bounded(-args[0] if len(args)==1 else args[0]-args[1])
    if op=='divide' and len(args)==2:return bounded(args[0]/args[1])
    if op=='power' and len(args)==2:
        exponent=args[1]
        if exponent!=int(exponent) or abs(exponent)>8:raise ValueError('bounded integer power required')
        return power(args[0],exponent)
    raise ValueError('unsupported MathML operation '+op)


class SBMLModel:
    """Bounded deterministic reaction/rule subset; no events/delays/plugins."""
    def __init__(self,raw):
        root=safe_xml(raw)
        if root.tag!='{http://www.sbml.org/sbml/level2/version4}sbml' or root.get('level')!='2' or root.get('version')!='4':raise ValueError('only SBML L2V4 semantics supported')
        core_ns=root.tag.rsplit('}',1)[0]
        if any('required' in k and v=='true' for k,v in root.attrib.items()):raise ValueError('required extension package unsupported')
        allowed={'sbml','model','notes','annotation','listOfCompartments','compartment','listOfSpecies','species','listOfParameters','parameter','listOfRules','assignmentRule','listOfReactions','reaction','listOfReactants','listOfProducts','speciesReference','kineticLaw','listOfModifiers','modifierSpeciesReference','listOfUnitDefinitions','unitDefinition','listOfUnits','unit'}
        for n in root.iter():
            if tag(n) in allowed and n.tag!=core_ns+'}'+tag(n):raise ValueError('foreign core semantic element')
            for attribute in ('constant','boundaryCondition','hasOnlySubstanceUnits','reversible','fast'):
                if attribute in n.attrib and n.attrib[attribute] not in {'true','false'}:raise ValueError('unsupported boolean lexical form')
            if n.tag.startswith(core_ns+'}') and tag(n) not in allowed:raise ValueError('unsupported SBML semantic element '+tag(n))
            if n.get('fast')=='true' or n.get('conversionFactor') is not None:raise ValueError('unsupported fast/conversion semantics')
        global_ids=[n.get('id') for n in root.iter() if n.get('id') and tag(n) in {'model','species','compartment','reaction','unitDefinition'}]
        if len(global_ids)!=len(set(global_ids)):raise ValueError('duplicate global identifier')
        model=first(root,'model')
        if model is None:raise ValueError('missing model')
        if any(tag(n) in {'event','rateRule','algebraicRule','initialAssignment','functionDefinition','delay','stoichiometryMath'} for n in model.iter()):raise ValueError('unsupported SBML semantic feature')
        self.sha256=hashlib.sha256(raw).hexdigest();self.model_id=model.get('id');self.species=[];self.initial=[];self.boundary=set();self.compartments={};self.parameters={};self.assignments=[];self.reactions=[]
        for n in model.iter():
            if tag(n)=='compartment':
                name=n.get('id')
                if name in self.compartments:raise ValueError('duplicate compartment')
                self.compartments[name]=fraction(n.get('size','1'))
                if self.compartments[name]<=0 or n.get('constant','true')=='false':raise ValueError('fixed positive compartment required')
        species_nodes=elements(model,'listOfSpecies')
        if not 1<=len(species_nodes)<=32:raise ValueError('bounded species required')
        self.species_compartment={}
        for n in species_nodes:
            if n.tag!=core_ns+'}species':raise ValueError('foreign species element')
            name=n.get('id')
            if not name or name in self.species:raise ValueError('duplicate species')
            volume=self.compartments[n.get('compartment')]
            if n.get('initialConcentration') is not None and n.get('initialAmount') is not None:raise ValueError('ambiguous initial quantity')
            initial=fraction(n.get('initialConcentration','0')) if n.get('initialAmount') is None else fraction(n.get('initialAmount'))/volume
            if n.get('hasOnlySubstanceUnits','false')=='true':raise ValueError('amount-only species needs separate semantics')
            self.species.append(name);self.initial.append(initial);self.species_compartment[name]=n.get('compartment')
            if n.get('boundaryCondition','false')=='true' or n.get('constant','false')=='true':self.boundary.add(name)
        for n in elements(model,'listOfParameters'):
            name=n.get('id')
            if name in self.parameters or name in global_ids:raise ValueError('duplicate global parameter')
            self.parameters[name]=fraction(n.get('value','0'))
            # Assignment-target mutability is validated after rule collection.
        for n in elements(model,'listOfRules'):
            if tag(n)!='assignmentRule':raise ValueError('unsupported rule')
            if n.get('variable') in {name for name,expr in self.assignments}:raise ValueError('duplicate assignment')
            self.assignments.append((n.get('variable'),first(n,'math')))
        assigned={name for name,expr in self.assignments}
        for name in assigned:
            if name not in self.species and name not in self.parameters:raise ValueError('undeclared assignment target')
            declarations=[n for n in species_nodes if n.get('id')==name]+[n for n in elements(model,'listOfParameters') if n.get('id')==name]
            if len(declarations)!=1 or declarations[0].get('constant','false' if name in self.species else 'true')=='true':raise ValueError('constant assignment target')
        if any(n.get('constant','true')=='false' and n.get('id') not in assigned for n in elements(model,'listOfParameters')):raise ValueError('unmodeled mutable parameter')
        self.dynamic=[name for name in self.species if name not in self.boundary|assigned]
        for n in elements(model,'listOfReactions'):
            if n.tag!=core_ns+'}reaction':raise ValueError('foreign reaction element')
            law=first(n,'kineticLaw')
            if law is None:raise ValueError('missing reaction law')
            locals_list=[p for p in law.iter() if tag(p) in {'parameter','localParameter'}]
            if len({p.get('id') for p in locals_list})!=len(locals_list):raise ValueError('duplicate local parameter')
            local={p.get('id'):fraction(p.get('value','0')) for p in locals_list}
            stoich={name:Fraction() for name in self.dynamic}
            for label,sign in [('listOfReactants',-1),('listOfProducts',1)]:
                for ref in elements(n,label):
                    name=ref.get('species')
                    if name not in self.species:raise ValueError('unknown reaction species')
                    if name in stoich:stoich[name]+=sign*fraction(ref.get('stoichiometry','1'))
            self.reactions.append({'id':n.get('id'),'math':first(law,'math'),'local':local,'stoich':stoich})
        if len(self.reactions)>64:raise ValueError('reaction bound')
        self.matrix=[[r['stoich'][name] for r in self.reactions] for name in self.dynamic]
        self.dynamic_initial=[self.initial[self.species.index(name)] for name in self.dynamic]
        if not self.reactions:raise ValueError('no reactions')
        self.rhs(0,self.dynamic_initial)
    def context(self,y):
        values={**self.parameters,**self.compartments,**dict(zip(self.species,self.initial)),**dict(zip(self.dynamic,y))}
        pending=list(self.assignments)
        for _ in range(len(pending)+1):
            rest=[]
            for name,expr in pending:
                try:values[name]=mathml(expr,values)
                except KeyError:rest.append((name,expr))
            if not rest:return values
            if len(rest)==len(pending):raise ValueError('cyclic or unresolved assignment dependency')
            pending=rest
        raise ValueError('assignment dependency bound')
    def rhs(self,t,y):
        values=self.context(y);rates=[mathml(r['math'],{**values,**r['local']}) for r in self.reactions]
        return [sum((r['stoich'][name]*v for r,v in zip(self.reactions,rates)),0)/self.compartments[self.species_compartment[name]] for name in self.dynamic]


def left_nullspace(matrix):
    """Exact nullspace of S-transpose, independently checked by dot products."""
    if not matrix:return []
    if len(matrix)>32 or not matrix[0] or len(matrix[0])>64 or any(len(row)!=len(matrix[0]) for row in matrix):raise ValueError('rectangular bounded matrix required')
    matrix=[[Fraction(x) for x in row] for row in matrix]
    rows=[list(column) for column in zip(*matrix)];n=len(matrix);pivots=[];rank=0
    for col in range(n):
        pivot=next((r for r in range(rank,len(rows)) if rows[r][col]),None)
        if pivot is None:continue
        rows[rank],rows[pivot]=rows[pivot],rows[rank];scale=rows[rank][col];rows[rank]=[v/scale for v in rows[rank]]
        for r in range(len(rows)):
            if r!=rank:
                f=rows[r][col];rows[r]=[a-f*b for a,b in zip(rows[r],rows[rank])]
        pivots.append(col);rank+=1
    result=[]
    for free in set(range(n))-set(pivots):
        v=[Fraction() for _ in range(n)];v[free]=Fraction(1)
        for i,pivot in enumerate(pivots):v[pivot]=-rows[i][free]
        scale=math.lcm(*(x.denominator for x in v));integers=[int(x*scale) for x in v]
        divisor=math.gcd(*integers);integers=[x//divisor for x in integers]
        if next(x for x in integers if x)!=abs(next(x for x in integers if x)):integers=[-x for x in integers]
        if any(sum(v*s for v,s in zip(integers,column)) for column in zip(*matrix)):raise ValueError('invalid conservation certificate')
        result.append(integers)
    return sorted(result)


def conservation(model):
    # Matrix is on amount derivatives. Concentration invariants need fixed
    # compartment volume weights; report both without assuming unit volumes.
    vectors=left_nullspace(model.matrix)
    return {'species':model.dynamic,'reaction_ids':[r['id'] for r in model.reactions],
            'matrix':[[str(x) for x in row] for row in model.matrix],
            'certificates':[{'amount_weights':w,'concentration_weights':[str(Fraction(v)*model.compartments[model.species_compartment[n]]) for n,v in zip(model.dynamic,w)],
                             'column_dot_products':[str(sum(v*s for v,s in zip(w,col))) for col in zip(*model.matrix)],
                             'initial_total':str(sum(Fraction(v)*model.compartments[model.species_compartment[n]]*y for n,v,y in zip(model.dynamic,w,model.dynamic_initial)))} for w in vectors],
            'scope':'Exact stoichiometric finite algebra. Continuous-trajectory conservation requires the specified ODE, complete dependencies, fixed compartments, and suitable differentiability; Python refinement and biological interpretation remain open.'}


def scalar_ast(expression,values):
    if len(expression)>10000:raise ValueError('expression bound')
    node=ast.parse(expression,mode='eval').body
    def visit(n,depth=0):
        if depth>64:raise ValueError('expression depth')
        if isinstance(n,ast.Constant) and type(n.value) in (float,int):return fraction(ast.get_source_segment(expression,n))
        if isinstance(n,ast.Name):return values[n.id]
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
            x=visit(n.operand,depth+1);return -x if isinstance(n.op,ast.USub) else x
        if isinstance(n,ast.BinOp):
            a,b=visit(n.left,depth+1),visit(n.right,depth+1)
            if isinstance(n.op,ast.Add):return bounded(a+b)
            if isinstance(n.op,ast.Sub):return bounded(a-b)
            if isinstance(n.op,ast.Mult):return bounded(a*b)
            if isinstance(n.op,ast.Div):return bounded(a/b)
            if isinstance(n.op,ast.Pow) and b==int(b) and abs(b)<=8:return power(a,b)
        raise ValueError('unsupported scalar syntax')
    return visit(node)


def matlab_correspondence(model,raw,samples=12):
    """Finite rational oracle for authored scalar Octave export; no execution."""
    if type(samples) is not int or not 1<=samples<=32:raise ValueError('positive bounded sample count required')
    text=raw.decode('utf-8');lines=[]
    body=re.search(r'(?m)^function\s+xdot\s*=\s*f\(x,t\)\s*$',text)
    if body is None:raise ValueError('supported derivative function not found')
    rest=text[body.end():];end=re.search(r'(?m)^end\s*$',rest)
    if end is None:raise ValueError('unterminated derivative function')
    checked_body=rest[:end.start()]
    for line in checked_body.splitlines():
        line=line.split('%',1)[0].strip()
        if not line:continue
        if re.fullmatch(r'xdot\s*=\s*zeros\(\s*'+str(len(model.species))+r'\s*,\s*1\s*\);',line):continue
        match=re.fullmatch(r'(compartment_[A-Za-z0-9_]+|reaction_[A-Za-z0-9_]+|x\(\d+\)|xdot\(\d+\))\s*=\s*(.+);',line)
        if match:lines.append(match.groups())
        else:raise ValueError('unsupported statement in derivative function')
    if not lines:raise ValueError('no supported author export expressions')
    discrepancies=[]
    for sample in range(samples):
        y=[Fraction((i+1)*(sample+1),100) for i in range(len(model.dynamic))];values=model.context(y)
        env={f'x_{i+1}':values[name] for i,name in enumerate(model.species)};outputs={}
        for lhs,expression in lines:
            expression=re.sub(r'\bx\((\d+)\)',r'x_\1',expression).replace('^','**')
            value=scalar_ast(expression,env)
            if lhs.startswith('xdot('):outputs[int(lhs[5:-1])]=value
            else:env[re.sub(r'^x\((\d+)\)$',r'x_\1',lhs)]=value
        actual=model.rhs(0,y)
        for name,expected in zip(model.dynamic,actual):
            index=model.species.index(name)+1
            if outputs.get(index)!=expected:discrepancies.append({'sample':sample,'species':name,'sbml':str(expected),'author_export':str(outputs.get(index))})
    return {'status':'MATCHED_FINITE_RATIONAL_SAMPLES' if not discrepancies else 'CONTRADICTED',
            'samples':samples,'full_program_semantics_checked':False,'checked_scope':'linear scalar derivative function only; initializer and unused helpers not executed or certified','discrepancies':discrepancies,'source_sha256':hashlib.sha256(raw).hexdigest(),
            'code_executed':False,'scope':'Independent finite correspondence check of static supported author-export expressions, not a proof of complete source-to-runtime equivalence.'}


def integrate_model(model,t_end=10.0):
    import numpy as np
    from scipy.integrate import solve_ivp
    if not 0<t_end<=100:raise ValueError('bounded horizon')
    times=np.linspace(0,t_end,101);initial=np.array(model.dynamic_initial,dtype=float)
    def rhs(t,y):return np.array(model.rhs(t,y),dtype=float)
    results=[]
    for method,tol in [('Radau',1e-7),('BDF',1e-8)]:
        started=__import__('time').monotonic()
        solution=solve_ivp(rhs,(0,t_end),initial,method=method,rtol=tol,atol=tol*1e-3,t_eval=times)
        if not solution.success or solution.y.shape!=(len(initial),len(times)) or not np.isfinite(solution.y).all():raise ValueError('numerical solver failure')
        certificate=conservation(model);drift=[]
        for vector in certificate['certificates']:
            w=np.array([float(Fraction(x)) for x in vector['concentration_weights']]);totals=w@solution.y
            drift.append(float(np.max(abs(totals-float(Fraction(vector['initial_total']))))))
        results.append({'method':method,'rtol':tol,'atol':tol*1e-3,'nfev':solution.nfev,'seconds':__import__('time').monotonic()-started,
                        'final_values':solution.y[:,-1].tolist(),'minimum_state_value':float(solution.y.min()),'conserved_total_max_abs_drift':drift,
                        'trajectory':solution.y.tolist()})
    a=np.array(results[0].pop('trajectory'));b=np.array(results[1].pop('trajectory'))
    return {'status':'REPRODUCED_NUMERICALLY','species':model.dynamic,'time_points':times.tolist(),'runs':results,
            'max_solver_difference':float(np.max(abs(a-b))),
            'scope':'Two independent algorithms in one pinned SciPy implementation, specified finite horizon/tolerances. Not a rigorous global numerical error bound, published figure reproduction, or empirical biological validation.'}
