from copy import deepcopy
import pytest
from pcs.experimental.omega import adaptive
from pcs.experimental.omega.corpus import generate
from pcs.experimental.omega.logic import digest


@pytest.fixture(scope='module')
def corpus():return generate(per_family=2)


@pytest.fixture(scope='module')
def model(corpus):return adaptive.train(corpus,epochs=2)


def test_actual_hidden_layer_training_and_family_firewall(corpus,model):
    assert any(model['hidden_bias'])
    assert any(model['output_weights'])
    assert len(model['input_weights'])==12 and all(len(w)==95 for w in model['input_weights'])
    train=[r for r in corpus['records'] if r['partition']=='train']
    assert model['training']['task_digests']==[r['task_sha256'] for r in train]
    assert model['training']['families']==['connective-confusion','negation-loss','swapped-implication']
    assert adaptive.train(corpus,epochs=2)==model
    contaminated=deepcopy(corpus);contaminated['records'][-1]['partition']='train'
    contaminated['corpus_sha256']=digest({k:v for k,v in contaminated.items() if k!='corpus_sha256'})
    with pytest.raises(ValueError):adaptive.train(contaminated,epochs=2)


@pytest.mark.parametrize('use_model',[False,True])
def test_checked_replay_and_budget(corpus,model,use_model):
    for record in corpus['records']:
        e=adaptive.search(record['task'],checks=4,proposals=32,model=model if use_model else None)
        assert adaptive.replay(e)
        assert e['checks_used']<=4 and len(e['attempts'])<=32
        assert e['checks_used']==1+sum(r['receipt'] is not None for r in e['attempts'])
        assert not e['pcs_authority'] and not e['lean_kernel_checked']


@pytest.mark.parametrize('field,value',[('checks_used',True),('witness_evaluations',-1),('pcs_authority',True),('solution',{}),('model_sha256','bad')])
def test_resigned_forged_episode_rejected(corpus,field,value):
    e=adaptive.search(corpus['records'][0]['task']);e[field]=value
    e['episode_sha256']=digest({k:v for k,v in e.items() if k!='episode_sha256'})
    with pytest.raises(ValueError):adaptive.replay(e)


def test_witness_filter_does_not_invent_full_checks(corpus):
    for record in corpus['records']:
        e=adaptive.search(record['task'],checks=4,proposals=32)
        row=next((r for r in e['attempts'] if r['rejected_by_witness'] is not None),None)
        if row:
            row['rejected_by_witness']=None
            e['episode_sha256']=digest({k:v for k,v in e.items() if k!='episode_sha256'})
            with pytest.raises(ValueError):adaptive.replay(e)
            return
    pytest.fail('Fixture must exercise genuine witness screening')


@pytest.mark.parametrize('mutate',[lambda m:m.update(authority='PCS'),lambda m:m['input_weights'][0].append(0),lambda m:m.update(output_bias=True),lambda m:m['training'].update(examples=0)])
def test_malformed_checkpoint_rejected(model,mutate):
    m=deepcopy(model);mutate(m);m['model_sha256']=digest({k:v for k,v in m.items() if k!='model_sha256'})
    with pytest.raises(ValueError):adaptive.validate(m)


def test_one_call_cannot_accept_unchecked_repair(corpus):
    e=adaptive.search(corpus['records'][0]['task'],checks=1)
    assert e['solution'] is None and not e['attempts'] and adaptive.replay(e)
