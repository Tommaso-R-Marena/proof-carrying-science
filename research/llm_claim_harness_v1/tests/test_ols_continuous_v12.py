"""Research-only v12 conservative tests; never substitute Mock for real Lean CI."""
from __future__ import annotations
from fractions import Fraction
from pathlib import Path
import itertools
import random
import unittest

from research.llm_claim_harness_v1.core import Source, canonical, sha
from research.llm_claim_harness_v1.ols_continuous_v12 import (
    _weights, make_continuous_mathlib_source, run_continuous, replay_continuous,
    MATHLIB_THEOREM, MathlibChecker,
)
from research.llm_claim_harness_v1.ols_uncertainty_v11 import UnsupportedUncertainty

FIX = Path(__file__).parents[1] / 'fixtures'
DATA = (FIX / 'ols_data.csv').read_bytes()
MANIFEST = (FIX / 'ols_table_spec.json').read_bytes()
NOTE = (FIX / 'ols_uncertainty_note_v11.txt').read_bytes()


def inputs(note=NOTE,data=DATA,manifest=MANIFEST):
    return Source.from_bytes(data),manifest,Source.from_bytes(note)


class MockMathlib:
    def __init__(self,ok=True): self.ok=ok;self.calls=[]
    def check(self,code):
        self.calls.append(code)
        return {'kernel_checked':self.ok,
                'status':'MOCK_ONLY_CHECKED' if self.ok else 'KERNEL_UNAVAILABLE',
                'lean_source':code,'lean_source_sha256':sha(code.encode())}


