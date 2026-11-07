"""Conditional, nonexecuting reconstruction of a bounded PEtab reaction model.

Source plugins/scripts never run. A disclosed structural projection is checked by
the unchanged older SBML parser; initial/time assignments use closed MathML.
Python/SBML refinement, numerical error bounds and scientific meaning remain open.
"""
from __future__ import annotations
from decimal import Decimal,localcontext
import hashlib
import math
import xml.etree.ElementTree as ET

from research.scientific_understanding_v2.model_checks import SBMLModel,safe_xml
from research.scientific_understanding_v2.interpretation import parse_expression
from .workflow import number,table,join_predictions,residual_statistics,source,record
from .correspondence import parse_project_links

NS='http://www.sbml.org/sbml/level2/version4'
ML='http://www.w3.org/1998/Math/MathML'
def tag(n):return n.tag.rsplit('}',1)[-1]
def first(n,name):return next((x for x in n if tag(x)==name),None)


def math_value(n,env,decimal=False,depth=0):
    if n is None or depth>64 or not n.tag.startswith('{'+ML+'}'):raise ValueError('MathML namespace/depth')
    op=tag(n);c=Decimal if decimal else float
    go=lambda child:math_value(child,env,decimal,depth+1)
    if op=='math':
        if len(n)!=1:raise ValueError('single expression required')
        r=go(n[0])
    elif op=='cn':
        text=(n.text or '').strip();kind=n.get('type','real')
        if len(n):
            if len(n)!=1 or n[0].tag!='{'+ML+'}sep':raise ValueError('compound constant')
            other=(n[0].tail or '').strip()
            if kind=='e-notation':
                if abs(int(other))>64:raise ValueError('exponent bound')
                text+='e'+other
            elif kind=='rational':
                q=number(text)/number(other);return c(q.numerator)/c(q.denominator)
            else:raise ValueError('compound constant type')
        number(text);r=c(text)
    elif op=='ci':r=env[(n.text or '').strip()]
    elif op=='csymbol' and n.get('definitionURL')=='http://www.sbml.org/sbml/symbols/time':r=env['__time__']
    elif op=='apply':
        if not 2<=len(n)<=65 or n[0].tag!='{'+ML+'}'+tag(n[0]):raise ValueError('MathML operator')
        operator=tag(n[0]);a=[go(x) for x in list(n)[1:]]
        if operator=='plus':r=sum(a,c(0))
        elif operator=='times':r=math.prod(a)
        elif operator=='minus' and len(a) in {1,2}:r=-a[0] if len(a)==1 else a[0]-a[1]
        elif operator=='divide' and len(a)==2:r=a[0]/a[1]
        elif operator=='power' and len(a)==2:
            x,p=a
            if abs(p)>16:raise ValueError('power bound')
            if p==int(p):r=x**int(p)
            elif p in {c('0.5'),c('-0.5')}:
                if x<0:raise ValueError('negative real root')
                r=x.sqrt() if decimal else math.sqrt(x)
                if p<0:r=1/r
            else:raise ValueError('unsupported noninteger power')
        elif operator in {'exp','ln'} and len(a)==1:
            if abs(a[0])>10000:raise ValueError('transcendental bound')
            r=(a[0].exp() if operator=='exp' else a[0].ln()) if decimal else (math.exp(a[0]) if operator=='exp' else math.log(a[0]))
        else:raise ValueError('unsupported MathML '+operator)
    else:raise ValueError('unsupported mathematical node '+op)
    if not (r.is_finite() if decimal else math.isfinite(r)):raise ValueError('nonfinite mathematics')
    return r


def scalar(ir,env,depth=0):
    if depth>40:raise ValueError('observable depth')
    op=ir['op']
    if op=='number':return float(number(ir['value']))
    if op=='symbol':return env[ir['name']]
    if op=='neg':return -scalar(ir['arg'],env,depth+1)
    a=[scalar(x,env,depth+1) for x in ir.get('args',[])]
    if op=='add':return sum(a)
    if op=='mul':return math.prod(a)
    if op=='sub' and len(a)==2:return a[0]-a[1]
    if op=='div' and len(a)==2:return a[0]/a[1]
    if op=='pow' and len(a)==2 and a[1]==int(a[1]) and abs(a[1])<=16:return a[0]**int(a[1])
    if op=='call' and ir['function'] in {'exp','log'} and len(a)==1 and not ir.get('keywords'):return math.exp(a[0]) if ir['function']=='exp' else math.log(a[0])
    raise ValueError('unsupported observable expression')


