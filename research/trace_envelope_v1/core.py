"""Untrusted exact-rational proposals for Lean-checked finite error envelopes."""
from __future__ import annotations

from fractions import Fraction as F
import csv
import io
import re

from pcs import transport_trace_kernel_v1 as trace
from pcs.jsonio import strict_json_loads
from pcs.scientific_contracts_v1 import _bounded, rational
from research.flux_detective_v1.check import capture

MAX_CELLS = 8
MAX_STEPS = 16


def _guard_exponent(text):
    # Before Fraction can allocate enormous powers for a short exponent token.
    # Only numeric scalars are checked; identifiers/header text are not interpreted.
    if type(text) is not str:
        return
    match = re.fullmatch(r'-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)[eE]([+-]?[0-9]+)', text)
    if match and (len(match[1].lstrip('+-')) > 3 or abs(int(match[1])) > 512):
        raise ValueError('Envelope numeric exponent must be within [-512,512]')


def _preflight(raw):
    from research.flux_detective_v1.check import MAX_BYTES
    if type(raw) is not bytes or len(raw)>MAX_BYTES:
        raise ValueError('Bounded immutable input bytes required')
    value = strict_json_loads(raw.decode('utf-8'))
    if type(value) is not dict:
        return
    contract = value.get('contract')
    if type(contract) is dict:
        _guard_exponent(contract.get('time_step'))
        for group, fields in [('cells', ['volume','initial_concentration']),('edges',['conductance'])]:
            if type(contract.get(group)) is list:
                for item in contract[group]:
                    if type(item) is dict:
                        for field in fields: _guard_exponent(item.get(field))
    if type(value.get('trajectory')) is str:
        try:
            rows = csv.reader(io.StringIO(value['trajectory'], newline=''))
            next(rows,None)
            for row in rows:
                for item in row: _guard_exponent(item)
        except csv.Error as error:
            raise ValueError('Bounded CSV input required') from error


def prepare(raw: bytes, tolerance: str) -> tuple[dict, dict]:
    """Capture the unchanged receiver's interpretation; never a verifier verdict."""
    if type(tolerance) is not str or len(tolerance) > 1024:
        raise ValueError('Bounded rational tolerance text required')
    _guard_exponent(tolerance)
    _preflight(raw)
    tol = rational(tolerance, 'tolerance')
    if tol < 0:
        raise ValueError('Nonnegative tolerance required')
    contract, csv = capture(raw)
    data = trace.prepare(contract, csv)
    if len(data['model']['initial']) > MAX_CELLS or data['steps'] > MAX_STEPS:
        raise ValueError('Envelope replay supports at most 8 cells and 16 steps')
    if any(F(t) != k * F(data['dt']) for k, t in enumerate(data['times'])):
        raise ValueError('Exact declared timestamps required; residuals bound states only')
    return data, propose(data, str(tol))


def propose(data: dict, tolerance: str) -> dict:
    """Each row maximum is exact; cumulative bounds can be conservative."""
    trace.validate(data)
    matrix = [[F(x) for x in row] for row in data['model']['matrix']]
    initial = list(map(F, data['model']['initial']))
    states = [list(map(F, row)) for row in data['states']]
    residuals = [[_bounded(x - y) for x, y in zip(states[0], initial)]]
    for a, b in zip(states, states[1:]):
        expected = [_bounded(sum((_bounded(p*x) for p, x in zip(row, a)), F())) for row in matrix]
        residuals.append([_bounded(x - y) for x, y in zip(b, expected)])
    local = [max(map(abs, row)) for row in residuals]
    budgets = [local[0]]
    for e in local[1:]:
        budgets.append(_bounded(budgets[-1] + e))
    tol = rational(tolerance, 'tolerance')
    if tol < 0:
        raise ValueError('Nonnegative tolerance required')
    return dict(format='pcs-trace-envelope-proposal-v1',
                eta=str(local[0]), eps=list(map(str, local[1:])), budgets=list(map(str, budgets)),
                residuals=[[str(x) for x in row] for row in residuals],
                tolerance=str(tol), tolerance_budget_met=budgets[-1] <= tol,
                signed_residual_details_kernel_checked=False,
                kernel_checked=False, pcs_authority=False, empirical_validation=False)


