"""Check original PR ancestry and production-source preservation across selected PCS candidates.

Read-only source reconciliation; not an authorization, semantic equivalence or CI attestation.
"""
import argparse,json,subprocess,hashlib
from pathlib import Path

def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE,text=True).strip()
REGISTRY_SHA256='5d69305871d78e262ba3dfa25349743efa11577491f645da8583a15b7398fe05'
def check(roots,manifest):
 if not __debug__:raise RuntimeError("Do not disable source-check assertions")
 if hashlib.sha256(Path(manifest).read_bytes()).hexdigest()!=REGISTRY_SHA256:raise ValueError("Original PR registry differs from reviewed digest")
 if not roots or not set(roots)<={"proof-carrying-science","proof-carrying-science-site","certiforge"}:raise ValueError("At least one known candidate repository is required")
 data=json.loads(Path(manifest).read_text());assert data['format']=='pcs-open-pr-reconciliation-v1'
 expected={'proof-carrying-science':{196,197},'proof-carrying-science-site':{128,129,130,131,145,146,147},'certiforge':set()};result=[]
 assert {r['repository'].split('/')[-1] for r in data['repositories']}==set(expected)
 for entry in data['repositories']:
  name=entry['repository'].split('/')[-1];prs=entry['original_open_prs'];assert {p['number'] for p in prs}==expected[name] and len(prs)==len(expected[name])
  if name not in roots:continue
  root=Path(roots[name]);main=entry['protected']['main']
  for sha in [main,*[p['head'] for p in prs]]:
   assert len(sha)==40 and all(c in '0123456789abcdef' for c in sha)
   subprocess.run(['git','-C',str(root),'merge-base','--is-ancestor',sha,'HEAD'],check=True,capture_output=True)
  if name=='proof-carrying-science':
   for folder in ['pcs','formal']:
    assert git(root,'rev-parse','HEAD:'+folder)==git(root,'rev-parse',main+':'+folder),'Production source changed: '+folder
    assert not git(root,'status','--porcelain','--untracked-files=all','--',folder),'Production working source differs: '+folder
  if name=='proof-carrying-science-site':
   assert git(root,'rev-parse','HEAD:public')==git(root,'rev-parse',main+':public'),'Public deployment tree changed'
   assert not git(root,'status','--porcelain','--untracked-files=all','--','public'),'Public working source differs'
  result.append({'repository':entry['repository'],'candidate':git(root,'rev-parse','HEAD'),'original_prs_retained':[p['number'] for p in prs],'production_source_preserved':True})
 return {'passed':True,'checked':result,'pcs_authority':False,'scope':'Ancestry and exact production-tree identity, not semantics, immutable host storage or a deployment decision.'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--core');p.add_argument('--site');p.add_argument('--certiforge');p.add_argument('--manifest',default=str(Path(__file__).resolve().parents[1]/'docs/reconciliation/OPEN_PRS.json'));a=p.parse_args()
 roots={n:v for n,v in [('proof-carrying-science',a.core),('proof-carrying-science-site',a.site),('certiforge',a.certiforge)] if v};print(json.dumps(check(roots,a.manifest),indent=2))
