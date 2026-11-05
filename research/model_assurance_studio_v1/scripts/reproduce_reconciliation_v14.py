"""Fresh qualified Lean checks and actual official ONNX Runtime observations.

Does not overwrite historical evidence or promote a model/production authority.
"""
import argparse,hashlib,importlib.metadata,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from studio.checked_export_v14 import import_first
from studio.lean_status_v07 import check_proof
from studio.onnxruntime_crosscheck_v07 import compare

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(output,project,require_kernel=False,require_ort=False):
 out=Path(output).resolve();out.mkdir();results=[]
 for name in ['v07_iris_baseline_uncompiled.lean','v07_iris_drift_uncompiled.lean']:
  original=ROOT/'validation'/name;target=out/name.replace('_uncompiled','_import_first')
  target.write_text(import_first(original.read_text()))
  verdict=check_proof(target,project_dir=project,timeout=180)
  results.append({'historical_file':str(original.relative_to(ROOT)),'historical_sha256':sha(original),'successor_sha256':sha(target),'transformation':'Move the single Mathlib import before module documentation; mathematical statements and proof bodies unchanged.','verdict':verdict})
  if require_kernel and not verdict['kernel_checked']:raise RuntimeError('Required actual kernel check did not succeed: '+json.dumps(verdict))
 runtimes=[]
 for name in ['demo_dense_neural_violation.onnx','demo_trained_iris_mlp.onnx','demo_trained_iris_updated.onnx','demo_correlated_fp32_margin_v13.onnx']:
  raw=(ROOT/'samples'/name).read_bytes();r=compare(raw,count=64,seed=1771);runtimes.append({'model':name,'result':r})
  if require_ort and r['status'] not in {'OBSERVED_MATCH','OBSERVED_DIFFERENCES'}:raise RuntimeError('Required actual official runtime did not execute: '+json.dumps(r))
 versions={}
 for name in ['onnxruntime','onnx','numpy','protobuf','torch','cryptography']:
  try:versions[name]=importlib.metadata.version(name)
  except importlib.metadata.PackageNotFoundError:versions[name]=None
 report={'format':'pcs-studio-reconciliation-v14','proofs':results,'official_runtime_observations':runtimes,'dependency_versions':versions,
 'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'studio').glob('*.py'))},
 'pcs_authority':False,'onnx_parser_kernel_verified':False,'abstract_interpreter_kernel_verified':False,'runtime_universal_equivalence':False,'external_independent_validation':False,
 'scope':'Two abstract inequality implications checked by qualified Lean; finite observations using four screened curated ONNX fixtures and CPUExecutionProvider. Not a model deployment certificate or general AI safety result.'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--project-dir',default=str(ROOT.parents[1]));p.add_argument('--require-kernel',action='store_true');p.add_argument('--require-ort',action='store_true');a=p.parse_args();print(json.dumps(run(a.output,a.project_dir,a.require_kernel,a.require_ort),indent=2))
