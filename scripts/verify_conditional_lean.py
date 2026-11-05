"""Compile selected conditional claims; this is not a BDD refinement theorem."""
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pcs.experimental.conditional import validate, verify as verify_receipt


def lean_formula(f):
    op=f['op']
    if op=='atom':return f['symbol']
    if op in {'true','false'}:return op
    if op=='not':return '(!'+lean_formula(f['body'])+')'
    a,b=lean_formula(f['left']),lean_formula(f['right'])
    return '('+a+' '+{'and':'&&','or':'||','implies':'=>'}[op]+' '+b+')' if op!='implies' else '((!'+a+') || '+b+')'


def verify(output):
    data=json.loads((output/'measurements.json').read_text())
    for row in data['rows']:
        validate(row['task']); verify_receipt(row['receipt'])
        assert row['task']==row['receipt']['original_task']
    version=subprocess.check_output(['lake','env','lean','--version'],cwd=ROOT/'formal',text=True)
    assert re.search(r'Lean \(version 4\.28\.0(?:,|\))',version),version
    selected=[r for r in data['rows'] if r['receipt']['decision']=='equivalent_under_assumptions']
    source=['import Std'];names=[]
    for i,row in enumerate(selected):
        t=row['task'];name=f'conditional_target_{i}';names.append(name)
        binders=' ('+' '.join(t['variables'])+' : Bool)' if t['variables'] else ''
        ctx={'op':'true'}
        for f in t['assumptions']:ctx={'op':'and','left':ctx,'right':f}
        source.append(f'theorem {name}{binders} (h : {lean_formula(ctx)} = true) : {lean_formula(t["source"])} = {lean_formula(t["candidate"])} := by')
        source.append('  simp only [Bool.not_or]' if row['id'].startswith('de_morgan') else '  simp only [Bool.and_eq_true] at h\n  simp_all')
        source.append('#print axioms '+name)
    file=output/'Claims.lean';file.write_text('\n'.join(source)+'\n')
    positive=subprocess.run(['lake','env','lean',str(file.resolve())],cwd=ROOT/'formal',capture_output=True,text=True)
    (output/'lean-positive.log').write_text(positive.stdout+positive.stderr);assert positive.returncode==0,positive.stdout+positive.stderr
    inventories=re.findall(r"'(conditional_target_\d+)' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])",positive.stdout)
    assert len(inventories)==len(names) and {name for name,_ in inventories}==set(names)
    used=sorted({a.strip() for _,axioms in inventories for a in axioms.split(',') if a.strip()})
    assert set(used)<= {'propext'},used
    bad=output/'FalseClaim.lean';bad.write_text('import Std\ntheorem false_claim (A B : Bool) : (A && B) = (A || B) := by\n  cases A <;> cases B <;> decide\n')
    negative=subprocess.run(['lake','env','lean',str(bad.resolve())],cwd=ROOT/'formal',capture_output=True,text=True)
    (output/'lean-negative.log').write_text(negative.stdout+negative.stderr)
    assert negative.returncode!=0 and 'decide' in negative.stdout and 'error' in negative.stdout
    report={'format':'pcs-conditional-lean-controls-v1','version':version.strip(),'positive_theorems':len(names),'largest_variable_count':max(len(r['task']['variables']) for r in selected),'standard_axioms':used,'negative_target_rejected':True,'bdd_implementation_refinement_proved':False,'scope':'Selected declared Boolean equalities under explicit assumptions; no scientific grounding or general BDD correctness proof'}
    (output/'lean-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':verify(Path(sys.argv[1]).resolve())
