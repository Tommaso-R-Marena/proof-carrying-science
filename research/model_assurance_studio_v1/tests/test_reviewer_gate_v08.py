"""Reviewer-controlled gate: mutated source, claim, policy and certificate tests."""
import copy
import json
import unittest
from pathlib import Path
from studio.reviewer_gate_v08 import verify, SCHEMA

ROOT = Path(__file__).resolve().parents[1]


class IndependentReviewerGateV08(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = (ROOT/'samples/demo_trained_iris_mlp.onnx').read_bytes()
        cls.new = (ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
        cls.base = json.loads((ROOT/'validation/v06_iris_property_1_certificate.json').read_text())
        cls.drift = json.loads((ROOT/'validation/v06_update_drift_certificate.json').read_text())
        cls.policy = json.loads((ROOT/'validation/v08_iris_independent_reviewer_policy.json').read_text())

    def gate(self, policy=..., baseline=..., drift=..., old=..., new=...):
        return verify(self.old if old is ... else old,
                      self.new if new is ... else new,
                      self.base if baseline is ... else baseline,
                      self.drift if drift is ... else drift,
                      self.policy if policy is ... else policy)

    def test_accepts_only_conditional_evidence(self):
        result=self.gate()
        self.assertEqual(result['status'], 'PROVED_CONDITIONALLY')
        self.assertEqual(result['lean_kernel_verification'], 'NOT_ESTABLISHED')
        self.assertEqual(result['onnx_runtime_equivalence'], 'NOT_ESTABLISHED')
        self.assertEqual(result['deployment_authorization'], 'NOT_ESTABLISHED')
        self.assertIn('EXPERIMENTAL_PYTHON_CHECK', result['authority'])

    def test_tampered_model_bytes(self):
        for which in (0,1):
            with self.subTest(which=which):
                damaged=bytearray(self.old if which==0 else self.new)
                damaged[-1]^=1
                result=(self.gate(old=bytes(damaged)) if which==0
                        else self.gate(new=bytes(damaged)))
                self.assertEqual(result['status'], 'OPEN')

    def test_untrusted_policy_edits_refused(self):
        changes={
          'schema':'pcs-independent-model-update-review-policy-v0.7',
          'old_model_sha256':'0'*64,
          'new_model_sha256':'f'*64,
          'input_box':[['-0.5','0.5']]*4,
          'output_coefficients':['1','0','0'],
          'baseline_upper_limit':'-3/4',
          'drift_upper_limit':'1/16',
          'required_updated_upper_limit':'-1/2',
          'required_float32_upper_limit':'-1/2',
        }
        for key,value in changes.items():
            with self.subTest(key=key):
                policy=copy.deepcopy(self.policy)
                policy[key]=value
                self.assertEqual(self.gate(policy=policy)['status'],'OPEN')

    def test_bad_signs_and_large_or_unknown_policies(self):
        for change in ({'input_box':[['2','1']]*4},
                       {'output_coefficients':['0','0','0']},
                       {'output_coefficients':[True, 0, 0]},
                       {'input_box':'all the inputs'},
                       {'new_model_sha256':'A'*64},
                       {'required_float32_upper_limit':'nan'},
                       {'extra':'unexpected'}):
            with self.subTest(change=change):
                policy=copy.deepcopy(self.policy);policy.update(change)
                self.assertEqual(self.gate(policy=policy)['status'],'OPEN')

    def test_certificates_have_no_authority_to_modify_claim(self):
        for name,certificate in [('base',self.base),('drift',self.drift)]:
            with self.subTest(name=name):
                bad=copy.deepcopy(certificate)
                bad['input_box'][0]=['0','0']
                r=self.gate(baseline=bad) if name=='base' else self.gate(drift=bad)
                self.assertEqual(r['status'],'OPEN')
            with self.subTest(name=name+'-multiplier'):
                bad=copy.deepcopy(certificate)
                bad['multipliers'][0][1]='999'
                r=self.gate(baseline=bad) if name=='base' else self.gate(drift=bad)
                self.assertEqual(r['status'],'OPEN')

    def test_stricter_fp32_requirement_abstains(self):
        policy=copy.deepcopy(self.policy)
        policy['required_float32_upper_limit']='-3/8'
        self.assertEqual(self.gate(policy=policy)['status'],'OPEN')

    def test_no_policy_and_invalid_dtypes(self):
        for p in (None, [], True, 'wrong', {'schema':SCHEMA}):
            with self.subTest(p=p):
                self.assertEqual(self.gate(policy=p)['status'],'OPEN')
        self.assertEqual(verify(bytearray(self.old),self.new,self.base,self.drift,self.policy)['status'],'OPEN')


if __name__=='__main__': unittest.main()