def resolve(expressions,seed,decimal=False):
    todo=dict(expressions);values={k:v for k,v in seed.items() if k not in todo}
    while todo:
        done=[]
        for name,expr in todo.items():
            try:values[name]=math_value(expr,values,decimal);done.append(name)
            except KeyError:pass
        if not done:raise ValueError('cyclic/unresolved assignments')
        for name in done:del todo[name]
    return values


class ReactionRuntime:
    def __init__(self,raw,overrides):
        root=safe_xml(raw)
        if root.tag!='{'+NS+'}sbml':raise ValueError('SBML L2V4 subset required')
        self.original_sha256=hashlib.sha256(raw).hexdigest();model=first(root,'model');initial={};self.rules={}
        for n in model.iter():
            if tag(n) in {'event','rateRule','algebraicRule','functionDefinition','constraint','delay','stoichiometryMath'}:raise ValueError('unsupported original semantic feature '+tag(n))
            if tag(n) in {'initialAssignment','assignmentRule'}:
                if n.tag!='{'+NS+'}'+tag(n):raise ValueError('foreign assignment')
                target=initial if tag(n)=='initialAssignment' else self.rules;key=n.get('symbol') if tag(n)=='initialAssignment' else n.get('variable')
                if not key or key in target:raise ValueError('ambiguous assignment')
                target[key]=first(n,'math')
        pg=first(model,'listOfParameters');sg=first(model,'listOfSpecies')
        parameters=list(pg) if pg is not None else [];species=list(sg) if sg is not None else []
        declared={n.get('id') for n in parameters+species}
        if len(initial)>32 or len(self.rules)>32 or not (set(initial)|set(self.rules))<=declared or set(initial)&set(self.rules):raise ValueError('assignment target/budget')
        if set(overrides)&(set(initial)|set(self.rules)):raise ValueError('condition/assignment precedence unsupported')
        # Remove only independently interpreted constructs for structural parsing.
        for parent in model.iter():
            for child in list(parent):
                if tag(child) in {'listOfRules','listOfInitialAssignments'}:parent.remove(child)
        for n in parameters:
            if n.get('id') in overrides:n.set('value',str(overrides[n.get('id')]))
            n.set('constant','true')
        for n in species:
            if n.get('id') in overrides:
                if 'initialAmount' in n.attrib:raise ValueError('amount override unsupported')
                n.set('initialConcentration',str(overrides[n.get('id')]))
        self.projection=ET.tostring(root,encoding='utf-8');self.base=SBMLModel(self.projection)
        seed={**{k:float(v) for k,v in self.base.parameters.items()},**{k:float(v) for k,v in self.base.compartments.items()},**dict(zip(self.base.species,map(float,self.base.initial))),'__time__':0.0}
        float_initial=resolve(initial,resolve(self.rules,seed))
        with localcontext() as ctx:
            ctx.prec=80;d={k:Decimal(str(v)) for k,v in seed.items()}
            for n in parameters:d[n.get('id')]=Decimal(n.get('value','0'))
            exact=resolve(initial,resolve(self.rules,d,True),True)
        self.initial=[float(exact[s]) for s in self.base.dynamic];self.static={s:float(exact[s]) for s in self.base.species}
        self.initial_decimal80={s:str(exact[s]) for s in self.base.species}
        self.initial_difference=max(abs(float_initial[s]-float(exact[s])) for s in self.base.species)
        self.parameters={k:float(v) for k,v in self.base.parameters.items()}
    def environment(self,t,y):
        return resolve(self.rules,{**self.parameters,**{k:float(v) for k,v in self.base.compartments.items()},**self.static,**dict(zip(self.base.dynamic,y)),'__time__':float(t)})
    def rhs(self,t,y):
        env=self.environment(t,y);rates=[math_value(r['math'],{**env,**{k:float(v) for k,v in r['local'].items()}}) for r in self.base.reactions]
        return [sum(float(x)*v for x,v in zip(row,rates))/float(self.base.compartments[self.base.species_compartment[s]]) for s,row in zip(self.base.dynamic,self.base.matrix)]


