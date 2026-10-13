"""Source-provenance and split firewall for the public external Mathlib v4 set.

Integrity checks are not execution attestations or proof certificates. The set
contains statements only; imported Mathlib tactics can still know their proofs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

MATHLIB_REVISION = '8f9d9cff6bd728b17a24e163c9402775d9e6a365'
FORMAT = 'pcs-external-mathlib-benchmark-v4'
MAX_BYTES = 8 * 1024 * 1024
MAX_NODES = 20000
MAX_DEPTH = 256
PROOF_FIELDS = {'proof', 'proof_body', 'solution', 'tactics', 'actions', 'training_label', 'expected_actions'}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('duplicate benchmark JSON key')
        result[k] = v
    return result


def read_json(path: Path):
    if path.is_symlink() or path.stat().st_size > MAX_BYTES:
        raise ValueError('unsafe or oversized benchmark record')
    try:
        return json.loads(path.read_text(), object_pairs_hook=_unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite benchmark JSON')))
    except RecursionError as error:
        raise ValueError('benchmark nesting limit') from error


def _without_solutions(value, depth=0):
    if depth > MAX_DEPTH:
        raise ValueError('benchmark nesting limit')
    if isinstance(value, dict):
        if set(value) & PROOF_FIELDS:
            raise ValueError('evaluation record contains a solution-bearing field')
        for child in value.values():
            _without_solutions(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _without_solutions(child, depth + 1)


def alpha_signature(expression: dict, *, structural: bool = False) -> str:
    """Binder/universe-renaming invariant syntax hash, not semantic equivalence.

    Bound indices, constant identity, binder domains and quantifier order remain.
    Implicit/explicit binder presentation is retained in source metadata but does
    not change the proposition; the comparison omits that presentation field.
    The weaker structural hash abstracts literals and is a review hint only.
    It is never used to claim mathematical equivalence or silently drop a task.
    """
    universes = {}
    count = 0

    def level(text):
        def replace(match):
            name = match.group(0)
            if name not in universes:
                universes[name] = 'U' + str(len(universes))
            return universes[name]
        return re.sub(r'\b[A-Za-z_][A-Za-z_0-9]*\b',
                      lambda m: m.group(0) if m.group(0) in {'max', 'imax'} else replace(m), text)

    def walk(node, depth):
        nonlocal count
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH or not isinstance(node, dict):
            raise ValueError('bounded expression required')
        if not {'kind', 'value', 'children'} <= set(node):
            raise ValueError('incomplete expression node')
        k, v, children = node['kind'], node['value'], node['children']
        if not isinstance(k, str) or not isinstance(v, str) or not isinstance(children, list):
            raise ValueError('invalid expression node')
        if k in {'local', 'goal', 'metavariable'}:
            raise ValueError('benchmark type must be closed')
        if k in {'forall', 'lambda', 'let'}:
            v = ''
        elif k == 'sort':
            v = level(v)
        elif k == 'constant':
            name, sep, levels = v.partition(':')
            v = name + (':' + level(levels) if sep else '')
        elif structural and k in {'natural', 'string'}:
            v = '*'
        return {'kind': k, 'value': v,
                'children': [walk(child, depth + 1) for child in children]}

    return sha(walk(expression, 0))


def statement_symbols(expression):
    symbols = set()
    stack = [expression]
    visited = 0
    while stack:
        node = stack.pop()
        visited += 1
        if visited > MAX_NODES or not isinstance(node, dict):
            raise ValueError('bounded expression required')
        if node.get('kind') == 'constant':
            symbols.add(node['value'].partition(':')[0])
        stack.extend(node.get('children', []))
    return sorted(symbols)


def check_partitions(evaluation, training=(), validation=()):
    """Fail closed on explicit family/module/alpha duplicates across splits."""
    targets = {row['declaration'] for row in evaluation}
    evaluation_modules = {row['source']['module'] for row in evaluation}
    evaluation_families = {row['family'] for row in evaluation}
    evaluation_types = {alpha_signature(row['expression']) for row in evaluation}
    seen_ids = set()
    seen_types = set()
    for row in evaluation:
        _without_solutions(row)
        if row.get('split') != 'final' or row['id'] in seen_ids:
            raise ValueError('invalid evaluation membership')
        signature = alpha_signature(row['expression'])
        if signature in seen_types:
            raise ValueError('alpha-duplicate evaluation task')
        seen_ids.add(row['id'])
        seen_types.add(signature)
    other_ids = set()
    other_types = {}
    for label, rows in [('training', training), ('validation', validation)]:
        for row in rows:
            if row.get('id') in other_ids:
                raise ValueError(label + ' repeats training/validation task identity')
            other_ids.add(row.get('id'))
            if row.get('split') == 'final' or row.get('id') in seen_ids:
                raise ValueError(label + ' contains evaluation membership')
            if not isinstance(row.get('source'), dict) or not row['source'].get('module') or not row.get('family'):
                raise ValueError(label + ' source module/family provenance missing')
            if row['source']['module'] in evaluation_modules or row['family'] in evaluation_families:
                raise ValueError(label + ' source-module/theorem-family leakage')
            if row.get('declaration') in targets:
                raise ValueError(label + ' target-declaration leakage')
            if 'expression' not in row or alpha_signature(row['expression']) in evaluation_types:
                raise ValueError(label + ' missing type or alpha-equivalent answer leakage')
            signature = alpha_signature(row['expression'])
            if signature in other_types:
                raise ValueError(label + ' alpha-duplicates ' + other_types[signature])
            other_types[signature] = label
    return {'evaluation_tasks': len(evaluation), 'training_tasks': len(training),
            'validation_tasks': len(validation), 'module_family_disjoint': True,
            'alpha_duplicates': 0, 'scope': 'Explicit statement provenance only; imported library/proof dependencies are not disjoint.'}


def filter_premises(premises, evaluation, *, exclude_modules=()):
    """Exclude all exact target names and alpha-answer aliases, not known facts.

    Caller may pass training modules for a separately labeled strict sensitivity.
    Primary comparison permits lawful foundational facts from training modules.
    Missing structured types are rejected rather than treated as safe aliases.
    """
    target_names = {row['declaration'] for row in evaluation}
    target_signatures = {alpha_signature(row['expression']) for row in evaluation}
    excluded_modules = set(exclude_modules)
    kept, rejected = [], []
    for entry in premises:
        reason = None
        name = entry.get('name')
        if not isinstance(name, str) or not name:
            reason = 'missing_resolved_name'
        elif name in target_names:
            reason = 'evaluated_declaration'
        elif excluded_modules and not entry.get('module'):
            reason = 'module_provenance_missing_for_strict_filter'
        elif entry.get('module') in excluded_modules:
            reason = 'sensitivity_excluded_module'
        elif not isinstance(entry.get('expression'), dict):
            reason = 'missing_type_expression'
        else:
            try:
                if alpha_signature(entry['expression']) in target_signatures:
                    reason = 'alpha_equivalent_answer'
            except ValueError:
                reason = 'invalid_type_expression'
        if reason:
            rejected.append({'name': name, 'reason': reason})
        else:
            kept.append(entry)
    return kept, {'kept': len(kept), 'rejected': rejected,
                  'proof_dependency_leakage': 'not excluded; imported tactics and related theorems may transitively use target facts',
                  'semantic_equivalence_decided': False}


def _member(root: Path, name: str) -> Path:
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != name:
        raise ValueError('unsafe benchmark member path')
    path = root / relative
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError('symlink benchmark member')
    return path


def verify_benchmark(root: Path, *, mathlib: Path | None = None, expected_seal: str | None = None):
    root = root.resolve()
    seal_path = root / 'ARTIFACT_SHA256.json'
    if expected_seal is not None and file_sha(seal_path) != expected_seal:
        raise ValueError('receiver-approved benchmark seal mismatch')
    seal = read_json(seal_path)
    if seal.get('format') != 'pcs-mathlib-v4-artifact-seal' or not isinstance(seal.get('files'), dict):
        raise ValueError('invalid benchmark seal')
    for name, digest in seal['files'].items():
        if file_sha(_member(root, name)) != digest:
            raise ValueError('benchmark artifact checksum mismatch: ' + name)
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name != 'ARTIFACT_SHA256.json'}
    if actual != set(seal['files']):
        raise ValueError('benchmark artifact membership mismatch')
    protocol = read_json(root / 'protocol.json')
    tasks = read_json(root / 'tasks.json')
    if protocol.get('format') != FORMAT or protocol.get('mathlib_revision') != MATHLIB_REVISION:
        raise ValueError('wrong benchmark/library version')
    if protocol.get('tasks_sha256') != sha(tasks) or protocol.get('frozen_before_training') is not True:
        raise ValueError('benchmark task digest/freeze mismatch')
    for row in tasks:
        if row['statement_sha256'] != hashlib.sha256(row['statement'].encode()).hexdigest():
            raise ValueError('statement binding mismatch')
        if row['alpha_sha256'] != alpha_signature(row['expression']):
            raise ValueError('structured type binding mismatch')
        if row['source']['revision'] != MATHLIB_REVISION or row['source']['license'] != 'Apache-2.0':
            raise ValueError('source revision/license mismatch')
    partition = check_partitions(tasks)
    if len(tasks) != protocol['evaluation_tasks']:
        raise ValueError('incomplete frozen membership')
    if mathlib is not None:
        revision = subprocess.check_output(['git', '-C', str(mathlib), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != MATHLIB_REVISION:
            raise ValueError('approved Mathlib revision required')
        for row in tasks:
            source = row['source']
            if file_sha(_member(mathlib.resolve(), source['path'])) != source['file_sha256']:
                raise ValueError('actual source file changed')
            lines = (mathlib / source['path']).read_text().splitlines()
            header = '\n'.join(lines[source['lines'][0]-1:source['lines'][1]]).split(':=', 1)[0].rstrip()
            if hashlib.sha256(header.encode()).hexdigest() != source['header_sha256']:
                raise ValueError('source declaration header changed')
    return {'format': 'pcs-mathlib-v4-integrity-result', 'integrity_valid': True,
            'source_checked': mathlib is not None, 'partition': partition,
            'independently_replayed': False, 'proof_bodies_included': False,
            'production_authority': False,
            'limits': 'Unsigned integrity is not execution or mathematical novelty. Source signatures and rendered propositions require separate Lean replay.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--mathlib', type=Path)
    parser.add_argument('--expected-seal')
    args = parser.parse_args()
    print(json.dumps(verify_benchmark(args.root, mathlib=args.mathlib, expected_seal=args.expected_seal), indent=2))


if __name__ == '__main__':
    main()
