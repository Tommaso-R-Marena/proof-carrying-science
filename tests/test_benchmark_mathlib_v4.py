"""Public external-source benchmark provenance and evaluation-firewall controls."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from pcs.experimental.prover.benchmark_mathlib_v4 import (
    alpha_signature, check_partitions, filter_premises, read_json, sha,
    verify_benchmark,
)

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / 'benchmarks/mathlib-v4'


def node(kind, value='', *children, binder_info=''):
    return {'kind': kind, 'value': value, 'children': list(children), 'binder_info': binder_info}


def evaluation_task():
    return {'id': 'frozen-example', 'split': 'final', 'declaration': 'External.target',
            'family': 'heldout', 'source': {'module': 'Mathlib.Data.List.Basic'},
            'expression': node('forall', 'x', node('sort', 'u+1'),
                               node('application', '', node('constant', 'P:[u]'), node('bound', '0')),
                               binder_info='implicit')}


def test_actual_frozen_corpus_has_22_external_closed_statement_tasks_and_no_solutions():
    result = verify_benchmark(BENCHMARK)
    assert result['integrity_valid'] and not result['production_authority']
    assert result['partition']['evaluation_tasks'] == 22
    assert not result['independently_replayed']
    tasks = read_json(BENCHMARK / 'tasks.json')
    assert {x['family'] for x in tasks} == {'list', 'finset', 'factorial', 'group', 'real'}
    assert all(x['source']['license'] == 'Apache-2.0' for x in tasks)
    assert all(x['source']['declaration_header'] and ':=' not in x['source']['declaration_header'] for x in tasks)
    assert all(x['source']['lines'][0] <= x['source']['lines'][1] for x in tasks)
    assert len({x['alpha_sha256'] for x in tasks}) == 22
    assert all(not x['proof_bodies_included'] for x in tasks)


def test_real_coercions_are_explicit_and_fresh_type_roundtrip_is_preserved():
    tasks = {x['declaration']: x for x in read_json(BENCHMARK / 'tasks.json')}
    assert '(x : ℝ)' in tasks['Real.ratCast_lt']['statement']
    assert '(f j : ℝ)' in tasks['Real.mk_le_of_forall_le']['statement']
    receipt = read_json(BENCHMARK / 'statement-roundtrip-receipt.json')
    assert receipt['exit_code'] == 0 and receipt['declarations'] == 22
    assert (BENCHMARK / 'statement-roundtrip.log').read_text().count('PCS_SIGNATURE_ROUNDTRIP:') == 22
    # This unit check reads execution evidence; it does not itself rerun Lean.
    assert 'definition' in receipt['check']


def test_binder_and_universe_alpha_renaming_does_not_allow_answer_aliases():
    original = evaluation_task()['expression']
    renamed = copy.deepcopy(original)
    renamed['value'] = 'renamed_x'
    renamed['binder_info'] = 'explicit'
    renamed['children'][0]['value'] = 'u_42+1'
    renamed['children'][1]['children'][0]['value'] = 'P:[u_42]'
    assert alpha_signature(original) == alpha_signature(renamed)
    kept, evidence = filter_premises([
        {'name': 'External.target', 'expression': original},
        {'name': 'Alias.same_answer', 'expression': renamed},
        {'name': 'Foundation.other_fact', 'expression': node('constant', 'True:[]')},
        {'name': 'Unchecked.missing_type'},
    ], [evaluation_task()])
    assert [x['name'] for x in kept] == ['Foundation.other_fact']
    assert [x['reason'] for x in evidence['rejected']] == [
        'evaluated_declaration', 'alpha_equivalent_answer', 'missing_type_expression']
    assert not evidence['semantic_equivalence_decided']


def test_scope_negation_quantifier_order_and_constants_remain_distinct():
    pair = node('application', '', node('application', '', node('constant', 'R:[]'), node('bound', '1')),
                node('bound', '0'))
    goal = node('forall', 'a', node('constant', 'Nat:[]'),
                node('forall', 'b', node('constant', 'Nat:[]'), pair))
    swapped = copy.deepcopy(goal)
    swapped['children'][1]['children'][1]['children'][0]['children'][1]['value'] = '0'
    swapped['children'][1]['children'][1]['children'][1]['value'] = '1'
    assert alpha_signature(goal) != alpha_signature(swapped)
    assert alpha_signature(pair) != alpha_signature(node('application', '', node('constant', 'Not:[]'), pair))
    assert alpha_signature(node('constant', 'Nat:[]')) != alpha_signature(node('constant', 'Int:[]'))


def test_structural_near_duplicate_hints_are_not_exact_equivalence():
    one, two = node('natural', '1'), node('natural', '2')
    assert alpha_signature(one) != alpha_signature(two)
    assert alpha_signature(one, structural=True) == alpha_signature(two, structural=True)


@pytest.mark.parametrize('change', ['module', 'family', 'alpha', 'membership', 'solution', 'duplicate'])
def test_training_and_evaluation_firewall_rejects_explicit_leakage(change):
    target = evaluation_task()
    training = {'id': 'train', 'split': 'training', 'declaration': 'Training.example',
                'family': 'logic', 'source': {'module': 'Mathlib.Logic.Function.Basic'},
                'expression': node('constant', 'True:[]')}
    if change == 'module':
        training['source']['module'] = target['source']['module']
    elif change == 'family':
        training['family'] = target['family']
    elif change == 'alpha':
        training['expression'] = copy.deepcopy(target['expression'])
    elif change == 'membership':
        training['id'] = target['id']
    elif change == 'solution':
        target['solution'] = 'hidden evaluation answer'
    elif change == 'duplicate':
        with pytest.raises(ValueError, match='alpha-duplicate'):
            check_partitions([target, {**target, 'id': 'another'}])
        return
    with pytest.raises(ValueError):
        check_partitions([target], [training])


def test_primary_allows_foundation_and_strict_module_sensitivity_is_explicit():
    foundation = {'name': 'Known.foundational', 'module': 'Mathlib.Data.Set.Function',
                  'expression': node('constant', 'True:[]')}
    assert filter_premises([foundation], [evaluation_task()])[0] == [foundation]
    kept, record = filter_premises([foundation], [evaluation_task()],
                                  exclude_modules=['Mathlib.Data.Set.Function'])
    assert not kept and record['rejected'][0]['reason'] == 'sensitivity_excluded_module'
    missing = {k: v for k, v in foundation.items() if k != 'module'}
    assert filter_premises([missing], [evaluation_task()], exclude_modules=['M'])[1]['rejected'][0]['reason'] == 'module_provenance_missing_for_strict_filter'


def test_corrupted_corpus_and_receiver_approved_seal_fail_closed(tmp_path):
    directory = tmp_path / 'benchmark'
    shutil.copytree(BENCHMARK, directory)
    approved = hashlib.sha256((directory / 'ARTIFACT_SHA256.json').read_bytes()).hexdigest()
    assert verify_benchmark(directory, expected_seal=approved)['integrity_valid']
    tasks = read_json(directory / 'tasks.json')
    tasks[0]['statement'] = 'False'
    (directory / 'tasks.json').write_text(json.dumps(tasks))
    with pytest.raises(ValueError, match='checksum'):
        verify_benchmark(directory, expected_seal=approved)
    seal = read_json(directory / 'ARTIFACT_SHA256.json')
    seal['files']['tasks.json'] = hashlib.sha256((directory / 'tasks.json').read_bytes()).hexdigest()
    (directory / 'ARTIFACT_SHA256.json').write_text(json.dumps(seal))
    with pytest.raises(ValueError, match='approved benchmark seal'):
        verify_benchmark(directory, expected_seal=approved)


def test_unlisted_artifact_or_solution_cannot_silently_enter_frozen_set(tmp_path):
    directory = tmp_path / 'benchmark'
    shutil.copytree(BENCHMARK, directory)
    (directory / 'answers.json').write_text('{"proof": "unverified invented solution"}')
    with pytest.raises(ValueError, match='membership'):
        verify_benchmark(directory)


@pytest.mark.parametrize('raw', ['{"a":1,"a":2}', '{"a":NaN}'])
def test_duplicate_and_nonfinite_metadata_rejected(tmp_path, raw):
    path = tmp_path / 'record.json'
    path.write_text(raw)
    with pytest.raises(ValueError):
        read_json(path)


def test_open_metavariables_and_unbounded_types_rejected():
    with pytest.raises(ValueError, match='closed'):
        alpha_signature(node('metavariable', '?goal'))
    deeply_nested = node('constant', 'True:[]')
    for _ in range(258):
        deeply_nested = node('lambda', 'x', node('constant', 'Nat:[]'), deeply_nested)
    with pytest.raises(ValueError, match='bounded'):
        alpha_signature(deeply_nested)


def test_training_validation_id_and_alpha_duplicates_are_rejected():
    training = {'id': 'train', 'split': 'training', 'declaration': 'Known.base',
                'family': 'logic', 'source': {'module': 'Mathlib.Logic.Function.Basic'},
                'expression': node('constant', 'True:[]')}
    validation = {**training, 'id': 'dev', 'split': 'validation', 'declaration': 'Known.alias'}
    with pytest.raises(ValueError, match='alpha-duplicates training'):
        check_partitions([evaluation_task()], [training], [validation])
    validation['expression'] = node('constant', 'False:[]')
    validation['id'] = 'train'
    with pytest.raises(ValueError, match='task identity'):
        check_partitions([evaluation_task()], [training], [validation])
    validation['id'] = 'dev'
    assert check_partitions([evaluation_task()], [training], [validation])['module_family_disjoint']
