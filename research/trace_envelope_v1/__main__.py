"""Bound imported traces against their declared discrete model using actual Lean."""
import argparse
import json
from pathlib import Path

from research.flux_detective_v1.check import MAX_BYTES
from . import core, evidence, kernel


def main():
    p = argparse.ArgumentParser(__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    for name in ['analyze', 'check']:
        q = sub.add_parser(name, help='Diagnostic proposal only' if name=='analyze' else 'Run actual Lean and save fresh evidence')
        q.add_argument('input', type=Path)
        if name=='check': q.add_argument('out', type=Path)
        q.add_argument('--tolerance', required=True, help='Nonnegative exact rational bound on every recorded state error')
    q = sub.add_parser('verify', help='Regenerate from captured evidence and reexecute actual Lean')
    q.add_argument('evidence', type=Path)
    q.add_argument('out', type=Path, help='Fresh independent evidence directory')
    q = sub.add_parser('audit', help='Fresh general proof build, axiom inventory and same-kernel object replay')
    q.add_argument('out', type=Path)
    args = p.parse_args()
    try:
        if hasattr(args, 'out') and args.out.exists():
            raise ValueError('Fresh output directory required; historical evidence is never overwritten')
        if args.action=='audit':
            r = kernel.audit(args.out)
        elif args.action=='analyze':
            _, r = core.prepare(evidence.read_bounded(args.input, MAX_BYTES), args.tolerance)
            r.update(status='DIAGNOSTIC_ONLY', note='No Lean verdict. Budget excess does not prove actual error exceeds tolerance.')
        else:
            if args.action=='check':
                raw = evidence.read_bounded(args.input, MAX_BYTES)
                r = kernel.replay(raw, args.tolerance)
            else:
                # Verification captures all bytes before execution. Export the same
                # captured original input, not a newly opened mutable input path.
                r = evidence.verify(args.evidence, out=args.out)
            if args.action=='check' and 'proof' in r:
                evidence.export(args.out, raw, r)
        print(json.dumps({k: v for k,v in r.items() if k not in {'executions','proof','trace_certificate','axiom_closures'}}))
        if args.action=='analyze': return 0
        if not r['kernel_checked']: return 20
        return 10 if r.get('status')=='ENVELOPE_BUDGET_EXCEEDS_TOLERANCE' else 0
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError) as e:
        print(json.dumps(dict(status='REFUSED', error=str(e), kernel_checked=False, pcs_authority=False, scientific_acceptance=False)))
        return 20


if __name__=='__main__': raise SystemExit(main())
