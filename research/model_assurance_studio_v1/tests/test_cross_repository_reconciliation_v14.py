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

 def test_exact_research_receiver_exception_does_not_open_other_source(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL).decode().strip()
   def commit():git('add','.');git('-c','user.name=PCS tests','-c','user.email=pcs-tests@example.invalid','commit','-qm','source fixture');return git('rev-parse','HEAD')
   git('init','-q');(root/'pcs').mkdir();(root/'formal').mkdir()
   receiver=root/module.RESEARCH_RECEIVER
   receiver.write_bytes(subprocess.check_output(['git','-C',str(ROOT),'show','f20f3cab2938f2e085f137185e88f4700d5da2ed:'+module.RESEARCH_RECEIVER]))
   (root/'pcs/authority.py').write_text('protected source fixture\n');(root/'formal/example.lean').write_text('-- protected fixture\n')
   main=commit();receiver.write_bytes((ROOT/module.RESEARCH_RECEIVER).read_bytes());commit()
   self.assertTrue(module._core_source(root,main))
   receiver.write_bytes(receiver.read_bytes()+b'\n# unreviewed change\n');commit()
   with self.assertRaisesRegex(AssertionError,'receiver bytes'):module._core_source(root,main)
   receiver.write_bytes((ROOT/module.RESEARCH_RECEIVER).read_bytes());(root/'pcs/authority.py').write_text('unreviewed authority change\n');commit()
   with self.assertRaisesRegex(AssertionError,'outside exact research'):module._core_source(root,main)
   (root/'pcs/authority.py').write_text('protected source fixture\n');commit();receiver.chmod(0o755);commit()
   with self.assertRaisesRegex(AssertionError,'mode changed'):module._core_source(root,main)
