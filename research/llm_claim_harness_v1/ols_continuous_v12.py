"""Research v12: quantified continuous-response OLS coefficient perturbation bounds.

Proves a universally quantified theorem in Mathlib (rather than merely checking
all 2^n corners): for *all real-valued independent response deviations* with
absolute size <= ε, a linear functional with fixed real weights changes by at
most ε times the sum of the absolute weights.

The same generated proof includes v11's original CSV and note byte-checking
obligations plus a Lean-computed rational design-weight equality check.  The
application to an OLS *coefficient* invokes its known affine formula; a generic
Lean proof identifying OLS with this functional is intentionally tracked as a
separate remaining obligation in v12 (no claims about model choice or science).

There is no API/network access and no change to PCS production authority.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from .core import Source, canonical, sha
from .csv_integrated_v8 import _rat, _check_pin
from .ols_uncertainty_v11 import _prepare, make_uncertainty_lean_source, UnsupportedUncertainty
from .replay_table import parse_receipt, _write_private_json
from .table_evidence import parse_table_rows, parse_table_spec
from .typed import unit_value

SCHEMA = 'pcs-ols-continuous-v12-research'
REPLAY_SCHEMA = 'pcs-ols-continuous-replay-v12-research'
AUTHORITY = 'EXPERIMENTAL_NOT_PCS_V06_AUTHORITY'

# This is fixed, developer-authored Lean, not model-written Lean. No `sorry`,
# axioms, native_decide or external tactics are admitted.
MATHLIB_THEOREM = r'''
-- General REAL theorem; no finite grid or corner completeness assumption.
-- No source byte may define the contents of this theorem.
private theorem pcs_v12_abs_weighted_sum
    {n : ℕ} (w d : Fin n → ℝ) (ε : ℝ)
    (hδ : ∀ i, |d i| ≤ ε) :
    |∑ i, w i * d i| ≤ ε * ∑ i, |w i| := by
  calc
    |∑ i, w i * d i| ≤ ∑ i, |w i * d i| := Finset.abs_sum_le_sum_abs _ _
    _ = ∑ i, |w i| * |d i| := by simp only [abs_mul]
    _ ≤ ∑ i, |w i| * ε := by
      apply Finset.sum_le_sum
      intro i hi
      exact mul_le_mul_of_nonneg_left (hδ i) (abs_nonneg _)
    _ = ε * ∑ i, |w i| := by
      rw [Finset.mul_sum]
      apply Finset.sum_congr rfl
      intro i hi
      exact mul_comm _ _

private theorem pcs_v12_affine_shift {n : ℕ} (w y d : Fin n → ℝ) :
    (∑ i, w i * (y i + d i)) - (∑ i, w i * y i)
        = ∑ i, w i * d i := by
  simp_rw [mul_add]
  rw [Finset.sum_add_distrib]
  ring

-- Holds for EVERY δ in the continuous real box, not merely its vertices.
-- The threshold is explicit, as is the assumption of fixed weights.
theorem pcs_v12_continuous_affine_bound {n : ℕ}
    (w y d : Fin n → ℝ) (ε threshold : ℝ)
    (hbox : ∀ i, |d i| ≤ ε)
    (hthreshold : ε * (∑ i, |w i|) ≤ threshold) :
    |(∑ i, w i * (y i + d i)) - (∑ i, w i * y i)| ≤ threshold := by
  rw [pcs_v12_affine_shift]
  exact (pcs_v12_abs_weighted_sum w d ε hbox).trans hthreshold
'''

MATHLIB_OLS_REFINEMENT = r'''
-- Standard fixed-design ordinary least squares coefficient, real-valued.
private noncomputable def pcsV12RealSlope {n : ℕ} (x y : Fin n → ℝ) : ℝ :=
  (((n : ℝ) * (∑ i, x i * y i)) - (∑ i, x i) * (∑ i, y i)) /
    ((n : ℝ) * (∑ i, x i * x i) - (∑ i, x i) ^ 2)

private noncomputable def pcsV12RealSlopeWeight {n : ℕ} (x : Fin n → ℝ) (i : Fin n) : ℝ :=
  (((n : ℝ) * x i) - (∑ j, x j)) /
    ((n : ℝ) * (∑ j, x j * x j) - (∑ j, x j) ^ 2)

-- Algebraic identity, even when denominator is 0. The scientific OLS
-- interpretation separately REQUIRES a nondegenerate fixed design.
private theorem pcs_v12_real_ols_slope_is_affine {n : ℕ} (x y : Fin n → ℝ) :
    pcsV12RealSlope x y = ∑ i, pcsV12RealSlopeWeight x i * y i := by
  classical
  simp only [pcsV12RealSlope, pcsV12RealSlopeWeight]
  let sx : ℝ := ∑ i, x i
  let den : ℝ := (n : ℝ) * (∑ i, x i * x i) - sx ^ 2
  change ((n : ℝ) * (∑ i, x i * y i) - sx * (∑ i, y i)) / den =
    ∑ i, (((n : ℝ) * x i - sx) / den) * y i
  have hnum : (n : ℝ) * (∑ i, x i * y i) - sx * (∑ i, y i) =
    ∑ i, ((n : ℝ) * x i - sx) * y i := by
    calc
      (n : ℝ) * (∑ i, x i * y i) - sx * (∑ i, y i)
          = (∑ i, (n : ℝ) * (x i * y i)) - ∑ i, sx * y i := by
              rw [Finset.mul_sum, Finset.mul_sum]
      _ = ∑ i, ((n : ℝ) * x i - sx) * y i := by
            rw [← Finset.sum_sub_distrib]
            apply Finset.sum_congr rfl
            intro i hi
            ring
  rw [hnum]
  simp only [div_eq_mul_inv]
  rw [Finset.sum_mul]
  apply Finset.sum_congr rfl
  intro i hi
  ring

-- Every REAL response perturbation, expressed in actual closed-form OLS slope.
private theorem pcs_v12_ols_slope_response_bound {n : ℕ}
    (x y d : Fin n → ℝ) (ε tolerance : ℝ)
    (hbox : ∀ i, |d i| ≤ ε)
    (hthreshold : ε * (∑ i, |pcsV12RealSlopeWeight x i|) ≤ tolerance) :
    |pcsV12RealSlope x (fun i => y i + d i) - pcsV12RealSlope x y| ≤ tolerance := by
  rw [pcs_v12_real_ols_slope_is_affine, pcs_v12_real_ols_slope_is_affine]
  exact pcs_v12_continuous_affine_bound
    (pcsV12RealSlopeWeight x) y d ε tolerance hbox hthreshold
'''


MATHLIB_INTERCEPT_REFINEMENT = r'''
-- Standard OLS intercept is also a fixed-design affine functional of responses.
private noncomputable def pcsV12RealIntercept {n : ℕ} (x y : Fin n → ℝ) : ℝ :=
  ((∑ i, y i) - pcsV12RealSlope x y * (∑ i, x i)) / (n : ℝ)

private noncomputable def pcsV12RealInterceptWeight {n : ℕ} (x : Fin n → ℝ) (i : Fin n) : ℝ :=
  (1 / (n : ℝ)) - ((∑ j, x j) / (n : ℝ)) * pcsV12RealSlopeWeight x i

private theorem pcs_v12_real_ols_intercept_is_affine {n : ℕ} (x y : Fin n → ℝ) :
    pcsV12RealIntercept x y = ∑ i, pcsV12RealInterceptWeight x i * y i := by
  classical
  simp only [pcsV12RealIntercept, pcsV12RealInterceptWeight]
  rw [pcs_v12_real_ols_slope_is_affine]
  let sx : ℝ := ∑ i, x i
  let slope : ℝ := ∑ i, pcsV12RealSlopeWeight x i * y i
  change ((∑ i, y i) - slope * sx) / (n : ℝ) =
    ∑ i, ((1 / (n : ℝ)) - (sx / (n : ℝ)) * pcsV12RealSlopeWeight x i) * y i
  calc
    ((∑ i, y i) - slope * sx) / (n : ℝ) =
        (∑ i, (1 / (n : ℝ)) * y i) -
        ∑ i, (sx / (n : ℝ)) * (pcsV12RealSlopeWeight x i * y i) := by
          rw [← Finset.mul_sum, ← Finset.mul_sum]
          dsimp [slope]
          ring
    _ = ∑ i, ((1 / (n : ℝ)) - (sx / (n : ℝ)) * pcsV12RealSlopeWeight x i) * y i := by
          rw [← Finset.sum_sub_distrib]
          apply Finset.sum_congr rfl
          intro i hi
          ring

private theorem pcs_v12_ols_intercept_response_bound {n : ℕ}
    (x y d : Fin n → ℝ) (ε tolerance : ℝ)
    (hbox : ∀ i, |d i| ≤ ε)
    (hthreshold : ε * (∑ i, |pcsV12RealInterceptWeight x i|) ≤ tolerance) :
    |pcsV12RealIntercept x (fun i => y i + d i) - pcsV12RealIntercept x y| ≤ tolerance := by
  rw [pcs_v12_real_ols_intercept_is_affine, pcs_v12_real_ols_intercept_is_affine]
  exact pcs_v12_continuous_affine_bound
    (pcsV12RealInterceptWeight x) y d ε tolerance hbox hthreshold
'''


# A proof generated for this specific source computes the weights inside Lean
# from the SAME decoded CSV as all the earlier OLS/units checks.
WEIGHT_RECONSTRUCTION = r'''
def pcsV12DesignWeights : Option (List Rat) := do
  let pts ← pcsOLSOriginalPairs
  let n : Rat := pts.length
  let sx := pts.foldl (fun acc p => acc + p.1) (0 : Rat)
  let sx2 := pts.foldl (fun acc p => acc + p.1 * p.1) (0 : Rat)
  let den := n * sx2 - sx * sx
  if den == (0 : Rat) then none
  else some (pts.map (fun p => (n * p.1 - sx) / den))
'''


def _weights(data: Source, manifest: bytes, note: Source):
    parsed, _, original, radii, corners, flags = _prepare(data, manifest, note)
    spec = parse_table_spec(manifest)
    rows = parse_table_rows(data, spec)
    fields = {c.name: (i, c.unit) for i,c in enumerate(spec.columns)}
    xi, xunit = fields[parsed.x]
    xscale, _ = unit_value(xunit)
    x = tuple(Fraction(row.cells[xi].value) * xscale for row in rows)
    n = len(x)
    sx = sum(x, Fraction(0))
    den = n * sum((v*v for v in x), Fraction(0)) - sx*sx
    if den <= 0:
        raise UnsupportedUncertainty('degenerate regression design')
    w = tuple((n*v-sx)/den for v in x)
    b = tuple(Fraction(1,n)-sx*ww/n for ww in w)
    err, slope_tol, int_tol = parsed.bounds
    if sum((abs(ww) for ww in w), Fraction(0))*err != radii[0] or sum((abs(ww) for ww in b), Fraction(0))*err != radii[1]:
        raise UnsupportedUncertainty('analytical radius disagreement')
    return parsed, w, b, (err, slope_tol, int_tol), radii


def make_continuous_mathlib_source(data: Source, manifest: bytes, note: Source) -> tuple[str, dict]:
    parsed, slope_w, int_w, limits, radii = _weights(data, manifest, note)
    old, old_metrics = make_uncertainty_lean_source(data, manifest, note)
    # All source-dependent Lean definitions + exact finite checks still run in
    # the SAME file as the quantified Mathlib theorem, not separate receipts.
    def rat_list(values):
        return '[' + ', '.join(_rat(q) for q in values) + ']'
    assert len(slope_w) == old_metrics['row_count']
    anchors = [
        WEIGHT_RECONSTRUCTION,
        f'example : pcsV12DesignWeights = some ({rat_list(slope_w)} : List Rat) := by decide +kernel',
    ]
    for i, weight in enumerate(slope_w):
        anchors.append(f'example : pcsV12DesignWeights.bind (fun ws => ws[{i}]?) = some {_rat(weight)} := by decide +kernel')
    n = len(slope_w)
    spec = parse_table_spec(manifest)
    rows = parse_table_rows(data, spec)
    columns = {c.name: (i, c.unit) for i, c in enumerate(spec.columns)}
    xi, xu = columns[parsed.x]
    yi, yu = columns[parsed.y]
    xs, _ = unit_value(xu)
    ys, _ = unit_value(yu)
    xvalues = tuple(Fraction(row.cells[xi].value) * xs for row in rows)
    yvalues = tuple(Fraction(row.cells[yi].value) * ys for row in rows)
    encoded_pairs = '[' + ', '.join('(' + _rat(x) + ', ' + _rat(y) + ')'
                                  for x, y in zip(xvalues, yvalues)) + ']'
    anchors.append(f'example : pcsOLSOriginalPairs = some ({encoded_pairs} : List (Rat × Rat)) := by decide +kernel')
    # The two coefficient weights are explicit Rational-to-Real casts, their
    # numerical identity linked above to CSV-derived Rat weights; intercept
    # weights are recomputed from the same accepted fixed predictor design.
    def real_rat(q: Fraction):
        return f'((({_rat(q)}) : Rat) : ℝ)'
    def function_term(weights):
        return 'fun i : Fin ' + str(n) + ' => ' + ' '.join(
            f'(if i.val = {j} then {real_rat(v)} else '
            for j, v in enumerate(weights)
        ) + '(0 : ℝ)' + ')' * len(weights)
    slope_fun = function_term(slope_w)
    int_fun = function_term(int_w)
    x_fun = function_term(xvalues)
    extra = [
        f'def pcsV12DesignX : Fin {n} → ℝ := {x_fun}',
        f'def pcsV12SlopeWeights : Fin {n} → ℝ := {slope_fun}',
        (f'example : (fun i : Fin {n} => pcsV12RealSlopeWeight pcsV12DesignX i) = '
         'pcsV12SlopeWeights := by\n'
         '  funext i\n'
         '  fin_cases i <;> norm_num [pcsV12RealSlopeWeight, pcsV12DesignX, '
         'pcsV12SlopeWeights, Fin.sum_univ_succ]'),
        f'def pcsV12InterceptWeights : Fin {n} → ℝ := {int_fun}',
        (f'example : (fun i : Fin {n} => pcsV12RealInterceptWeight pcsV12DesignX i) = '
         'pcsV12InterceptWeights := by\n'
         '  funext i\n'
         '  fin_cases i <;> norm_num [pcsV12RealInterceptWeight, pcsV12RealSlopeWeight, '
         'pcsV12DesignX, pcsV12InterceptWeights, Fin.sum_univ_succ]'),
        f'def pcsV12Error : ℝ := {real_rat(limits[0])}',
        f'def pcsV12SlopeThreshold : ℝ := {real_rat(limits[1])}',
        f'def pcsV12InterceptThreshold : ℝ := {real_rat(limits[2])}',
        'example : pcsV12Error * (∑ i, |pcsV12SlopeWeights i|) = '
        f'{real_rat(radii[0])} := by norm_num [pcsV12Error, pcsV12SlopeWeights, Fin.sum_univ_succ]',
        'example : pcsV12Error * (∑ i, |pcsV12InterceptWeights i|) = '
        f'{real_rat(radii[1])} := by norm_num [pcsV12Error, pcsV12InterceptWeights, Fin.sum_univ_succ]',
    ]
    for target, weights, tol, radius in [('Slope','SlopeWeights',limits[1],radii[0]),('Intercept','InterceptWeights',limits[2],radii[1])]:
        good = radius <= tol
        # We explicitly prove (or refute) the proposed continuous guarantee
        # based on the data-derived exact affine radius. A false threshold
        # never receives an unconditional true theorem.
        comparator = '<=' if good else '>'
        extra.append(
            f'example : pcsV12Error * (∑ i, |pcsV12{weights} i|) '
            f'{comparator} pcsV12{target}Threshold := by norm_num '
            f'[pcsV12Error, pcsV12{weights}, pcsV12{target}Threshold, Fin.sum_univ_succ]'
        )
        if good:
            extra.append(f'''example (y d : Fin {n} → ℝ)
    (hbox : ∀ i, |d i| ≤ pcsV12Error) :
    |(∑ i, pcsV12{weights} i * (y i + d i)) -
       (∑ i, pcsV12{weights} i * y i)| ≤ pcsV12{target}Threshold := by
  apply pcs_v12_continuous_affine_bound
  · exact hbox
  · norm_num [pcsV12Error, pcsV12{weights}, pcsV12{target}Threshold, Fin.sum_univ_succ]''')
    if radii[0] <= limits[1]:
        extra.append(
            f'example (y d : Fin {n} → ℝ) '
            '(hbox : ∀ i, |d i| ≤ pcsV12Error) :\n'
            '|pcsV12RealSlope pcsV12DesignX (fun i => y i + d i) - '
            'pcsV12RealSlope pcsV12DesignX y| ≤ pcsV12SlopeThreshold := by\n'
            '  apply pcs_v12_ols_slope_response_bound\n'
            '  · exact hbox\n'
            '  · norm_num [pcsV12Error, pcsV12DesignX, pcsV12RealSlopeWeight, '
            'pcsV12SlopeThreshold, Fin.sum_univ_succ]'
        )
    if radii[1] <= limits[2]:
        extra.append(
            f'example (y d : Fin {n} → ℝ) '
            '(hbox : ∀ i, |d i| ≤ pcsV12Error) :\n'
            '|pcsV12RealIntercept pcsV12DesignX (fun i => y i + d i) - '
            'pcsV12RealIntercept pcsV12DesignX y| ≤ pcsV12InterceptThreshold := by\n'
            '  apply pcs_v12_ols_intercept_response_bound\n'
            '  · exact hbox\n'
            '  · norm_num [pcsV12Error, pcsV12DesignX, pcsV12RealInterceptWeight, '
            'pcsV12RealSlopeWeight, pcsV12InterceptThreshold, Fin.sum_univ_succ]'
        )
    code = 'import Mathlib\n\n' + MATHLIB_THEOREM + '\n\n' + MATHLIB_OLS_REFINEMENT + '\n\n' + MATHLIB_INTERCEPT_REFINEMENT + '\n\n' + old + '\n\n' + '\n\n'.join(anchors+extra) + '\n'
    return code, {
        'row_count': n,
        'continuous_theorem': 'ALL_REAL_BOX_PERTURBATIONS_OF_SOURCE_DERIVED_AFFINE_FUNCTIONAL',
        'source_anchored_slope_weights': [str(v) for v in slope_w],
        'source_anchored_intercept_weights': [str(v) for v in int_w],
        'max_slope_shift_si': str(radii[0]),
        'max_intercept_shift_si': str(radii[1]),
        'slope_tolerance_holds': radii[0] <= limits[1],
        'intercept_tolerance_holds': radii[1] <= limits[2],
        'ols_to_affine_refinement_proved': None, # receive authority only after native kernel check
        'ols_slope_closed_form_identity_in_generated_lean': True,
        'ols_intercept_closed_form_identity_in_generated_lean': True,
        'source_anchored_real_slope_instantiation_in_generated_lean': True,
        'source_anchored_real_intercept_instantiation_in_generated_lean': True,
        'semantic_fidelity': 'NOT_ESTABLISHED',
        'scientific_status': 'NOT_ASSESSED',
    }


class MathlibChecker:
    """No model-provided commands. Require exact 4.28.0 and existing Lake config."""
    def __init__(self, *, repo: Path | None = None, timeout: int = 180):
        self.repo = Path(repo) if repo else Path(__file__).resolve().parents[2]
        self.timeout = timeout
        if not 1 <= timeout <= 900:
            raise ValueError('invalid time budget')

    def check(self, code: str) -> dict:
        result = {'kernel_checked': False, 'status': 'KERNEL_UNAVAILABLE',
                  'lean_source_sha256': sha(code.encode('utf-8')), 'lean_source': code}
        lean, lake = shutil.which('lean'), shutil.which('lake')
        if not lean or not lake:
            return result
        try:
            version = subprocess.run([lean,'--version'],capture_output=True,timeout=15,check=False,text=True)
            if version.returncode or not version.stdout.startswith('Lean (version 4.28.0'):
                result['status'] = 'UNPINNED_LEAN_VERSION';return result
            if not (self.repo/'lakefile.toml').is_file():
                result['status'] = 'MATHLIB_PROJECT_NOT_FOUND';return result
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',suffix='.lean', prefix='PCSResearchV12_', dir=self.repo,delete=False) as fp:
                path=Path(fp.name);fp.write(code)
            try:
                result['lean_version']=version.stdout.strip()
                proc=subprocess.run([lake,'env','lean',str(path)],cwd=self.repo,capture_output=True,timeout=self.timeout,check=False,text=True)
            finally:
                path.unlink(missing_ok=True)
            if proc.returncode == 0:
                result['kernel_checked'] = True;result['status']='CONTINUOUS_AFFINE_THEOREM_CHECKED'
            else:
                result['status']='KERNEL_REJECTED';result['lean_diagnostic']=(proc.stdout+'\n'+proc.stderr)[:2400]
        except (OSError, subprocess.TimeoutExpired) as exc:
            result['status']='KERNEL_INVOCATION_FAILED';result['lean_diagnostic']=str(exc)[:400]
        return result


def run_continuous(data: Source, manifest: bytes, note: Source, *, checker: MathlibChecker | None = None,
                   expected_data_sha256: str | None = None,
                   expected_manifest_sha256: str | None = None,
                   expected_note_sha256: str | None = None) -> dict:
    _check_pin(expected_data_sha256, data.digest, 'data')
    _check_pin(expected_manifest_sha256, sha(manifest), 'manifest')
    _check_pin(expected_note_sha256, note.digest, 'note')
    code, info = make_continuous_mathlib_source(data,manifest,note)
    checked = (checker or MathlibChecker()).check(code)
    verified = bool(checked['kernel_checked'])
    return {
        'schema_version':SCHEMA,'authority':AUTHORITY,'kernel_checked':verified,
        'formal_status':checked['status'],
        'data_sha256':data.digest,'manifest_sha256':sha(manifest),'note_sha256':note.digest,
        'expected_data_sha256':expected_data_sha256,
        'expected_manifest_sha256':expected_manifest_sha256,
        'expected_note_sha256':expected_note_sha256,
        'scope':'All real-valued response deviations within independent absolute box bounds; quantified affine linear functional theorem, exact rational source weight anchors; OLS affine refinement and semantic/scientific adequacy not yet proved.',
        'continuous_affine_certificate':'KERNEL_CHECKED' if verified else 'UNVERIFIED',
        'ols_regression_semantics':'SOURCE_GROUNDED_REAL_SLOPE_AND_INTERCEPT_PROVED' if verified else 'NOT_FORMALLY_REFINED',
        'ols_slope_identity_kernel_checked':verified,
        'ols_intercept_identity_kernel_checked':verified,
        'source_specific_ols_coefficients_kernel_checked':verified,
        'scientific_status':'NOT_ASSESSED',
        'metrics':info,
        **{k:v for k,v in checked.items() if k not in {'kernel_checked','status'}},
    }


def replay_continuous(data: Source, manifest: bytes, note: Source, receipt: bytes,
                      *, checker: MathlibChecker | None = None,
                      expected_data_sha256: str | None = None,
                      expected_manifest_sha256: str | None = None,
                      expected_note_sha256: str | None = None) -> dict:
    incoming=parse_receipt(receipt)
    output={'schema_version':REPLAY_SCHEMA,'receipt_sha256':sha(receipt),
            'status':'RECEIPT_REJECTED','matched':False,'scientific_status':'NOT_ASSESSED'}
    if (incoming.get('schema_version') != SCHEMA or incoming.get('authority') != AUTHORITY or
        incoming.get('data_sha256') != data.digest or incoming.get('manifest_sha256') != sha(manifest) or
        incoming.get('note_sha256') != note.digest or
        incoming.get('expected_data_sha256') != expected_data_sha256 or
        incoming.get('expected_manifest_sha256') != expected_manifest_sha256 or
        incoming.get('expected_note_sha256') != expected_note_sha256):
        return output
    new=run_continuous(data,manifest,note,checker=checker,
                       expected_data_sha256=expected_data_sha256,
                       expected_manifest_sha256=expected_manifest_sha256,
                       expected_note_sha256=expected_note_sha256)
    if not new['kernel_checked']:
        output['status']='KERNEL_UNAVAILABLE_OR_REJECTED'
    elif canonical(new) == canonical(incoming):
        output.update(status='REPLAYED_CONTINUOUS_AFFINE',matched=True)
    return output


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description='PCS research v12 continuous affine response uncertainty')
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--table-spec',type=Path,required=True)
    p.add_argument('--uncertainty-note',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--expected-data-sha256')
    p.add_argument('--expected-manifest-sha256')
    p.add_argument('--expected-note-sha256')
    p.add_argument('--receipt',type=Path)
    p.add_argument('--timeout',type=int,default=180)
    a=p.parse_args(argv)
    try:
        data=Source.from_bytes(a.source.read_bytes());manifest=a.table_spec.read_bytes()
        note=Source.from_bytes(a.uncertainty_note.read_bytes())
        checker=MathlibChecker(timeout=a.timeout)
        kwargs=dict(checker=checker,expected_data_sha256=a.expected_data_sha256,
                    expected_manifest_sha256=a.expected_manifest_sha256,
                    expected_note_sha256=a.expected_note_sha256)
        if a.receipt:
            result=replay_continuous(data,manifest,note,a.receipt.read_bytes(),**kwargs)
            success=result['matched']
        else:
            result=run_continuous(data,manifest,note,**kwargs)
            success=result['kernel_checked']
        _write_private_json(a.out,result)
        print('v12 research:',result.get('formal_status',result.get('status')))
        return 0 if success else 2
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print('v12 rejected:',str(exc),file=sys.stderr);return 1


if __name__ == '__main__':
    raise SystemExit(main())
