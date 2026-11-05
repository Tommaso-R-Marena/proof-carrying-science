import math,struct,unittest
from pathlib import Path
from studio.onnxruntime_crosscheck_v07 import ulp_distance
from studio.checked_export_v14 import import_first
from studio.lean_status_v07 import _source
ROOT=Path(__file__).resolve().parents[1]
class ReconciliationV14(unittest.TestCase):
 def test_ulp_signed_zero_and_across_zero(self):
  tiny=2**-149
  for a,b,n in [(0.,-0.,0),(0.,tiny,1),(-tiny,-0.,1),(-tiny,tiny,2),(1.,1.,0)]:
   self.assertEqual(ulp_distance(a,b),n);self.assertEqual(ulp_distance(b,a),n)
 def test_preserved_legacy_becomes_import_first_without_math_change(self):
  raw=(ROOT/'validation/v07_iris_baseline_uncompiled.lean').read_text();new=import_first(raw)
  self.assertTrue(new.startswith('import Mathlib\n'));self.assertEqual(new.removeprefix('import Mathlib\n\n'),raw.replace('import Mathlib\n','',1));self.assertEqual(len(_source(new.encode())[1]),2)
 def test_no_source_escape_can_be_misreported_as_kernel_success(self):
  original=import_first((ROOT/'validation/v07_iris_baseline_uncompiled.lean').read_text())
  for token in ['sorry','admit','axiom forged : False','unsafe def forged := 0','#eval IO.println "ACCEPT"','native_decide']:
   with self.assertRaises(ValueError):_source((original+'\n'+token).encode())
 def test_wrong_import_or_theorem_census_is_rejected(self):
  original=import_first((ROOT/'validation/v07_iris_baseline_uncompiled.lean').read_text())
  for text in [original.replace('import Mathlib','import Std'),original.replace('theorem certified_relation','theorem arbitrary'),original+'\ntheorem forged : True := True.intro\n']:
   with self.assertRaises(ValueError):_source(text.encode())

class ExportCLIV14(unittest.TestCase):
 def test_real_certificate_exports_import_first_source(self):
  import tempfile,subprocess,sys,json
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'Proof.lean'
   p=subprocess.run([sys.executable,'-m','studio.checked_export_v14','relation','samples/demo_trained_iris_mlp.onnx','validation/v06_iris_property_1_certificate.json','validation/v06_iris_property_1_reviewer_policy.json',str(out)],cwd=ROOT,capture_output=True,text=True)
   self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['status'],'SOURCE_EXPORTED_NOT_KERNEL_CHECKED');self.assertTrue(out.read_text().startswith('import Mathlib\n'))
 def test_existing_export_is_never_overwritten(self):
  import tempfile,subprocess,sys
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'Proof.lean';out.write_text('preserved')
   p=subprocess.run([sys.executable,'-m','studio.checked_export_v14','relation','samples/demo_trained_iris_mlp.onnx','validation/v06_iris_property_1_certificate.json','validation/v06_iris_property_1_reviewer_policy.json',str(out)],cwd=ROOT,capture_output=True,text=True)
   self.assertNotEqual(p.returncode,0);self.assertEqual(out.read_text(),'preserved')
 def test_forged_multiplier_never_generates_source(self):
  import tempfile,subprocess,sys,json
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'Proof.lean';cert=Path(tmp)/'forged.json';value=json.loads((ROOT/'validation/v06_iris_property_1_certificate.json').read_text());value['multipliers'][0][1]='11';cert.write_text(json.dumps(value))
   p=subprocess.run([sys.executable,'-m','studio.checked_export_v14','relation','samples/demo_trained_iris_mlp.onnx',str(cert),'validation/v06_iris_property_1_reviewer_policy.json',str(out)],cwd=ROOT,capture_output=True,text=True)
   self.assertNotEqual(p.returncode,0);self.assertFalse(out.exists())
