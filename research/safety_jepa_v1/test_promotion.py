"""Actual finite-execution store tests; no affirmative Lean verdict is mocked.

Constructed constant neural controls test rejection. A small genuinely trained
expert fixture tests accepted updates; it is not the research benchmark.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil

import pytest
import torch

from .environment import ACTIONS, ToolEnvironment
from .scenarios import scenarios, safe_workflow
from .model import SafetyJEPA
from .promotion import (ResearchStore, IntegrityFailure, ProposalRejected,
                        StaleHead, canonical)


@pytest.fixture(scope='module')
def model_bytes(tmp_path_factory):
    root=tmp_path_factory.mktemp('promotion-fixtures')
    def fixture(action):
        model=SafetyJEPA(width=8)
        with torch.no_grad():
            for p in model.parameters(): p.zero_()
            model.actions.weight[ACTIONS.index(action),0]=1.
            # Actor concatenates online state, action, predicted successor.
            model.actor[0].weight[0,model.width]=4.
            model.actor[2].weight[0,0]=1.
        path=root/(action+'.json')
        model.save(path,{'fixture':'constructed constant proposal; not trained or verified authority'})
        return path.read_bytes()
    bad,quiet=fixture('read_secret'),fixture('inspect')
    # This fixture genuinely learns only TRAIN expert transitions, confirmed by
    # actual successful guarded execution. It is not a benchmark checkpoint.
    torch.manual_seed(9002)
    trained=SafetyJEPA(width=8)
    examples=[]
    rows=[r for r in scenarios() if r['split']=='train'][:4]
    for i,row in enumerate(rows):
        env=ToolEnvironment(row,root/('expert-'+str(i)),guarded=True)
        for action in safe_workflow(row['goal'],inspect=False):
            obs=env.observe();_,_,_,info=env.step(action)
            assert info['admitted'] and not info['unsafe_execution']
            examples.append((obs,ACTIONS.index(action)))
        assert env.success
    optimizer=torch.optim.Adam([p for p in trained.parameters() if p.requires_grad],lr=.01)
    before=trained.online.tokens.weight.detach().clone()
    for _ in range(120):
        terms=[torch.nn.functional.cross_entropy(trained(obs,list(ACTIONS))[0].unsqueeze(0),torch.tensor([label]))
               for obs,label in examples]
        loss=torch.stack(terms).mean();optimizer.zero_grad();loss.backward()
        torch.nn.utils.clip_grad_norm_(trained.parameters(),1.);optimizer.step()
    assert not torch.equal(before,trained.online.tokens.weight)
    path=root/'trained.json'
    trained.save(path,{'fixture':'real supervised fit of16 guarded expert transitions;4train tasks;seed9002;epochs120',
                       'source_ids':[r['id'] for r in rows],'research_benchmark':False})
    return {'bad':bad,'quiet':quiet,'trained':path.read_bytes()}


def initialized(tmp_path,model_bytes):
    store=ResearchStore(tmp_path/'store')
    head=store.initialize(model_bytes['bad'])
    assert head['generation']==0
    return store,head


def test_real_finite_update_accepts_less_blocking_without_unsafe_effects(tmp_path,model_bytes):
    store,head=initialized(tmp_path,model_bytes)
    receipt=store.promote(model_bytes['trained'],head)
    assert receipt['incumbent_measurement']['blocked']>0
    assert receipt['candidate_measurement']['successes']>0
    assert receipt['candidate_measurement']['unsafe_executions']==0
    assert receipt['candidate_measurement']['leaks']==0
    assert receipt['candidate_measurement']['successes']>receipt['incumbent_measurement']['successes']
    assert store.head()['generation']==1
    assert store.snapshot().raw==model_bytes['trained']
    with pytest.raises(StaleHead): store.promote(model_bytes['bad'],head)
    with pytest.raises(ProposalRejected): store.promote(model_bytes['bad'],store.head())
    with pytest.raises(ProposalRejected): store.promote(model_bytes['trained'],store.head())


def test_verified_byte_snapshot_survives_path_removal(tmp_path,model_bytes):
    store,_=initialized(tmp_path,model_bytes)
    snapshot=store.snapshot()
    row={'goal':'public','stage':0,'history':[],'document':''}
    before=snapshot.rank(row,list(ACTIONS))
    (store.root/'models'/(snapshot.raw_sha256+'.json')).unlink()
    assert snapshot.rank(row,list(ACTIONS))==before
    assert snapshot.raw==model_bytes['bad']
    with pytest.raises(IntegrityFailure,match='missing model'):store.head()


def test_mutated_artifact_refused(tmp_path,model_bytes):
    store,head=initialized(tmp_path,model_bytes)
    path=store.root/'models'/(head['model_sha']+'.json')
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(IntegrityFailure,match='identity'):store.snapshot()


def test_invalid_checkpoint_never_initializes_store(tmp_path):
    store=ResearchStore(tmp_path/'store')
    with pytest.raises(IntegrityFailure):store.initialize(b'{"authority":"ALLOW"}')
    assert not store.root.exists()


def test_receipt_corruption_is_not_adopted(tmp_path,model_bytes):
    store,head=initialized(tmp_path,model_bytes)
    store.promote(model_bytes['trained'],head)
    receipt=store.root/'receipts'/'00000001.json'
    payload=json.loads(receipt.read_text());payload['before_model_sha']='0'*64
    receipt.write_bytes(canonical(payload))
    with pytest.raises(IntegrityFailure,match='receipt chain'):store.head()


def test_head_rollback_with_retained_receipt_extent_is_detected(tmp_path,model_bytes):
    store,head=initialized(tmp_path,model_bytes)
    store.promote(model_bytes['trained'],head)
    (store.root/'HEAD.json').write_bytes(canonical(head))
    with pytest.raises(IntegrityFailure,match='extent'):store.head()


def test_missing_receipt_is_not_recovered_silently(tmp_path,model_bytes):
    store,head=initialized(tmp_path,model_bytes)
    store.promote(model_bytes['trained'],head)
    (store.root/'receipts'/'00000001.json').unlink()
    with pytest.raises(IntegrityFailure,match='extent'):store.head()


def test_concurrent_generation_compare_and_swap(tmp_path,model_bytes):
    store,head=initialized(tmp_path,model_bytes)
    def attempt(_):
        try:
            ResearchStore(store.root).promote(model_bytes['trained'],head)
            return 'accepted'
        except StaleHead:return 'stale'
    with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(attempt,range(2)))
    assert sorted(outcomes)==['accepted','stale']
    assert store.head()['generation']==1


def test_caller_cannot_supply_verifier_or_metric_labels(tmp_path,model_bytes):
    store,head=initialized(tmp_path,model_bytes)
    with pytest.raises(TypeError):store.promote(model_bytes['trained'],head,verifier=lambda:True)
    with pytest.raises(TypeError):store.promote(model_bytes['trained'],head,metrics={'successes':16})
    assert store.head()==head


def test_linked_root_is_rejected(tmp_path):
    real=tmp_path/'real';real.mkdir()
    link=tmp_path/'linked';link.symlink_to(real,target_is_directory=True)
    with pytest.raises(IntegrityFailure,match='linked'):ResearchStore(link)


def test_all_zero_completion_efficiency_update_is_rejected(tmp_path,model_bytes):
    store,head=initialized(tmp_path,model_bytes)
    # Inspect forever reduces denials, but completes no legitimate task.
    with pytest.raises(ProposalRejected): store.promote(model_bytes['quiet'],head)
    assert store.head()==head


def test_optimizer_style_tensor_mutation_invalidates_pinned_inference(tmp_path,model_bytes):
    store,_=initialized(tmp_path,model_bytes)
    snapshot=store.snapshot()
    observation={'goal':'public','stage':0,'history':[],'document':''}
    assert len(snapshot.rank(observation,list(ACTIONS)))==len(ACTIONS)
    with torch.no_grad():
        next(snapshot.model.parameters()).add_(.125)
    with pytest.raises(IntegrityFailure,match='tensors changed before'):
        snapshot.rank(observation,list(ACTIONS))


def test_missing_actual_lean_cannot_initialize_or_promote(tmp_path,model_bytes,monkeypatch):
    # Negative availability injection only; no positive checker response is mocked.
    absent=ResearchStore(tmp_path/'absent')
    with monkeypatch.context() as context:
        context.setenv('PATH','')
        with pytest.raises(IntegrityFailure,match='qualification'):absent.initialize(model_bytes['bad'])
    assert not (tmp_path/'absent'/'HEAD.json').exists()
    store,head=initialized(tmp_path,model_bytes)
    with monkeypatch.context() as context:
        context.setenv('PATH','')
        with pytest.raises(IntegrityFailure,match='qualification'):store.promote(model_bytes['trained'],head)
    assert store.head()==head
