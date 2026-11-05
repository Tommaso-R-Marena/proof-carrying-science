"""Independent reviewer/host enforcement tests: all proof checks in Python -S mode."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from studio.relational_kernel import canonical
from studio.operating_envelope_v09 import (verify_envelope,OperatingEnvelopeGate,POLICY_SCHEMA)
from studio.guarded_reference_infer_v09 import reference_infer

ROOT=Path(__file__).resolve().parents[1]

class OperatingEnvelopeV09(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=(ROOT/'samples/demo_trained_iris_mlp.onnx').read_bytes()
        cls.new=(ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
        cls.policy=json.loads((ROOT/'validation/v09_demo_envelope_reviewer_policy.json').read_text())
        cls.bundle=json.loads((ROOT/'validation/v09_demo_envelope_evidence.json').read_text())
        cls.words=json.loads((ROOT/'validation/v09_demo_input_words.json').read_text())
        cls.pinned=hashlib.sha256(canonical(cls.policy)).hexdigest()
        cls.gate=OperatingEnvelopeGate(cls.old,cls.new,cls.bundle,cls.policy,cls.pinned)

    _unspecified=object()

    def check(self, *, policy=None,bundle=None,old=None,new=None,expected=_unspecified):
        return verify_envelope(self.old if old is None else old,self.new if new is None else new,
            self.bundle if bundle is None else bundle,self.policy if policy is None else policy,
            self.pinned if expected is self._unspecified else expected)

    def test_three_distinct_classes_are_certified(self):
        report=self.gate.review()
        self.assertEqual(report['status'],'PROVED_CONDITIONALLY')
        self.assertEqual(report['checked_comparisons'],6)
        self.assertEqual(report['region_count'],3)
        self.assertEqual(report['lean_kernel_verification'],'NOT_ESTABLISHED')
        self.assertEqual(report['deployment_authorization'],'NOT_ESTABLISHED')
        self.assertNotIn('verified_regions',report)
        for sample,cls in [('22',0),('62',1),('118',2)]:
            with self.subTest(sample=sample):
                result=self.gate.admit(self.words[sample])
                self.assertEqual(result['status'],'ADMIT_CONDITIONALLY')
                self.assertEqual(result['class_index'],cls)
                self.assertEqual(result['minimum_margin'],'1/4')

    def test_real_reference_inference_after_gate(self):
        for sample,cls in [('22',0),('62',1),('118',2)]:
            with self.subTest(sample=sample):
                result=reference_infer(self.gate,self.new,self.words[sample])
                self.assertEqual(result['status'],'EXECUTED_CONDITIONALLY')
                self.assertEqual(result['class_index'],cls)
                self.assertEqual(len(result['output_bits']),3)
                self.assertEqual(result['runtime_equivalence'],'NOT_ESTABLISHED')

    def test_outside_region_abstains_without_computing(self):
        with patch('studio.guarded_reference_infer_v09.sequential_eval',side_effect=AssertionError('should not run')):
            outcome=reference_infer(self.gate,self.new,['00000000']*4)
        self.assertEqual(outcome['status'],'ABSTAIN')
        self.assertIn('Gate abstained',outcome['reason'])

    def test_unknown_or_nonfinite_input_bits_abstain(self):
        for words in ([],['00000000']*3,['00000000']*5,
                      ['7f800000']*4,['ff800000']*4,['7fc00001']*4,
                      [1,2,3,4],['0000000G']*4,['0000000A']*4,
                      ['000000000']*4,[None]*4,True):
            with self.subTest(words=words):
                self.assertEqual(self.gate.admit(words)['status'],'ABSTAIN')

    def test_missing_trusted_policy_hash(self):
        for fingerprint in ('',None,'0'*64,'A'*64):
            with self.subTest(fingerprint=fingerprint):
                self.assertEqual(self.check(expected=fingerprint)['status'],'OPEN')

    def test_policy_mutations_are_rejected_even_if_proposer_agrees(self):
        for field,value in [('schema','older'),('old_model_sha256','0'*64),
                            ('new_model_sha256','a'*64),('regions',[]),
                            ('unexpected','x')]:
            with self.subTest(field=field):
                pol=copy.deepcopy(self.policy);pol[field]=value
                self.assertEqual(self.check(policy=pol)['status'],'OPEN')
        for key,value in [('class_index',2),('minimum_margin','0'),
                          ('minimum_margin','1/2'),('baseline_upper_limit','-1/4'),
                          ('drift_upper_limit','1/2'),('required_float32_upper_limit','0'),
                          ('id','../evil'),('box',[['-1','1']]*4)]:
            with self.subTest(key=key):
                pol=copy.deepcopy(self.policy);pol['regions'][0][key]=value
                self.assertEqual(self.check(policy=pol)['status'],'OPEN')

    def test_model_substitution_and_post_admission_mutation_denied(self):
        for original in ('old','new'):
            raw=bytearray(self.old if original=='old' else self.new);raw[-1]^=1
            with self.subTest(original=original):
                kwargs={original:bytes(raw)}
                self.assertEqual(self.check(**kwargs)['status'],'OPEN')
        model=bytearray(self.new);model[-1]^=1
        self.assertEqual(reference_infer(self.gate,bytes(model),self.words['22'])['status'],'ABSTAIN')

    def test_all_competitor_proofs_required(self):
        for mutation in ('missing','swapped','duplicate','wrong_class','wrong_cert'):
            with self.subTest(mutation=mutation):
                evidence=copy.deepcopy(self.bundle)
                comps=evidence['entries'][0]['comparisons']
                if mutation=='missing':comps.pop()
                if mutation=='swapped':comps.reverse()
                if mutation=='duplicate':comps[1]['other_class_index']=comps[0]['other_class_index']
                if mutation=='wrong_class':comps[0]['other_class_index']=2
                if mutation=='wrong_cert':comps[0]['baseline_certificate']['multipliers'][0][1]='999'
                self.assertEqual(self.check(bundle=evidence)['status'],'OPEN')

    def test_source_claim_identity_and_cert_binding(self):
        for key,bad in [('schema','bad'),('policy_sha256','0'*64),('old_model_sha256','0'*64),
                        ('new_model_sha256','0'*64)]:
            with self.subTest(key=key):
                bundle=copy.deepcopy(self.bundle);bundle[key]=bad
                self.assertEqual(self.check(bundle=bundle)['status'],'OPEN')
        data=copy.deepcopy(self.bundle)
        data['entries'][0]['comparisons'][0]['drift_certificate']['relation']['upper_limit']='100'
        self.assertEqual(self.check(bundle=data)['status'],'OPEN')

    def test_missing_region_or_duplicate_id_fails_globally(self):
        data=copy.deepcopy(self.bundle);data['entries'].pop()
        self.assertEqual(self.check(bundle=data)['status'],'OPEN')
        pol=copy.deepcopy(self.policy);pol['regions'][1]['id']=pol['regions'][0]['id']
        pinned=hashlib.sha256(canonical(pol)).hexdigest()
        data=copy.deepcopy(self.bundle);data['policy_sha256']=pinned
        data['entries'][1]['region_id']=pol['regions'][0]['id']
        self.assertEqual(self.check(bundle=data,policy=pol,expected=pinned)['status'],'OPEN')

    def test_missing_proof_cannot_be_ignored_by_input_routing(self):
        altered=copy.deepcopy(self.bundle)
        altered['entries'][2]['comparisons'][0]['baseline_certificate']['multipliers']=[]
        gate=OperatingEnvelopeGate(self.old,self.new,altered,self.policy,self.pinned)
        self.assertEqual(gate.review()['status'],'OPEN')
        self.assertEqual(gate.admit(self.words['22'])['status'],'ABSTAIN')

    def test_execution_refuses_unverified_gate(self):
        fake={'status':'PROVED_CONDITIONALLY','model_sha256':hashlib.sha256(self.new).hexdigest()}
        self.assertEqual(reference_infer(fake,self.new,self.words['22'])['status'],'ABSTAIN')

    def test_rehashed_adversarial_multiplier_mutations_rejected(self):
        # A certificate hash is not a signature or mathematical proof. Test
        # attacker-edited dual coefficients with a fresh, internally valid hash.
        import random
        rng=random.Random(90121)
        from studio.relational_kernel import digest
        for trial in range(64):
            evidence=copy.deepcopy(self.bundle)
            region=rng.randrange(len(evidence['entries']))
            comp=rng.randrange(2)
            which='baseline_certificate' if trial%2 else 'drift_certificate'
            cert=evidence['entries'][region]['comparisons'][comp][which]
            term=rng.randrange(len(cert['multipliers']))
            prior=cert['multipliers'][term][1]
            cert['multipliers'][term][1]='0'
            cert['certificate_sha256']=digest(canonical({k:v for k,v in cert.items() if k!='certificate_sha256'}))
            with self.subTest(trial=trial,region=region,comp=comp,source=prior):
                self.assertEqual(self.check(bundle=evidence)['status'],'OPEN')

    def test_local_http_demo_and_host_denial(self):
        try:
            from fastapi.testclient import TestClient
            from studio.server import app
        except ImportError:
            self.skipTest('FastAPI optional frontend not installed')
        with TestClient(app,base_url='http://testserver') as client:
            r=client.get('/api/operating-envelope-demo')
            self.assertEqual(r.status_code,200)
            doc=r.json()
            self.assertEqual(doc['review']['status'],'PROVED_CONDITIONALLY')
            self.assertEqual(len(doc['examples']),3)
            self.assertTrue(all(x['reference_execution']['status']=='EXECUTED_CONDITIONALLY' for x in doc['examples']))
            self.assertEqual(doc['outside_example']['reference_execution']['status'],'ABSTAIN')
            bad=client.get('/api/operating-envelope-demo',headers={'host':'attacker.invalid'})
            self.assertEqual(bad.status_code,403)

    def test_policy_file_digest_and_report_bound(self):
        self.assertEqual(self.gate.review()['policy_sha256'],self.pinned)
        for sample,words in self.words.items():
            r=self.gate.admit(words)
            self.assertEqual(r['policy_sha256'],self.pinned)
            self.assertEqual(r['input_bits'],words)

if __name__=='__main__':unittest.main()
