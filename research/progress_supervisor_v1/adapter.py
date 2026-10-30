"""Fresh qualification of the fixed adapter specification; never authorization.

The native table is a differential observation. The ordinary Lean kernel checks
all ten theorem closures, including the bridge to the exact workflow certificate.
Python/SQLite/compiler correspondence remains tested rather than proved.
"""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import time

from pcs.transport_kernel_v1 import _inventory
from .authority import Authority
from .binding import HERE, SPEC_FILES, source_inventory
from .certificate import encode, propose, sha
from .example import model

ADAPTER = ['PCSProgressAdapter.' + name for name in (
    'initial_valid', 'step_refines', 'valid_publication', 'goal_halts',
    'execution_invariant', 'execution_no_private_publication', 'completion_rows')]
BRIDGE = ['PCSProgressAdapterBridge.' + name for name in (
    'edges_declared', 'step_declared', 'execution_path')]


def qualify(output):
    """Compile first-party fixed sources with the existing exact tool pins."""
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = source_inventory()
    raw = encode(model())
    started = time.monotonic()
    with Authority(raw, encode(propose(raw, [4])), out / 'supervisor') as authority:
        proof = out / 'adapter';proof.mkdir()
        env = dict(authority.env, LEAN_PATH=str(proof) + ':' + str(authority.out))
        executions, axioms, sources = [], {}, {}

        def run(command, timeout):
            authority.check()
            result = subprocess.run(list(map(str, command)), cwd=proof, env=env,
                                    capture_output=True, timeout=timeout)
            executions.append(dict(command=list(map(str, command)), returncode=result.returncode,
                                   stdout=result.stdout.decode('utf-8'), stderr=result.stderr.decode('utf-8')))
            (out / 'executions.json').write_text(json.dumps(executions, indent=2) + '\n')
            authority.check()
            if result.returncode or result.stderr:
                raise ValueError('actual adapter qualification rejected: ' +
                                 (result.stdout + result.stderr).decode('utf-8')[-2000:])
            return result.stdout

        for name in SPEC_FILES:
            source = (HERE / name).read_bytes()
            if sha(source) != before[name]:
                raise ValueError('adapter source changed')
            names = ADAPTER if name == 'Adapter.lean' else BRIDGE if name == 'AdapterBridge.lean' else []
            staged = source + ('\n' + '\n'.join('#print axioms ' + n for n in names) + '\n').encode()
            sources[name] = staged
            (proof / name).write_bytes(staged)
            stdout = run([authority.tools['lean'], '-j1', '-M2048', '-D', 'Elab.async=false',
                          '--root=' + str(proof), '-o', name[:-5] + '.olean', '-c', name[:-5] + '.c', name], 90)
            if names:axioms.update(_inventory(stdout.decode('utf-8'), names))
        run([authority.tools['leanchecker'], '--fresh', 'AdapterTable'], 180)
        run([authority.tools['leanc'], '-O2', '-o', 'adapter-table',
             'AdapterTable.c', 'AdapterBridge.c', 'Adapter.c',
             *[authority.out / (n + '.c') for n in ('Data', 'Codec', 'Wire', 'Progress', 'PCSActionShield')]], 90)
        image_sha = sha((proof / 'adapter-table').read_bytes())
        table = run([proof / 'adapter-table'], 15)
        if sha((proof / 'adapter-table').read_bytes()) != image_sha:
            raise ValueError('adapter observation executable changed')
        if any((proof / n).read_bytes() != value for n, value in sources.items()) or source_inventory() != before:
            raise ValueError('adapter qualification source changed')
        (out / 'table.csv').write_bytes(table)
        result = dict(format='pcs-fixed-adapter-qualification-v1', sources=before,
                      model_sha256=sha(raw), certificate_sha256=sha(authority.cert_raw),
                      axiom_closures=axioms, fresh_objects_checked=True,
                      table_sha256=sha(table), native_image_sha256=image_sha,
                      cases=len(table.splitlines()), seconds=round(time.monotonic() - started, 6),
                      implementation_correspondence='DIFFERENTIALLY_TESTED_NOT_PROVED', pcs_authority=False)
        (out / 'qualification.json').write_text(json.dumps(result, indent=2) + '\n')
        return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('output')
    print(json.dumps(qualify(parser.parse_args().output)))
