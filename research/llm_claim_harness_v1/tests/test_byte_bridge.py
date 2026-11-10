"""V7 independent byte/rational Lean bridge adversarial tests (fake checker never a proof)."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest

from research.llm_claim_harness_v1.byte_bridge import (
    MAX_BRIDGE_BYTES, make_byte_lean_source, run_byte_bridge,
    replay_byte_bridge, main,
)
from research.llm_claim_harness_v1.core import Source, sha, canonical
from research.llm_claim_harness_v1.table_evidence import UnsupportedTable

ROOT=Path(__file__).resolve().parents[1] / 'fixtures'
DATA=(ROOT/'table_data.csv').read_bytes()
MANIFEST=(ROOT/'table_spec.json').read_bytes()

class FakeLean:
    def __init__(self): self.calls=[]
    def _check_generated(self,code,truth,scope):
        self.calls.append((code,truth,scope))
        return {'status':scope+'_PROVED', 'kernel_checked':True,
                'lean_source_sha256':sha(code.encode()), 'lean_source':code}

def s(data=DATA): return Source.from_bytes(data)

class ByteBridgeTests(unittest.TestCase):
    def test_real_decimals_generated_from_all_bytes(self):
        src,count=make_byte_lean_source(s(),MANIFEST)
        self.assertEqual(count,6)
        self.assertIn('def pcsAsciiDecimal',src)
        self.assertIn('def pcsRawBytes : List Nat := [',src)
        self.assertIn('pcsByteChunks 10 pcsRawBytes',src)
        self.assertIn('pcsByteSlice pcsRawBytes',src)
        self.assertIn('List (Option Rat)',src)
        self.assertIn('by decide +kernel',src)
        self.assertEqual(src.count('example :'),2)
        self.assertEqual(src.count('pcsAsciiDecimal (pcsByteSlice pcsRawBytes'),6)
        self.assertNotIn('sorry',src)
        self.assertNotIn('native_decide',src)

    def test_receipt_no_fake_scientific_authority(self):
        fake=FakeLean()
        r=run_byte_bridge(s(),MANIFEST,lean=fake)
        self.assertEqual(r['formal_status'],'BYTE_GROUNDING_PROVED')
        self.assertTrue(r['kernel_checked'])
        self.assertEqual(r['cell_count'],6)
        self.assertEqual(r['data_sha256'],s().digest)
        self.assertEqual(r['scientific_status'],'NOT_ASSESSED')
        self.assertEqual(len(fake.calls),1)

    def test_absent_lean_fails_closed(self):
        r=run_byte_bridge(s(),MANIFEST)
        self.assertEqual(r['formal_status'],'KERNEL_UNAVAILABLE')
        self.assertFalse(r['kernel_checked'])

    def test_mutated_csv_changes_generated_leanscript(self):
        a=run_byte_bridge(s(),MANIFEST,lean=FakeLean())
        b=run_byte_bridge(s(DATA.replace(b'4,2,9',b'4,2,8')),MANIFEST,lean=FakeLean())
        self.assertNotEqual(a['lean_source_sha256'],b['lean_source_sha256'])
        self.assertNotEqual(a['data_sha256'],b['data_sha256'])

    def test_unaltered_decimals_and_negative(self):
        data=(DATA.split(b'\n')[0]+b'\n-2,3,-6\n0.1,0.2,0.02\n')
        src,count=make_byte_lean_source(s(data), MANIFEST)
        self.assertEqual(count,6)
        self.assertIn('pcsAsciiDecimal',src)
        self.assertIn('45,50',src)  # -2 source bytes preserved
        self.assertIn('48,46,49',src) # 0.1 byte sequence preserved

    def test_rejects_crlf_text_with_bad_cells(self):
        for data in (DATA.replace(b'4,2,9',b'4,NaN,9'),
                     DATA.replace(b'4,2,9',b'4,2,1e+9'),
                     DATA.replace(b'4,2,9',b'4,2,=2+7')):
            with self.subTest(data=data),self.assertRaises(UnsupportedTable):
                run_byte_bridge(s(data),MANIFEST,lean=FakeLean())

    def test_crlf_input_source_bytes_preserved(self):
        src,count=make_byte_lean_source(s(DATA.replace(b'\n',b'\r\n')),MANIFEST)
        self.assertEqual(count,6)
        self.assertIn('13,10',src)

    def test_excess_byte_budget_refuses_without_partial_check(self):
        header=DATA.split(b'\n')[0]
        data=header+b'\n'+b'2,3,6\n'*16
        self.assertLessEqual(len(data),MAX_BRIDGE_BYTES)
        # Large input from long but valid header+rows to exercise the budget.
        # Source can be within the v5 grammar but outside the stricter bridge limit.
        big_manifest=json.loads(MANIFEST)
        extra=[{'name':f'c{i}', 'unit':'1'} for i in range(7)]
        big_manifest['columns'].extend(extra)
        lines=[b','.join([b'2',b'3',b'6']+[b'111111']*7)]*16
        raw=b','.join(col['name'].encode() for col in big_manifest['columns'])+b'\n'+b'\n'.join(lines)+b'\n'
        self.assertGreater(len(raw),MAX_BRIDGE_BYTES)
        fake=FakeLean()
        with self.assertRaisesRegex(ValueError,'too large'):
            run_byte_bridge(s(raw),canonical(big_manifest),lean=fake)
        self.assertEqual(fake.calls,[])

    def test_replay_match(self):
        prior=run_byte_bridge(s(),MANIFEST,lean=FakeLean())
        result=replay_byte_bridge(s(),MANIFEST,canonical(prior)+b'\n',lean=FakeLean())
        self.assertEqual(result['status'],'REPLAYED_BYTE_GROUNDING')
        self.assertTrue(result['matched'])

    def test_replay_altered_fields_fail(self):
        prior=run_byte_bridge(s(),MANIFEST,lean=FakeLean())
        for k,v in [('authority','PCS_V06'),('cell_count',5),('scientific_status','CERTIFIED'),('lean_source','theorem fake : True := by trivial')]:
            tampered=copy.deepcopy(prior)
            tampered[k]=v
            result=replay_byte_bridge(s(),MANIFEST,canonical(tampered),lean=FakeLean())
            self.assertEqual(result['status'],'RECEIPT_REJECTED')

    def test_replay_modified_source_or_manifest_blocks_proof(self):
        prior=run_byte_bridge(s(),MANIFEST,lean=FakeLean())
        fake=FakeLean()
        res=replay_byte_bridge(s(DATA.replace(b'4,2,9',b'4,2,8')),MANIFEST,canonical(prior),lean=fake)
        self.assertFalse(res['matched'])
        self.assertEqual(fake.calls,[])
        spec=json.loads(MANIFEST)
        spec['columns'][0]['unit']='g'
        res=replay_byte_bridge(s(),canonical(spec),canonical(prior),lean=fake)
        self.assertFalse(res['matched'])
        self.assertEqual(fake.calls,[])

    def test_cli_provides_unverified_receipt_without_lean(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'receipt.json'
            code=main(['--source',str(ROOT/'table_data.csv'),'--table-spec',str(ROOT/'table_spec.json'),
                      '--out',str(out),'--lean','__not_installed__'])
            self.assertEqual(code,2)
            self.assertEqual(json.loads(out.read_text())['formal_status'],'KERNEL_UNAVAILABLE')

if __name__ == '__main__': unittest.main()
