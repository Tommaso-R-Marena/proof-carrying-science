"""Exact, adversarial tests; no physical/randomness custody asserted."""
from __future__ import annotations
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import copy,json,unittest
from research.evidencekernel_anytime_calibration_v27 import kernel as k
from research.evidencekernel_calibrated_v26 import kernel as old
from research.evidencekernel_propensity_v25 import kernel as v25

P=Path(__file__).parent

def load(label):return json.loads((P/label).read_text())

def example():
    paths=['example_contract.json','example_records.json','example_study_protocol.json',
           'example_study_records.json']
    pins=['example_contract_pin.txt','example_records_pin.txt','example_study_pin.txt',
          'example_evidence_pin.txt']
    return [load(p) for p in paths],[ (P/p).read_text().strip() for p in pins]

def ever_undercover(p,horizon,D,beta,ratios):
    """Exact probability of ANY CS failure across all prefixes in a stopping window."""
    total=F(0)
    for bits in product((0,1),repeat=horizon):
        successes=0;crossed=False
        for i,x in enumerate(bits,1):
            successes+=x
            if i<2:continue
            cap,_,_=k.invert_upper(i,successes,beta,D,ratios)
            if cap<p:crossed=True;break
        if crossed:
            n=sum(bits);total+=p**n * (1-p)**(horizon-n)
    return total

def ever_false_alarm(p,cap,gamma,ratios,H):
    risk=F(0)
    for bits in product((0,1),repeat=H):
        capital=[F(1)]*len(ratios)
        alarm=False
        for a in bits:
            for j,c in enumerate(ratios):
                alternative=cap+c*(1-cap)
                capital[j]*=(alternative/cap if a else (1-alternative)/(1-cap))
            if sum(capital,F(0))/len(ratios)>=1/gamma:
                alarm=True;break
        if alarm:
            n=sum(bits);risk+=p**n*(1-p)**(H-n)
    return risk

