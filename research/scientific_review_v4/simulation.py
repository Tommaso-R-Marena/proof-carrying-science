"""Conditional, nonexecuting reconstruction of a bounded PEtab reaction model.

Source plugins/scripts never run. A disclosed structural projection is checked by
the unchanged older SBML parser; initial/time assignments use closed MathML.
Python/SBML refinement, numerical error bounds and scientific meaning remain open.
"""
from __future__ import annotations
from decimal import Decimal,localcontext
from fractions import Fraction
import re
import hashlib
import math
import xml.etree.ElementTree as ET

from research.scientific_understanding_v2.model_checks import SBMLModel,safe_xml
from research.scientific_understanding_v2.interpretation import parse_expression
from .workflow import number,table,join_predictions,residual_statistics,source,record,_unique
from .correspondence import parse_project_links

NS='http://www.sbml.org/sbml/level2/version4'
ML='http://www.w3.org/1998/Math/MathML'
def tag(n):return n.tag.rsplit('}',1)[-1]
def first(n,name):
    namespace=ML if name=='math' else NS
    return next((x for x in n if x.tag=='{'+namespace+'}'+name),None)
def elements(n,name):
    group=first(n,name)
    return [] if group is None else list(group)

# An object key cannot collide with any legal source identifier, including
# a parameter literally named "__time__".
_TIME=object()
_INTEGER=re.compile(r'[+-]?[0-9]+\Z')
_REAL=re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z')


def _constant(n,decimal):
    if set(n.attrib)-{'type','base'} or n.get('base','10')!='10':raise ValueError('unsupported numeric base/attributes/units')
    kind=n.get('type','real');text=(n.text or '').strip()
    if kind not in {'real','integer','rational','e-notation'}:raise ValueError('unsupported numeric type')
    if kind in {'rational','e-notation'}:
        if len(n)!=1 or n[0].tag!='{'+ML+'}sep' or n[0].attrib or len(n[0]) or (n[0].text or '').strip():raise ValueError('compound constant requires one empty sep')
        other=(n[0].tail or '').strip()
        if not _INTEGER.fullmatch(other):raise ValueError('integer denominator/exponent required')
        if kind=='rational':
            if not _INTEGER.fullmatch(text):raise ValueError('integer rational numerator required')
            q=number(text)/number(other)
        else:
            if not _REAL.fullmatch(text) or abs(int(other))>64:raise ValueError('bounded decimal mantissa/exponent required')
            q=number(text+'e'+other)
    else:
        if len(n) or (kind=='integer' and not _INTEGER.fullmatch(text)):raise ValueError('invalid scalar numeric literal')
        q=number(text)
    return Decimal(q.numerator)/Decimal(q.denominator) if decimal else float(q)


def math_value(n,env,decimal=False,depth=0):
    if n is None or depth>64 or not n.tag.startswith('{'+ML+'}'):raise ValueError('MathML namespace/depth')
    op=tag(n);c=Decimal if decimal else float
    go=lambda child:math_value(child,env,decimal,depth+1)
    if op!='cn' and (any((x.tail or '').strip() for x in n) or (op in {'math','apply'} and (n.text or '').strip())):raise ValueError('mixed mathematical content')
    if op=='math':
        if n.attrib or len(n)!=1:raise ValueError('single expression required')
        r=go(n[0])
    elif op=='cn':r=_constant(n,decimal)
    elif op=='ci':
        if n.attrib or len(n) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',(n.text or '').strip()):raise ValueError('scalar identifier required')
        r=env[(n.text or '').strip()]
    elif op=='csymbol':
        if len(n) or set(n.attrib)-{'definitionURL','encoding'} or n.get('definitionURL')!='http://www.sbml.org/sbml/symbols/time' or n.get('encoding','text')!='text':raise ValueError('unsupported csymbol')
        r=env[_TIME]
    elif op=='apply':
        if n.attrib or not 2<=len(n)<=65 or n[0].tag!='{'+ML+'}'+tag(n[0]) or n[0].attrib or len(n[0]) or (n[0].text or '').strip():raise ValueError('MathML operator')
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


