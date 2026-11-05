"""Deterministic synthetic falsification, including tightness and conservative refusals.

Reference traces come from the inherited independent edge-flux implementation.
No population, physical, learning or educational validity is asserted.
"""
from __future__ import annotations

import argparse
import csv
from fractions import Fraction as F
import io
import json
from pathlib import Path
import subprocess
import time

from pcs.transport_kernel_v1 import sha
from research.portable_transport_v2.campaign import generated
from .core import prepare

ROOT = Path(__file__).resolve().parents[2]


def quantize(x: F, digits: int) -> F:
    """Round nearest with ties to even using exact integer operations."""
    scale = 10**digits
    q, r = divmod(x.numerator*scale, x.denominator)
    if 2*r > x.denominator or (2*r == x.denominator and q % 2):
        q += 1
    return F(q, scale)


def case(width=2, steps=4, seed=0, mode='drift', digits=2):
    contract_raw, csv_raw = generated(width, steps, seed)
    contract = json.loads(contract_raw)
    rows = list(csv.reader(io.StringIO(csv_raw.decode())))
    exact = [list(map(F, row[1:])) for row in rows[1:]]
    unit = F(1, 10**digits)
    if mode=='drift':
        states = [[x+k*unit for x in row] for k, row in enumerate(exact)]
    elif mode=='cancel':
        states = [[x+(-1)**k*unit for x in row] for k, row in enumerate(exact)]
    elif mode=='round_each':
        states = [[quantize(x, digits) for x in row] for row in exact]
    elif mode=='round_loop':
        volumes = [F(c['volume']) for c in contract['cells']]
        dt = F(contract['time_step'])
        current = [quantize(x, digits) for x in exact[0]]
        states = [current]
        for _ in range(steps):
            amounts = [v*x for v,x in zip(volumes, current)]
            # Independent edge-flux update; no matrix proposer is used.
            for i in range(width-1):
                transfer = dt*F(1,8)*(current[i]-current[i+1])
                amounts[i] -= transfer
                amounts[i+1] += transfer
            current = [quantize(a/v, digits) for a,v in zip(amounts,volumes)]
            states.append(current)
    elif mode=='exact':
        states = exact
    else:
        raise ValueError('Known experiment mode required')
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(rows[0])
    for k, row in enumerate(states):
        writer.writerow([rows[k+1][0], *map(str,row)])
    raw = json.dumps(dict(format='pcs-flux-detective-export-v1', seed=seed,
                          level=0, choice=0, contract=contract, trajectory=stream.getvalue()),
                     sort_keys=True, separators=(',',':')).encode()
    errors = [max(abs(a-b) for a,b in zip(row, ref)) for row,ref in zip(states,exact)]
    return raw, errors


def run():
    started = time.monotonic()
    results = []
    for width in [2,3,5,8]:
        for steps in [1,4,16]:
            for seed in [0,1,20261022]:
                for digits in [2,4,8]:
                    for mode in ['drift','cancel','round_each','round_loop']:
                        raw, errors = case(width, steps, seed, mode, digits)
                        data, proposal = prepare(raw, str(F(1,10**digits)))
                        budgets = list(map(F, proposal['budgets']))
                        if not all(e<=b for e,b in zip(errors,budgets)):
                            raise AssertionError('Counterexample to the claimed envelope')
                        if mode=='drift' and errors != budgets:
                            raise AssertionError('Coherent drift must saturate the bound')
                        tol = F(proposal['tolerance'])
                        results.append(dict(width=width,steps=steps,seed=seed,digits=digits,mode=mode,
                                            input_sha256=sha(raw), final_budget=str(budgets[-1]),
                                            max_actual_error=str(max(errors)), errors=list(map(str,errors)),
                                            budgets=proposal['budgets'],
                                            budget_met=proposal['tolerance_budget_met'],
                                            actual_within=max(errors)<=tol,
                                            kernel_checked=False))
    return dict(format='pcs-trace-envelope-experiment-v1',
                head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                samples=len(results), seeds=[0,1,20261022], results=results,
                envelope_violations=0,
                conservative_budget_refusals=sum(r['actual_within'] and not r['budget_met'] for r in results),
                budgets_met=sum(r['budget_met'] for r in results),
                actual_within=sum(r['actual_within'] for r in results),
                tight_drift_cases=sum(r['mode']=='drift' for r in results),
                kernel_checked=False, pcs_authority=False, empirical_validation=False,
                synthetic_fixtures_are_not_population_samples=True,
                source_sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in
                    [Path(__file__),Path(__file__).with_name('core.py'),ROOT/'research/portable_transport_v2/campaign.py']},
                wall_seconds=round(time.monotonic()-started,6))


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    r=run();(args.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    (args.out/'REPORT.md').write_text(f'''# Synthetic finite-trace envelope experiment

{r['samples']} deterministic constructed cases; no envelope violations against an
independent edge-flux oracle. {r['tight_drift_cases']} coherent-drift cases saturate
the bound. {r['conservative_budget_refusals']} cases exceed the cumulative budget
despite actual error remaining within tolerance. Budget acceptance:
{r['budgets_met']}; actual within tolerance: {r['actual_within']}.

These are reproducible rational rounding/perturbation experiments, not physical,
population or human-learning evidence. Individual cases in this experiment are
not kernel checked; the separate real-Lean tests check selected instances.
''')
    print(json.dumps({k:v for k,v in r.items() if k not in {'results','source_sha256'}}))


if __name__=='__main__': main()