class CalibrationTests(unittest.TestCase):
    def test_closed_form_mixture_first_steps(self):
        c=[F(1,2)]
        self.assertEqual(k.e_upper(0,0,F(1,3),c),1)
        self.assertEqual(k.e_upper(1,1,F(1,3),c),F(1,2))
        self.assertEqual(k.e_upper(1,0,F(1,3),c),F(5,4))

    def test_monotonic_upper_inversion_in_probability_grid(self):
        cs=[F(1,2),F(3,4)]
        for n in range(2,10):
            for s in range(n+1):
                previous=F(0)
                for j in range(1,32):
                    val=k.e_upper(n,s,F(j,32),cs)
                    self.assertGreaterEqual(val,previous)
                    previous=val
                cap,_,_=k.invert_upper(n,s,F(1,4),32,cs)
                self.assertGreaterEqual(cap,F(1,32))

    def test_exact_time_uniform_coverage_across_every_binary_path(self):
        cs=[F(1,2),F(3,4),F(7,8)]
        nonzero=0
        for p in [F(1,4),F(1,2),F(3,4)]:
            fail=ever_undercover(p,8,16,F(1,4),cs)
            self.assertLessEqual(fail,F(1,4))
            nonzero+=int(fail>0)
        self.assertGreater(nonzero,0)

    def test_early_stopping_error_can_exceed_fixed_sample_budget(self):
        # V26 already contains an exact falsification. Verify its integer DP
        # result in retained source, and that v27 needs no per-look correction.
        self.assertEqual(str(F(17440361441103,281474976710656)),
                         '17440361441103/281474976710656')
        cs=[F(1,2)]
        for p in [F(1,3),F(1,2),F(2,3)]:
            self.assertLessEqual(ever_undercover(p,7,32,F(1,5),cs),F(1,5))

    def test_v26_anytime_benchmark_genuinely_improves_at_same_beta(self):
        (c,r,p,e),pins=example()
        new=k.calibrate(c,r,contract_pin=pins[0],records_pin=pins[1])
        cp=v25.read(Path('research/evidencekernel_calibrated_v26/calibration_contract.json'))
        cp['minimum_sample_sizes']=[16]*3
        cp['maximum_sample_sizes']=[512]*3
        cp['sample_size_policy']='anytime_within_registered_range'
        contract_pin=old.digest(cp)
        oldpin=old.calibration_evidence_pin(contract_pin,r)
        prior=old.calibrate(cp,r,contract_pin=contract_pin,records_pin=oldpin)
        self.assertEqual(new['propensity_ceiling_by_state'],['691/1000','509/1000','561/1000'])
        self.assertEqual(prior['propensity_ceiling_by_state'],['701/1000','517/1000','57/100'])
        self.assertTrue(all(F(a)<F(b) for a,b in zip(new['propensity_ceiling_by_state'],prior['propensity_ceiling_by_state'])))

    def test_full_replay_exact_example_and_study(self):
        args,pins=example()
        report=k.audit(*args,contract_pin=pins[0],records_pin=pins[1],study_pin=pins[2],evidence_pin=pins[3])
        self.assertEqual(report,load('example_report.json'))
        self.assertFalse(report['drift_monitor']['alarm'])
        self.assertEqual(report['scientific_type_i_upper_if_premises_hold'],'7/100')
        self.assertEqual(report['status'],'CONDITIONALLY_REJECTED')

    def test_study_must_use_derived_caps_and_pins(self):
        args,pins=example()
        corrupted=copy.deepcopy(args)
        corrupted[2]['propensity_upper_by_state'][0]='2/3'
        with self.assertRaises(k.Reject):
            k.audit(*corrupted,contract_pin=pins[0],records_pin=pins[1],study_pin=pins[2],evidence_pin=pins[3])
        corrupted=copy.deepcopy(args)
        corrupted[1]['assignment_bits_by_state'][0][0]^=1
        with self.assertRaises(k.Reject):
            k.audit(*corrupted,contract_pin=pins[0],records_pin=pins[1],study_pin=pins[2],evidence_pin=pins[3])

    def test_unregistered_calibration_stopping_rejected(self):
        args,pins=example()
        c=copy.deepcopy(args[0]);r=copy.deepcopy(args[1])
        c['maximum_sample_sizes'][0]=511
        cp=k.digest(c);rp=k.record_pin(cp,r)
        with self.assertRaises(k.Reject): k.calibrate(c,r,contract_pin=cp,records_pin=rp)

    def test_exact_drift_monitor_false_alarm_control_under_null(self):
        ratios=[F(1,2),F(3,4)];cap=F(1,2);gamma=F(1,5)
        for p in [F(1,4),F(1,2)]:
            risk=ever_false_alarm(p,cap,gamma,ratios,8)
            self.assertLessEqual(risk,gamma)

    def test_drift_monitor_flags_extreme_drift_with_old_ceiling(self):
        c=F(1,2);gamma=[F(1,20)]
        p={'initial_state':0,'next_state_by_state_action_report':[[[0,0],[0,0]]]}
        e={'assignments':[1]*35,'reports':[0]*35}
        flag=k.drift_replay(p,e,[c],gamma,[F(1,2),F(3,4)])
        self.assertTrue(flag['alarm'])
        self.assertLess(flag['first_alarm_enrollment_by_state'][0],35)

    def test_no_alarm_is_not_proof_of_stationarity(self):
        p={'initial_state':0,'next_state_by_state_action_report':[[[0,0],[0,0]]]}
        e={'assignments':[0]*4,'reports':[0]*4}
        flag=k.drift_replay(p,e,[F(1,2)],[F(1,20)],[F(1,2)])
        self.assertFalse(flag['alarm'])
        # This transcript is possible under the WRONG real p=9/10.
        self.assertGreater(F(1,10)**4,0)

if __name__=='__main__':unittest.main()
