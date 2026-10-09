"""Reproduce a fixed-setting comparison without fitting or selecting on holdouts."""
from pathlib import Path
import time
from . import adaptive
from .corpus import generate
from .experiments import write
from .learning import train as train_linear
from .search import search as baseline, verify_episode
from .logic import digest, lean_source


def reproduce(output, *, seeds=(20261009,20261010,20261011), per_family=24):
    output=Path(output)
    if output.exists():raise ValueError('Use a fresh output directory')
    output.mkdir(parents=True)
    rows=[];proofs=[];parity=[]
    for seed in seeds:
        corpus=generate(seed=seed,per_family=per_family)
        started=time.perf_counter();model=adaptive.train(corpus,seed=seed,epochs=24)
        training_seconds=time.perf_counter()-started
        linear=train_linear(corpus,seed=seed)
        bag=train_linear(corpus,'bag',seed=seed)
        write(output/str(seed)/'corpus.json',corpus);write(output/str(seed)/'model.json',model)
        for partition in ('validation','test'):
            for budget in (4,8):
                for name in ('bfs','random','structural','bag','graph','adaptive','nonlinear'):
                    results=[];started=time.perf_counter()
                    for r in corpus['records']:
                        if r['partition']!=partition:continue
                        if name in ('adaptive','nonlinear'):
                            e=adaptive.search(r['task'],checks=budget,depth=3,proposals=128,model=model if name=='nonlinear' else None)
                            adaptive.replay(e)
                        else:
                            e=baseline(r['task'],checks=budget,strategy='learned' if name in ('graph','bag') else name,
                                model=linear if name=='graph' else bag if name=='bag' else None,seed=seed+len(results))
                            verify_episode(e)
                        results.append({'id':r['id'],'family':r['family'],'solved':e['solution'] is not None,
                            'checks':e['checks_used'],'examined_proposals':len(e['attempts']),
                            'witness_evaluations':e.get('witness_evaluations',0),'episode_sha256':e['episode_sha256']})
                        if seed==seeds[0] and partition=='test' and budget==4 and name in ('adaptive','nonlinear') and len(results)<=8:
                            parity.append(e)
                        if name=='adaptive' and budget==8 and partition=='test' and e['solution']:
                            value={**r['task'],'candidate':e['solution']['candidate']}
                            source=lean_source(value).replace('omega_equivalence','adaptive_'+str(len(proofs)))
                            proofs.append(source)
                    row={'seed':seed,'partition':partition,'budget':budget,'strategy':name,'tasks':len(results),
                        'solved':sum(x['solved'] for x in results),'wall_seconds':time.perf_counter()-started,
                        'mean_checks':sum(x['checks'] for x in results)/len(results),
                        'mean_examined_proposals':sum(x['examined_proposals'] for x in results)/len(results),
                        'mean_witness_evaluations':sum(x['witness_evaluations'] for x in results)/len(results),
                        'training_seconds':training_seconds if name=='nonlinear' else None,'results':results}
                    rows.append(row);print(seed,partition,budget,name,row['solved'],'/',len(results),flush=True)
    report={'format':'pcs-omega-adaptive-evaluation-v2','seeds':list(seeds),'epochs':24,'depth':3,'proposal_budget':128,
        'rows':rows,'scope':'Public generated Boolean tasks; whole-family and source/semantic holdouts within each seed.',
        'limitations':['Seeds may overlap; results are not independent external scientific problems.',
            'Witness screening and additional proposal work are reported separately; equal full-check budgets do not mean equal compute.',
            'Nonlinear model is a trained MLP over fixed graph/syntax features, not an end-to-end GNN.',
            'No human data or paid inference; no scientific authority granted.'], 'pcs_authority':False}
    write(output/'evaluation.json',report);write(output/'parity-episodes.json',parity)
    (output/'Repairs.lean').write_text('\n'.join(proofs))
    return report
