"""Actual end-to-end byte intake, bounded analysis and adversarial replay."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from research.scientific_intake_v1.intake import canonical
from research.scientific_review_v4.pipeline import run, replay


MODEL = b'<sbml xmlns="http://www.sbml.org/sbml/level2/version4" level="2" version="4"><model id="demo"><listOfParameters><parameter id="rate" value="3" units="second"/></listOfParameters></model></sbml>'


def project(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'model.sbml').write_bytes(MODEL)
    (source / 'notes.xml').write_text('<article><body><p>Protein A activates protein B.</p></body></article>\n', encoding='utf-8')
    return source


def reseal(output, name, value):
    (output / name).write_bytes(canonical(value) + b'\n')
    manifest = json.loads((output / 'manifest.json').read_text())
    manifest['files'][name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    (output / 'manifest.json').write_bytes(canonical(manifest) + b'\n')


def test_unchecked_review_and_snapshot_only_replay(tmp_path):
    source = project(tmp_path)
    output = tmp_path / 'evidence'
    summary = run(source, output)
    assert summary['authorized_checks'] is False
    assert summary['authority'] is False
    assert json.loads((output / 'checks.json').read_text()) == []
    (source / 'model.sbml').write_bytes(b'changed after intake')
    result = replay(output, recheck=False)
    assert result['status'] == 'INTEGRITY_ONLY'
    assert result['cache_used'] is False
    assert (output / 'review.html').is_file()
    interpretation = json.loads((output / 'interpretation.json').read_text())
    assert any(c['source']['quote'].find('value="3"') >= 0 for c in interpretation['claims'])
    with pytest.raises(ValueError, match='overwrite'):
        run(source, output)


def test_authorized_checks_replay_without_cache(tmp_path):
    output = tmp_path / 'evidence'
    summary = run(project(tmp_path), output, check=True)
    checks = json.loads((output / 'checks.json').read_text())
    assert summary['authorized_checks'] is True
    assert any(c['status'] == 'SOURCE_DECLARATION_CHECKED' for c in checks)
    assert all(c['authority'] is False and c['scientific_meaning'] == 'OPEN' for c in checks)
    result = replay(output)
    assert result['status'] == 'REPLAYED'
    assert result['replayed_checks'] == len(checks)
    assert result['v4_checks_independently_recomputed'] == len(checks)


@pytest.mark.parametrize('mutation', ['unknown_status', 'authority', 'missing', 'fake_positive', 'nested_timing'])
def test_resealed_check_tampering_rejected_even_integrity_only(tmp_path, mutation):
    output = tmp_path / 'evidence'
    run(project(tmp_path), output, check=True)
    checks = json.loads((output / 'checks.json').read_text())
    if mutation == 'unknown_status':
        checks[0]['status'] = 'VERIFIED_EVERYTHING'
    elif mutation == 'authority':
        checks[0]['authority'] = True
    elif mutation == 'missing':
        checks.pop()
    elif mutation == 'nested_timing':
        next(c for c in checks if isinstance(c.get('evidence'), dict))['evidence']['seconds'] = 123
    else:
        record = next(c for c in checks if c['status'] == 'UNKNOWN')
        record['status'] = 'REPRODUCED_COMPUTATION'
    reseal(output, 'checks.json', checks)
    with pytest.raises(ValueError):
        replay(output, recheck=False)


def test_physical_census_rejects_unlisted_file(tmp_path):
    output = tmp_path / 'evidence'
    run(project(tmp_path), output)
    (output / 'unexpected.txt').write_text('not listed in manifest')
    with pytest.raises(ValueError, match='census'):
        replay(output)


def test_physical_census_rejects_symlink(tmp_path):
    output = tmp_path / 'evidence'
    run(project(tmp_path), output)
    (output / 'unexpected-link').symlink_to(output / 'checks.json')
    with pytest.raises(ValueError, match='symlink'):
        replay(output)


@pytest.mark.parametrize('kwargs', [{'check': 1}, {'formal_check': 1}, {'formal_check': True}])
def test_explicit_boolean_authorizations_required(tmp_path, kwargs):
    with pytest.raises(ValueError, match='Boolean|authorization'):
        run(project(tmp_path), tmp_path / 'evidence', **kwargs)
    assert not (tmp_path / 'evidence').exists()


def test_output_inside_source_refused(tmp_path):
    source = project(tmp_path)
    with pytest.raises(ValueError, match='inside source'):
        run(source, source / 'output')


def test_large_binary_is_inventoried_without_aborting_review(tmp_path):
    source = project(tmp_path)
    raw = b'\x00' * 1_000_001
    (source / 'large.bin').write_bytes(raw)
    output = tmp_path / 'evidence'
    summary = run(source, output)
    assert summary['artifacts'] == 3
    original = output / 'parent/intake/objects' / hashlib.sha256(raw).hexdigest()
    assert original.read_bytes() == raw
    meaning = json.loads((output / 'interpretation.json').read_text())
    assert any('budget' in row.get('reason', '') for row in meaning['unresolved'])
    assert replay(output, recheck=False)['status'] == 'INTEGRITY_ONLY'


def test_pinned_manifest_mismatch_rejected(tmp_path):
    output = tmp_path / 'evidence'
    run(project(tmp_path), output)
    with pytest.raises(ValueError, match='pinned'):
        replay(output, expected_manifest_sha256='0' * 64)


@pytest.mark.skipif(not Path('/usr/bin/pdftotext').is_file(), reason='actual PDF adapter unavailable')
def test_large_actual_pdf_derived_source_stays_unverified(tmp_path):
    from research.scientific_intake_v1.test_adapters import _pdf
    source = tmp_path / 'source'
    source.mkdir()
    raw = _pdf(text='Protein A activates protein B.' + ' ' * 1_001_000)
    assert 1_000_000 < len(raw) < 5 * 1024**2
    (source / 'paper.pdf').write_bytes(raw)
    output = tmp_path / 'evidence'
    run(source, output, check=True)
    meaning = json.loads((output / 'interpretation.json').read_text())
    claims = [c for c in meaning['claims'] if c['source'].get('transformation', {}).get('kind') == 'adapter_extracted_text']
    assert claims and claims[0]['source']['path'] == 'paper.pdf'
    assert 'byte_start' not in claims[0]['source']
    assert claims[0]['source']['sha256'] == hashlib.sha256(raw).hexdigest()
    checks = json.loads((output / 'checks.json').read_text())
    assert all(next(c for c in checks if c.get('claim_id') == claim['id'])['status'] == 'UNKNOWN' for claim in claims)
    assert replay(output)['status'] == 'REPLAYED'


def test_actual_nine_theorem_formal_receipt_and_replay(tmp_path):
    from research.scientific_review_v4.review import classify
    assert shutil.which('lean') or Path('/workspace/.onboarding/tools/lean-4.28.0-linux/bin/lean').is_file(), 'The required Lean 4.28 toolchain must be installed'
    output = tmp_path / 'evidence'
    run(project(tmp_path), output, check=True, formal_check=True)
    checks = json.loads((output / 'checks.json').read_text())
    receipt = next(c for c in checks if c['id'] == 'formal-v4-residual-semantics')
    assert receipt['status'] == 'KERNEL_CHECKED_ABSTRACT_RESIDUAL_SEMANTICS'
    assert receipt['theorem_count'] == receipt['axiom_audit_count'] == 9
    assert receipt['returncode'] == 0
    assert classify(receipt)[0] == 'proof'
    assert replay(output)['status'] == 'REPLAYED'


def test_resealed_nested_parent_authority_rejected(tmp_path):
    output = tmp_path / 'evidence'
    run(project(tmp_path), output, check=True)
    checks = json.loads((output / 'parent/checks.json').read_text())
    assert checks
    checks[0]['authority'] = True
    reseal(output / 'parent', 'checks.json', checks)
    manifest = json.loads((output / 'manifest.json').read_text())
    for name in ('parent/checks.json', 'parent/manifest.json'):
        manifest['files'][name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    (output / 'manifest.json').write_bytes(canonical(manifest) + b'\n')
    with pytest.raises(ValueError, match='parent check|authority'):
        replay(output, recheck=False)
