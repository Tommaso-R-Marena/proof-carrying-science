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
 assert len(names) == 673
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


def test_inline_attributes_do_not_remove_declarations_from_audit(tmp_path, monkeypatch):
 module = tmp_path / 'Attributed.lean'
 module.write_text('namespace PCSCR.Py\n@[simp] theorem inline_one : True := trivial\n@[simp] @[grind] lemma inline_two : True := trivial\ntheorem plain : True := trivial\n')
 monkeypatch.setattr(gate, 'MODULES', tmp_path)
 monkeypatch.setattr(gate, 'ROOT', tmp_path)
 names = [row['name'] for row in gate.declared_inventory()]
 assert names == ['PCSCR.Py.inline_one', 'PCSCR.Py.inline_two', 'PCSCR.Py.plain']
 module.write_text(module.read_text().replace('@[simp] ', '').replace('@[grind] ', ''))
 assert [row['name'] for row in gate.declared_inventory()] == names


def test_fresh_replay_imports_override_conflicting_cached_module(tmp_path, monkeypatch):
 import os
 import shutil
 if not shutil.which('lake'):
  if os.environ.get('PCS_REQUIRE_PROVER') == '1':
   pytest.fail('required pinned Lean toolchain unavailable')
  pytest.skip('Lean toolchain unavailable')
 cached, fresh = tmp_path / 'cached', tmp_path / 'fresh'
 cached.mkdir(); fresh.mkdir()
 monkeypatch.setenv('LEAN_PATH', str(cached))
 env, _version = gate.fresh_lean_environment(fresh)
 for folder, value in [(cached, 'False'), (fresh, 'True')]:
  source = folder / 'PCSReplayPrecedenceRegression.lean'
  source.write_text('namespace PCSReplayPrecedenceRegression\ndef fresh : Prop := ' + value + '\nend PCSReplayPrecedenceRegression\n')
  compiled = gate.execute(['lake', 'env', 'lean', '--root=' + str(folder), '-o', str(source.with_suffix('.olean')), str(source)], env)
  assert compiled['returncode'] == 0, compiled
 probe = tmp_path / 'FreshReplayProbe.lean'
 probe.write_text('import PCSReplayPrecedenceRegression\nexample : PCSReplayPrecedenceRegression.fresh := True.intro\n')
 checked = gate.execute(['lake', 'env', 'lean', str(probe)], env)
 assert checked['returncode'] == 0, checked
 # A conflicting cached import would turn this proof into a false proposition.
 stale_env = dict(env)
 stale_env['LEAN_PATH'] = str(cached) + os.pathsep + env['LEAN_PATH']
 stale = gate.execute(['lake', 'env', 'lean', str(probe)], stale_env)
 assert stale['returncode'] != 0 and 'type mismatch' in stale['stdout'].lower(), stale