def _validate_math(n,depth=0):
    if n is None or depth>64 or not n.tag.startswith('{'+ML+'}'):raise ValueError('MathML namespace/depth')
    op=tag(n)
    if op=='cn':
        with localcontext() as ctx:ctx.prec=80;_constant(n,True)
        return
    if any((x.tail or '').strip() for x in n) or (op in {'math','apply'} and (n.text or '').strip()):raise ValueError('mixed mathematical content')
    if op=='ci':
        if n.attrib or len(n) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',(n.text or '').strip()):raise ValueError('scalar identifier required')
    elif op=='csymbol':
        if len(n) or set(n.attrib)-{'definitionURL','encoding'} or n.get('definitionURL')!='http://www.sbml.org/sbml/symbols/time' or n.get('encoding','text')!='text':raise ValueError('unsupported csymbol')
    elif op=='math':
        if n.attrib or len(n)!=1:raise ValueError('single expression required')
        _validate_math(n[0],depth+1)
    elif op=='apply':
        if n.attrib or not 2<=len(n)<=65:raise ValueError('MathML operator')
        operator=n[0];name=tag(operator);arity=len(n)-1
        if operator.tag!='{'+ML+'}'+name or operator.attrib or len(operator) or (operator.text or '').strip():raise ValueError('MathML operator')
        if not ((name in {'plus','times'} and arity>=1) or (name=='minus' and arity in {1,2}) or (name in {'divide','power'} and arity==2) or (name in {'exp','ln'} and arity==1)):raise ValueError('unsupported MathML operation')
        for child in list(n)[1:]:_validate_math(child,depth+1)
    else:raise ValueError('unsupported mathematical node '+op)


# Strict structure precedes the older structural parser. Only direct core model
# containers activate declarations; core notes/annotation are semantically inert.
_CHILDREN={
    'sbml':{'model'},
    'model':{'listOfUnitDefinitions','listOfCompartments','listOfSpecies','listOfParameters','listOfInitialAssignments','listOfRules','listOfReactions'},
    'listOfUnitDefinitions':{'unitDefinition'},'unitDefinition':{'listOfUnits'},'listOfUnits':{'unit'},
    'listOfCompartments':{'compartment'},'listOfSpecies':{'species'},'listOfParameters':{'parameter'},
    'listOfInitialAssignments':{'initialAssignment'},'listOfRules':{'assignmentRule'},
    'listOfReactions':{'reaction'},'reaction':{'listOfReactants','listOfProducts','listOfModifiers','kineticLaw'},
    'listOfReactants':{'speciesReference'},'listOfProducts':{'speciesReference'},'listOfModifiers':{'modifierSpeciesReference'},
    'kineticLaw':{'math','listOfParameters'},'initialAssignment':{'math'},'assignmentRule':{'math'},
    'unit':set(),'compartment':set(),'species':set(),'parameter':set(),'speciesReference':set(),'modifierSpeciesReference':set(),
}
_ATTRS={
    'sbml':{'level','version'},'model':set(),
    'listOfUnitDefinitions':set(),'unitDefinition':set(),'listOfUnits':set(),
    'unit':{'kind','exponent','scale','multiplier','offset'},
    'listOfCompartments':set(),'compartment':{'size','spatialDimensions','units','constant'},
    'listOfSpecies':set(),'species':{'compartment','initialAmount','initialConcentration','substanceUnits','hasOnlySubstanceUnits','boundaryCondition','constant','charge'},
    'listOfParameters':set(),'parameter':{'value','units','constant'},
    'listOfInitialAssignments':set(),'initialAssignment':{'symbol'},'listOfRules':set(),'assignmentRule':{'variable'},
    'listOfReactions':set(),'reaction':{'reversible','fast'},'listOfReactants':set(),'listOfProducts':set(),
    'listOfModifiers':set(),'speciesReference':{'species','stoichiometry'},'modifierSpeciesReference':{'species'},
    'kineticLaw':set(),
}
_SINGLETONS={'model','listOfUnitDefinitions','listOfCompartments','listOfSpecies','listOfParameters','listOfInitialAssignments','listOfRules','listOfReactions','listOfUnits','listOfReactants','listOfProducts','listOfModifiers','kineticLaw','math'}


