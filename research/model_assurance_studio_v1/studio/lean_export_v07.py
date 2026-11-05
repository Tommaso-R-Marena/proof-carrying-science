"""Export exact Farkas inequalities as Lean 4 / Mathlib proof obligations.

IMPORTANT: The output is a *source artifact*. Until it builds under a pinned Lean
kernel, status is NOT_VERIFIED. Even after compiling, it proves only that the
reconstructed inequalities entail the stated inequality; it does not validate
the Python ONNX decoder, runtime semantics, or correspondence of those rows to
a physical machine. No use of `sorry`, `admit`, `native_decide` or `axiom`.
"""
from __future__ import annotations
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import json
from .relational_kernel import build,relation,rational
from .verify_relational import verify_with_policy
from .verify_update import verify_update_policy
from .update_kernel import joint
from .dense_nn import screen_onnx


def _rat(x):
    q=Fraction(x)
    if q.denominator==1:
        return f'({q.numerator} : ℚ)'
    return f'(({q.numerator} : ℚ) / {q.denominator})'


def _sum(terms):
    return ' + '.join(terms) if terms else '(0 : ℚ)'


def _row(vec,n):
    # Expand only the finite nonzero support, eliminating empty columns.
    return _sum([f'{_rat(c)} * x{i}' for i,c in sorted(vec.items()) if c])


def _theorem(poly,goal,multipliers,limit,theorem_name):
    n=poly['variable_count']
    if n>512 or len(multipliers)>5000:raise ValueError('Lean export budget')
    rows=[]
    for k,entry in enumerate(multipliers):
        idx,qtext=entry
        if idx<0 or idx>=len(poly['rows']):raise ValueError('invalid row id')
        coeffs,rhs=poly['rows'][idx]
        rows.append((k,coeffs,rhs,rational(qtext)))
    vars=' '.join(f'(x{i} : ℚ)' for i in range(n))
    hyps='\n'.join(f'    (h{k} : ({_row(row,n)}) ≤ {_rat(rhs)})' for k,row,rhs,q in rows)
    have='\n'.join(f'  have hh{k} : ({_rat(q)} * ({_row(row,n)})) ≤ ({_rat(q)} * {_rat(rhs)}) :=\n    mul_le_mul_of_nonneg_left h{k} (by norm_num)' for k,row,rhs,q in rows)
    # Full goal vector, not only nonzero coefficients.
    conclusion=_row(goal,n)
    lhs=_sum([f'({_rat(q)} * ({_row(row,n)}))' for _,row,rhs,q in rows])
    rhs=_sum([f'({_rat(q)} * {_rat(rhs)})' for _,row,rhs,q in rows])
    hnames=', '.join('hh'+str(k) for k,_,_,_ in rows)
    return f'''theorem {theorem_name} {vars}
{hyps}
    : ({conclusion}) ≤ {_rat(limit)} := by
{have}
  calc
    ({conclusion}) = ({lhs}) := by ring
    _ ≤ ({rhs}) := by linarith only [{hnames}]
    _ ≤ {_rat(limit)} := by norm_num
'''


def export_relational(raw:bytes,cert:dict,policy:dict)->str:
    accepted,why=verify_with_policy(raw,cert,policy)
    if not accepted:raise ValueError('Certificate fails independent Python reviewer: '+str(why))
    if cert['schema']!='pcs-relational-farkas-real-v0.6':
        raise ValueError('Lean exporter currently supports exact-dual Farkas certificates only')
    spec=screen_onnx(raw)
    poly=build(spec,cert['input_box'])
    cs,limit=relation(cert['relation']['output_coefficients'],cert['relation']['upper_limit'],spec['output_width'])
    goal={i:c for i,c in zip(poly['output_variables'],cs) if c}
    theorem=_theorem(poly,goal,cert['multipliers'],limit,'certified_relation')
    return _wrap(raw,cert,policy,theorem,'exact-relational')


def export_update(old:bytes,new:bytes,cert:dict,policy:dict)->str:
    accepted,why=verify_update_policy(old,new,cert,policy)
    if not accepted:raise ValueError('Update fails independent Python reviewer: '+str(why))
    ospec=screen_onnx(old);nspec=screen_onnx(new)
    poly=joint(ospec,nspec,cert['input_box'])
    cs,limit=relation(cert['relation']['output_coefficients'],cert['relation']['upper_limit'],ospec['output_width'])
    goal={}
    for i,c in zip(poly['old_outputs'],cs):goal[i]=goal.get(i,Fraction(0))-c
    for i,c in zip(poly['new_outputs'],cs):goal[i]=goal.get(i,Fraction(0))+c
    goal={i:v for i,v in goal.items() if v}
    theorem=_theorem(poly,goal,cert['multipliers'],limit,'certified_update_drift')
    return _wrap(old+new,cert,policy,theorem,'exact-update')


def _wrap(raw,cert,policy,theorem,kind):
    model=sha256(raw).hexdigest()
    cert_sha=sha256(json.dumps(cert,sort_keys=True).encode()).hexdigest()
    policy_sha=sha256(json.dumps(policy,sort_keys=True).encode()).hexdigest()
    return f'''/-!
  PCS v0.7 experimental generated Lean proof: {kind}
  Model byte SHA-256: {model}
  Certificate JSON SHA-256: {cert_sha}
  Reviewer policy JSON SHA-256: {policy_sha}
  Status when generated: NOT KERNEL CHECKED.
  These theorem hypotheses are abstract polytope inequalities. Their asserted
  relationship to an ONNX model is NOT established by this Lean file.
-/
import Mathlib

namespace PCSModelAssurance

{theorem}
-- The formal composition step is a standard mathematical consequence.
theorem bounded_update_composition (old new baseline drift required : ℚ)
    (hbase : old ≤ baseline) (hdelta : new - old ≤ drift)
    (hrequired : baseline + drift ≤ required) : new ≤ required := by
  linarith

end PCSModelAssurance
'''


def main():
    import argparse
    from .verify_relational import strict_load
    p=argparse.ArgumentParser(description='Emit uncompiled Lean proof source for exact dual certificate')
    sub=p.add_subparsers(dest='mode',required=True)
    r=sub.add_parser('relation');r.add_argument('model');r.add_argument('certificate');r.add_argument('reviewer_policy');r.add_argument('out')
    u=sub.add_parser('update');u.add_argument('old_model');u.add_argument('new_model');u.add_argument('certificate');u.add_argument('reviewer_policy');u.add_argument('out')
    a=p.parse_args()
    if a.mode=='relation':
        src=export_relational(Path(a.model).read_bytes(),strict_load(a.certificate),strict_load(a.reviewer_policy))
    else:
        src=export_update(Path(a.old_model).read_bytes(),Path(a.new_model).read_bytes(),strict_load(a.certificate),strict_load(a.reviewer_policy))
    Path(a.out).write_text(src)
    print('WROTE UNCOMPILED LEAN SOURCE:',a.out,'— do not call it kernel-checked until lake env lean returns zero.')

if __name__=='__main__':main()
