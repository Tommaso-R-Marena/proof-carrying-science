"""Independent boundary tests for v0.2 research checkers."""
import json
import math
import struct
import random
import unittest
from fractions import Fraction
from pathlib import Path
from importlib.util import find_spec

from studio.engine import analyze, parse_policy
from studio.research import formula_elements, sbml_conservation, _rref_nullspace
from studio.verify_receipt import verify
from tests.make_samples import onnx_sample, safe_sample
ROOT=Path(__file__).resolve().parents[1]


def status(report,id):
    return next(c['status'] for c in report['checks'] if c['id']==id)


def make_safetensors(dtype, blob, count):
    h=json.dumps({'weight':{'dtype':dtype,'shape':[count],'data_offsets':[0,len(blob)]}},separators=(',',':')).encode()
    return struct.pack('<Q',len(h))+h+blob


def sbml(xml):
    return analyze('model.sbml',xml.encode())


class TestExtended(unittest.TestCase):
    def test_candidate_true_violation_identity(self):
        r=analyze('i.onnx',onnx_sample(),{'check_output_bounds':True,'output_min':-.5,'output_max':.5})
        w=r['details']['candidate_counterexample']
        self.assertEqual(w['inputs']['features'],-1.)
        self.assertEqual(w['exact_output_fractions']['prediction'],'-1')
        self.assertEqual(w['status'],'CANDIDATE_UNREPLAYED')
        self.assertEqual(status(r,'ONNX_WITNESS'),'OPEN')
        self.assertEqual(r['decision'],'OPEN')
        self.assertEqual(w['artifact_sha256'],r['sha256'])
        self.assertEqual(w['policy_sha256'],r['policy_sha256'])
        self.assertTrue(verify(r,onnx_sample())[0])

    def test_candidate_relu_violation(self):
        r=analyze('r.onnx',onnx_sample(op='Relu'),{'check_output_bounds':True,'output_min':0,'output_max':.5})
        w=r['details']['candidate_counterexample']
        self.assertGreater(w['outputs']['prediction'],.5)
        self.assertGreater(w['inputs']['features'],.5)
        self.assertEqual(status(r,'ONNX_INTERVAL'),'OPEN')

    def test_no_witness_is_not_a_pass(self):
        r=analyze('r.onnx',onnx_sample(op='Relu'),{'check_output_bounds':True,'output_min':0,'output_max':1})
        self.assertNotIn('candidate_counterexample',r['details'])
        self.assertEqual(status(r,'ONNX_WITNESS'),'OPEN')
        self.assertEqual(status(r,'ONNX_INTERVAL'),'PASS')
        self.assertEqual(r['decision'],'OPEN')

    def test_witness_disabled(self):
        r=analyze('r.onnx',onnx_sample(),{'check_output_bounds':True,'search_scalar_witness':False})
        self.assertEqual(status(r,'ONNX_WITNESS'),'OPEN')
        self.assertNotIn('candidate_counterexample',r['details'])

    def test_witness_abstains_on_unparsed_or_unsafe_graph(self):
        for model in [onnx_sample(missing=True),onnx_sample(custom=True),onnx_sample(op='Sin')]:
            with self.subTest(model=model[:20]):
                r=analyze('x.onnx',model,{'check_output_bounds':True})
                self.assertEqual(status(r,'ONNX_WITNESS'),'OPEN')
                self.assertNotIn('candidate_counterexample',r['details'])

    def test_onnx_witness_bounded_by_policy_not_filename(self):
        r=analyze('evil_file_name.onnx',onnx_sample(),{'check_output_bounds':True,'output_min':-100,'output_max':100})
        self.assertNotIn('candidate_counterexample',r['details'])
        self.assertTrue(verify(r,onnx_sample())[0])

    def test_real_network_invariant(self):
        r=analyze('net.sbml',(ROOT/'samples/demo_reaction.sbml').read_bytes())
        x=r['details']['reaction_only_invariants']
        self.assertEqual(x['conservation_basis'],[{'A':1,'B':1}])
        self.assertEqual(x['stoichiometric_rank'],1)
        self.assertEqual(status(r,'SBML_STOICHIOMETRY'),'PASS')
        self.assertEqual(r['decision'],'OPEN')

    def test_elemental_balance_good_bad(self):
        good=analyze('w.sbml',(ROOT/'samples/demo_water_balanced.sbml').read_bytes())
        bad=analyze('w.sbml',(ROOT/'samples/demo_water_imbalanced.sbml').read_bytes())
        self.assertEqual(status(good,'SBML_ELEMENT_BALANCE'),'PASS')
        self.assertEqual(status(bad,'SBML_ELEMENT_BALANCE'),'FAIL')
        self.assertEqual(bad['decision'],'FAIL')
        self.assertEqual(bad['details']['elemental_balance']['imbalanced_reactions_sample'][0]['element_imbalance'],{'H':'-2','O':'-1'})
        self.assertTrue(verify(good,(ROOT/'samples/demo_water_balanced.sbml').read_bytes())[0])

    def test_formula_parser_does_not_guess(self):
        self.assertEqual(formula_elements('H2O'),{'H':2,'O':1})
        self.assertEqual(formula_elements('C6H12O6'),{'C':6,'H':12,'O':6})
        for bad in ('Xx2','(CH3)2','H0','H-2','Fe+2','D2O','',None,'C00000000','Mg1.2'):
            with self.subTest(bad=bad):self.assertIsNone(formula_elements(bad))

    def test_network_abstains_on_rules(self):
        text=(ROOT/'samples/demo_reaction.sbml').read_text()
        text=text.replace('</model>','<listOfRules><rateRule variable="A"><math/></rateRule></listOfRules></model>')
        r=sbml(text)
        self.assertEqual(status(r,'SBML_STOICHIOMETRY'),'OPEN')
        self.assertNotIn('reaction_only_invariants',r['details'])

    def test_network_abstains_on_boundary_species(self):
        text=(ROOT/'samples/demo_reaction.sbml').read_text().replace('id="A" compartment', 'id="A" boundaryCondition="true" compartment')
        self.assertEqual(status(sbml(text),'SBML_STOICHIOMETRY'),'OPEN')

    def test_stoichiometric_rref_independent_example(self):
        rank,basis=_rref_nullspace([[Fraction(-1),Fraction(1),Fraction(0)],
                                    [Fraction(0),Fraction(-1),Fraction(1)]],3)
        self.assertEqual(rank,2)
        self.assertEqual(basis,[[1,1,1]])
        self.assertEqual(_rref_nullspace([[Fraction(-1)]],1),(1,[]))
        self.assertEqual(_rref_nullspace([[Fraction(0),Fraction(0)]],2),(0,[[1,0],[0,1]]))

    @unittest.skipUnless(find_spec('sympy'),'optional independent symbolic reference unavailable')
    def test_exact_nullspace_against_sympy_random(self):
        from sympy import Matrix
        rng=random.Random(2604)
        for _ in range(80):
            m=rng.randint(1,6);n=rng.randint(1,6)
            rows=[[Fraction(rng.randint(-3,3),rng.randint(1,5)) for _ in range(n)] for _ in range(m)]
            rank,basis=_rref_nullspace(rows,n)
            sym=Matrix([[str(x) for x in row] for row in rows])
            self.assertEqual(rank,sym.rank())
            self.assertEqual(len(basis),n-rank)
            for b in basis:
                for row in rows:
                    self.assertEqual(sum(x*y for x,y in zip(row,b)),0)

    def test_half_float_nan_inf(self):
        for dtype,values in [('F16',[0x3c00,0x7c00]),('BF16',[0x3f80,0x7fc0])]:
            with self.subTest(dtype=dtype):
                raw=b''.join(struct.pack('<H',v) for v in values)
                r=analyze('x.safetensors',make_safetensors(dtype,raw,2))
                self.assertEqual(status(r,'NONFINITE_WEIGHTS'),'FAIL')
                self.assertEqual(r['metrics']['nonfinite_sampled'],1)
        for dtype,values in [('F16',[0x3c00,0x0000]),('BF16',[0x3f80,0x0000])]:
            with self.subTest(dtype=dtype):
                r=analyze('x.safetensors',make_safetensors(dtype,b''.join(struct.pack('<H',v) for v in values),2))
                self.assertEqual(status(r,'NONFINITE_WEIGHTS'),'PASS')

    def test_bounded_prefix_does_not_announce_pass(self):
        n=250002
        raw=b'\0\0'*250001 + struct.pack('<H',0x7c00)
        r=analyze('x.safetensors',make_safetensors('F16',raw,n))
        self.assertEqual(status(r,'NONFINITE_WEIGHTS'),'OPEN')
        self.assertEqual(r['metrics']['float_values_sampled'],250000)

    @unittest.skipUnless(find_spec('gemmi'),'optional mmCIF native reader unavailable')
    def test_mmcif_works(self):
        raw=(ROOT/'samples/demo_protein.cif').read_bytes()
        r=analyze('x.cif',raw)
        self.assertEqual(status(r,'MMCIF_PARSER'),'PASS')
        self.assertEqual(r['metrics']['atoms'],2)
        self.assertEqual(r['metrics']['severe_close_pairs_heuristic'],0)
        self.assertEqual(r['decision'],'OPEN')
        self.assertTrue(verify(r,raw)[0])

    def test_mmcif_malformed_is_not_accepted(self):
        r=analyze('x.cif',b'data_x\nloop_\n_tag\n"unterminated')
        self.assertNotEqual(r['decision'],'PASS')

    def test_dns_rebinding_host_header_is_rejected(self):
        from fastapi.testclient import TestClient
        from studio.server import app
        c=TestClient(app)
        self.assertEqual(c.get('/api/status',headers={'Host':'evil.example'}).status_code,403)
        self.assertEqual(c.get('/api/status',headers={'Host':'localhost:8765'}).status_code,200)

    def test_api_demo_and_receipt(self):
        from fastapi.testclient import TestClient
        from studio.server import app
        c=TestClient(app)
        sample=c.get('/api/sample/demo_relu_violation.onnx')
        self.assertEqual(sample.status_code,200)
        from urllib.parse import quote
        h={'X-PCS-Filename':quote('a.onnx'), 'X-PCS-Policy':quote(json.dumps({'check_output_bounds':True,'output_min':0,'output_max':.5}))}
        r=c.post('/api/analyze',content=sample.content,headers=h)
        self.assertEqual(r.status_code,200)
        self.assertIn('candidate_counterexample',r.json()['details'])
        self.assertTrue(verify(r.json(),sample.content)[0])

    def test_fuzz_unsupported_inputs_dont_assert_safety(self):
        rng=random.Random(1009)
        for fam in ['.onnx','.sbml','.cif','.safetensors','.pdb']:
            for _ in range(75):
                raw=rng.randbytes(rng.randrange(1,500))
                r=analyze('adversarial'+fam,raw)
                self.assertIn(r['decision'],('OPEN','FAIL'))
                self.assertEqual(r['sha256'],__import__('hashlib').sha256(raw).hexdigest())
                self.assertTrue(verify(r,raw)[0])

if __name__=='__main__':unittest.main()
