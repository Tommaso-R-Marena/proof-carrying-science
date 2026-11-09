"""Independent finite dataset and prediction checks, not scientific authority."""
from __future__ import annotations
from collections import defaultdict
import csv
from fractions import Fraction
import hashlib
import io
import math
import re

from research.scientific_intake_v1.intake import canonical

MAX_ROWS=20000
MAX_FILE=5*1024**2
NUM=re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z')


def number(value):
    if type(value) not in (str,int):raise ValueError('exact finite decimal required')
    value=str(value)
    if len(value)>96 or not NUM.fullmatch(value):raise ValueError('bounded finite decimal required')
    if 'e' in value.lower() and abs(int(value.lower().split('e')[1]))>64:raise ValueError('decimal exponent bound')
    return Fraction(value)


def table(raw,path):
    if len(raw)>MAX_FILE:raise ValueError('table file bound')
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig'),newline=''),delimiter='\t' if path.lower().endswith('.tsv') else ',',strict=True)
    columns=reader.fieldnames
    if not columns or len(columns)>256 or any(not h or h.strip()!=h for h in columns) or len(set(columns))!=len(columns):raise ValueError('ambiguous table header')
    rows=[]
    for row in reader:
        if len(rows)>=MAX_ROWS or None in row or any(v is None for v in row.values()):raise ValueError('table shape/row bound')
        rows.append(row)
    return columns,rows