def reconstruct(artifacts):
    bindings=[]
    try:
        links=parse_project_links(artifacts)
        if len(links)!=1:raise ValueError('one explicit PEtab problem required')
        link=links[0]
        if any(len(link[k])!=1 for k in ['sbml_files','measurement_files','condition_files','observable_files']):raise ValueError('one table/model per problem required')
        paths=[link['config_path'],link['parameter_file'],link['sbml_files'][0],link['measurement_files'][0],link['condition_files'][0],link['observable_files'][0]]
        bindings=[source(p,artifacts[p]) for p in paths]
        p_rows=table(artifacts[paths[1]],paths[1])[1];params={r['parameterId']:r['nominalValue'] for r in p_rows}
        measurements=table(artifacts[paths[3]],paths[3])[1];conditions={r['conditionId']:r for r in table(artifacts[paths[4]],paths[4])[1]};observables={r['observableId']:r for r in table(artifacts[paths[5]],paths[5])[1]}
        if not 0<len(measurements)<=2000 or len(conditions)>12 or any(r.get('preequilibrationConditionId') for r in measurements):raise ValueError('reconstruction budget/preequilibration unsupported')
        from scipy.integrate import solve_ivp
        import numpy as np
        predictions={'Radau':[],'BDF':[]};details=[]
        for cid in sorted({r['simulationConditionId'] for r in measurements}):
            rows=[r for r in measurements if r['simulationConditionId']==cid];times=sorted({float(number(r['time'])) for r in rows})
            if min(times)<0 or max(times)>1e6:raise ValueError('time domain')
            overrides=dict(params)
            for k,v in conditions[cid].items():
                if k in {'conditionId','conditionName'} or not v:continue
                overrides[k]=params.get(v,v);number(overrides[k])
            runtime=ReactionRuntime(artifacts[paths[2]],overrides);states={};costs={}
            for method in predictions:
                if max(times)==0:ys=np.asarray(runtime.initial)[:,None];cost=0
                else:
                    solved=solve_ivp(runtime.rhs,(0,max(times)),runtime.initial,t_eval=times,method=method,rtol=1e-9,atol=1e-12)
                    if not solved.success or not np.isfinite(solved.y).all():raise ValueError('solver failed')
                    ys=solved.y;cost=solved.nfev
                states[method]=ys;costs[method]=cost
                for row in rows:
                    t=float(number(row['time']));env=runtime.environment(t,ys[:,times.index(t)]);oid=row['observableId']
                    for i,v in enumerate(row.get('observableParameters','').split(';') if row.get('observableParameters') else [],1):env[f'observableParameter{i}_{oid}']=float(number(params.get(v,v)))
                    value=float(scalar(parse_expression(observables[oid]['observableFormula']),env))
                    if not math.isfinite(value):raise ValueError('nonfinite observable')
                    predictions[method].append({**{k:v for k,v in row.items() if k!='measurement'},'simulation':repr(value)})
            details.append({'condition':cid,'states':runtime.base.dynamic,'times':times,'initial_decimal80':runtime.initial_decimal80,'initial_float_decimal_difference':runtime.initial_difference,
                'solver_max_state_difference':float(np.max(np.abs(states['Radau']-states['BDF']))),'rhs_calls':costs,
                'stoichiometric_matrix':[[str(v) for v in row] for row in runtime.base.matrix],'structural_projection_sha256':hashlib.sha256(runtime.projection).hexdigest()})
        pairs,_=join_predictions(measurements,predictions['Radau']);stats=residual_statistics(pairs);provided=[]
        for p,raw in artifacts.items():
            if not p.lower().endswith(('.csv','.tsv')):continue
            try:
                if 'simulation' in table(raw,p)[0]:provided.append(p)
            except (ValueError,UnicodeError):pass
        difference=None
        if len(provided)==1:
            peer=provided[0];comparison,_=join_predictions([{**p,'measurement':p['simulation']} for p in predictions['Radau']],table(artifacts[peer],peer)[1])
            difference=float(max(abs(x['measurement']-x['simulation']) for x in comparison));bindings.append(source(peer,artifacts[peer]))
        return record('conditional_ode_reconstruction','REPRODUCED_COMPUTATION',bindings,{'conditions':details,'measurements':len(measurements),'residuals':stats,
            'maximum_observable_solver_difference':max(abs(float(a['simulation'])-float(b['simulation'])) for a,b in zip(predictions['Radau'],predictions['BDF'])),
            'provided_prediction_max_absolute_difference':difference,'Python_SBML_refinement':'OPEN',
            'assumptions':['Closed SBML L2V4 reactions, fixed compartments, acyclic initial/assignment expressions, no events/rate rules/functions/external parameter updates.',
              'PEtab nominal parameters, literal conditions and measurement-specific observable scale placeholders are interpreted according to the declared problem.',
              'Finite two-solver comparison, not a rigorous error enclosure, fit-optimum proof or empirical validation.']},'Conditional independent model reconstruction from source and finite comparison to supplied predictions')
    except (ValueError,KeyError,TypeError,ZeroDivisionError,OverflowError,ArithmeticError,ImportError,ET.ParseError) as exc:
        return record('conditional_ode_reconstruction','UNKNOWN',bindings,{'reason':type(exc).__name__+': '+str(exc)[:300]},'Reconstruction subset unsupported or failed; no affirmative result inferred')
