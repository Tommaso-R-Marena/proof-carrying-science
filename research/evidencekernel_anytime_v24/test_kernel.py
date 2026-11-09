"""Exact adversarial, theorem-obligation, and regression checks for v24."""
import copy
from fractions import Fraction
from itertools import product
import json
from pathlib import Path
import tempfile
import random
import unittest

from . import kernel as m
from . import make_demo
from . import counterexample

ROOT=Path(__file__).parent

class AnytimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=json.loads((ROOT/'example_protocol.json').read_text())
        cls.e=json.loads((ROOT/'example_evidence.json').read_text())
        cls.pp=(ROOT/'example_protocol_pin.txt').read_text().strip()
        cls.ep=(ROOT/'example_evidence_pin.txt').read_text().strip()

    def audit(self,p,e):
        pp=m.digest(p)
        return m.audit(p,e,protocol_pin=pp,evidence_pin=m.evidence_digest(pp,e))

    def test_signed_synthetic_early_stop_and_long_horizon(self):
        for name in ('example','scale'):
            with tempfile.TemporaryDirectory(prefix='ekv24-scale-') as tmp:
                location=ROOT if name=='example' else Path(tmp)
                if name=='scale':
                    make_demo.save(location,n=4096,min_enrollment=4096,
                                   stop_enabled=False,label='scale')
                p=json.loads((location/f'{name}_protocol.json').read_text())
                e=json.loads((location/f'{name}_evidence.json').read_text())
                pp=(location/f'{name}_protocol_pin.txt').read_text().strip()
                ep=(location/f'{name}_evidence_pin.txt').read_text().strip()
                answer=m.audit(p,e,protocol_pin=pp,evidence_pin=ep)
                self.assertEqual(answer,json.loads((location/f'{name}_report.json').read_text()))
                self.assertEqual(answer['status'],'CONDITIONALLY_REJECTED')
        self.assertEqual(self.audit(self.p,self.e)['enrolled_units'],457)
        self.assertEqual(self.audit(self.p,self.e)['anytime_lower_ate'],'6009709/11796480')

    def test_protocol_is_not_trust_anchor_unless_pinned(self):
        p=copy.deepcopy(self.p);p['null_ate_upper']='1/2'
        with self.assertRaisesRegex(m.Reject,'registration commitment'):
            m.audit(p,self.e,protocol_pin=self.pp,evidence_pin=self.ep)
        e=copy.deepcopy(self.e);e['reports'][0]^=1
        with self.assertRaisesRegex(m.Reject,'observed-prefix commitment'):
            m.audit(self.p,e,protocol_pin=self.pp,evidence_pin=self.ep)

    def test_taylor_proof_and_alpha_spending_fail_closed(self):
        p=copy.deepcopy(self.p);p['tuning'][0]['log_upper']='4'
        with self.assertRaisesRegex(m.Reject,'log upper-bound certificate'):
            self.audit(p,self.e)
        p=copy.deepcopy(self.p);p['tuning'][0]['alpha_spend']='1/2'
        with self.assertRaises(m.Reject):self.audit(p,self.e)
        p=copy.deepcopy(self.p);p['tuning'][0]['lambda']='1/4' # still valid
        self.assertIn('anytime_lower_ate',self.audit(p,self.e))

    def test_zero_probability_arms_and_noncanonical_numbers_rejected(self):
        p=copy.deepcopy(self.p);p['allocation_weights_by_state'][1][0]=0
        with self.assertRaisesRegex(m.Reject,'both treatment arms'):
            self.audit(p,self.e)
        p=copy.deepcopy(self.p);p['confidence_alpha']='2/40'
        with self.assertRaisesRegex(m.Reject,'canonical'):
            self.audit(p,self.e)
        p=copy.deepcopy(self.p);p['registered_units']=True
        with self.assertRaisesRegex(m.Reject,'registered_units'):
            self.audit(p,self.e)

    def test_missing_or_extra_reports_or_early_stop_rejected(self):
        e=copy.deepcopy(self.e);e['reports'].pop()
        with self.assertRaisesRegex(m.Reject,'truncated'):
            self.audit(self.p,e)
        e=copy.deepcopy(self.e)
        e['assignments'].pop();e['reports'].pop();e['true_intervals'].pop()
        with self.assertRaisesRegex(m.Reject,'terminal length'):
            self.audit(self.p,e)
        e=copy.deepcopy(self.e);e['true_intervals'][7]='2'
        with self.assertRaisesRegex(m.Reject,'binary measurement'):
            self.audit(self.p,e)

    def test_miss_correction_is_exact_one_sided_worst_case(self):
        # Small exhaustive pairwise checks for p=1/2 or 2/3 and all observed
        # binary interval labels. A single invalid label cannot bias the
        # certified *lower* HT estimate by more than the top-K correction.
        for p in (Fraction(1,2),Fraction(2,3)):
            for acts in product((0,1),repeat=3):
                for truth in product((0,1),repeat=3):
                    for labels in product(('0','1','01'),repeat=3):
                        mismatch=sum(lab!='01' and int(lab)!=y for lab,y in zip(labels,truth))
                        if mismatch>1:continue
                        lo=Fraction(0);real=Fraction(0);cost=[]
                        for a,y,lab in zip(acts,truth,labels):
                            lower=int(lab=='1');upper=int(lab!='0')
                            lo+=(Fraction(lower,p) if a else -Fraction(upper,1-p))
                            real+=(Fraction(y,p) if a else -Fraction(y,1-p))
                            cost.append(Fraction(lower,p) if a else Fraction(1-upper,1-p))
                        self.assertLessEqual(lo-max(cost),real)

    def test_prematurely_stopped_prefix_cannot_be_reopened(self):
        p=copy.deepcopy(self.p);e=copy.deepcopy(self.e)
        # Force every report to trigger stopping from first eligible time.
        p['stop_after_by_state_action_report']=[[[True,True],[True,True]] for _ in range(3)]
        with self.assertRaisesRegex(m.Reject,'terminal length'):
            self.audit(p,e)

    def test_true_fixed_cohort_ate_covers_after_arbitrary_stopping(self):
        # All 4^5 binary potential tables. For each, enumerate every possible
        # treatment history under the policy with positive exact probability.
        # Here reports equal A, and stop immediately after 3rd unit if A=1.
        p=make_demo.protocol(n=5,min_enrollment=3,stop_enabled=False)
        p['stop_after_by_state_action_report']=[[[False,False],[False,True]] for _ in range(3)]
        p['confidence_alpha']='1/2';p['calibration_failure_bound']='0';p['max_interval_misses']=0
        p['tuning']=[{'lambda':'1/4','alpha_spend':'1/2','log_upper':'1','taylor_terms':8}]
        for world in product(range(4),repeat=5):
            truth=[(v>>1,v&1) for v in world]
            ate=sum(y1-y0 for y0,y1 in truth)/5
            bad=Fraction(0)
            def visit(actions,reports,labels,state,mass):
                nonlocal bad
                i=len(actions)
                for a in (0,1):
                    pr=Fraction(p['allocation_weights_by_state'][state][a],
                                sum(p['allocation_weights_by_state'][state]))
                    r=a;y=truth[i][a]
                    aa=actions+[a];rr=reports+[r];ll=labels+[str(y)]
                    if i+1==5 or (i+1>=3 and a==1):
                        report=self.audit(p,{'assignments':aa,'reports':rr,'true_intervals':ll})
                        if Fraction(report['anytime_lower_ate'])>Fraction(ate):
                            bad+=mass*pr
                    else:
                        ns=p['next_state_by_state_action_report'][state][a][r]
                        visit(aa,rr,ll,ns,mass*pr)
            visit([],[],[],0,Fraction(1))
            self.assertLessEqual(bad,Fraction(1,2))

    def test_misstated_propensity_has_large_false_positive_rate(self):
        example=counterexample.evaluate()
        self.assertGreater(Fraction(example['exact_false_positive_probability']),Fraction(999,1000))
        self.assertEqual(example['rejected_treated_counts'][0],43)

    def test_strict_file_reader_detects_duplicate_keys(self):
        tmp=ROOT/'_tmp_duplicate_v24.json'
        try:
            tmp.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(m.Reject,'duplicate JSON key'):m.read(tmp)
        finally:
            tmp.unlink(missing_ok=True)

if __name__=='__main__':unittest.main()
