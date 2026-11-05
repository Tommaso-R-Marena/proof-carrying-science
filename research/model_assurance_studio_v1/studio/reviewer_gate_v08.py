"""Independent review of a proposed proof-gated model update.

This module does not generate or infer a policy. The reviewer supplies a pinned
policy through an *independently controlled* channel, including model byte
identities. This is a conditional research result, never a deployment approval.

The trusted computing base remains Python, the screened ONNX parser and exact
rational/float32 error checkers. Neither Lean kernel verification nor deployed
ONNX Runtime correspondence is claimed here.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from .relational_kernel import rational
from .verify_relational import strict_load, verify_with_policy, POLICY_SCHEMA
from .verify_update import verify_update_policy, UPDATE_POLICY_SCHEMA
from .fp32_lift_v07 import lift_update

SCHEMA = 'pcs-independent-model-update-review-policy-v0.8'
_KEYS = {'schema', 'old_model_sha256', 'new_model_sha256', 'input_box',
         'output_coefficients', 'baseline_upper_limit', 'drift_upper_limit',
         'required_updated_upper_limit', 'required_float32_upper_limit'}
_MAX_BYTES = 16384


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _valid_digest(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def verify(old: bytes, new: bytes, baseline_cert: dict, update_cert: dict,
           reviewer_policy: dict) -> dict:
    """Fail closed. Must be called with reviewer-controlled policy bytes.

    Returns statuses PROVED_CONDITIONALLY or OPEN, never SAFE. In particular,
    the runner cannot promote an uncompiled Lean file or an unrun ONNX Runtime
    comparison to success.
    """
    outcome = {'schema': 'pcs-independent-model-update-review-result-v0.8',
               'status': 'OPEN', 'lean_kernel_verification': 'NOT_ESTABLISHED',
               'onnx_runtime_equivalence': 'NOT_ESTABLISHED',
               'deployment_authorization': 'NOT_ESTABLISHED'}
    try:
        if not isinstance(old, bytes) or not isinstance(new, bytes):
            raise ValueError('model bytes required')
        if not isinstance(reviewer_policy, dict) or set(reviewer_policy) != _KEYS:
            raise ValueError('unknown reviewer policy fields')
        if reviewer_policy['schema'] != SCHEMA:
            raise ValueError('unknown reviewer policy version')
        if len(json.dumps(reviewer_policy, allow_nan=False)) > _MAX_BYTES:
            raise ValueError('reviewer policy too large')
        oldsha, newsha = reviewer_policy['old_model_sha256'], reviewer_policy['new_model_sha256']
        if not (_valid_digest(oldsha) and _valid_digest(newsha)):
            raise ValueError('invalid source identities')
        if _digest(old) != oldsha or _digest(new) != newsha:
            raise ValueError('reviewer-pinned model hash mismatch')
        box = reviewer_policy['input_box']
        coeffs = reviewer_policy['output_coefficients']
        if not isinstance(box, list) or not 1 <= len(box) <= 16:
            raise ValueError('invalid input box')
        if not isinstance(coeffs, list) or not 1 <= len(coeffs) <= 16:
            raise ValueError('invalid coefficients')
        if not any(rational(x) != 0 for x in coeffs):
            raise ValueError('zero relation')
        for pair in box:
            if not isinstance(pair, list) or len(pair) != 2 or rational(pair[0]) > rational(pair[1]):
                raise ValueError('invalid input bounds')
        baseline_bound = rational(reviewer_policy['baseline_upper_limit'])
        drift_bound = rational(reviewer_policy['drift_upper_limit'])
        exact_requirement = rational(reviewer_policy['required_updated_upper_limit'])
        float_requirement = rational(reviewer_policy['required_float32_upper_limit'])
        # Construction is based ONLY on the independently supplied policy, not
        # claims contained in the proposed certificate or user-facing browser.
        base_policy = {'schema': POLICY_SCHEMA, 'input_box': box,
                       'output_coefficients': coeffs, 'upper_limit': str(baseline_bound)}
        change_policy = {'schema': UPDATE_POLICY_SCHEMA, 'old_model_sha256': oldsha,
                         'new_model_sha256': newsha, 'input_box': box,
                         'output_coefficients': coeffs, 'upper_limit': str(drift_bound)}
        ok, reason = verify_with_policy(old, baseline_cert, base_policy)
        if not ok: raise ValueError('baseline proof rejected: ' + str(reason)[:150])
        ok, reason = verify_update_policy(old, new, update_cert, change_policy)
        if not ok: raise ValueError('update proof rejected: ' + str(reason)[:150])
        if baseline_bound + drift_bound > exact_requirement:
            raise ValueError('conditional exact-real model update limit exceeded')
        float_result = lift_update(old, new, baseline_cert, base_policy,
                                   update_cert, change_policy, str(float_requirement))
        if float_result.get('status') != 'PROVED_CONDITIONALLY':
            raise ValueError('conditional binary32 bound not established: ' + str(float_result.get('reason', 'insufficient margin'))[:100])
        return dict(outcome, status='PROVED_CONDITIONALLY',
                    old_model_sha256=oldsha, new_model_sha256=newsha,
                    reviewer_policy_sha256=_digest(json.dumps(reviewer_policy,
                                            sort_keys=True, separators=(',', ':'),
                                            allow_nan=False).encode('utf-8')),
                    ideal_real_new_upper_bound=str(baseline_bound + drift_bound),
                    required_exact_real_upper_bound=str(exact_requirement),
                    float32_bound=float_result['derived_float32_upper_bound'],
                    required_float32_upper_bound=str(float_requirement),
                    assumptions='screened ONNX exact-real model; float32 bound assumes finite correctly rounded operations, no FTZ/reassociation outside contract',
                    authority='EXPERIMENTAL_PYTHON_CHECK; no Lean or live runtime verification')
    except (KeyError, TypeError, ValueError, OverflowError, ArithmeticError, MemoryError) as exc:
        return dict(outcome, reason=type(exc).__name__ + ': ' + str(exc)[:180])


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description='Independent reviewer-controlled conditional model-update gate')
    p.add_argument('old_model')
    p.add_argument('new_model')
    p.add_argument('baseline_certificate')
    p.add_argument('update_certificate')
    p.add_argument('reviewer_policy')
    p.add_argument('--report')
    a = p.parse_args(argv)
    try:
        old = Path(a.old_model).read_bytes()
        new = Path(a.new_model).read_bytes()
        result = verify(old, new, strict_load(a.baseline_certificate),
                        strict_load(a.update_certificate), strict_load(a.reviewer_policy))
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        result = {'schema':'pcs-independent-model-update-review-result-v0.8',
                  'status':'OPEN','reason':type(exc).__name__,
                  'lean_kernel_verification':'NOT_ESTABLISHED',
                  'onnx_runtime_equivalence':'NOT_ESTABLISHED',
                  'deployment_authorization':'NOT_ESTABLISHED'}
    output = json.dumps(result, sort_keys=True, indent=2)
    if a.report: Path(a.report).write_text(output + '\n', encoding='utf-8')
    print(output)
    return 0 if result['status'] == 'PROVED_CONDITIONALLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
