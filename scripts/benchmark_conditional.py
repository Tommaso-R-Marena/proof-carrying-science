"""Actual symbolic/independent-exhaustive measurements, never extrapolated speedups."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pcs.experimental.conditional import check, from_text, verify


def truth(f, world):
    op = f['op']
    if op == 'atom': return world[f['symbol']]
    if op == 'true': return True
    if op == 'false': return False
    if op == 'not': return not truth(f['body'],world)
    a, b = truth(f['left'],world), truth(f['right'],world)
    return a and b if op=='and' else a or b if op=='or' else (not a) or b


def exhaustive(task):
    allowed = False; first_bad = None
    for bits in itertools.product([False,True],repeat=len(task['variables'])):
        world = dict(zip(task['variables'],bits))
        if not all(truth(f,world) for f in task['assumptions']): continue
        allowed = True
        if truth(task['source'],world)!=truth(task['candidate'],world) and first_bad is None: first_bad=world
    return ('inconsistent_assumptions' if not allowed else 'counterexample' if first_bad is not None else 'equivalent_under_assumptions'), first_bad


def cases():
    rows=[]
    for size in [4,8,12,16,20,24]:
        names=['V'+str(i).zfill(2) for i in range(size)]
        source='NOT ('+' OR '.join(names)+')';candidate=' AND '.join('NOT '+n for n in names)
        for kind,values in [
            ('de_morgan',(source,candidate,'')),
            ('gap',(' AND '.join(names),' OR '.join(names),'')),
            ('conditional',(' AND '.join(names),' OR '.join(names),' AND '.join(names))),
            ('conflict',(source,candidate,names[0]+'\nNOT '+names[0]+'\n'+names[-1]))]:
            rows.append({'id':f'{kind}-{size}','task':from_text(*values)})
    pairs=[f'((A{i:02} -> B{i:02}) AND (B{i:02} -> A{i:02}))' for i in range(12)]
    dense=' AND '.join(pairs)
    rows.append({'id':'dense-ordering-limit-24','task':from_text(dense,'TRUE')})
    rows.append({'id':'dense-query-conflict-first-24','task':from_text(dense,'TRUE','A00\nNOT A00')})
    rows.append({'id':'constant-gap','task':from_text('TRUE','FALSE')})
    return rows


def run(output):
    output.mkdir(parents=True,exist_ok=False);rows=[]
    for case in cases():
        task=case['task'];start=time.perf_counter();r=check(task);elapsed=time.perf_counter()-start
        start=time.perf_counter();verify(r);replay=time.perf_counter()-start
        row={**case,'receipt':r,'possible_worlds':2**len(task['variables']), 'check_wall_seconds':elapsed,'replay_wall_seconds':replay,'exhaustive':None}
        if len(task['variables'])<=12:
            start=time.perf_counter();decision,witness=exhaustive(task);duration=time.perf_counter()-start
            assert decision==r['decision'];assert witness==(r['counterexample']['assignment'] if r['counterexample'] else None)
            row['exhaustive']={'decision':decision,'valuations_visited':2**len(task['variables']),'wall_seconds':duration}
        rows.append(row)
    assert next(r for r in rows if r['id']=='dense-ordering-limit-24')['receipt']['decision']=='resource_limit'
    assert next(r for r in rows if r['id']=='dense-query-conflict-first-24')['receipt']['decision']=='inconsistent_assumptions'
    source=Path(__file__).resolve().parents[1]/'pcs/experimental/conditional.py'
    report={'format':'pcs-conditional-measurements-v1','data':'First-party analytical Boolean examples; no participant data or learned model evaluation','python_version':sys.version.split()[0],'python_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limits':{'nodes':4096,'operations':100000},'exhaustive_max_variables':12,'rows':rows}
    (output/'measurements.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'decisions':{d:sum(r['receipt']['decision']==d for r in rows) for d in ['equivalent_under_assumptions','counterexample','inconsistent_assumptions','resource_limit']},'output':str(output)}))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();run(args.output)
