"""Exact calibration and v25 gate tests; no external randomness or physical custody claimed."""
from __future__ import annotations
import copy
from fractions import Fraction as F
from math import comb
from itertools import product
from pathlib import Path
import json
import unittest
from research.evidencekernel_calibrated_v26 import kernel as m

ROOT=Path(__file__).parent

def frozen():
    c=json.loads((ROOT/'calibration_contract.json').read_text())
    r=json.loads((ROOT/'calibration_records.json').read_text())
    p=json.loads((ROOT/'study_protocol.json').read_text())
    e=json.loads((ROOT/'study_records.json').read_text())
    return c,r,p,e

def audits(c,r,p,e):
    cp=m.digest(c)
    rp=m.calibration_evidence_pin(cp,r)
    pp=m.digest(p)
    ep=m.v25.evidence_digest(pp,e)
    return m.audit(c,r,p,e,calibration_contract_pin=cp,calibration_records_pin=rp,
                   study_protocol_pin=pp,study_records_pin=ep)

def any_stop_risk(looks_min,looks_max,p,beta,D,corrected=False):
    # Exact finite enumeration via DP, with absorbed paths weighted by completions.
    thresholds={}
    local=beta/(looks_max-looks_min+1) if corrected else beta
    for t in range(looks_min,looks_max+1):
        thresholds[t]=[m.find_upper(t,x,local,D)[0] for x in range(t+1)]
    survivors={0:F(1)}
    absorbed=F(0)
    for t in range(1,looks_max+1):
        nxt={}
        for x,probability in survivors.items():
            for draw,weight in ((0,1-p),(1,p)):
                count=x+draw
                candidate=probability*weight
                if t>=looks_min and thresholds[t][count]<p:
                    absorbed+=candidate
                else:
                    nxt[count]=nxt.get(count,F(0))+candidate
        survivors=nxt
    assert absorbed+sum(survivors.values(),F(0))==1
    return absorbed

