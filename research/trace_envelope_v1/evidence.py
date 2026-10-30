"""Hash-bound evidence convenience; no signed receipt or stored verdict authority."""
from __future__ import annotations

import json
from pathlib import Path

from pcs.jsonio import strict_json_loads
from research.flux_detective_v1.check import MAX_BYTES
from . import core, kernel
from .report import render as render_report


def read_bounded(path, limit):
    with Path(path).open('rb') as f:
        raw = f.read(limit+1)
    if len(raw) > limit:
        raise ValueError('Bounded captured file required')
    return raw


def export(out: Path, raw: bytes, result: dict):
    """Reviewers must reexecute; even a self-consistent forged result is no verdict."""
    frozen = kernel.sources()
    if (result.get('input_sha256') != kernel.model.sha(raw)
            or result.get('source_sha256') != {n: kernel.model.sha(b) for n, b in frozen.items()}):
        raise ValueError('Captured input and receiving sources must match')
    data, proposal = core.prepare(raw, result['proposal']['tolerance'])
    proof, _ = core.render(data, proposal)
    if (result['proposal'] != proposal or result['proof'] != proof.decode()
            or result['proof_sha256'] != kernel.model.sha(proof)):
        raise ValueError('Regenerated proposed proof and budget must match')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    files = {'input.json': raw, 'Replay.lean': proof, 'REPORT.md':render_report(result).encode(),
             'request.json': json.dumps({'format':'pcs-trace-envelope-request-v1', 'tolerance':proposal['tolerance']}, sort_keys=True).encode()+b'\n',
             'result.json': json.dumps(result, indent=2).encode()+b'\n',
             **{'sources/'+n: b for n, b in frozen.items()}}
    for name, b in files.items():
        p = out/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    (out/'SHA256.json').write_text(json.dumps({n: kernel.model.sha(b) for n, b in files.items()}, indent=2)+'\n')


def verify(folder: Path, *, timeout=120, out: Path | None = None):
    """Snapshot bounded bytes, compare reviewed sources, regenerate and run Lean."""
    if out is not None and Path(out).exists():
        raise ValueError('Fresh independent output directory required')
    folder = Path(folder)
    inventory = strict_json_loads(read_bounded(folder/'SHA256.json', 128*1024))
    frozen = kernel.sources()
    names = {'input.json', 'request.json', 'Replay.lean', 'result.json', 'REPORT.md'} | {'sources/'+n for n in frozen}
    if type(inventory) is not dict or set(inventory) != names:
        raise ValueError('Exact evidence inventory required')
    snapshot = {}
    total = 0
    for name in sorted(names):
        b = read_bounded(folder/name, MAX_BYTES if name=='input.json' else 8*1024*1024)
        total += len(b)
        if total > 32*1024*1024 or kernel.model.sha(b) != inventory[name]:
            raise ValueError('Changed or oversized evidence')
        snapshot[name] = b
    if any(snapshot['sources/'+n] != b for n, b in frozen.items()):
        raise ValueError('Evidence differs from independently reviewed sources')
    req = strict_json_loads(snapshot['request.json'])
    if type(req) is not dict or set(req) != {'format', 'tolerance'} or req['format'] != 'pcs-trace-envelope-request-v1':
        raise ValueError('Exact versioned replay request required')
    data, proposal = core.prepare(snapshot['input.json'], req['tolerance'])
    proof, _ = core.render(data, proposal)
    if snapshot['Replay.lean'] != proof:
        raise ValueError('Stored proof differs from receiving-side regeneration')
    # result.json is inventoried, but NEVER read for authorization or a verdict.
    result = kernel.replay(snapshot['input.json'], req['tolerance'], timeout=timeout)
    if out is not None and 'proof' in result:
        export(out, snapshot['input.json'], result)
    return result
