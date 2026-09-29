import json
import tempfile
import unittest
from pathlib import Path
from pcs.kernel import build_certificate, verify_certificate, validate_workflow, AssuranceError

class KernelTests(unittest.TestCase):
    def test_example_round_trip(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            cert = build_certificate(root/'examples/biopharma_demo/manifest.json', d)
            self.assertEqual(cert['claims'][0]['assessment']['status'],'COMPUTATIONALLY_SUPPORTED')
            result = verify_certificate(Path(d)/'certificate.json')
            self.assertTrue(result['valid'], result['errors'])

    def test_tamper_detected(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            cert = build_certificate(root/'examples/biopharma_demo/manifest.json', d)
            train = next(a for a in cert['artifacts'] if a['id'] == 'train')
            p = Path(d) / train['path']
            p.write_text(p.read_text() + 'EVIL,0\n')
            result = verify_certificate(Path(d)/'certificate.json')
            self.assertFalse(result['valid'])
            self.assertTrue(any('hash mismatch' in e for e in result['errors']))

    def test_cycle_rejected(self):
        arts={'a','b'}
        wf={'nodes':[{'id':'n1','operation':'x','inputs':['b'],'outputs':['a']},{'id':'n2','operation':'y','inputs':['a'],'outputs':['b']}]}
        with self.assertRaises(AssuranceError):
            validate_workflow(wf, arts)

class FormalBoundaryTests(unittest.TestCase):
    def test_unchecked_external_proof_never_becomes_formally_verified(self):
        from pcs.kernel import derive_claim_status
        claim={'id':'c','kind':'formal','required_evidence':['e'],'assumptions':[]}
        evidence={'e':{'id':'e','kind':'formal_proof','outcome':'UNVERIFIED'}}
        self.assertEqual(derive_claim_status(claim,evidence)['status'],'OPEN')

class EvidenceReplayAttackTests(unittest.TestCase):
    def test_forged_pass_with_rehashed_certificate_is_rejected(self):
        from pcs.hashing import sha256_file, sha256_json
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            built = build_certificate(root/'examples/biopharma_demo/manifest.json', d)
            cert_path = Path(d)/'certificate.json'; cert = json.loads(cert_path.read_text())
            test_artifact = next(a for a in built['artifacts'] if a['id'] == 'test')
            test_path = Path(d) / test_artifact['path']
            test_path.write_text('subject_id,concentration_mg_L\nS001,9.8\nS102,6.1\n')
            for a in cert['artifacts']:
                if a['id'] == 'test': a['sha256'] = sha256_file(test_path)
            cert['integrity_hash']=''; cert['integrity_hash']=sha256_json(cert)
            cert_path.write_text(json.dumps(cert, indent=2, sort_keys=True))
            result=verify_certificate(cert_path)
            self.assertFalse(result['valid'])
            self.assertTrue(any('evidence replay outcome mismatch: E1' in e for e in result['errors']), result['errors'])

class PathAndConsistencyTests(unittest.TestCase):
    def test_manifest_artifact_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); outside=p.parent/'pcs-outside.txt'; outside.write_text('secret')
            manifest={'subject':'x','assumptions':[],'claims':[],'artifacts':[{'id':'a','path':'../pcs-outside.txt','role':'input'}],'checks':[],'workflow':{'nodes':[]}}
            (p/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(AssuranceError):
                build_certificate(p/'manifest.json', p/'out')
            outside.unlink(missing_ok=True)

    def test_unsafe_id_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'x.txt').write_text('x')
            manifest={'subject':'x','assumptions':[],'claims':[],'artifacts':[{'id':'../a','path':'x.txt','role':'input'}],'checks':[],'workflow':{'nodes':[]}}
            (p/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(AssuranceError):
                build_certificate(p/'manifest.json', p/'out')

    def test_workflow_summary_tamper_rejected_even_after_rehash(self):
        from pcs.hashing import sha256_json
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            build_certificate(root/'examples/biopharma_demo/manifest.json', d)
            cp=Path(d)/'certificate.json'; c=json.loads(cp.read_text())
            c['workflow_summary']['node_count']=999; c['integrity_hash']=''; c['integrity_hash']=sha256_json(c)
            cp.write_text(json.dumps(c,indent=2,sort_keys=True))
            r=verify_certificate(cp)
            self.assertFalse(r['valid']); self.assertIn('workflow_summary mismatch',r['errors'])

    def test_evidence_detail_tamper_rejected_even_after_rehash(self):
        from pcs.hashing import sha256_json
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            build_certificate(root/'examples/biopharma_demo/manifest.json', d)
            cp=Path(d)/'certificate.json'; c=json.loads(cp.read_text())
            c['evidence'][0]['details']['left_unique']=99999; c['integrity_hash']=''; c['integrity_hash']=sha256_json(c)
            cp.write_text(json.dumps(c,indent=2,sort_keys=True))
            r=verify_certificate(cp)
            self.assertFalse(r['valid'])
            self.assertTrue(any('evidence replay details mismatch: E1' in e for e in r['errors']),r['errors'])

class SemanticBindingTests(unittest.TestCase):
    def test_computational_claim_requires_predicate(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            src=json.loads((root/'examples/biopharma_demo/manifest.json').read_text()); del src['claims'][0]['predicate']
            for name in ('train.csv','test.csv','model_spec.txt'):
                (Path(d)/name).write_bytes((root/'examples/biopharma_demo'/name).read_bytes())
            mp=Path(d)/'manifest.json'; mp.write_text(json.dumps(src))
            with self.assertRaises(AssuranceError): build_certificate(mp,Path(d)/'out')

    def test_unrelated_passing_evidence_cannot_support_typed_claim(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            src=json.loads((root/'examples/biopharma_demo/manifest.json').read_text())
            src['claims'][0]['required_evidence']=['E3']; src['checks'][2]['claim_ids'].append('C1')
            for name in ('train.csv','test.csv','model_spec.txt'):
                (Path(d)/name).write_bytes((root/'examples/biopharma_demo'/name).read_bytes())
            mp=Path(d)/'manifest.json'; mp.write_text(json.dumps(src))
            with self.assertRaises(AssuranceError): build_certificate(mp,Path(d)/'out')

    def test_evidence_claim_binding_tamper_rejected_after_rehash(self):
        from pcs.hashing import sha256_json
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            build_certificate(root/'examples/biopharma_demo/manifest.json',d)
            cp=Path(d)/'certificate.json'; c=json.loads(cp.read_text())
            c['evidence'][0]['claim_ids']=['C2']; c['integrity_hash']=''; c['integrity_hash']=sha256_json(c)
            cp.write_text(json.dumps(c,indent=2,sort_keys=True))
            r=verify_certificate(cp)
            self.assertFalse(r['valid'])
            self.assertTrue(any('evidence replay claim binding mismatch: E1' in e for e in r['errors']),r['errors'])



class FullRequiredEvidenceBindingTests(unittest.TestCase):
    def test_one_matching_and_one_unrelated_required_evidence_is_rejected(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            src = json.loads(
                (root / "examples/biopharma_demo/manifest.json").read_text(encoding="utf-8")
            )
            # E1 is the claim's original matching check. Add E3 as another
            # required object and declare claim support, while retaining E3's
            # different predicate. The old kernel accepted this because one
            # required evidence object matched; the Lean refinement does not.
            src["claims"][0]["required_evidence"] = ["E1", "E3"]
            if src["claims"][0]["id"] not in src["checks"][2]["claim_ids"]:
                src["checks"][2]["claim_ids"].append(src["claims"][0]["id"])
            for name in ("train.csv", "test.csv", "model_spec.txt"):
                (p / name).write_bytes(
                    (root / "examples/biopharma_demo" / name).read_bytes()
                )
            mp = p / "manifest.json"
            mp.write_text(json.dumps(src), encoding="utf-8")
            with self.assertRaisesRegex(
                AssuranceError, "required evidence E3 is not predicate-bound"
            ):
                build_certificate(mp, p / "out")

    def test_untyped_noncomputational_claim_cannot_require_typed_check(self):
        claim = {
            "id": "F",
            "kind": "formal",
            "required_evidence": ["E"],
            "assumptions": [],
        }
        evidence = {
            "E": {
                "id": "E",
                "kind": "formal_proof",
                "outcome": "PASS",
                "check_spec": {
                    "id": "E",
                    "type": "pkpd_contract",
                    "model_artifact": "m",
                    "claim_ids": ["F"],
                },
            }
        }
        with self.assertRaisesRegex(
            AssuranceError, "required evidence E is not predicate-bound"
        ):
            from pcs.kernel import _validate_claim_semantics
            _validate_claim_semantics(claim, evidence)
