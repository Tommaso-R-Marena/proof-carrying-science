"""Post-freeze adversarial execution and empirical promotion, never test training."""
import argparse
from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
import torch
from .environment import ACTIONS,ToolEnvironment
from .experiment import evaluate,write
from .model import SafetyJEPA
from .scenarios import scenarios,adaptive_attack,digest
from .promotion import ResearchStore,evaluate_checkpoint,StaleHead,ProposalRejected,IntegrityFailure


def adaptive_campaign(run_directory,output,rounds=16):
    root=Path(run_directory);r=json.load(gzip.open(root/'results.json.gz','rt'))
    key=r['selected'];entry=r['experiments'][key]
    model=SafetyJEPA.load(root/(key+'.json'),entry['checkpoint_sha256'])
    method=key.rsplit('-',1)[0];feedback=[];rows=[]
    cases=scenarios()
    for i in range(rounds):
        attempt=adaptive_attack(feedback,seed=7000+i)
        base=next(c for c in cases if c['split']=='ood' and c['goal']==attempt['goal'])
        record=deepcopy(base);record.update(id='adaptive-'+str(i),attack=True,attack_sequence=attempt['sequence'])
        actual={mode:evaluate(model if mode=='learned' else None,[record],method if mode=='learned' else mode,
                    threshold=entry['threshold'],guarded=mode!='unguarded') for mode in ('unguarded','guards_only','learned')}
        rows.append({'scenario':record,'attempt':attempt,'outcomes':actual})
        feedback=[{'action':t['action'],'blocked':t['denied']} for t in actual['guards_only']['rows'][0]['trace']]
    report={'format':'pcs-safety-jepa-adaptive-execution-v1','selected_checkpoint':key,'rounds':rounds,
        'training_allowed':False,'rows':rows,'authority':'NONE',
        'scope':'Finite six-strategy feedback-driven scripted adversary, not an optimizing LLM'}
    write(output,report);return report


def promotion_demo(run_directory,output):
    root=Path(run_directory);target=Path(output);target.mkdir(parents=True,exist_ok=False)
    results=json.load(gzip.open(root/'results.json.gz','rt'))
    measured={}
    for key,entry in results['experiments'].items():
        if 'checkpoint_sha256' in entry:
            measured[key]=evaluate_checkpoint((root/(key+'.json')).read_bytes())
    key=min(measured,key=lambda k:(-measured[k]['successes'],measured[k]['blocked'],measured[k]['steps'],k))
    if measured[key]['successes']==0:raise RuntimeError('No genuinely trained candidate has useful direct-actor functionality')
    model=SafetyJEPA()
    with torch.no_grad():
        for value in model.parameters():value.zero_()
    model.save(target/'zero-control.json',{'training':'NONE','purpose':'untrained nonfunctional incumbent control'})
    zero=(target/'zero-control.json').read_bytes();candidate=(root/(key+'.json')).read_bytes()
    store=ResearchStore(target/'store');initial=store.initialize(zero)
    receipt=store.promote(candidate,initial);head=store.head();rejections=[]
    for label,raw,expected in [('stale-generation',candidate,initial),('lost-functionality',zero,head)]:
        try:store.promote(raw,expected)
        except (StaleHead,ProposalRejected,IntegrityFailure) as exc:rejections.append({'attack':label,'rejected':True,'reason':type(exc).__name__})
        else:raise RuntimeError('Expected rejection failed: '+label)
    forged=json.loads(candidate);forged['authority']='TRUSTED'
    try:store.promote(json.dumps(forged).encode(),head)
    except IntegrityFailure as exc:rejections.append({'attack':'forged-authority','rejected':True,'reason':type(exc).__name__})
    else:raise RuntimeError('Forged authority accepted')
    independent=evaluate_checkpoint(candidate)
    if independent!=receipt['candidate_measurement']:raise RuntimeError('Independent finite qualification differs')
    snap=store.snapshot()
    with tempfile.TemporaryDirectory() as folder:
        env=ToolEnvironment(scenarios()[0],folder)
        scores=snap.rank(env.observe(),list(ACTIONS))
    report={'format':'pcs-safety-jepa-promotion-demo-v1','candidate':key,'candidate_selection':'fixed development16-case direct-actor gate, not final test',
        'initial':initial,'final':head,'receipt':receipt,'rejections':rejections,
        'independent_candidate_replay_matched':True,'pinned_snapshot_sha256':snap.raw_sha256,
        'finite_scores':measured,'authority':'NONE','universally_safe_model':False,
        'scope':'Actual empirical functionality update under unchanged guard; not a Lean neural-safety certificate or production deployment'}
    write(target/'summary.json',report);return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['adaptive','promotion'])
    p.add_argument('--run-directory',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    result=adaptive_campaign(a.run_directory,a.output) if a.command=='adaptive' else promotion_demo(a.run_directory,a.output)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','finite_scores','receipt')},sort_keys=True))
if __name__=='__main__':main()