def render(data: dict, proposal: dict) -> tuple[bytes, list[str]]:
    """Only typed bounded rational/natural literals enter generated proof syntax."""
    from pcs import transport_kernel_v1 as model
    trace.validate(data)
    # Exact receiving-side regeneration; no caller-controlled claims or Lean code.
    if proposal != propose(data, proposal.get('tolerance')):
        raise ValueError('Exact regenerated envelope proposal required')
    n, steps = len(data['model']['initial']), data['steps']
    lit = model._literal
    vector = lambda xs: '[' + ', '.join(map(lit, xs)) + ']'
    original = trace.render(data, negative=True).decode()
    original = original[:original.index('theorem trace_rejected :')]
    original += 'end PCSTransportTraceReplay\n'
    text = 'import Envelope\nimport RawDecide\n' + original.replace('by decide +kernel', 'by pcs_kernel_decide_raw')
    text += f'''
namespace PCSEnvelopeReplay
open PCSReal.Transport PCSTransportReplay PCSTransportTraceReplay PCSTraceEnvelope
def eta : ℚ := {lit(proposal['eta'])}
def eps (k : Nat) : ℚ := ({vector(proposal['eps'])} : List ℚ).getD k 0
def budgets (k : Nat) : ℚ := ({vector(proposal['budgets'])} : List ℚ).getD k 0
def tolerance : ℚ := {lit(proposal['tolerance'])}
theorem initial_budget : Within (states 0) initial eta := by pcs_kernel_decide_raw
'''
    names = ['initial_budget']
    def cases(names):
        term = 'fun impossible => Fin.elim0 impossible'
        for name in reversed(names):
            term = f'Fin.cases {name} ({term})'
        return term
    locals_ = []
    for k in range(steps):
        name = f'local_{k}'
        text += (f'theorem {name} : 0 ≤ eps {k} ∧ Within (states {k+1}) '
                 f'(step matrix (states {k})) (eps {k}) := by pcs_kernel_decide_raw\n')
        locals_.append(name)
    names += locals_
    text += f'''theorem local_rows : ∀ k : Fin {steps}, 0 ≤ eps k.val ∧
    Within (states (k.val + 1)) (step matrix (states k.val)) (eps k.val) := by
  exact {cases(locals_)}
theorem times_exact : ∀ k : Fin {steps+1}, times k.val = (k.val : ℚ) * dt := by pcs_kernel_decide_raw
theorem envelope_checked : PCSTraceEnvelope.check matrix initial states times dt eta eps {steps} = true := by
  simp only [PCSTraceEnvelope.check, decide_eq_true_eq]
  exact ⟨by pcs_kernel_decide_raw, initial_budget, local_rows, times_exact⟩
theorem envelope_sound :
    (∀ k, k ≤ {steps} → Within (states k) (evolve matrix initial k) (radius eta eps k)) ∧
    (∀ k, k ≤ {steps} → times k = (k : ℚ) * dt) :=
  PCSTraceEnvelope.check_sound (PCSReal.Transport.check_sound matrix_checked) envelope_checked
'''
    names += ['local_rows', 'times_exact', 'envelope_checked', 'envelope_sound']
    bounds = []
    for k in range(steps+1):
        name = f'radius_{k}'
        text += f'theorem {name} : radius eta eps {k} = budgets {k} := by pcs_kernel_decide_raw\n'
        bounds.append(name)
    names += bounds
    text += f'''theorem bound_values : ∀ k : Fin {steps+1}, radius eta eps k.val = budgets k.val := by
  exact {cases(bounds)}
theorem recorded_bounds (k : Nat) (hk : k ≤ {steps}) :
    Within (states k) (evolve matrix initial k) (budgets k) := by
  rw [← bound_values ⟨k, Nat.lt_succ_of_le hk⟩]
  exact envelope_sound.1 k hk
theorem recorded_real_bounds (k : Nat) (hk : k ≤ {steps}) :
    Within (fun i => (states k i : ℝ))
      (evolve (fun i j => (matrix i j : ℝ)) (fun i => (initial i : ℝ)) k) (budgets k : ℝ) :=
  PCSTraceEnvelope.real_bound (recorded_bounds k hk)
'''
    names += ['bound_values', 'recorded_bounds', 'recorded_real_bounds']
    if proposal['tolerance_budget_met']:
        text += f'''theorem tolerance_met : radius eta eps {steps} ≤ tolerance := by pcs_kernel_decide_raw
theorem uniform_bound (k : Nat) (hk : k ≤ {steps}) :
    Within (states k) (evolve matrix initial k) tolerance :=
  PCSTraceEnvelope.check_uniform (PCSReal.Transport.check_sound matrix_checked) envelope_checked tolerance_met k hk
'''
        names += ['tolerance_met', 'uniform_bound']
    else:
        text += f'theorem budget_exceeds : tolerance < radius eta eps {steps} := by pcs_kernel_decide_raw\n'
        names += ['budget_exceeds']
    text += 'end PCSEnvelopeReplay\n'
    names = ['PCSEnvelopeReplay.'+n for n in names]
    text += '\n'.join('#print axioms '+name for name in names)+'\n'
    return text.encode(), model.REPLAY_THEOREMS + names
