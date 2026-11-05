"""Fixed receiving-side proof construction; external results never supply verdicts."""
from __future__ import annotations

import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

from pcs import transport_kernel_v1 as model
from pcs import transport_trace_kernel_v1 as trace
from research.trace_lab_v1.audit import pinned_tool
from . import core

HERE = Path(__file__).resolve().parent
GENERAL = ['PCSTraceEnvelope.'+n for n in (
    'step_sub', 'within_step', 'step_add_const', 'coherent_residual', 'radius_constant', 'coherent_sharp',
    'within_trans', 'propagate', 'radius_mono',
    'uniform', 'check_sound', 'check_uniform', 'real_bound')]
MODULES = [('PCSReal/Transport.lean', model.GENERAL_THEOREMS),
           ('PCSReal/TransportTrace.lean', trace.GENERAL),
           ('RawDecide.lean', []), ('Envelope.lean', GENERAL)]


def sources():
    return {**trace.sources(),
            'RawDecide.lean': (HERE.parent/'portable_transport_v2/RawDecide.lean').read_bytes(),
            'tool-pins.py.txt': (HERE.parent/'trace_lab_v1/audit.py').read_bytes(),
            **{name: (HERE/name).read_bytes() for name in
               ['Envelope.lean', 'core.py', 'kernel.py', 'evidence.py', 'report.py', '__main__.py']}}


def _session(out, frozen, result, remaining):
    lean, env, version = model._environment(min(30, remaining()))
    tools = {'lean': Path(lean), 'leanchecker': Path(lean).with_name('leanchecker')}
    result.update(lean_version=version, mathlib_revision=model.MATHLIB_REVISION,
                  tool_sha256={n: pinned_tool(n, p) for n, p in tools.items()})
    env = dict(env, LEAN_PATH=str(out)+os.pathsep+env['LEAN_PATH'])

    def run(command):
        p = subprocess.run(list(map(str, command)), cwd=out, env=env,
                           text=True, capture_output=True, timeout=remaining())
        result['executions'].append(dict(command=list(map(str, command)),
                                         returncode=p.returncode, stdout=p.stdout, stderr=p.stderr))
        if p.returncode:
            raise ValueError('Actual Lean proof or object replay rejected')
        return p.stdout

    objects = {}
    staged = {}

    def compile_(name, raw, names):
        p = out/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        staged[name] = raw
        if p.read_bytes() != raw:
            raise ValueError('Staged proof source changed before compilation')
        stdout = run([lean, '-j1', '-M2048', '-D', 'Elab.async=false',
                      '--root='+str(out), '-o', p.with_suffix('.olean'), p])
        if p.read_bytes() != raw:
            raise ValueError('Staged proof source changed during compilation')
        result['axiom_closures'].update(model._inventory(stdout, names))
        objects[name] = model.sha(p.with_suffix('.olean').read_bytes())

    for name, names in MODULES:
        raw = frozen[name]
        if names:
            raw += ('\n'+'\n'.join('#print axioms '+n for n in names)+'\n').encode()
        compile_(name, raw, names)

    def finish():
        if staged != {n: (out/n).read_bytes() for n in staged}:
            raise ValueError('Staged proof source changed during replay')
        if frozen != sources():
            raise ValueError('Receiving sources changed during replay')
        if result['tool_sha256'] != {n: pinned_tool(n, p) for n, p in tools.items()}:
            raise ValueError('Compiler/checker bytes changed during replay')
        if objects != {n: model.sha((out/n).with_suffix('.olean').read_bytes()) for n in objects}:
            raise ValueError('Compiled object changed during replay')
        result.update(sources_stable=True, object_sha256=objects)

    return compile_, run, tools, finish


def _budget(timeout):
    if type(timeout) not in {int, float} or not math.isfinite(timeout) or not 0 < timeout <= 300:
        raise ValueError('Finite timeout in (0,300] required')
    start = time.monotonic()

    def remaining():
        value = start+timeout-time.monotonic()
        if value <= 0:
            raise subprocess.TimeoutExpired('trace envelope replay', timeout)
        return value
    return start, remaining


def replay(raw: bytes, tolerance: str, *, timeout=120):
    start, remaining = _budget(timeout)
    r = dict(format='pcs-trace-envelope-replay-v1', status='REFUSED',
             kernel_checked=False, pcs_authority=False, scientific_acceptance=False,
             empirical_validation=False, implementation_correspondence='OPEN',
             continuum_accuracy='OPEN', executions=[], axiom_closures={})
    try:
        data, proposal = core.prepare(raw, tolerance)
        frozen = sources()
        proof, names = core.render(data, proposal)
        r.update(input_sha256=model.sha(raw), source_sha256={n: model.sha(b) for n, b in frozen.items()},
                 proof_sha256=model.sha(proof), proposal=proposal, proof=proof.decode(),
                 trace_certificate=data)
        with tempfile.TemporaryDirectory(prefix='pcs-envelope-') as folder:
            compile_, _, _, finish = _session(Path(folder), frozen, r, remaining)
            compile_('Replay.lean', proof, names)
            finish()
        r.update(kernel_checked=True,
                 status='ENVELOPE_WITHIN_TOLERANCE' if proposal['tolerance_budget_met'] else 'ENVELOPE_BUDGET_EXCEEDS_TOLERANCE')
    except (OSError, ValueError, TypeError, KeyError, RecursionError, subprocess.SubprocessError) as error:
        r.update(kernel_checked=False, error=f'{type(error).__name__}: {error}')
    r['wall_seconds'] = round(time.monotonic()-start, 6)
    return r


def audit(out: Path, *, timeout=300):
    start, remaining = _budget(timeout)
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    r = dict(format='pcs-trace-envelope-audit-v1', kernel_checked=False,
             fresh_object_checked=False, pcs_authority=False, executions=[], axiom_closures={})
    try:
        frozen = sources()
        r['source_sha256'] = {n: model.sha(b) for n, b in frozen.items()}
        _, run, tools, finish = _session(out, frozen, r, remaining)
        run([tools['leanchecker'], '--fresh', 'Envelope'])
        finish()
        r.update(kernel_checked=True, fresh_object_checked=True)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        r['error'] = f'{type(error).__name__}: {error}'
    r['wall_seconds'] = round(time.monotonic()-start, 6)
    import json
    (out/'result.json').write_text(json.dumps(r, indent=2)+'\n')
    return r
