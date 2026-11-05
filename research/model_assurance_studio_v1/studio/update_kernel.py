"""Exact-rational, independently checkable certificates for model updates.

For the SAME mathematical input x in a reviewer-specified box B, prove
  c·f_new(x) - c·f_old(x) <= delta
without executing either untrusted model or trusting the numerical proposer.

Shared nodes with identical structural DAG semantics are equated exactly.
Everything is narrowly scoped to the screened ONNX real-arithmetic grammar.
A bound relative to an unsafe baseline does NOT establish a safe update.
"""
from __future__ import annotations
from fractions import Fraction
from .relational_kernel import build, relation, rational, cut, digest, canonical, Unsupported

SCHEMA='pcs-proof-gated-update-real-v0.6'
SCOPE='same-input-exact-real-screened-onnx-model-update'
MAX_DUAL=4000


def _semantic_signatures(spec, intern):
    """Intern exact expression DAGs without trusting probabilistic fingerprints."""
    signatures={}
    def add(key):
        if key not in intern:intern[key]=len(intern)+1
        return intern[key]
    signatures[spec['input']]=add(('input',spec['input_width']))
    for name,w in spec['weights'].items():
        signatures[name]=add(('weight',tuple(w['shape']),tuple(Fraction.from_float(float(v)) for v in w['values'])))
    for node in spec['nodes']:
        inputs=tuple(signatures[i] for i in node['inputs'])
        signatures[node['out']]=add(('node',node['op'],inputs))
    return signatures


def joint(old_spec,new_spec,box):
    if old_spec['input_width']!=new_spec['input_width'] or old_spec['output_width']!=new_spec['output_width']:
        raise Unsupported('old and new model input/output dimensions must match')
    old=build(old_spec,box);new=build(new_spec,box)
    shift=old['variable_count'];rows=list(old['rows'])
    old_count=len(rows)
    for r,b in new['rows']:rows.append(({i+shift:v for i,v in r.items()},b))
    bound_ids={i:pair for i,pair in old['bound_ids'].items()}
    for i,(up,down) in new['bound_ids'].items():
        bound_ids[i+shift]=(old_count+up,old_count+down)
    # Explicit same-input constraint, verified by exact integer coefficients.
    for a,b in zip(old['variables'][old_spec['input']],new['variables'][new_spec['input']]):
        rows.append(({a:Fraction(1),b+shift:Fraction(-1)},Fraction(0)))
        rows.append(({a:Fraction(-1),b+shift:Fraction(1)},Fraction(0)))
    # Exact semantic matching: independent graph nodes with structurally equal
    # expression DAGs must produce identical real-number values on shared x.
    intern={}
    osig=_semantic_signatures(old_spec,intern)
    nsig=_semantic_signatures(new_spec,intern)
    matched={}
    for name,sign in osig.items():
        if name in old['variables'] and name!=old_spec['input']:
            matched.setdefault(sign,[]).append(old['variables'][name])
    matched_groups=0;matching_units=0
    for name,sign in nsig.items():
        if name not in new['variables'] or name==new_spec['input'] or sign not in matched:continue
        new_indices=new['variables'][name]
        for old_indices in matched[sign]:
            if len(old_indices)!=len(new_indices):raise Unsupported('structurally matched width mismatch')
            matched_groups+=1
            for a,b in zip(old_indices,new_indices):
                rows.append(({a:Fraction(1),b+shift:Fraction(-1)},Fraction(0)))
                rows.append(({a:Fraction(-1),b+shift:Fraction(1)},Fraction(0)))
                matching_units+=1
    if len(rows)>5000 or shift+new['variable_count']>512:raise Unsupported('model update analysis budget')
    return {'rows':rows,'bound_ids':bound_ids,'variable_count':shift+new['variable_count'],
            'old_outputs':old['output_variables'],'new_outputs':[i+shift for i in new['output_variables']],
            'input_box':old['input_box'],'semantically_matched_nodes':matched_groups,
            'semantically_matched_units':matching_units}


def verify(old_bytes,new_bytes,certificate):
    try:
        from .dense_nn import screen_onnx
        if not isinstance(certificate,dict) or set(certificate)!={'schema','scope','old_sha256','new_sha256','input_box','relation','multipliers','certificate_sha256'}:
            return False,'unknown update certificate structure'
        if certificate['schema']!=SCHEMA or certificate['scope']!=SCOPE:return False,'unsupported model-update claim scope'
        if len(canonical(certificate))>400000:return False,'certificate byte budget'
        if certificate['certificate_sha256']!=digest(canonical({k:v for k,v in certificate.items() if k!='certificate_sha256'})):
            return False,'certificate digest mismatch'
        if certificate['old_sha256']!=digest(old_bytes) or certificate['new_sha256']!=digest(new_bytes):
            return False,'old/new source model bytes differ'
        old_spec=screen_onnx(old_bytes);new_spec=screen_onnx(new_bytes)
        poly=joint(old_spec,new_spec,certificate['input_box'])
        rel=certificate['relation']
        if not isinstance(rel,dict) or set(rel)!={'output_coefficients','upper_limit'}:return False,'relation format'
        cs,limit=relation(rel['output_coefficients'],rel['upper_limit'],old_spec['output_width'])
        goal={}
        for idx,c in zip(poly['old_outputs'],cs):goal[idx]=goal.get(idx,Fraction(0))-c
        for idx,c in zip(poly['new_outputs'],cs):goal[idx]=goal.get(idx,Fraction(0))+c
        goal={k:v for k,v in goal.items() if v}
        terms=certificate['multipliers']
        if not isinstance(terms,list) or not 1<=len(terms)<=MAX_DUAL:return False,'dual size'
        val={}; bound=Fraction(0);used=set()
        for e in terms:
            if not isinstance(e,list) or len(e)!=2 or type(e[0]) is not int:return False,'multiplier format'
            ix=e[0]
            if ix<0 or ix>=len(poly['rows']) or ix in used:return False,'invalid multiplier position'
            used.add(ix);q=rational(e[1])
            if q<=0:return False,'nonpositive multiplier'
            r,rhs=poly['rows'][ix]
            bound=cut(bound+q*rhs)
            for col,a in r.items():val[col]=cut(val.get(col,Fraction(0))+q*a)
        val={k:v for k,v in val.items() if v}
        if val!=goal:return False,'model-update dual identity fails'
        if bound>limit:return False,'model-update bound exceeds reviewer limit'
        return True,{'status':'PROVED_CONDITIONALLY','verified_update_upper_bound':str(bound),
            'required_update_upper_bound':str(limit),'linear_constraints':len(poly['rows']),
            'variables':poly['variable_count'],'multipliers':len(terms),
            'semantically_matched_nodes':poly['semantically_matched_nodes'],
            'scope':'same input, screened exact-real neural semantics; not ONNX Runtime/IEEE/Lean'}
    except Exception as exc:
        return False,type(exc).__name__+': '+str(exc)[:140]
