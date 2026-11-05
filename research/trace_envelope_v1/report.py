"""Human-readable evidence summary with the same explicit claim limits."""


def render(result):
    p=result['proposal']
    verdict='Lean checked these finite-model bounds.' if result['kernel_checked'] else 'No affirmative Lean verdict: this is a refused proposal.'
    interpretation=('Every recorded coordinate is within the requested tolerance of the declared exact discrete recurrence.'
                    if result['kernel_checked'] and p['tolerance_budget_met'] else
                    'The cumulative budget exceeds tolerance. This does not prove that actual error exceeds tolerance.'
                    if result['kernel_checked'] else 'Do not use the proposed bounds as a certificate.')
    rows='\n'.join(f'| {k} | {e} | {b} |' for k,(e,b) in enumerate(zip([p['eta'],*p['eps']],p['budgets'])))
    return f'''# Finite-trace error envelope

Status: **{result['status']}**. {verdict}

{interpretation}

Requested tolerance: `{p['tolerance']}`. Final cumulative radius: `{p['budgets'][-1]}`.
Units are those of the declared concentration. Exact timestamps are required.

| Recorded step | Initial/local residual bound | Cumulative radius |
| --- | --- | --- |
{rows}

Captured original input SHA256: `{result['input_sha256']}`.
Generated proof SHA256: `{result['proof_sha256']}`.

Independent replay from a separately reviewed checkout:

```sh
python -m research.trace_envelope_v1 verify ./envelope-evidence ./independent-evidence
```

Stored reports and hashes are evidence conveniences, not signed receipts or verifier
verdicts. Replay regenerates the proof and executes actual Lean. The original exact
checker is unchanged. This result does not establish conservation of the approximate
trace, continuum/physical accuracy, implementation or byte-decoder refinement, or
empirical validity, and grants no PCS production authority. The host, compiler and
imported objects remain trusted; binary pins do not establish an immutable root.
'''
