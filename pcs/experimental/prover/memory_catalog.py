"""Playable checked induction and reusable-rule missions; no held-out answers."""
import argparse,json,gzip
from pathlib import Path
from .bridge_catalog import build,verify
from .memory_environment import MemoryEnvironment,structural_rank

def generate(output,models):
    folder=Path(models);library=json.loads((folder/'library.json').read_text())
    tasks=json.loads((folder/'tasks.json').read_text())
    ids=[('nat_left_cancel','Shared cargo','Both trains carry the same extra cargo. Can you remove it and compare what remains?'),
         ('predicate_induction','Infinite staircase','Start on step zero, then prove the rule moves you from any step to the next.'),
         ('function_unit_recurrence','Counting machine','A machine adds one at every step. Build a proof of its output after any number of steps.'),
         ('triple_append_length','Reusable toolbox','Reuse a checked length rule to count three joined trains without rebuilding its proof.')]
    authored=[]
    for identity,title,description in ids:
        task=next(t for t in tasks if t['id']==identity)
        if task['split'] not in {'train','utility'}:raise ValueError('evaluation proof cannot enter public game')
        authored.append(('memory-'+identity,title,description,task['original_statement']))
    trajectory=folder/'training-source-trajectories.json.gz'
    records=json.loads(gzip.decompress(trajectory.read_bytes())) if trajectory.exists() else json.loads(trajectory.with_suffix('').read_text())
    # Teach induction through the collected multi-step proof, rather than
    # selecting a whole-training-theorem memory shortcut at the first click.
    paths={'memory-'+r['id']:r['result']['receipt']['actions'] for r in records if r['id'] in {'predicate_induction','function_unit_recurrence'}}
    paths['memory-nat_left_cancel']=[{'kind':'intro','argument':'h'+str(i)} for i in range(4)]+[
        {'kind':'apply','argument':'PCSKnownL0'},{'kind':'exact','argument':'h3'}]
    env=MemoryEnvironment(library,timeout=30)
    return build(output,environment=env,authored_missions=authored,filename='memory-workshop-catalog',rank=structural_rank,primary_paths=paths,
        metadata={'environment':'pcs-grounded-memory-v1','model_family':'verified-memory-v1','library':library,
                  'primitive_catalog_sha256':env.primitive_catalog_sha256,
                  'tutorial_provenance':'Developer-authored shared-cargo path, independently checked by Lean; other induction paths come from actual training search.',
                  'dataset_split_by_mission':{'memory-'+t['id']:t['split'] for t in tasks if 'memory-'+t['id'] in {a[0] for a in authored}},
                  'dataset_boundary':'Public authored training and utility calibration tasks; no selection or final benchmark answers.'})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output');p.add_argument('--models',default='research/verified-memory-v1');p.add_argument('--verify');a=p.parse_args()
    if a.verify:print(json.dumps(verify(json.loads(Path(a.verify).read_text()))))
    elif a.output:generate(a.output,a.models)
    else:p.error('--output or --verify required')
if __name__=='__main__':main()
