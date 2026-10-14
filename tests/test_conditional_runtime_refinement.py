"""Fail closed on swapped runtime bytes, altered proof inputs and partial audits."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('conditional_refinement_gate', ROOT / 'scripts/verify_conditional_runtime_refinement.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_complete_inventory_includes_both_principals_and_source_certificates():
 rows = gate.declared_inventory()
 names = [r['name'] for r in rows]
 assert len(names) == 478
 assert all(name in names for name in gate.PRINCIPALS)
 assert 'PCSCR.Py.conditional_py_source_bound' in names
 assert 'PCSCR.Js.conditional_js_source_bound' in names


@pytest.mark.parametrize('mutation', ['diagram-limit', 'allow-partial-success', 'counter-reset', 'hash-field'])
def test_changed_current_javascript_rejected(tmp_path, mutation):
 source = ROOT / 'formal/source_reference/current/proof-carrying-science-site/public/conditional-core.mjs.txt'
 raw = source.read_bytes()
 old, new = {
  'diagram-limit': (b'>=this.limits.nodes', b'>this.limits.nodes'),
  'allow-partial-success': (b"decision:'resource_limit'", b"decision:'equivalent'"),
  'counter-reset': (b'this.operations++', b'this.operations+=2'),
  'hash-field': (b'receipt_sha256', b'producer_sha256'),
 }[mutation]
 assert old in raw
 (tmp_path / 'public').mkdir()
 (tmp_path / 'public/conditional-core.mjs').write_bytes(raw.replace(old, new))
 with pytest.raises(ValueError, match='current conditional runtime source changed'):
  gate.check_sources(tmp_path)


@pytest.mark.parametrize('kind', ['drop', 'duplicate', 'wrong-name'])
def test_complete_axiom_inventory_cannot_be_producer_selected(kind):
 names = ['A', 'B']
 log = "'A' depends on axioms: [propext]\n'B' depends on axioms: []\n"
 if kind == 'drop': log = log.splitlines()[0]
 elif kind == 'duplicate': log += "'A' depends on axioms: [propext]\n"
 else: log = log.replace("'B'", "'C'")
 with pytest.raises(ValueError): gate.check_inventory(log, names)


def test_unapproved_axiom_rejected():
 with pytest.raises(ValueError):
  gate.check_inventory("'A' depends on axioms: [sorryAx]\n", ['A'])

@pytest.mark.parametrize('change', ['omitted', 'duplicate', 'renamed'])
def test_declaration_inventory_tampering_rejected(tmp_path, monkeypatch, change):
 rows = gate.declared_inventory()
 if change == 'omitted': rows = rows[:-1]
 elif change == 'duplicate': rows = rows + rows[:1]
 else:
  rows = [dict(r) for r in rows]
  rows[0]['name'] = 'PCSCR.producer_replacement'
 monkeypatch.setattr(gate, 'declared_inventory', lambda: rows)
 with pytest.raises(ValueError, match='complete theorem inventory changed'):
  gate.check_sources(tmp_path)