def _original_tree(raw):
    root=safe_xml(raw)
    if root.tag!='{'+NS+'}sbml' or root.get('level')!='2' or root.get('version')!='4':raise ValueError('SBML L2V4 subset required')
    def check(n):
        if n.tag!='{'+NS+'}'+tag(n) or tag(n) not in _CHILDREN:raise ValueError('unsupported/foreign core semantic element '+tag(n))
        if set(n.attrib)-_ATTRS[tag(n)]-{'id','name','metaid','sboTerm'}:raise ValueError('unsupported SBML attributes')
        if any('}' in k for k in n.attrib):raise ValueError('SBML extension attributes unsupported')
        if n.get('offset') not in {None,'0','0.0'}:raise ValueError('offset units unsupported')
        for flag in ('constant','boundaryCondition','hasOnlySubstanceUnits','reversible','fast'):
            if flag in n.attrib and n.attrib[flag] not in {'true','false'}:raise ValueError('unsupported boolean lexical form')
        if n.get('fast')=='true' or n.get('conversionFactor') is not None:raise ValueError('unsupported fast/conversion semantics')
        # Removing the whole metadata subtree prevents an embedded core-looking
        # assignment from being discovered or numerically activated.
        for child in list(n):
            if child.tag in {'{'+NS+'}notes','{'+NS+'}annotation'}:n.remove(child)
        seen=set()
        for child in n:
            name=tag(child)
            if name not in _CHILDREN[tag(n)]:raise ValueError('unsupported/nested semantic element '+name)
            if name in _SINGLETONS and name in seen:raise ValueError('duplicate core container '+name)
            seen.add(name)
            if name=='math':
                if child.tag!='{'+ML+'}math':raise ValueError('foreign mathematics')
                _validate_math(child)
            else:check(child)
    check(root)
    models=[n for n in root if n.tag=='{'+NS+'}model']
    if len(models)!=1:raise ValueError('exactly one core model required')
    model=models[0]
    global_ids=[n.get('id') for n in root.iter() if tag(n) in {'model','unitDefinition','compartment','species','reaction'} or (tag(n)=='parameter' and n in elements(model,'listOfParameters'))]
    if any(not x or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',x) for x in global_ids) or len(global_ids)!=len(set(global_ids)):raise ValueError('duplicate/missing/invalid global identifier')
    return root,model


def model_identifiers(raw):
    _,model=_original_tree(raw)
    return {name:{n.get('id') for n in elements(model,group)} for name,group in [('parameters','listOfParameters'),('species','listOfSpecies'),('compartments','listOfCompartments')]}


class ReactionRuntime:
    def __init__(self,raw,overrides):
        root,model=_original_tree(raw)
        self.original_sha256=hashlib.sha256(raw).hexdigest();initial={};self.rules={}
        for group,kind,keyattr,target in [('listOfInitialAssignments','initialAssignment','symbol',initial),('listOfRules','assignmentRule','variable',self.rules)]:
            for n in elements(model,group):
                key=n.get(keyattr)
                if n.tag!='{'+NS+'}'+kind or not key or key in target or len(n)!=1 or first(n,'math') is None:raise ValueError('ambiguous/unsupported assignment')
                target[key]=first(n,'math')
        parameters=elements(model,'listOfParameters');species=elements(model,'listOfSpecies')
        declared={n.get('id') for n in parameters+species}
        if not set(overrides)<=declared:raise ValueError('unknown/compartment model override unsupported')
        if len(initial)>32 or len(self.rules)>32 or not (set(initial)|set(self.rules))<=declared or set(initial)&set(self.rules):raise ValueError('assignment target/budget')
        if set(overrides)&(set(initial)|set(self.rules)):raise ValueError('condition/assignment precedence unsupported')
        for n in parameters+species:
            if n.get('id') in self.rules and n.get('constant','false' if n in species else 'true')!='false':raise ValueError('constant original assignment target')
        # The projection removes only independently interpreted assignments and
        # inert metadata, fixes initialized parameters, and marks rule species
        # as boundary variables so the older parser supplies structure only.
        for child in list(model):
            if tag(child) in {'listOfRules','listOfInitialAssignments'}:model.remove(child)
        for n in parameters:
            if n.get('id') in overrides:number(overrides[n.get('id')]);n.set('value',str(overrides[n.get('id')]))
            n.set('constant','true')
        for n in species:
            if n.get('id') in overrides:
                if 'initialAmount' in n.attrib:raise ValueError('amount override unsupported')
                number(overrides[n.get('id')]);n.set('initialConcentration',str(overrides[n.get('id')]))
            if n.get('id') in self.rules:n.set('boundaryCondition','true')
        self.projection=ET.tostring(root,encoding='utf-8');self.base=SBMLModel(self.projection)
        exact_seed={**self.base.parameters,**self.base.compartments,**dict(zip(self.base.species,self.base.initial)),_TIME:Fraction(0)}
        seed={k:float(v) for k,v in exact_seed.items()};assignments={**initial,**self.rules}
        float_initial=resolve(assignments,seed)
        with localcontext() as ctx:
            ctx.prec=80
            d={k:Decimal(v.numerator)/Decimal(v.denominator) for k,v in exact_seed.items()}
            exact=resolve(assignments,d,True)
        self.initial=[float(exact[s]) for s in self.base.dynamic];self.static={s:float(exact[s]) for s in self.base.species}
        self.initial_decimal80={s:str(exact[s]) for s in self.base.species}
        self.initial_difference=max(abs(float_initial[s]-float(exact[s])) for s in self.base.species)
        self.parameters={k:float(exact[k]) for k in self.base.parameters}
    def environment(self,t,y):
        return resolve(self.rules,{**self.parameters,**{k:float(v) for k,v in self.base.compartments.items()},**self.static,**dict(zip(self.base.dynamic,y)),_TIME:float(t)})
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
        p_rows=table(artifacts[paths[1]],paths[1])[1];_unique(p_rows,'parameterId')
        params={r['parameterId']:r['nominalValue'] for r in p_rows}
        for value in params.values():number(value)
        measurements=table(artifacts[paths[3]],paths[3])[1]
        condition_columns,condition_rows=table(artifacts[paths[4]],paths[4]);_unique(condition_rows,'conditionId')
        observable_rows=table(artifacts[paths[5]],paths[5])[1];_unique(observable_rows,'observableId')
        conditions={r['conditionId']:r for r in condition_rows};observables={r['observableId']:r for r in observable_rows}
        identifiers=model_identifiers(artifacts[paths[2]])
        model_targets=identifiers['parameters']|identifiers['species']
        if set(params)&identifiers['compartments']:raise ValueError('compartment parameterization unsupported')
        if set(condition_columns)-{'conditionId','conditionName'}-model_targets:raise ValueError('unknown/compartment condition column unsupported')
        if not 0<len(measurements)<=2000 or len(conditions)>12 or any(r.get('preequilibrationConditionId') for r in measurements):raise ValueError('reconstruction budget/preequilibration unsupported')
        from scipy.integrate import solve_ivp
        import numpy as np
        predictions={'Radau':[],'BDF':[]};details=[]
        for cid in sorted({r['simulationConditionId'] for r in measurements}):
            rows=[r for r in measurements if r['simulationConditionId']==cid];times=sorted({float(number(r['time'])) for r in rows})
            if min(times)<0 or max(times)>1e6:raise ValueError('time domain')
            overrides={k:v for k,v in params.items() if k in model_targets}
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
                'stoichiometric_matrix':[[str(v) for v in row] for row in runtime.base.matrix],'original_model_sha256':runtime.original_sha256,'structural_projection_changes':['Remove core notes/annotation and independently interpreted initial assignments/assignment rules.','Fix parameter declarations for structural parsing; exclude assignment-rule species from independent dynamic state.'],'structural_projection_sha256':hashlib.sha256(runtime.projection).hexdigest()})
        pairs,_=join_predictions(measurements,predictions['Radau']);stats=residual_statistics(pairs);provided=[]
        solver_pairs,_=join_predictions([{**p,'measurement':p['simulation']} for p in predictions['Radau']],predictions['BDF'])
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
            'maximum_observable_solver_difference':float(max(abs(p['measurement']-p['simulation']) for p in solver_pairs)),
            'provided_prediction_max_absolute_difference':difference,'Python_SBML_refinement':'OPEN',
            'assumptions':['Closed SBML L2V4 reactions, fixed compartments, acyclic initial/assignment expressions, no events/rate rules/functions/external parameter updates.',
              'PEtab nominal parameters, literal conditions and measurement-specific observable scale placeholders are interpreted according to the declared problem.',
              'Finite two-solver comparison, not a rigorous error enclosure, fit-optimum proof or empirical validation.']},'Conditional independent model reconstruction from source and finite comparison to supplied predictions')
    except (ValueError,KeyError,TypeError,ZeroDivisionError,OverflowError,ArithmeticError,ImportError,ET.ParseError) as exc:
        return record('conditional_ode_reconstruction','UNKNOWN',bindings,{'reason':type(exc).__name__+': '+str(exc)[:300]},'Reconstruction subset unsupported or failed; no affirmative result inferred')
