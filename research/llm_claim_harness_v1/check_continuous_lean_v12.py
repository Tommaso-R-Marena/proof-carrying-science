"""Mandatory real Mathlib kernel check for PCS research v12.

Runs only in the dedicated hosted job with Lean 4.28 + pinned Mathlib cache.
Untrusted research inputs are static fixtures. No provider calls.
"""
from __future__ import annotations
from pathlib import Path
import sys

from .core import Source, canonical
from .ols_continuous_v12 import MathlibChecker, run_continuous, replay_continuous

HERE=Path(__file__).parent


def main() -> int:
    base=HERE/'fixtures'
    csv=Source.from_bytes((base/'ols_data.csv').read_bytes())
    manifest=(base/'ols_table_spec.json').read_bytes()
    note=Source.from_bytes((base/'ols_uncertainty_note_v11.txt').read_bytes())
    checker=MathlibChecker(timeout=500)
    report=run_continuous(csv,manifest,note,checker=checker,
                          expected_data_sha256=csv.digest,
                          expected_note_sha256=note.digest)
    if not report['kernel_checked'] or not report['metrics']['slope_tolerance_holds'] or not report['metrics']['intercept_tolerance_holds']:
        print('FAIL: v12 quantified continuous-real bound was not kernel-checked',file=sys.stderr)
        print(report.get('lean_diagnostic',report['formal_status']),file=sys.stderr)
        return 1
    if (report['scientific_status'] != 'NOT_ASSESSED' or
        report['ols_regression_semantics'] != 'SOURCE_GROUNDED_REAL_SLOPE_PROVED_INTERCEPT_PENDING' or
        'pcsV12RealSlope pcsV12DesignX' not in report['lean_source']):
        print('FAIL: scientific interpretation or OLS refinement inappropriately elevated',file=sys.stderr)
        return 1
    replay=replay_continuous(csv,manifest,note,canonical(report),checker=checker,
                              expected_data_sha256=csv.digest,expected_note_sha256=note.digest)
    if not replay['matched']:
        print('FAIL: v12 independent kernel replay',replay,file=sys.stderr)
        return 1
    # Negative control: forge a source-bound slope weight while leaving the
    # original CSV untouched. The kernel must reject this false byte-derived fact.
    code=report['lean_source']
    original='pcsV12DesignWeights = some ([((-3 : Rat) / (10 : Rat))'
    forged='pcsV12DesignWeights = some ([((-2 : Rat) / (10 : Rat))'
    if original not in code:
        print('FAIL: source-derived coefficient anchor not generated',file=sys.stderr)
        return 1
    reject=checker.check(code.replace(original,forged,1))
    if reject['status'] != 'KERNEL_REJECTED':
        print('FAIL: forged source coefficient was not rejected',reject['status'],file=sys.stderr)
        return 1
    # Negative control: a universal bound of ZERO for nonzero error must fail.
    old='pcsV12Error * (∑ i, |pcsV12SlopeWeights i|) <= pcsV12SlopeThreshold'
    forged='pcsV12Error * (∑ i, |pcsV12SlopeWeights i|) <= (0 : ℝ)'
    if old not in code:
        print('FAIL: universal tolerance target missing',file=sys.stderr)
        return 1
    reject2=checker.check(code.replace(old,forged,1))
    if reject2['status'] != 'KERNEL_REJECTED':
        print('FAIL: false zero uncertainty bound was accepted',reject2['status'],file=sys.stderr)
        return 1
    print('PASS: all-real affine bound and source-specific exact closed-form OLS slope theorem, Lean 4.28.0 + Mathlib')
    print('PASS: complete CSV/manifest/note math bound, fresh replay, two forged certificates rejected')
    print('LIMIT: intercept OLS refinement and scientific/semantic validity remain unproved')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