class Tests(unittest.TestCase):
    def test_source_anchored_exact_coefficients(self):
        code,inf=make_continuous_mathlib_source(*inputs())
        self.assertEqual(inf['row_count'],4)
        self.assertEqual(inf['source_anchored_slope_weights'],['-3/10','-1/10','1/10','3/10'])
        self.assertEqual(inf['source_anchored_intercept_weights'],['7/10','2/5','1/10','-1/5'])
        self.assertEqual(inf['max_slope_shift_si'],'2/25')
        self.assertEqual(inf['max_intercept_shift_si'],'7/50')
        self.assertTrue(inf['slope_tolerance_holds'])
        self.assertTrue(inf['intercept_tolerance_holds'])
        for token in ['import Mathlib','pcs_v12_continuous_affine_bound','(hbox : ∀ i, |d i| ≤ pcsV12Error)',
                      'pcsV12DesignWeights = some', 'pcsOLSRawCSV','pcsOLSUncertaintyRawNote',
                      'pcsOLSRobustFlags.map List.length = some 16']:
            self.assertIn(token,code)
        self.assertIn('pcs_v12_real_ols_slope_is_affine',code)
        self.assertIn('pcs_v12_ols_slope_response_bound',code)
        self.assertIn('pcsOLSOriginalPairs = some',code)
        self.assertIn('pcsV12RealSlope pcsV12DesignX',code)
        self.assertIn('pcsV12RealSlopeWeight pcsV12DesignX',code)

    def test_generic_theorem_free_of_untrusted_axioms(self):
        for token in ['sorry','native_decide','axiom ', 'unsafe def', 'admit', 'False.elim']:
            self.assertNotIn(token,MATHLIB_THEOREM)

    def test_source_and_note_are_pinned(self):
        a,b,c=inputs()
        with self.assertRaises(ValueError):
            run_continuous(a,b,c,checker=MockMathlib(),expected_data_sha256='a'*64)
        with self.assertRaises(ValueError):
            run_continuous(a,b,c,checker=MockMathlib(),expected_manifest_sha256='b'*64)
        with self.assertRaises(ValueError):
            run_continuous(a,b,c,checker=MockMathlib(),expected_note_sha256='c'*64)

    def test_missing_lean_fails_closed(self):
        result=run_continuous(*inputs(),checker=MockMathlib(False))
        self.assertFalse(result['kernel_checked'])
        self.assertEqual(result['continuous_affine_certificate'],'UNVERIFIED')
        self.assertEqual(result['scientific_status'],'NOT_ASSESSED')

    def test_mock_is_not_scientific_certification(self):
        result=run_continuous(*inputs(),checker=MockMathlib(True))
        self.assertEqual(result['scientific_status'],'NOT_ASSESSED')
        self.assertEqual(result['ols_regression_semantics'],'SOURCE_GROUNDED_REAL_SLOPE_PROVED_INTERCEPT_PENDING')
        self.assertFalse(result['metrics']['ols_to_affine_refinement_proved'])

    def test_note_adjusted_slope_tight(self):
        bad=NOTE.replace(b'max_slope_shift_si=0.08',b'max_slope_shift_si=0.07')
        _,m=make_continuous_mathlib_source(*inputs(note=bad))
        self.assertFalse(m['slope_tolerance_holds'])
        self.assertTrue(m['intercept_tolerance_holds'])
        code,_=make_continuous_mathlib_source(*inputs(note=bad))
        self.assertIn('> pcsV12SlopeThreshold',code)
        self.assertNotIn('≤ pcsV12SlopeThreshold := by\n  apply pcs_v12_continuous_affine_bound',code)

    def test_note_adjusted_intercept_tight(self):
        bad=NOTE.replace(b'max_intercept_shift_si=0.14',b'max_intercept_shift_si=0.13')
        _,m=make_continuous_mathlib_source(*inputs(note=bad))
        self.assertTrue(m['slope_tolerance_holds'])
        self.assertFalse(m['intercept_tolerance_holds'])

    def test_tamper_source_fails(self):
        data=DATA.replace(b'300,7',b'300,8')
        with self.assertRaises((ValueError,UnsupportedUncertainty)):
            make_continuous_mathlib_source(*inputs(data=data))

    def test_tamper_manifest_fails(self):
        man=MANIFEST.replace(b'x_cm',b'xxx')
        with self.assertRaises((ValueError,UnsupportedUncertainty)):
            make_continuous_mathlib_source(*inputs(manifest=man))

    def test_injected_lean_cannot_enter_note(self):
        note=NOTE.replace(b'0.10',b'0.10\naxiom falseProven : False')
        with self.assertRaises((ValueError,UnsupportedUncertainty)):
            make_continuous_mathlib_source(*inputs(note=note))

    def test_bad_header_fails(self):
        note=NOTE.replace(b'PCS-OLS-UNCERTAINTY/1',b'PCS-OLS-UNCERTAINTY/2')
        with self.assertRaises((ValueError,UnsupportedUncertainty)):
            make_continuous_mathlib_source(*inputs(note=note))

    def test_nonzero_box_all_real_is_stronger_than_corners(self):
        # Independent Python diagnostic: enumerate arbitrary RATIONAL interior
        # errors; the Lean theorem quantifies over every REAL error, separately.
        _,w,b,lims,radii=_weights(*inputs())
        random.seed(42)
        points=[Fraction(random.randint(-1000,1000),10000) for _ in range(600)]
        for k in range(0,len(points),4):
            d=[max(-lims[0],min(lims[0],v)) for v in points[k:k+4]]
            self.assertLessEqual(abs(sum((a*x for a,x in zip(w,d)),Fraction(0))),radii[0])
            self.assertLessEqual(abs(sum((a*x for a,x in zip(b,d)),Fraction(0))),radii[1])

    def test_all_16_extreme_combinations_tight(self):
        _,w,b,lims,radii=_weights(*inputs())
        vals=[]
        for signs in itertools.product((-1,1),repeat=4):
            delta=[lims[0]*s for s in signs]
            vals.append((abs(sum((a*x for a,x in zip(w,delta)),Fraction())),
                         abs(sum((a*x for a,x in zip(b,delta)),Fraction()))))
        self.assertEqual(max(x for x,y in vals),radii[0])
        self.assertEqual(max(y for x,y in vals),radii[1])

    def test_replay_missing_checker_refuses(self):
        result=run_continuous(*inputs(),checker=MockMathlib(True))
        replay=replay_continuous(*inputs(),canonical(result),checker=MockMathlib(False))
        self.assertFalse(replay['matched'])
        self.assertEqual(replay['status'],'KERNEL_UNAVAILABLE_OR_REJECTED')

    def test_replay_rejects_modified_receipt(self):
        result=run_continuous(*inputs(),checker=MockMathlib(True))
        result['metrics']['max_slope_shift_si']='0'
        replay=replay_continuous(*inputs(),canonical(result),checker=MockMathlib(True))
        self.assertFalse(replay['matched'])

    def test_replay_rejects_other_input(self):
        result=run_continuous(*inputs(),checker=MockMathlib(True))
        bad=NOTE.replace(b'0.10',b'0.11')
        replay=replay_continuous(*inputs(note=bad),canonical(result),checker=MockMathlib(True))
        self.assertFalse(replay['matched'])

    def test_v12_no_real_lean_available(self):
        # If Lean is missing, no amount of Python parsing can promote a proof.
        check=MathlibChecker(repo=FIX)
        self.assertIn(check.check('bad')['status'], {'KERNEL_UNAVAILABLE','MATHLIB_PROJECT_NOT_FOUND','UNPINNED_LEAN_VERSION'})


if __name__=='__main__':
    unittest.main()
