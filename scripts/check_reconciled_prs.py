"""Check retained PR source history and exact selected bytes across PCS candidates.

Read-only source reconciliation; not an authorization, semantic equivalence or CI attestation.
"""
import argparse,json,subprocess,hashlib
from pathlib import Path

def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE,text=True).strip()
REGISTRY_SHA256='5d69305871d78e262ba3dfa25349743efa11577491f645da8583a15b7398fe05'

# Exact qualified source histories, retained independently of linear main history.
# A mutable branch/tag name is not trusted in place of its exact object ID.
INTAKES={
 'proof-carrying-science':('0b521f39af99f5856b69dfcc25bc274ec9dc804a','pcs-source-intake/core-open-prs-v1-20261105'),
 'proof-carrying-science-site':('d35e2b5e6b29e0a27dc0cb117986895fd58c1456','pcs-source-intake/site-open-prs-v1-20261105'),
}
COMMON_CONTROLS={'scripts/check_reconciled_prs.py','scripts/test_reconciled_prs.py'}
CONTROLS={
 'proof-carrying-science':COMMON_CONTROLS|{
  '.github/workflows/model-assurance-studio-research.yml',
  'research/integration_v2/reconcile.py','research/integration_v2/test_reconcile.py',
  'docs/integration/2026-11-05/RECONCILIATION_V22.json',
  'docs/integration/2026-11-05/RECONCILIATION.md','docs/integration/2026-11-05/LINEAR_HISTORY.md'},
 'proof-carrying-science-site':COMMON_CONTROLS|{
  '.github/workflows/open-pr-reconciliation.yml',
  'docs/reconciliation/RECONCILIATION.md','docs/reconciliation/LINEAR_HISTORY.md'},
}

def _tree(root,ref):
 raw=subprocess.check_output(['git','-C',str(root),'ls-tree','-rz',ref])
 result={}
 for row in raw.split(b'\0'):
  if row:
   meta,path=row.split(b'\t',1);result[path.decode()]=tuple(meta.decode().split())
 return result

def _retained_sources(root,main,intake,tag,heads,controls):
 assert git(root,'rev-parse','refs/tags/'+tag+'^{commit}')==intake,'Retained source tag differs'
 for earlier,later in [(main,'HEAD'),(main,intake),*[(sha,intake) for sha in heads]]:
  subprocess.run(['git','-C',str(root),'merge-base','--is-ancestor',earlier,later],check=True,capture_output=True)
 before=_tree(root,intake);after=_tree(root,'HEAD')
 assert {p:v for p,v in before.items() if p not in controls}=={p:v for p,v in after.items() if p not in controls},'Qualified non-control source bytes, modes or census differ'
 for name in controls:
  assert name in after and after[name][:2]==('100644','blob'),'Tracked regular integration control required: '+name
  path=Path(root)/name
  assert path.is_file() and not path.is_symlink(),'Regular integration control required: '+name
 assert not git(root,'status','--porcelain','--untracked-files=all'),'Working source differs from committed snapshot'
 return {'qualified_source_commit':intake,'retention_tag':tag,
         'original_ancestry_preserved_at_intake':True,
         'selected_noncontrol_source_files_checked':len(set(before)-controls),
         'current_main_may_use_squash_history':True}


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
  lineage={}
  if name in INTAKES:
   intake,tag=INTAKES[name]
   lineage=_retained_sources(root,main,intake,tag,[p['head'] for p in prs],CONTROLS[name])
  else:
   subprocess.run(['git','-C',str(root),'merge-base','--is-ancestor',main,'HEAD'],check=True,capture_output=True)
  if name=='proof-carrying-science':
   _core_source(root,main)
  if name=='proof-carrying-science-site':
   assert git(root,'rev-parse','HEAD:public')==git(root,'rev-parse',main+':public'),'Public deployment tree changed'
   assert not git(root,'status','--porcelain','--untracked-files=all','--','public'),'Public working source differs'
  result.append({'repository':entry['repository'],'candidate':git(root,'rev-parse','HEAD'),'original_prs_retained':[p['number'] for p in prs],'production_source_preserved':True,**lineage})
 return {'passed':True,'checked':result,'pcs_authority':False,'scope':'Fixed retained source ancestry and exact selected-source/authority/formal/public identities compatible with protected linear main history; not semantics, immutable storage or deployment.'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--core');p.add_argument('--site');p.add_argument('--certiforge');p.add_argument('--manifest',default=str(Path(__file__).resolve().parents[1]/'docs/reconciliation/OPEN_PRS.json'));a=p.parse_args()
 roots={n:v for n,v in [('proof-carrying-science',a.core),('proof-carrying-science-site',a.site),('certiforge',a.certiforge)] if v};print(json.dumps(check(roots,a.manifest),indent=2))
