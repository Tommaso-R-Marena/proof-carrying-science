"""Fresh scientific audit/witness/recovery proofs, with complete namespace audit.

The default uses the standalone Lake project. Explicit direct mode uses reviewed
source-identical prebuilt imports and fresh outputs for every new module. Source
hashes do not establish object provenance, honest OS execution or protected keys.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parent / 'formal'
ALLOWED = {'propext', 'Classical.choice', 'Quot.sound'}
NAMESPACE = 'PCSScientificAuthorityV2.'
MODULES = ('PCSScientificAuthorityV2/Audit', 'PCSScientificAuthorityV2/Witness',
           'PCSScientificAuthorityV2/Recovery', 'PCSScientificAuthorityV2/Fixtures',
           'PCSScientificAuthorityV2')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def unchanged_tree(local, reviewed):
    paths = subprocess.check_output(['git', 'ls-files', '--', str(local.relative_to(ROOT))],
                                    cwd=ROOT, text=True).splitlines()
    for name in paths:
        source = ROOT / name
        relative = source.relative_to(local)
        if source.is_file() and sha(source) != sha(reviewed / relative):
            raise RuntimeError('old import source differs: ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lean', type=Path, required=True)
    parser.add_argument('--dependency-checkout', type=Path)
    parser.add_argument('--receiver-qualification', type=Path)
    parser.add_argument('--history-checkout', type=Path)
    parser.add_argument('--join-checkout', type=Path)
    args = parser.parse_args()
    direct = [args.dependency_checkout, args.receiver_qualification,
              args.history_checkout, args.join_checkout]
    if any(direct) and not all(direct):
        parser.error('direct mode requires all four cache/qualification/checkouts')
    lean = args.lean.resolve(strict=True)
    version = subprocess.check_output([str(lean), '--version'], text=True, cwd=PROJECT)
    if 'version 4.28.0,' not in version:
        raise RuntimeError('Lean 4.28.0 is required')
    sys.path.insert(0, str(ROOT))
    from scripts.audit_lean_source import audit
    sources = sorted(p for p in PROJECT.rglob('*.lean') if '.lake' not in p.relative_to(PROJECT).parts)
    findings = audit(sources)
    if findings:
        raise RuntimeError('forbidden Lean source: ' + repr(findings))
    projects = [ROOT, PROJECT, ROOT / 'research/scientific_receiver_v1/formal',
                ROOT / 'research/authorization_history_v1/formal',
                ROOT / 'research/scientific_history_v1/formal']
    manifests = [json.loads((p / 'lake-manifest.json').read_bytes()) for p in projects]
    pins = [{p['name']: p['rev'] for p in m['packages'] if p['type'] == 'git'} for m in manifests]
    counts = [sum(p['type'] == 'git' for p in m['packages']) for m in manifests]
    if counts != [9] * len(projects) or any(p != pins[0] for p in pins[1:]):
        raise RuntimeError('all five manifests must match the same nine exact Git revisions')
    fixed = [*sources, PROJECT / 'lakefile.toml', PROJECT / 'lake-manifest.json',
             PROJECT / 'lean-toolchain', Path(__file__)]
    before = {str(p.relative_to(ROOT)): sha(p) for p in fixed}
    out = PROJECT / '.lake/build/lib/lean'
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    imports = {'mode': 'standalone Lake', 'fresh_dependency_rebuild_claimed': False}
    if all(direct):
        from research.authorization_history_v1.formal_inputs import verify_cache
        base = args.dependency_checkout.resolve(strict=True)
        libraries = verify_cache(base, pins[0])
        old_scopes = ('formal', 'research/integration_v1/formal',
                      'incubation/pcs_certified_numerics_v1', 'incubation/pcs_conservation_algebra_v1')
        for scope in old_scopes:
            unchanged_tree(ROOT / scope, base / scope)
        history = args.history_checkout.resolve(strict=True) / 'research/authorization_history_v1/formal'
        joined = args.join_checkout.resolve(strict=True) / 'research/scientific_history_v1/formal'
        unchanged_tree(ROOT / 'research/authorization_history_v1/formal', history)
        unchanged_tree(ROOT / 'research/scientific_history_v1/formal', joined)
        qualified = args.receiver_qualification.resolve(strict=True)
        q = json.loads((qualified / 'qualification.json').read_bytes())
        if sha(lean) != q['lean_sha256']:
            raise RuntimeError('compiler differs from reviewed receiver compiler')
        for name, expected in q['source_sha256'].items():
            if name.startswith('research/scientific_receiver_v1/formal/') and sha(ROOT / name) != expected:
                raise RuntimeError('receiver source differs: ' + name)
        manifest = qualified / 'module-artifacts.json'
        if sha(manifest) != q['module_artifacts_sha256']:
            raise RuntimeError('receiver artifact manifest differs')
        artifacts = json.loads(manifest.read_bytes())['artifacts']
        for item in artifacts:
            if item['module'].startswith('PCSScientificReceiver') and sha(item['path']) != item['sha256']:
                raise RuntimeError('receiver import artifact differs: ' + item['path'])
        cache_roots = [joined / '.lake/build/lib/lean', history / '.lake/build/lib/lean']
        object_pins = {str(p): sha(p) for cache in cache_roots for p in sorted(cache.rglob('*.olean*'))}
        if not object_pins:
            raise RuntimeError('no compiled history/join import cache')
        roots = [out, *cache_roots, qualified / 'fresh-lean',
                 *(base / scope / '.lake/build/lib/lean' for scope in old_scopes[1:]),
                 base / 'formal/.lake/build/lib/lean', *libraries]
        env['LEAN_PATH'] = os.pathsep.join(map(str, roots))
        command = [str(lean)]
        for module in MODULES:
            target = out / (module + '.olean')
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([*command, '-o', str(target), module + '.lean'], cwd=PROJECT, env=env, check=True)
        if object_pins != {p: sha(p) for p in object_pins}:
            raise RuntimeError('old history/join cache changed during new checking')
        imports = {'mode': 'fresh new modules with source-checked read-only imports',
                   'receiver_qualification_sha256': sha(qualified / 'qualification.json'),
                   'history_join_object_sha256': object_pins,
                   'fresh_dependency_rebuild_claimed': False,
                   'source_to_prebuilt_object_correspondence_proved': False}
    else:
        subprocess.run(['lake', 'build', 'PCSScientificAuthorityV2'], cwd=PROJECT, env=env, check=True)
        command = ['lake', 'env', 'lean']
    result = subprocess.run([*command, str(PROJECT / 'Audit.lean')], cwd=PROJECT,
                            env=env, capture_output=True, text=True, check=True)
    text = result.stdout + result.stderr
    (out / 'statements-and-axioms.log').write_text(text)
    closures = {name: sorted(set(re.findall(r'[A-Za-z_.]+', axioms))) for name, axioms in
                re.findall(r"'([^']+)' depends on axioms: \[([^]]*)\]", text, re.S)}
    closures.update({name: [] for name in re.findall(r"'([^']+)' does not depend on any axioms", text)})
    authored = {}
    for source in sources:
        for match in re.finditer(r'^theorem (\w+)', source.read_text(), re.M):
            name = NAMESPACE + match.group(1)
            if name in authored:
                raise RuntimeError('duplicate authored theorem ' + name)
            authored[name] = {'source': str(source.relative_to(ROOT)),
                              'line': source.read_text()[:match.start()].count('\n') + 1}
    if not authored.keys() <= closures.keys() or any(set(a) - ALLOWED for a in closures.values()):
        raise RuntimeError('missing authored theorem audit or unapproved axiom')
    if before != {str(p.relative_to(ROOT)): sha(p) for p in fixed}:
        raise RuntimeError('new sources changed while checking')
    declarations = {}
    for name, axioms in sorted(closures.items()):
        pattern = r'(?m)^' + re.escape(name) + r'(?=\s)(.*?)(?=\n\x27' + re.escape(name) + r'\x27 (?:depends|does))'
        found = re.search(pattern, text, re.S)
        if not found:
            raise RuntimeError('statement missing from audit: ' + name)
        declarations[name] = {'statement': name + found.group(1).rstrip(), 'axioms': axioms,
                              'authored': name in authored, **authored.get(name, {})}
    report = {'format': 'pcs-scientific-authority-v2-formal-qualification-v1',
              'lean_version': version.strip(), 'lean_sha256': sha(lean), 'sources': before,
              'dependency_revisions': pins[0], 'imports': imports,
              'authored_theorems': len(authored), 'theorems_including_generated': len(closures),
              'declarations': declarations, 'scientific_acceptance': False,
              'production_authority': False, 'independent_administration_established': False}
    (out / 'formal-report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'authored': len(authored), 'all_theorem_closures': len(closures), 'status': 'PROVED'}))


if __name__ == '__main__':
    main()