def source(path,raw):return {'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw)}


def record(checker,status,sources,evidence,scope):
    r={'checker':checker,'status':status,'sources':sources,'evidence':evidence,'scope':scope,'authority':False,'scientific_meaning':'OPEN','empirical_validity':'NOT_ESTABLISHED'}
    r['id']='workflow-'+hashlib.sha256(canonical(r)).hexdigest()[:24]
    return r


def _unique(rows,key):
    vals=[r[key] for r in rows]
    if any(not v for v in vals) or len(set(vals))!=len(vals):raise ValueError('duplicate/missing '+key)
    return set(vals)


def _time(value):return 'steady_state:inf' if value in {'inf','Inf','INF','+inf'} else str(number(value))


def join_predictions(measurements,predictions):
    """Join full observation identities, never list position or bare time.

    Replicate measurements can share a key only when the provided prediction is
    unique at that key. Distinct predictions require a distinguishing identity.
    """
    if not measurements or not predictions:raise ValueError('empty numerical table')
    required={'observableId','simulationConditionId','time'}
    measurement_columns=set(measurements[0]);prediction_columns=set(predictions[0])
    if not required|{'measurement'}<=measurement_columns or not required|{'simulation'}<=prediction_columns:raise ValueError('observation key/value missing')
    # The table reader enforces a common header. Keep the public helper equally
    # strict so metadata appearing only in a later row can never be discarded.
    if any(set(r)!=measurement_columns for r in measurements) or any(set(r)!=prediction_columns for r in predictions):raise ValueError('inconsistent observation metadata columns')
    keys=sorted((measurement_columns|prediction_columns)-{'measurement','simulation'})
    for k in keys:
        if k not in measurements[0] or k not in predictions[0]:
            present=measurements if k in measurements[0] else predictions
            if any(r.get(k,'') for r in present):raise ValueError('unmatched metadata '+k)
    def key(r):return tuple(_time(r.get(k,'')) if k=='time' else r.get(k,'') for k in keys)
    lookup=defaultdict(set)
    for r in predictions:lookup[key(r)].add(number(r['simulation']))
    if len(lookup)>4000 or any(len(v)!=1 for v in lookup.values()):raise ValueError('ambiguous or oversized prediction groups')
    if {key(r) for r in measurements}!=set(lookup):raise ValueError('missing/extra observation identities')
    return [{'measurement_index':i,'key':key(r),'measurement':number(r['measurement']),'simulation':next(iter(lookup[key(r)])),'row':r} for i,r in enumerate(measurements)],keys


def residual_statistics(pairs):
    errors=[p['measurement']-p['simulation'] for p in pairs]
    rss=sum((e*e for e in errors),Fraction(0))
    if max(rss.numerator.bit_length(),rss.denominator.bit_length())>65536:raise ValueError('exact residual bit bound')
    grouped=defaultdict(list)
    for p,e in zip(pairs,errors):grouped[(p['row']['observableId'],p['row']['simulationConditionId'])].append(e)
    try:
        rss_float=float(rss)
    except OverflowError:
        rss_float=None
    if rss_float is not None and not math.isfinite(rss_float):rss_float=None
    projection={'source':'rss_exact','format':'binary64','status':'FINITE_APPROXIMATION' if rss_float is not None else 'OUT_OF_RANGE'}
    if rss and rss_float==0:projection['status']='UNDERFLOW_TO_ZERO'
    return {'observations':len(pairs),'rss_exact':str(rss),'rss_float':rss_float,'rss_float_projection':projection,'nonzero_residuals':sum(e!=0 for e in errors),
            'max_absolute_residual_exact':str(max(map(abs,errors),default=Fraction(0))),
            'groups':[{'observable':k[0],'condition':k[1],'n':len(v),'rss_exact':str(sum((e*e for e in v),Fraction(0)))} for k,v in sorted(grouped.items())],
            'assumptions':['Full source observation keys align the same observable, condition, time and calibration metadata.',
                           'Tabulated decimals are interpreted exactly; supplied predictions have not thereby been independently executed.']}


def analyze(artifacts):
    results=[];tables={};roles=defaultdict(list)
    for path,raw in sorted(artifacts.items()):
        if not path.lower().endswith(('.csv','.tsv')):continue
        try:tables[path]=table(raw,path)
        except (ValueError,UnicodeError,csv.Error) as exc:
            results.append(record('table_schema','UNKNOWN',[source(path,raw)],{'reason':str(exc)},'Table subset unsupported or malformed'))
    for path,(headers,rows) in tables.items():
        for role,needed in [('measurement',{'measurement','observableId','simulationConditionId','time'}),('simulation',{'simulation','observableId','simulationConditionId','time'}),
                            ('condition',{'conditionId'}),('observable',{'observableId','observableFormula','noiseFormula'}),('parameter',{'parameterId','nominalValue','lowerBound','upperBound'})]:
            if needed<=set(headers):roles[role].append(path)
    for path in roles['parameter']:
        bindings=[source(path,artifacts[path])]
        try:
            rows=tables[path][1];_unique(rows,'parameterId');bad=[]
            for i,r in enumerate(rows):
                lo,hi,v=map(number,(r['lowerBound'],r['upperBound'],r['nominalValue']))
                scale=r.get('parameterScale','lin')
                if not lo<hi or not lo<=v<=hi or r.get('estimate','1') not in {'0','1'} or scale not in {'lin','log','log10'} or (scale in {'log','log10'} and not all(x>0 for x in (lo,v,hi))):bad.append(i)
            results.append(record('parameter_domain','REFUTED' if bad else 'REPRODUCED_COMPUTATION',bindings,{'parameters':len(rows),'invalid_rows':bad,'scale_policy':'PEtab nominal/bounds are untransformed values; no optimization certificate'},'Declared parameter identifiers and bounds'))
        except (ValueError,KeyError) as exc:results.append(record('parameter_domain','UNKNOWN',bindings,{'reason':str(exc)},'Parameter table validation'))
    for path in roles['measurement']:
        rows=tables[path][1];bindings=[source(path,artifacts[path])]
        try:
            for r in rows:number(r['measurement']);_time(r['time'])
            if len(roles['observable'])!=1 or len(roles['condition'])!=1:raise ValueError('table association requires unique explicit problem')
            op,cp=roles['observable'][0],roles['condition'][0];obs=_unique(tables[op][1],'observableId');conds=_unique(tables[cp][1],'conditionId')
            bindings.extend([source(op,artifacts[op]),source(cp,artifacts[cp])])
            missing={'observable':sorted({r['observableId'] for r in rows}-obs),'condition':sorted(({r['simulationConditionId'] for r in rows}|{r['preequilibrationConditionId'] for r in rows if r.get('preequilibrationConditionId')})-conds)}
            results.append(record('measurement_dependencies','REFUTED' if any(missing.values()) else 'REPRODUCED_COMPUTATION',bindings,{'measurements':len(rows),'observables':sorted(obs),'simulation_conditions':sorted({r['simulationConditionId'] for r in rows}),'missing_references':missing},'Finite declared measurement/condition/observable references, not empirical adequacy'))
        except (ValueError,KeyError) as exc:results.append(record('measurement_dependencies','UNKNOWN',bindings,{'reason':str(exc)},'Measurement dependency validation'))
        if len(roles['measurement'])==1 and len(roles['simulation'])==1:
            sp=roles['simulation'][0]
            try:
                pairs,key=join_predictions(rows,tables[sp][1]);stats=residual_statistics(pairs)
                results.append(record('provided_prediction_residuals','REPRODUCED_COMPUTATION',[source(path,artifacts[path]),source(sp,artifacts[sp])],{**stats,'join_columns':key,'simulation_reexecution':'NOT_PERFORMED'},'Exact finite residual arithmetic between measurements and supplied predictions'))
            except (ValueError,KeyError,ZeroDivisionError) as exc:results.append(record('provided_prediction_residuals','UNKNOWN',[source(path,artifacts[path]),source(sp,artifacts[sp])],{'reason':str(exc)},'Provided prediction correspondence'))
    if not roles['measurement']:results.append(record('workflow_coverage','UNKNOWN',[],{'reason':'No supported measurement workflow; supported source statements can still be inspected.'},'Bounded workflow subset'))
    return {'schema':'pcs-study-workflow-v4','checks':results,'table_roles':dict(roles),'authority':False}
