#!/usr/bin/env python3
"""Receiver-owned source binding and fresh Lean replay for conditional runtimes.

The proof concerns the declared heap-language semantics. Validation, digests and
JavaScript imported exact/integer helpers remain explicit theorem hypotheses.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_lean_source import audit
from verify_omega_dd_formal import check_inventory

EVIDENCE = ROOT / 'research/aristotle-conditional-runtime-v1'
MODULES = ROOT / 'formal/PCSConditionalRuntime'
SOURCES = [
 ('python', ROOT, 'pcs/experimental/conditional.py', 'proof-carrying-science'),
 ('javascript', None, 'public/conditional-core.mjs', 'proof-carrying-science-site'),
]
ASSUMPTIONS = {
 'python': ['distinct declared names', 'TaskDen typed JSON task', 'valid limits',
            'ValidateAccepts: unextracted validate accepts and preserves task',
            'DigestOK: unextracted digest is pure function dg'],
 'javascript': ['distinct declared names', 'TaskDen typed JSON task', 'valid limits',
                'JsTaskBounds: <=24 names, <=8 assumptions, <=128 nodes per formula',
                'JValidateAccepts: unextracted validator accepts and preserves task',
                'JExactOK: unextracted exact helper preserves valid inputs',
                'JIntegerOK: unextracted integer helper preserves valid inputs',
                'DigestOK: unextracted digest is pure function dg'],
 'external': ['declared Python/JavaScript heap-subset semantics',
              'source-reading elaborator and trusted Lean toolchain environment',
              'no native interpreter/compiler/OS correspondence theorem',
              'no SHA256/JCS/cryptographic implementation refinement'],
}
PRINCIPALS = ['PCSCR.Py.python_conditional_refines_reference',
              'PCSCR.Js.javascript_conditional_refines_reference']


def sha(path: Path) -> str:
 return hashlib.sha256(path.read_bytes()).hexdigest()


def declared_inventory() -> list[dict]:
 rows = []
 for p in sorted(MODULES.glob('*.lean')):
  namespace = ''
  for line in p.read_text().splitlines():
   m = re.match(r'^namespace (\S+)', line)
   if m: namespace = m[1]
   m = re.match(r'^(?:@\[[^\]]+\]\s*)*(?:theorem|lemma) (\S+)', line)
   if m: rows.append({'name': namespace + '.' + m[1], 'path': str(p.relative_to(ROOT))})
 names = [r['name'] for r in rows]
 if not names or len(names) != len(set(names)):
  raise ValueError('missing or duplicate complete theorem inventory')
 return rows


def check_sources(site: Path) -> dict:
 manifest = json.loads((EVIDENCE / 'source-manifest.json').read_text())
 for row in manifest['files']:
  if sha(ROOT / row['path']) != row['sha256']:
   raise ValueError('imported proof/source identity changed: ' + row['path'])
  if row.get('returned_sha256'):
   returned = EVIDENCE / 'returned-source' / Path(row['path']).name
   if sha(returned) != row['returned_sha256']:
    raise ValueError('returned original source changed')
   checker = 'checkSegs' if returned.stem.startswith('Py') else 'checkJSegs'
   segments = 'conditionalSegs' if returned.stem.startswith('Py') else 'conditionalJsSegs'
   if returned.stem.startswith('Py'):
    overlay = '  simp only [' + segments + ', ' + checker + ', Bool.and_eq_true]\n  repeat\' apply And.intro\n  all_goals decide +kernel'
   else:
    overlay = '  have constantsLength : (JItem.renderB jsConstants).length = 3 := by rfl\n  have codeLength : (JItem.renderB [jsEvaluate, jsResourceLimit, jsDiagram, jsCheck]).length = 29 := by rfl\n  simp only [conditionalJsSegs, checkJSegs, constantsLength, codeLength, Bool.and_eq_true]\n  repeat\' apply And.intro\n  all_goals decide +kernel'
   integrated = (ROOT / row['path']).read_text()
   if integrated.count(overlay) != 1 or integrated.replace(overlay, '  decide +kernel', 1) != returned.read_text():
    raise ValueError('source overlay changed declarations, algorithms or theorem types')
 declared = declared_inventory()
 expected = json.loads((EVIDENCE / 'theorem-inventory.json').read_text())
 if declared != expected or len(declared) != 673:
  raise ValueError('complete theorem inventory changed')
 rows = []
 for language, component, path, name in SOURCES:
  actual = (component or site) / path
  snapshot = ROOT / 'formal/source_reference/current' / name / (path + '.txt')
  if actual.read_bytes() != snapshot.read_bytes():
   raise ValueError('current conditional runtime source changed: ' + path)
  rows.append({'language': language, 'source': path, 'sha256': sha(actual)})
 findings = audit([MODULES, ROOT / 'formal/PCSConditionalRuntime.lean'])
 if findings: raise ValueError('\n'.join(findings))
 return {'archive_sha256': manifest['archive_sha256'], 'source_files': rows,
         'proof_sources': manifest['files'], 'theorem_targets': [r['name'] for r in declared]}


def fresh_lean_environment(overlay: Path) -> tuple[dict, dict]:
 """Resolve Lake once, then use its exact Lean directly with fresh imports first."""
 env = dict(os.environ)
 for variable in ['PATH', 'LEAN_PATH']:
  resolved = execute(['lake', 'env', 'printenv', variable])
  if resolved['returncode']:
   raise RuntimeError('could not resolve pinned Lake environment: ' + variable)
  env[variable] = resolved['stdout'].strip()
 executable = shutil.which('lean', path=env['PATH'])
 if executable is None: raise RuntimeError('pinned Lean executable unavailable')
 env['_PCS_FRESH_LEAN'] = str(Path(executable).resolve())
 env['LEAN_PATH'] = str(overlay) + os.pathsep + env['LEAN_PATH']
 version = execute([env['_PCS_FRESH_LEAN'], '--version'], env)
 expected = 'Lean (version 4.28.0,'
 commit = 'commit 7e01a1bf5c70fc6167d49c345d3bf80596e9a79b,'
 if version['returncode'] or not version['stdout'].startswith(expected) or commit not in version['stdout']:
  raise RuntimeError('conditional replay requires the exact pinned Lean 4.28.0 release')
 return env, version


def execute(command: list[str], env: dict | None = None, timeout: int = 600) -> dict:
 if env and env.get('_PCS_FRESH_LEAN') and command[:3] == ['lake', 'env', 'lean']:
  # Lake would prepend cached build directories ahead of the fresh overlay.
  # Its environment was resolved above; invoking the pinned executable directly
  # is necessary for fresh lowering/principal/audit imports to use this replay.
  command = [env['_PCS_FRESH_LEAN'], *command[3:]]
 start = time.monotonic()
 proc = subprocess.run(command, cwd=ROOT / 'formal', env=env, text=True,
                       capture_output=True, timeout=timeout)
 return {'command': command, 'returncode': proc.returncode, 'stdout': proc.stdout,
         'stderr': proc.stderr, 'wall_seconds': round(time.monotonic() - start, 6)}


def compile_module(path: Path, output: Path, env: dict, memory_mb: int, heavy_timeout: int) -> dict:
 result = execute(['lake', 'env', 'lean', '-j1', '-M' + str(memory_mb), '-D', 'Elab.async=false',
                   '-D', 'maxHeartbeats=0', '-D', 'maxRecDepth=100000',
                   '-o', str(output), str(path)], env, heavy_timeout)
 if result['returncode']:
  raise RuntimeError('fresh conditional proof elaboration failed\n' + result['stdout'] + result['stderr'])
 return result


def verify(site: Path, *, output: Path | None = None, negative_controls: bool = False,
           memory_mb: int = 7500, heavy_timeout: int = 1800) -> dict:
 """Fresh proof check; stable_contract excludes timings and temporary filenames."""
 site = site.resolve()
 if not 1024 <= memory_mb <= 32000: raise ValueError('memory cap must be in [1024,32000] MB')
 if not 900 <= heavy_timeout <= 3600: raise ValueError('heavy timeout must be in [900,3600] seconds')
 source = check_sources(site)
 frozen = {ROOT / row['path']: row['sha256'] for row in source['proof_sources']}
 records = []
 negatives = []
 with tempfile.TemporaryDirectory(prefix='pcs-conditional-replay-') as folder:
  temp = Path(folder)
  (temp / 'PCSConditionalRuntime').mkdir()
  env, toolchain = fresh_lean_environment(temp)
  records.append(toolchain)
  # Fresh source-read certificates and lowering are required; cached extraction
  # oleans cannot stand in for current snapshot bytes. Remaining proof modules
  # are source-pinned and must already have passed the complete library build.
  for stem in ['PyConditional', 'JsConditional', 'PyConditionalLowered', 'JsConditionalLowered',
               'PyMain', 'JsMain']:
   records.append(compile_module(MODULES / (stem + '.lean'),
                                 temp / 'PCSConditionalRuntime' / (stem + '.olean'), env, memory_mb, heavy_timeout))
  driver = temp / 'CompleteAudit.lean'
  driver.write_text('import PCSConditionalRuntime\n' +
                    '\n'.join('#print axioms ' + n for n in source['theorem_targets']) + '\n')
  result = execute(['lake', 'env', 'lean', '-j1', str(driver)], env)
  if result['returncode']: raise RuntimeError(result['stdout'] + result['stderr'])
  inventory = check_inventory(result['stdout'], source['theorem_targets'])
  records.append(result)
  if negative_controls:
   # Deliberately false source claims use the actual extracted checker. Their
   # nonzero elaboration and sorryAx inventory are rejected, never interpreted
   # as evidence. Current native source mutations are also rejected by byte gate.
   for lang, expr in [('python', 'PCSCR.Py.checkSegs PCSCR.Py.conditionalPySrc []'),
                      ('javascript', 'PCSCR.Js.checkJSegs PCSCR.Js.conditionalJsSrc []')]:
    probe = temp / ('FalseSource_' + lang + '.lean')
    probe.write_text('import PCSConditionalRuntime\nexample : ' + expr + ' = true := by decide +kernel\n')
    failed = execute(['lake', 'env', 'lean', '-j1', str(probe)], env)
    log = failed['stdout'] + failed['stderr']
    if failed['returncode'] == 0 or 'is false' not in log:
     raise ValueError('false extraction contract was not rejected semantically')
    negatives.append({'language': lang, 'rejected': True, **failed})
  if any(sha(path) != identity for path, identity in frozen.items()):
   raise ValueError('proof sources changed during replay')
  if check_sources(site) != source: raise ValueError('runtime sources changed during replay')
 stable = {**source, 'kernel_theorems': inventory, 'principals': PRINCIPALS,
           'assumptions': ASSUMPTIONS, 'assurance': 'source-bound declared heap-subset refinement',
           'native_execution_correspondence_proved': False, 'scientific_acceptance': False}
 report = {'format': 'pcs-conditional-runtime-refinement-v1', 'stable_contract': stable,
           'fresh_elaboration': records, 'negative_controls': negatives}
 if output:
  output.parent.mkdir(parents=True, exist_ok=True)
  output.write_text(json.dumps(report, indent=2) + '\n')
 return report


def main() -> None:
 parser = argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--site', type=Path, required=True)
 parser.add_argument('--output', type=Path)
 parser.add_argument('--negative-controls', action='store_true')
 parser.add_argument('--build', action='store_true', help='Freshly build all library modules sequentially first')
 parser.add_argument('--build-output', type=Path, help='New file for complete build evidence (required with --build)')
 parser.add_argument('--memory-mb', type=int, default=7500, help='Bounded Lean process cap, at most 32000 MB')
 parser.add_argument('--heavy-timeout', type=int, default=1800, help='Bounded per-module timeout, at most 3600 seconds')
 args = parser.parse_args()
 if args.build:
  if not args.build_output: parser.error('--build requires --build-output')
  from build_conditional_runtime import build
  build(args.build_output,args.memory_mb,args.heavy_timeout)
 report = verify(args.site, output=args.output, negative_controls=args.negative_controls,
                 memory_mb=args.memory_mb, heavy_timeout=args.heavy_timeout)
 print(json.dumps({'fresh_public_theorems': len(report['stable_contract']['kernel_theorems']),
                   'principals': PRINCIPALS, 'scientific_acceptance': False}))

if __name__ == '__main__': main()
