"""Deterministic falsification, retaining counterexamples rather than labels from PCS."""
from pathlib import Path
import copy
import hashlib
import json
import shutil
from fractions import Fraction
from .corpus import materialize
from .pipeline import run,replay
from .model_checks import SBMLModel,conservation
from .interpretation import parse_expression
from .rational_equivalence import compare
from .checks import eval_ir
from .dimensions import check_derivative


def campaign(output):
    output=Path(output);output.mkdir(parents=True);records=materialize(output/'originals',split='development');byid={x['id']:x for x in records};rows=[]
    # Authored numerical counterexample to treating fixed samples as universal.
    a=parse_expression('x+x*x');b=parse_expression('x+x*x+'+'*'.join(f'(x-{i}/100)' for i in range(1,13)))
    equal=[eval_ir(a,{'x':Fraction(i,100)})==eval_ir(b,{'x':Fraction(i,100)}) for i in range(1,13)]
    algebra=compare(a,b)
    rows.append({'attack':'fixed-sample polynomial aliasing','finite_samples_all_equal':all(equal),'normal_form':algebra,
                 'held_out_witness':{'x':'1/2','source':str(eval_ir(a,{'x':Fraction(1,2)})),'attack':str(eval_ir(b,{'x':Fraction(1,2)}))},
                 'detected':algebra['status']=='DISTINCT_RATIONAL_FUNCTIONS','scope':'A counterexample to universalizing finite semantic tests; exact normal-form computation catches this case.'})
    # An explicit bad unit declaration, evaluated under recorded conditions.
    r=check_derivative('k*C','C',{'k':'kg','C':'mM','time':'s'},time_unit='s')
    rows.append({'attack':'incorrect dimensional declaration','detected':r['status']=='REFUTED','result':r})
    for key,attack in [('biomodels_tyson1991','altered_export'),('scipy_rosenbrock','altered_report')]:
        source=output/attack;shutil.copytree(byid[key]['path'],source)
        if attack=='altered_export':
            p=next(source.glob('*.m'));raw=p.read_text();p.write_text(raw.replace('reaction_Reaction4_k3=200.0','reaction_Reaction4_k3=201.0',1))
        else:
            p=next(source.glob('*.rst'));raw=p.read_text();p.write_text(raw.replace('Current function value: 0.000000','Current function value: -1.000000',1))
        s=run(source,output/(attack+'-review'),check=True)
        checks=json.loads((output/(attack+'-review')/'checks.json').read_text())
        relevant=[x for x in checks if x['checker'] in {'model_assurance','document_reproduction'}]
        rows.append({'attack':attack,'detected':any(x['status']=='REFUTED' for x in relevant),'summary':s,'evidence':relevant,'replay':replay(output/(attack+'-review'))})
    source=output/'malicious';source.mkdir();marker=output/'EXECUTED'
    (source/'payload.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').touch()\n')
    (source/'paper.md').write_text('This abstract proves a clinical cure with certainty.\nMeasured dose: 2 ± 0.1 mg.\n')
    s=run(source,output/'malicious-review',check=True)
    rows.append({'attack':'uploaded_code_and_misleading_abstract','detected':not marker.exists() and s['scientific_claims_certified']==0 and s['unresolved']>0,
                 'code_executed':marker.exists(),'summary':s,'replay':replay(output/'malicious-review')})
    result={'format':'pcs-scientific-adversarial-v2','cases':rows,'all_detected':all(x['detected'] for x in rows),'authority':False,
            'scope':'Finite deterministic internal attacks, not universal security or independent external validation.'}
    (output/'results.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return result
