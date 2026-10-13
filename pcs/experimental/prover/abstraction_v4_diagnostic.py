"""Preregistered developer-planned reuse diagnostic, not autonomous solve rate."""
import argparse,json,subprocess,time
from pathlib import Path
from .environment import ROOT
from .induction_ir import digest
from .abstraction_v4_experiment import TRANSFER,measurement,delta,write
from .mathlib_environment_v4 import MathlibEnvironmentV4

def action(kind,argument=None):return {'kind':kind,'argument':argument}
def plans():
 rows=[]
 corrected_real={**TRANSFER[1],'id':'corrected-real-order-from-image-chain','statement':TRANSFER[1]['statement'].replace('ℝ → Nat','ℝ → ℝ'),'semantic_correction':'Injective Real→Real has realizable witnesses; original Real→Nat fixture remains preserved and excluded from substantive transfer.'}
 for task,count,prelude,hf,hab,hbc in [(TRANSFER[0],10,'mul_right_cancel','h7','h8','h9'),(TRANSFER[2],7,'congrArg','h4','h5','h6'),(corrected_real,7,'le_of_eq','h4','h5','h6')]:
  prefix=[action('intro','h'+str(i)) for i in range(count)]+[action('apply_lemma',prelude)]
  rows.append({**task,'no_library_actions':prefix+[action('apply_local',hf),action('apply_lemma','Eq.trans'),action('exact_local',hab),action('exact_local',hbc)],'discovered_library_actions':prefix+[action('apply_lemma','PCSAbstractL0'),action('assumption'),action('assumption'),action('assumption')]})
 return rows

def freeze(folder,library_source):
 folder=Path(folder)
 if folder.exists():raise ValueError('new diagnostic generation required')
 source=json.loads(Path(library_source).read_text());rows=plans();folder.mkdir(parents=True)
 protocol={'format':'pcs-abstraction-planned-use-protocol-v4','kind':'developer-authored typed-action diagnostic after exposed failed search; NOT autonomous solve improvement or untouched evaluation','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'library_source_sha256':digest(source),'plans_sha256':digest(rows),'original_search_failure_retained':True,'comparison':'same algebraic prelude; admitted intermediate lemma versus primitive injectivity+Eq.trans; exact checker-verified actions only','novel_mathematics_claim':False,'source_license':'CC0-1.0'}
 write(folder/'protocol.json',protocol);write(folder/'plans.json',rows);write(folder/'library_source.json',source)

def execute(folder):
 folder=Path(folder)
 if (folder/'results.json').exists():raise ValueError('completed diagnostic is immutable')
 protocol=json.loads((folder/'protocol.json').read_text());rows=json.loads((folder/'plans.json').read_text());source=json.loads((folder/'library_source.json').read_text())
 if digest(rows)!=protocol['plans_sha256'] or digest(source)!=protocol['library_source_sha256']:raise ValueError('changed frozen diagnostic')
 total=time.monotonic();baseline=MathlibEnvironmentV4(timeout=12);baseline_startup=measurement(baseline)
 library=MathlibEnvironmentV4(timeout=12);library_startup=measurement(library);before=measurement(library)
 try:
  entry=source['admission'];library.admit(entry['name'],entry['statement'],entry['actions'],source=entry['source'],license=entry['license']);admission=delta(before,measurement(library));results=[]
  for row in rows:
   results.append({k:v for k,v in row.items() if not k.endswith('_actions')})
   for mode,env in [('no_library',baseline),('discovered_library',library)]:
    actions=row[mode+'_actions'];before=measurement(env);tick=time.monotonic()
    try:
     observed=env.observe(row['statement'],actions)
     if observed['status']!='closed':raise RuntimeError(observed['error'] or 'goals remain open')
     receipt=env.verify(row['statement'],actions);result={'status':'verified','receipt':receipt,'states':observed['states']}
    except (RuntimeError,ValueError) as error:result={'status':'unknown','error':str(error)}
    results[-1][mode]={**result,'cost':delta(before,measurement(env)),'wall_seconds':time.monotonic()-tick,'submitted_action_count':len(actions)}
  report={'format':'pcs-abstraction-planned-use-results-v4','protocol_sha256':digest(protocol),'rows':results,'startup':{'baseline':baseline_startup,'library':library_startup},'fresh_library_admission_cost':admission,'total_wall_seconds':time.monotonic()-total,'autonomous_solver_improvement_claim':False,'novel_mathematics_claim':False,'pcs_authority':False}
  write(folder/'results.json',report);print(json.dumps({'diagnostic':[(r['id'],r['no_library']['status'],r['discovered_library']['status']) for r in results]}))
 finally:baseline.close();library.close()

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['freeze','execute']);p.add_argument('folder');p.add_argument('--library-source');a=p.parse_args();freeze(a.folder,a.library_source) if a.command=='freeze' else execute(a.folder)
