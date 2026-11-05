import hashlib,importlib.util,json,tempfile,unittest,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('source_reconciliation',ROOT/'scripts/check_reconciled_prs.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ReconciledSourceTests(unittest.TestCase):
 def test_actual_original_core_heads_and_production_tree(self):
  value=module.check({'proof-carrying-science':ROOT},ROOT/'docs/reconciliation/OPEN_PRS.json');self.assertTrue(value['passed']);self.assertFalse(value['pcs_authority']);self.assertEqual(set(value['checked'][0]['original_prs_retained']),{196,197})
 def test_rehashed_or_missing_registry_is_not_self_authorizing(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'registry.json';data=json.loads((ROOT/'docs/reconciliation/OPEN_PRS.json').read_text());data['repositories'][0]['original_open_prs'][0]['head']='0'*40;p.write_text(json.dumps(data))
   with self.assertRaisesRegex(ValueError,'reviewed digest'):module.check({'proof-carrying-science':ROOT},p)
 def test_empty_scope_cannot_be_reported_as_a_pass(self):
  with self.assertRaises(ValueError):module.check({},ROOT/'docs/reconciliation/OPEN_PRS.json')
