"""Check original PR ancestry and production-source preservation across selected PCS candidates.

Read-only source reconciliation; not an authorization, semantic equivalence or CI attestation.
"""
import argparse,json,subprocess,hashlib
from pathlib import Path

def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE,text=True).strip()
REGISTRY_SHA256='5d69305871d78e262ba3dfa25349743efa11577491f645da8583a15b7398fe05'

# One exact non-authority proof-construction repair. All other PCS source and
# every formal source must retain protected main bytes/modes. This helper has
# pcs_authority=False; the trusted production acceptance code is unchanged.
RESEARCH_RECEIVER='pcs/transport_trace_kernel_v1.py'
RECEIVER_OLD='b158a573c428e27b7008a335cdf9cf5daf654a9f1283a3023a8ec3195ea5b605'
RECEIVER_NEW='ff409b9a4a1c062c51761afc2c05f459d95f56eb3ca689c2a3a59b4d0e20e4eb'
def _core_source(root,main):
 assert git(root,'rev-parse','HEAD:formal')==git(root,'rev-parse',main+':formal'),'Formal source changed'
 changed=git(root,'diff','--name-only',main,'HEAD','--','pcs').splitlines()
 assert changed in [[],[RESEARCH_RECEIVER]],'PCS changes outside exact research receiver repair'
 if changed:
  for ref,expected in [(main,RECEIVER_OLD),('HEAD',RECEIVER_NEW)]:
   raw=subprocess.check_output(['git','-C',str(root),'show',ref+':'+RESEARCH_RECEIVER])
   assert hashlib.sha256(raw).hexdigest()==expected,'Unreviewed research receiver bytes'
   assert git(root,'ls-tree',ref,'--',RESEARCH_RECEIVER).split()[0]=='100644','Research receiver mode changed'
 for folder in ['pcs','formal']:
  assert not git(root,'status','--porcelain','--untracked-files=all','--',folder),'Working source differs: '+folder
 return bool(changed)

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
   _core_source(root,main)
  if name=='proof-carrying-science-site':
   assert git(root,'rev-parse','HEAD:public')==git(root,'rev-parse',main+':public'),'Public deployment tree changed'
   assert not git(root,'status','--porcelain','--untracked-files=all','--','public'),'Public working source differs'
  result.append({'repository':entry['repository'],'candidate':git(root,'rev-parse','HEAD'),'original_prs_retained':[p['number'] for p in prs],'production_source_preserved':True})
 return {'passed':True,'checked':result,'pcs_authority':False,'scope':'Ancestry and exact authority/formal/public source identity with one digest-pinned non-authority receiver repair; not semantics, immutable storage or deployment.'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--core');p.add_argument('--site');p.add_argument('--certiforge');p.add_argument('--manifest',default=str(Path(__file__).resolve().parents[1]/'docs/reconciliation/OPEN_PRS.json'));a=p.parse_args()
 roots={n:v for n,v in [('proof-carrying-science',a.core),('proof-carrying-science-site',a.site),('certiforge',a.certiforge)] if v};print(json.dumps(check(roots,a.manifest),indent=2))