class CalibrationGateTests(unittest.TestCase):
    def test_full_synthetic_pair_with_derived_propensity_risk(self):
        c,r,p,e=frozen()
        outcome=audits(c,r,p,e)
        self.assertEqual(outcome,json.loads((ROOT/'example_report.json').read_text()))
        self.assertEqual(outcome['calibration']['propensity_ceiling_by_state'],
                         ['167/250','481/1000','267/500'])
        self.assertEqual(outcome['derived_propensity_calibration_failure_budget'],'1/100')
        self.assertEqual(outcome['joint_failure_bound_if_all_physical_assumptions_hold'],'7/100')
        self.assertEqual(outcome['study_v25']['enrolled_units'],457)
        self.assertEqual(outcome['status'],'CONDITIONALLY_REJECTED')

    def test_integer_binomial_tail_matches_direct_fraction(self):
        for n in range(1,13):
            for x in range(n+1):
                for g in range(0,17):
                    numerator=m.binomial_lower_tail_numerator(n,x,g,16)
                    reference=sum(F(comb(n,j))*F(g,16)**j*F(16-g,16)**(n-j)
                                  for j in range(x+1))
                    self.assertEqual(F(numerator,16**n),reference)

    def test_fixed_sample_exact_coverage_on_many_true_propensities(self):
        # End-to-end CP inversion over all count outcomes, including off-grid p.
        for n in (16,20):
            for beta in (F(1,4),F(1,10),F(1,20)):
                upper=[m.find_upper(n,x,beta,32)[0] for x in range(n+1)]
                self.assertEqual(upper,sorted(upper))
                for p in (F(1,10),F(1,3),F(1,2),F(2,3),F(9,10)):
                    bad=sum((F(comb(n,x))*p**x*(1-p)**(n-x)
                             for x in range(n+1) if upper[x]<p),F(0))
                    self.assertLessEqual(bad,beta)

    def test_optional_calibration_peeking_counterexample_and_repair(self):
        p=F(1,2); beta=F(1,20)
        naive=any_stop_risk(16,48,p,beta,32,False)
        repaired=any_stop_risk(16,48,p,beta,32,True)
        self.assertEqual(naive,F(17440361441103,281474976710656))
        self.assertGreater(naive,beta)
        self.assertLessEqual(repaired,beta)

    def test_optional_calibration_is_conservative_with_finite_union_budget(self):
        for p in (F(1,3),F(1,2),F(2,3)):
            self.assertLessEqual(any_stop_risk(16,22,p,F(1,4),16,True),F(1,4))

    def test_peek_range_affects_cap_even_if_realized_length_is_identical(self):
        c,r,_,_=frozen()
        c['sample_size_policy']='anytime_within_registered_range'
        c['minimum_sample_sizes'][0]=500
        c['maximum_sample_sizes'][0]=512
        cp=m.digest(c);rp=m.calibration_evidence_pin(cp,r)
        new=m.calibrate(c,r,contract_pin=cp,records_pin=rp)
        old=audits(*frozen())['calibration']
        self.assertGreaterEqual(F(new['propensity_ceiling_by_state'][0]),
                                F(old['propensity_ceiling_by_state'][0]))
        self.assertEqual(new['statewise_calibration'][0]['permitted_calibration_looks'],13)
        self.assertEqual(new['statewise_calibration'][0]['effective_tail_threshold'],'1/3900')

    def test_anytime_calibration_full_study_gate(self):
        c,r,p,e=frozen()
        c['sample_size_policy']='anytime_within_registered_range'
        c['minimum_sample_sizes']=[500,500,500]
        c['maximum_sample_sizes']=[512,512,512]
        cp=m.digest(c);rp=m.calibration_evidence_pin(cp,r)
        cert=m.calibrate(c,r,contract_pin=cp,records_pin=rp)
        self.assertEqual(cert['total_propensity_failure_budget'],'1/100')
        self.assertEqual(cert['calibration_sample_size_policy'],
                         'anytime_within_registered_range')
        p['propensity_upper_by_state']=cert['propensity_ceiling_by_state']
        combined=audits(c,r,p,e)
        self.assertEqual(combined['joint_failure_bound_if_all_physical_assumptions_hold'],
                         '7/100')
        self.assertEqual(combined['calibration']['statewise_calibration'][0]
                         ['permitted_calibration_looks'],13)

    def test_missing_or_substituted_calibration_stream_rejected(self):
        c,r,p,e=frozen()
        cp=m.digest(c); rp=m.calibration_evidence_pin(cp,r)
        bad=copy.deepcopy(r);bad['assignment_bits_by_state'][0].pop()
        with self.assertRaisesRegex(m.Reject,'record pin mismatch'):
            m.calibrate(c,bad,contract_pin=cp,records_pin=rp)
        with self.assertRaisesRegex(m.Reject,'calibration stream'):
            audits(c,bad,p,e)
        bad=copy.deepcopy(r);bad['assignment_bits_by_state'][0][0]^=1
        with self.assertRaisesRegex(m.Reject,'record pin mismatch'):
            m.calibrate(c,bad,contract_pin=cp,records_pin=rp)

    def test_study_with_understated_propensity_cap_is_rejected(self):
        c,r,p,e=frozen()
        p['propensity_upper_by_state'][0]='1/2'
        with self.assertRaisesRegex(m.Reject,'not equal to independently calibrated'):
            audits(c,r,p,e)

    def test_distribution_shift_breaks_calibration_transfer(self):
        # All-null world (Y0=Y1=1). Pretrial true propensity p0=3/5,
        # derived ceiling 167/250; STUDY propensity secretly shifts to 9/10.
        # Shows why an exact CP certificate cannot establish temporal stationarity.
        n=64;actual=F(9,10);q=F(1,2);cap=F(167,250)
        lam=F(1,8);c=F(3)
        width=1/q+1/(1-q)
        threshold=c/lam+lam*n*width*width/8+max(F(0),cap-q)*width*n
        risk=sum((F(comb(n,k))*actual**k*(1-actual)**(n-k)
                  for k in range(n+1)
                  if F(k,q)-F(n-k,1-q)>threshold),F(0))
        self.assertGreater(risk,F(9,10))
        self.assertGreater(actual,cap)


    def test_vacuous_zero_information_and_malformed_contract(self):
        c,r,p,e=frozen()
        r['assignment_bits_by_state'][0]=[1]*512
        with self.assertRaisesRegex(m.Reject,'vacuous'):
            audits(c,r,p,e)
        c,r,p,e=frozen()
        c['sample_size_policy']='fixed_per_state'
        c['minimum_sample_sizes'][0]=511
        with self.assertRaisesRegex(m.Reject,'fixed calibration sample'):
            audits(c,r,p,e)
        c,r,p,e=frozen()
        c['beta_spend_by_state'][0]='2/1'
        with self.assertRaises(m.Reject):
            audits(c,r,p,e)

    def test_state_count_and_study_protocol_mutation_fail_closed(self):
        c,r,p,e=frozen()
        p['states']=2
        with self.assertRaises(m.Reject):
            audits(c,r,p,e)
        c,r,p,e=frozen()
        p['propensity_upper_by_state'].reverse()
        with self.assertRaises(m.Reject):
            audits(c,r,p,e)
        c,r,p,e=frozen()
        original=copy.deepcopy(e)
        e['assignments'][0]^=1
        cp=m.digest(c);rp=m.calibration_evidence_pin(cp,r);pp=m.digest(p)
        ep=m.v25.evidence_digest(pp,original)
        with self.assertRaisesRegex(m.Reject,'observed-prefix commitment'):
            m.audit(c,r,p,e,calibration_contract_pin=cp,calibration_records_pin=rp,
                    study_protocol_pin=pp,study_records_pin=ep)

    def test_duplicate_json_rejected_by_source_reader(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/'bad.json'
            file.write_text('{"stage":"prestudy","stage":"prestudy"}')
            with self.assertRaisesRegex(m.Reject,'duplicate JSON key'):
                m.v25.read(file)

if __name__=='__main__':unittest.main()
