"""Train and evaluate a frozen factorial experiment using real PCS Lean replay.

No generated tactic strings, pickle, fabricated rewards, or evaluation feedback
are used for training. An open tactic state never constitutes a certificate.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import resource
import time

import torch
from torch import nn
from pcs.experimental.prover.environment import LeanEnvironment as PCSLeanEnvironment, search
from pcs.experimental.prover.memory_cost import CostLedger
from pcs.experimental.prover.model import ReasoningNetwork, actor_critic
from pcs.experimental.prover.ir import digest
from .data import tasks, audit_splits, collect, replay_receipt
from .model import ProofJEPA

class LeanEnvironment(CostLedger, PCSLeanEnvironment):
    """Existing physical attempt ledger; does not change checker behavior."""


ROOT = Path(__file__).resolve().parents[2]
METHODS = ('supervised', 'jepa', 'rl', 'jepa_rl', 'proof_guided')

def write_json(path, data):
    raw = (json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if str(path).endswith('.gz'):
        raw = gzip.compress(raw, mtime=0)
    Path(path).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def configure(seed):
    random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)


def source_manifest():
    paths = [*Path(__file__).parent.glob('*.py'),
             ROOT/'pcs/experimental/prover/environment.py',
             ROOT/'pcs/experimental/prover/model.py',
             ROOT/'pcs/experimental/prover/memory_cost.py',
             ROOT/'pcs/experimental/prover/data.py', ROOT/'pcs/experimental/prover/ir.py',
             ROOT/'pcs/jsonio.py',
             ROOT/'pcs/experimental/prover/induction_ir.py',
             ROOT/'formal/PCSProofProbe.lean', ROOT/'formal/PCSProofWorker.lean']
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def fit(model, transitions, method, *, seed, epochs):
    """Same verified imitation examples/order in every neural arm.

    RL arms share an imitation warmup; 'RL' here means no JEPA objective,
    not reward-only learning from scratch. Train budget/cost is reported.
    """
    if method not in METHODS or not transitions or epochs < 1:
        raise ValueError('invalid training configuration')
    if any(t.get('split') != 'train' for t in transitions):
        raise ValueError('evaluation firewall: training transitions only')
    if any(t.get('kernel_completed') and (not t.get('receipt_sha256') or not t.get('valid')) for t in transitions):
        raise ValueError('missing completed-proof provenance')
    configure(seed)
    optimizer = torch.optim.Adam((p for p in model.parameters() if p.requires_grad), lr=.003)
    before = {k:p.detach().clone() for k,p in model.named_parameters()}
    positive = [t for t in transitions if t.get('valid') and t.get('kernel_completed') is True and (t.get('remaining') or 0) > 0]
    if not positive:
        raise ValueError('no kernel-verified successful training paths')
    rng = random.Random(seed)
    losses = []
    start = time.perf_counter()
    for epoch in range(epochs):
        indices = list(range(len(positive))); rng.shuffle(indices)
        batch_losses = []
        for offset in range(0, len(indices), 12):
            batch = [positive[i] for i in indices[offset:offset+12]]
            loss = None
            for transition in batch:
                from pcs.experimental.prover.environment import candidates
                options = candidates(transition['state'])
                if transition['action'] not in options:
                    continue
                logits, value, invalid = model(transition['state'], options)
                target = torch.tensor([options.index(transition['action'])], device=logits.device)
                term = nn.functional.cross_entropy(logits.unsqueeze(0), target)
                loss = term if loss is None else loss + term
            if loss is None:
                raise ValueError('no supported demonstration actions')
            loss = loss/len(batch)
            if method in {'jepa','jepa_rl','proof_guided'}:
                loss = loss + .5 * model.predictive_loss(batch, proof_guided=method=='proof_guided')
            if method == 'proof_guided':
                # Labels are actual earlier Lean outcomes, never self-reported.
                for transition in rng.sample(transitions, min(4,len(transitions))):
                    _, _, invalid = model(transition['state'], [transition['action']])
                    label = invalid.new_tensor([float(not transition['valid'])])
                    loss = loss + .025*nn.functional.binary_cross_entropy(invalid, label)
            optimizer.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_((p for p in model.parameters() if p.requires_grad), 1.)
            optimizer.step(); model.update_target()
            batch_losses.append(float(loss.detach()))
        losses.append(sum(batch_losses)/len(batch_losses))
    changed = [name for name,p in model.named_parameters() if not torch.equal(before[name],p)]
    embeddings = torch.stack([model.encode(t['state']).detach() for t in positive[:64]])
    return {'epochs':epochs, 'examples':len(positive), 'seconds':time.perf_counter()-start,
            'losses':losses, 'changed_parameters':changed,
            'embedding_mean_std':float(embeddings.std(dim=0,unbiased=False).mean()),
            'target_parameters_require_grad':any(p.requires_grad for p in model.target.parameters()),
            'predictive_metrics':getattr(model,'last_predictive_metrics',{})}


def evaluate(model, records, *, cache, budget=32, beam=4, depth=16):
    """Identical candidate/action budgets; no cross-task observation-cache reuse.

    Action attempts exclude the mandatory initial probe/final kernel audit.
    All actual worker requests and extra independent audit calls are also counted.
    Compilation/worker bootstrap is separate; all methods reuse one worker each.
    """
    env = LeanEnvironment(cache=cache, timeout=30)
    start = time.perf_counter(); cpu_start = time.process_time()
    rows=[]; inference=[]
    rank = model.rank if model else None
    def ranked(state, options):
        tick=time.perf_counter(); scores=rank(state,options)
        inference.append(time.perf_counter()-tick)
        return scores
    try:
        for record in records:
            env.observations.clear()
            calls, wire, attempts = env.invocations, getattr(env,'worker_wire_requests',0), env.actual_calls
            tick=time.perf_counter(); cpu=time.process_time()
            result=search(env,record['goal'],ranked if rank else None,budget=budget,depth=depth,beam=beam)
            seconds=time.perf_counter()-tick
            search_calls=env.invocations-calls
            search_attempts=env.actual_calls-attempts
            # Independent fresh kernel theorem/axiom replay even after search.verify.
            replay=None
            if result['status']=='verified':
                replay=replay_receipt(env,record,result['receipt'])
            rows.append({'id':record['id'],'family':record['family'],'split':record['split'],
                         'status':result['status'],'solved':result['status']=='verified',
                         'expansions':result['expansions'],'checker_calls':search_calls,
                         'physical_call_attempts':search_attempts,
                         'wire_requests_including_bootstrap_and_replay':getattr(env,'worker_wire_requests',0)-wire,
                         'independent_replay_calls':env.invocations-calls-search_calls,
                         'invalid':sum(a['status']=='invalid' for a in result['attempts']),
                         'resource_errors':sum(a['status']=='resource_exhaustion' for a in result['attempts']),
                         'wall_seconds':seconds,'python_cpu_seconds_including_replay':time.process_time()-cpu,
                         'receipt':result.get('receipt'),'independent_replay':replay})
    finally:
        env.close()
    solved=sum(r['solved'] for r in rows)
    return {'rows':rows,'solved':solved,'tasks':len(rows),'completion_rate':solved/max(1,len(rows)),
            'search_checker_calls':sum(r['checker_calls'] for r in rows),
            'physical_call_attempts':sum(r['physical_call_attempts'] for r in rows),
            'checker_calls_per_solved_including_unsolved_spend':sum(r['checker_calls'] for r in rows)/solved if solved else None,
            'invalid':sum(r['invalid'] for r in rows), 'expansions':sum(r['expansions'] for r in rows),
            'wall_seconds_including_independent_replay':time.perf_counter()-start,
            'python_cpu_seconds':time.process_time()-cpu_start,
            'inference_calls':len(inference),'inference_seconds':sum(inference),
            'mean_inference_ms':1000*sum(inference)/len(inference) if inference else None}


def published():
    folder=ROOT/'research/lean-learning-v2'
    registry=json.loads((folder/'registry.json').read_text())
    entry=next(m for m in registry['models'] if m['id']==registry['selected_local_experiment'])
    return ReasoningNetwork.load(folder/entry['checkpoint'],entry['sha256']),entry


def run(output, *, seeds=(17,31,47), epochs=6, rl_episodes=24, budget=32):
    output=Path(output)
    if output.exists():
        raise ValueError('refuse overwrite: choose a new experiment directory')
    if not seeds or len(set(seeds))!=len(seeds) or any(type(s) is not int or not 0<=s<2**31 for s in seeds):
        raise ValueError('invalid seeds')
    if not 1<=epochs<=200 or not 1<=rl_episodes<=4096 or not 1<=budget<=256:
        raise ValueError('invalid bounded experiment parameters')
    output.mkdir(parents=True)
    records=tasks(); split_audit=audit_splits(records)
    old, entry = published()
    configure(seeds[0])
    protocol={'format':'pcs-proof-jepa-protocol-v1','seeds':list(seeds),'epochs':epochs,
              'rl_episodes':rl_episodes,'action_attempt_budget':budget,'beam':4,'depth':16,
              'methods':['deterministic','published',*METHODS],
              'shared_imitation_warmup':True,
              'schedule':'joint predictive/imitation warmup then sequential on-policy actor-critic; EMA updated during warmup only',
              'cost_head_target':'unit checker-action proxy, not measured latency','checkpoint_selection':'validation only, before test execution',
              'authority':'NONE','source_manifest':source_manifest(),'split_audit':split_audit,
              'tasks_sha256':digest(records),'python':platform.python_version(),'torch':torch.__version__,
              'platform':platform.platform(),'cuda_available':torch.cuda.is_available(),
              'torch_threads':torch.get_num_threads(), 'published_baseline':entry}
    write_json(output/'protocol.json',protocol); write_json(output/'tasks.json',records)
    env=LeanEnvironment(cache=output/'lean-cache',timeout=30)
    protocol['lean']=env.version
    protocol['lean_binary_sha256']=hashlib.sha256(Path(env.lean).read_bytes()).hexdigest()
    collection_start=time.perf_counter()
    try:
        corpus=collect(env,[r for r in records if r['split']=='train'],budget=64,depth=18,beam=4)
        protocol['collection_checker_calls']=env.invocations
        protocol['collection_seconds']=time.perf_counter()-collection_start
    finally:
        env.close()
    write_json(output/'protocol.json',protocol)
    corpus_hash=write_json(output/'training.json.gz',corpus)
    transitions=corpus['transitions']
    if not transitions: raise RuntimeError('no verified transitions')
    validation=[r for r in records if r['split']=='validation']
    heldout=[r for r in records if r['split'] not in {'train','validation'}]
    summaries=[]; evaluations={}; models=[]
    for seed in seeds:
        for method in METHODS:
            configure(seed); model=ProofJEPA(width=24)
            meta=fit(model,transitions,method,seed=seed,epochs=epochs)
            if method in {'rl','jepa_rl','proof_guided'}:
                rl_env=LeanEnvironment(cache=output/'lean-cache',timeout=30,max_steps=18)
                tick=time.perf_counter()
                try:
                    rl=actor_critic(model,rl_env,[r for r in records if r['split']=='train'],episodes=rl_episodes,seed=seed+101)
                    meta['rl_checker_calls']=rl_env.invocations
                    meta['rl_seconds']=time.perf_counter()-tick
                finally: rl_env.close()
                write_json(output/f'{method}-{seed}-rl.json.gz',rl)
                meta['rl_verified_episodes']=rl['verified_episodes']
                meta['rl_weights_changed']=rl['weights_changed']
            key=f'{method}-{seed}'
            checkpoint=output/(key+'.json')
            sha=model.save(checkpoint,{'method':method,'seed':seed,'training_sha256':corpus_hash,
                                       'protocol_sha256':hashlib.sha256((output/'protocol.json').read_bytes()).hexdigest(),
                                       'pcs_authority':False})
            restored=ProofJEPA.load(checkpoint,sha)
            val=evaluate(restored,validation,cache=output/'lean-cache',budget=budget)
            evaluations[key]={'validation':val,'training':meta,'checkpoint_sha256':sha,
                              'parameters':sum(p.numel() for p in model.parameters() if p.requires_grad),
                              'checkpoint_bytes':checkpoint.stat().st_size}
            models.append((key,restored))
            print(json.dumps({'trained':key,'losses':meta['losses'],'validation_solved':val['solved'],
                              'validation_calls':val['search_checker_calls'],'train_seconds':meta['seconds']}),flush=True)
    # Freeze selection before any held-out measurements. Do not tune on test.
    selected=min(evaluations,key=lambda k:(-evaluations[k]['validation']['solved'],
        evaluations[k]['validation']['search_checker_calls'], k))
    write_json(output/'selection.json',{'selected':selected,'rule':protocol['checkpoint_selection'],
                                     'validation_complete_before_test':True})
    # Seeded interleaving reduces systematic order effects; raw timing remains host-dependent.
    policies=[('deterministic',None),('published',old),*models]
    random.Random(991).shuffle(policies)
    for key,model in policies:
        result=evaluate(model,heldout,cache=output/'lean-cache',budget=budget)
        evaluations.setdefault(key,{})['test']=result
        print(json.dumps({'evaluated':key,'solved':result['solved'],'tasks':result['tasks'],
                          'calls':result['search_checker_calls'],'invalid':result['invalid']}),flush=True)
    report={'format':'pcs-proof-jepa-results-v1','authority':'NONE','selected_on_validation':selected,
            'protocol':protocol,'training_sha256':corpus_hash,'evaluations':evaluations,
            'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'cpu_usage_note':'Python process CPU excludes Lean children; wall time includes actual checker work; peak RSS is cumulative process-wide, not per-policy.',
            'gpu_usage':None,'claims':'Authored bounded template-disjoint benchmark, not new mathematics or general safety.'}
    write_json(output/'results.json.gz',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True)
    p.add_argument('--seeds',type=int,nargs='+',default=[17,31,47])
    p.add_argument('--epochs',type=int,default=6)
    p.add_argument('--rl-episodes',type=int,default=24)
    p.add_argument('--budget',type=int,default=32)
    args=p.parse_args()
    run(args.output,seeds=tuple(args.seeds),epochs=args.epochs,rl_episodes=args.rl_episodes,budget=args.budget)
if __name__=='__main__': main()
