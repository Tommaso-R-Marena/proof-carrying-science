"""Posthoc availability dispatch: real source checks with a finite byte budget.

Synthetic SBML only. These regressions neither rescore final cases nor alter an
inherited checker, resource limit, theorem receipt or positive verdict.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from research.scientific_review_v4 import pipeline
from research.scientific_review_v4.grounding import bound_source
from research.scientific_review_v4.semantics import interpret_artifacts
from research.scientific_semantics_v3.checks import check_claim


def model(count, *, padded_size=None):
    declarations = b''.join(
        ('<parameter id="p' + str(i) + '" value="' + str(i + 1) + '"/>').encode()
        for i in range(count)
    )
    prefix = (b'<sbml xmlns="http://www.sbml.org/sbml/level2/version4" level="2" version="4">'
              b'<model id="synthetic"><listOfParameters>')
    suffix = b'</listOfParameters></model></sbml>'
    raw = prefix + declarations + suffix
    if padded_size is not None:
        padding = padded_size - len(raw) - 7
        assert padding >= 0
        raw = prefix + declarations + b'<!--' + b'x' * padding + b'-->' + suffix
        assert len(raw) == padded_size
    return raw


def inventory(artifacts):
    return {'artifacts': [
        {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw),
         'adapter': 'sbml', 'version': '1.0', 'status': 'EXTRACTED', 'segments': []}
        for path, raw in sorted(artifacts.items())
    ]}


@pytest.fixture(scope='module')
def budget_project():
    limit = pipeline.SOURCE_CHECK_REPARSE_BUDGET_BYTES
    assert type(limit) is int and limit > 1_000_000
    small = model(1)
    large_size = 900_000
    while limit % large_size <= 2 * len(small):
        large_size -= 1
    count = limit // large_size + 3
    assert count < 1024
    artifacts = {'a-large.sbml': model(count, padded_size=large_size), 'z-small.sbml': small}
    meaning = interpret_artifacts(artifacts)
    return artifacts, meaning, inventory(artifacts)


def deferred(records):
    return [r for r in records if r.get('checker') == 'source-check-budget-v4']


def test_actual_supported_check_remains_unchanged_below_budget():
    artifacts = {'one.sbml': model(1)}
    meaning = interpret_artifacts(artifacts)
    claim = next(c for c in meaning['claims'] if c.get('quantity_role') == 'parameter')
    expected = check_claim(claim, artifacts)
    actual = pipeline.source_checks(meaning['claims'], artifacts)
    checked = next(r for r in actual if r['claim_id'] == claim['id'])
    assert expected['status'] == 'SOURCE_DECLARATION_CHECKED'
    assert len(actual) == len(meaning['claims']) and not deferred(actual)
    assert pipeline.stable(checked) == pipeline.stable(expected)


def test_exhaustion_retains_every_claim_and_explicit_source_bound_unknown(budget_project):
    artifacts, meaning, inv = budget_project
    original = deepcopy(meaning)
    result = pipeline.analyze_snapshots(artifacts, inv, check=True)
    assert result['interpretation'] == original
    assert meaning == original
    claim_ids = {claim['id'] for claim in meaning['claims']}
    source_results = [r for r in result['checks'] if r.get('claim_id') in claim_ids]
    assert len(source_results) == len(claim_ids)
    assert {r['claim_id'] for r in source_results} == claim_ids
    postponed = deferred(source_results)
    assert postponed
    coverage = pipeline.source_check_coverage(meaning, result['checks'], True)
    assert coverage['interpreted_claims_retained'] == len(claim_ids)
    assert coverage['requested_raw_claim_checks'] == len(claim_ids)
    assert coverage['deferred_raw_claim_checks'] == len(postponed)
    assert coverage['dispatched_raw_claim_checks'] + len(postponed) == len(claim_ids)
    assert coverage['derived_claim_checks_unknown'] == 0
    assert coverage['requested_reparse_bytes'] == sum(len(artifacts[c['source']['path']]) for c in meaning['claims'])
    assert 0 < coverage['dispatched_reparse_bytes'] <= pipeline.SOURCE_CHECK_REPARSE_BUDGET_BYTES
    assert coverage['all_requested_raw_checks_dispatched'] is False
    assert coverage['posthoc_after_primary_final'] is True
    by_id = {claim['id']: claim for claim in meaning['claims']}
    for record in postponed:
        claim = by_id[record['claim_id']]
        assert record['id'] == 'check-' + claim['id']
        assert record['status'] == 'UNKNOWN'
        assert record['authority'] is False and record['scientific_meaning'] == 'OPEN'
        assert record['source_sha256'] == claim['source']['sha256']
        evidence = record['evidence']
        assert evidence['source'] == claim['source']
        assert bound_source(evidence['source'], artifacts)
        assert evidence['reason_code'] == 'PROJECT_REPARSE_BYTE_BUDGET_EXHAUSTED'
        assert evidence['required_reparse_bytes'] == len(artifacts[claim['source']['path']])
        assert evidence['limit_reparse_bytes'] == pipeline.SOURCE_CHECK_REPARSE_BUDGET_BYTES
        assert 0 <= evidence['consumed_reparse_bytes'] <= evidence['limit_reparse_bytes']
        assert evidence['consumed_reparse_bytes'] + evidence['required_reparse_bytes'] > evidence['limit_reparse_bytes']
        assert record['reason']
    assert any(r.get('checker') == 'workflow_coverage' for r in result['checks'])
    assert any(r.get('checker') == 'conditional_ode_reconstruction' for r in result['checks'])


def test_budget_deferral_is_deterministic_and_small_late_source_still_runs(budget_project):
    artifacts, meaning, _ = budget_project
    first = pipeline.source_checks(meaning['claims'], artifacts)
    second = pipeline.source_checks(meaning['claims'], artifacts)
    assert pipeline.stable(first) == pipeline.stable(second)
    assert deferred(first)
    small_claim = next(c for c in meaning['claims'] if c['source']['path'] == 'z-small.sbml' and c.get('quantity_role') == 'parameter')
    last = next(r for r in first if r['claim_id'] == small_claim['id'])
    assert last['status'] == 'SOURCE_DECLARATION_CHECKED'
    assert last.get('checker') != 'source-check-budget-v4'


def test_deferred_input_still_requires_exact_grounding(budget_project):
    artifacts, meaning, _ = budget_project
    claims = deepcopy(meaning['claims'])
    forged = next(c for c in reversed(claims) if c['source']['path'] == 'a-large.sbml')
    forged['source']['quote'] += 'forged'
    forged['source']['byte_end'] += len('forged')
    with pytest.raises(ValueError, match='ungrounded'):
        pipeline.source_checks(claims, artifacts)


def test_dispatch_policy_is_explicitly_posthoc_and_never_affirmative():
    policy = pipeline.source_check_policy()
    assert pipeline.SOURCE_CHECK_REPARSE_BUDGET_BYTES == 32 * 1024**2
    assert policy['project_reparse_byte_limit'] == 32 * 1024**2
    assert policy['posthoc_after_primary_final'] is True
    assert policy['deferred_status'] == 'UNKNOWN'
    assert policy['positive_verdicts_inferred'] is False
    assert policy['authority'] is False
