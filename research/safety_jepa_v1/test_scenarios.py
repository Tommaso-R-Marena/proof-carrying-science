"""Corpus provenance/partition/adaptive-script checks; no safety verdict mocks."""
from copy import deepcopy
import pytest
from .scenarios import (ACTIONS, scenarios, audit_scenarios, scenario_manifest,
                        safe_workflow, adaptive_attack)


def test_frozen_counts_and_risky_word_controls():
    rows=scenarios(); audit=audit_scenarios(rows)
    assert audit['counts']=={'train':40,'validation':12,'test':24,'ood':24}
    assert audit['families']==40 and len(rows)==100
    assert audit['semantic_attack_family_holdout'] is False
    assert any(audit['shared_scripted_plans_between_splits'].values())
    assert audit['max_cross_split_template_token_jaccard'] < .85
    assert rows==scenarios()
    for split in ('train','validation','test','ood'):
        selected=[r for r in rows if r['split']==split]
        assert any(r['attack'] for r in selected)
        assert any(not r['attack'] for r in selected)
    assert any('password' in r['document'] for r in rows if not r['attack'])
    assert any('secret' in r['document'] for r in rows if not r['attack'])


def test_cross_partition_family_is_rejected():
    rows=scenarios(); rows[-1]['family']=rows[0]['family']
    with pytest.raises(ValueError,match='family leakage'):audit_scenarios(rows)


def test_duplicate_document_is_rejected():
    rows=scenarios(); rows[-1]['document']=rows[0]['document']
    with pytest.raises(ValueError,match='duplicate'):audit_scenarios(rows)


def test_template_relabel_does_not_hide_leakage():
    rows=scenarios(); rows[-1]['template_sha256']=rows[0]['template_sha256']
    with pytest.raises(ValueError,match='template leakage'):audit_scenarios(rows)


def test_normalized_case_renaming_does_not_hide_leakage():
    rows=scenarios()
    import re
    rows[-1]['document']=re.sub(r'R[0-9]{5}-[0-9]{3}','R11111-222',rows[0]['document'])
    with pytest.raises(ValueError,match='normalized document'):audit_scenarios(rows)


@pytest.mark.parametrize('sequence',[['inspect','unknown'],['inspect']*11,['draft','publish']])
def test_unsupported_or_unbounded_actions_rejected(sequence):
    rows=scenarios();rows[0]['attack_sequence']=sequence
    with pytest.raises(ValueError,match='sequence'):audit_scenarios(rows)


def test_sensitive_payload_is_ordinary_synthetic_data():
    rows=scenarios()
    assert all('PRIVATE:' not in r['payload'] for r in rows)
    assert safe_workflow('sensitive')==['inspect','read_sensitive','draft','redact','verify','publish']
    assert safe_workflow('public')==['inspect','read_public','draft','verify','publish']
    with pytest.raises(ValueError):safe_workflow('unknown')


def test_source_influence_hashes_are_actual_and_narrowly_scoped():
    manifest=scenario_manifest()
    assert len(manifest['agentdojo_influence']['files_checked'])==4
    assert manifest['agentdojo_influence']['commit']=='a75aba7631d3ca5fb7ab938965c97ead2f9ff84b'
    assert manifest['external_proof_development_traces_used'] is False
    assert manifest['trusted_safety_authority'] is False
    assert 'no full AgentDojo' in manifest['agentdojo_influence']['scope']


def test_adaptive_sequence_changes_with_actual_block_feedback():
    blocked_publish=[{'action':'publish','blocked':True}]
    blocked_secret=[{'action':'read_secret','info':{'blocked':True}}]
    first=adaptive_attack(blocked_publish,seed=17)
    second=adaptive_attack(blocked_secret,seed=17)
    assert first['sequence']!=second['sequence']
    assert first==adaptive_attack(blocked_publish,seed=17)
    assert first['feedback_sha256']!=second['feedback_sha256']
    assert all(a in ACTIONS for a in first['sequence'])
    assert len(first['sequence'])<=10 and first['training_allowed'] is False
    assert 'verify' in first['sequence'] and first['sequence'].index('verify')<len(first['sequence'])-2


def test_adaptive_feedback_and_seed_bounds():
    for feedback,seed in [(None,0),([{}]*513,0),([],True),([],2**32),([1],0)]:
        with pytest.raises(ValueError):adaptive_attack(feedback,seed)
