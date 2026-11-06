"""Replay an exact integer source-bound stoichiometry certificate in Lean."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from research.scientific_intake_v1.verify_formal import lean_path


def verify_certificate(certificate, *, lean=None):
    matrix=certificate['matrix'];weights=certificate['weights']
    if not 1<=len(weights)<=32 or len(matrix)!=len(weights) or not matrix[0] or len(matrix[0])>64:raise ValueError('certificate shape bound')
    if any(type(v) is not int or abs(v)>1000000 for v in weights):raise ValueError('bounded integer weights')
    rows=[]
    for row in matrix:
        if len(row)!=len(matrix[0]):raise ValueError('ragged certificate matrix')
        values=[]
        for v in row:
            if not re.fullmatch(r'-?[0-9]{1,7}',str(v)):raise ValueError('integer stoichiometry required')
            values.append(int(v))
        rows.append(values)
    columns=[list(col) for col in zip(*rows)]
    def vector(v):return '['+','.join('('+str(x)+')' for x in v)+']'
    prefix=Path(__file__).with_name('formal').joinpath('Conservation.lean').read_text()
    proof='\n'.join('  apply ScientificConservation.NullColumns.cons\n  · decide\n  · decide' for c in columns)+'\n  exact ScientificConservation.NullColumns.nil'
    # Each invocation fixes every integer from the source, with no injected text.
    text=prefix+'\nnamespace SourceBound\ndef weights : List Int := '+vector(weights)+'\ndef columns : List (List Int) := ['+','.join(vector(c) for c in columns)+']\ntheorem nulls : ScientificConservation.NullColumns weights columns := by\n'+proof+'\ntheorem conservation (rates : List Int) (h : rates.length = columns.length) :\n ScientificConservation.dot weights (ScientificConservation.linearCombination weights.length columns rates) = 0 :=\n ScientificConservation.conserved_linear_combination weights nulls rates h\nend SourceBound\n#print axioms SourceBound.nulls\n#print axioms SourceBound.conservation\n'
    binary=lean_path(lean)
    if binary is None:raise RuntimeError('Lean unavailable')
    version=subprocess.check_output([str(binary),'--version'],text=True,timeout=10).strip()
    if 'version 4.28.0,' not in version:raise ValueError('Lean 4.28.0 required')
    with tempfile.TemporaryDirectory(prefix='pcs-model-conservation-') as folder:
        p=Path(folder)/'Certificate.lean';p.write_text(text)
        result=subprocess.run([str(binary),'-j1','-M512',str(p)],cwd=folder,env={'PATH':str(binary.parent)+':/usr/bin:/bin','LANG':'C.UTF-8','LEAN_NUM_THREADS':'1'},capture_output=True,text=True,timeout=30)
    if result.returncode:raise ValueError('Lean certificate rejected: '+result.stdout[:2000]+result.stdout[-1000:]+result.stderr[-1000:])
    audit={}
    for name in ['SourceBound.nulls','SourceBound.conservation']:
        m=re.search("'"+name+r"' (does not depend on any axioms|depends on axioms: \[([^\]]*)\])",result.stdout)
        if not m:raise ValueError('missing certificate axiom audit')
        axioms=[] if m[1].startswith('does not') else [s.strip() for s in m[2].split(',') if s.strip()]
        if set(axioms)-{'propext'}:raise ValueError('unapproved certificate axiom')
        audit[name]=axioms
    return {'status':'KERNEL_CHECKED_FINITE_INTEGER_CONSERVATION','source_sha256':hashlib.sha256(text.encode()).hexdigest(),
            'certificate':certificate,'axioms':audit,'lean_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
            'scope':'Finite integer matrix algebra for arbitrary matching integer rate vectors. Real-valued ODE trajectories, Python refinement and biological interpretation are not proved.','authority':False}
