"""Frozen authored development/transfer experiment, never private/blind testing."""
import argparse,gzip,hashlib,json,subprocess,time
from pathlib import Path
from .environment import ROOT
from .induction_ir import digest
from .mathlib_environment_v4 import MathlibEnvironmentV4
from .abstraction_v4 import propose,CANDIDATE,REPAIRED,COUNTEREXAMPLE,COUNTER_PROOF,REPAIR_ACTIONS,counterexample_search

SOURCES=[
 {'id':'nat-successor-chain','module':'Mathlib.Data.Nat.Basic','statement':'∀ (a b c : Nat), Nat.succ a = Nat.succ b → Nat.succ b = Nat.succ c → a = c','proof':'  intro a b c hab hbc\n  exact Nat.succ.inj (Eq.trans hab hbc)'},
 {'id':'list-cons-chain','module':'Mathlib.Data.List.Basic','statement':'∀ (a b c : List Nat), (0 :: a) = (0 :: b) → (0 :: b) = (0 :: c) → a = c','proof':'  intro a b c hab hbc\n  exact (List.cons.inj (Eq.trans hab hbc)).2'}]
TRANSFER=[
 {'id':'group-right-cancellation','domain':'Group','module':'Mathlib.Algebra.Group.Basic','statement':'∀ (G : Type) [Group G] (f : G → Nat) (a b c k : G), Function.Injective f → f (a * k) = f (b * k) → f (b * k) = f (c * k) → a = c'},
 {'id':'real-order-from-image-chain','domain':'Real order','module':'Mathlib.Data.Real.Basic','statement':'∀ (f : ℝ → Nat) (a b c : ℝ), Function.Injective f → f a = f b → f b = f c → a ≤ c'},
 {'id':'list-length-congruence','domain':'List length','module':'Mathlib.Data.List.Basic','statement':'∀ (f : List Nat → Nat) (a b c : List Nat), Function.Injective f → f a = f b → f b = f c → a.length = c.length'},
 {'id':'set-membership-transport','domain':'Set membership','module':'Mathlib.Data.Set.Basic','statement':'∀ (f : Nat → Nat) (a b c : Nat) (s : Set Nat), Function.Injective f → f a = f b → f b = f c → a ∈ s → c ∈ s'}]

def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def freeze(folder):
 folder=Path(folder)
 if folder.exists():raise ValueError('immutable experiment generation requires new directory')
 folder.mkdir(parents=True)
 protocol={'format':'pcs-verified-abstraction-protocol-v4','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'inputs_sha256':digest([SOURCES,TRANSFER]),'source_license':'CC0-1.0','evaluation':'public developer-authored frozen transfer; not private, blind or external-corpus generalization','excluded_final_benchmark':'benchmarks/mathlib-v4 final was neither read nor used','discovery_sources':2,'transfer_tasks':4,'search_budget':{'actions':48,'depth':18,'beam':4,'premises':8,'seconds':45},'strongest_baseline':'Mathlib simp_all/omega/aesop/grind/ring-linarith portfolio','novel_mathematics_claim':False,'discovery_accounting':'source verification, structured states, counterexample, repair admission, signature extraction, retrieval construction and terminal double compilation retained separately'}
 write(folder/'protocol.json',protocol);write(folder/'sources.json',SOURCES);write(folder/'transfer.json',TRANSFER)

def freeze_diagnostic(folder,parent):
 parent=Path(parent);original=json.loads((parent/'summary.json').read_text())
 if json.loads((parent/'protocol.json').read_text())['inputs_sha256']!=digest([SOURCES,TRANSFER]):raise ValueError('different original discovery/transfer inputs')
 freeze(folder);path=Path(folder)/'protocol.json';protocol=json.loads(path.read_text())
 protocol.update(development_reuse_exposed_transfers=True,private_blind_or_final_evaluation=False,original_results_sha256=digest(original),original_metrics=original['metrics'],purpose='Receiver forced-introduction scheduling diagnostic; unchanged48action/18depth/4beam/8premise/45second bounds; all original outcomes retained')
 write(path,protocol)

def measurement(env):return {'standalone_compiler_calls':env.calls,'structured_worker_requests':env.worker_requests,'physical_Lean_calls':env.calls+env.worker_requests,'cpu_seconds':env.cpu_seconds,'wall_seconds_standalone_compile':env.seconds,'max_child_rss_kib':env.max_child_rss_kib,'cache_hits':env.cache_hits}
def delta(before,after):return {k:after[k]-before[k] for k in before if k!='max_child_rss_kib'}|{'max_child_rss_kib':after['max_child_rss_kib']}
def compile_independently(env,statement,proof):
 kernels=[env._record(f'theorem pcs_abstraction_{name} : {statement} := by\n{proof}\n#pcs_audit pcs_abstraction_{name}\n','PCS_KERNEL:') for name in ['source','replay']]
 if kernels[0]!=kernels[1] or not set(kernels[0]['axioms'])<={'propext','Classical.choice','Quot.sound'}:raise RuntimeError('independent kernel replay rejected')
 return {'statement':statement,'goal_sha256':digest(statement),'proof':proof,'kernel':kernels[0],'independent_kernel':kernels[1],'pcs_authority':False}

def execute(folder):
 folder=Path(folder)
 if (folder/'results.json').exists() or (folder/'results.json.gz').exists():raise ValueError('completed experiment is immutable')
 protocol=json.loads((folder/'protocol.json').read_text());sources=json.loads((folder/'sources.json').read_text());transfers=json.loads((folder/'transfer.json').read_text())
 if digest([sources,transfers])!=protocol['inputs_sha256']:raise ValueError('changed frozen inputs')
 total=time.monotonic();env=MathlibEnvironmentV4(timeout=12);construction=measurement(env);start=measurement(env)
 try:
  checked=[]
  for source in sources:
   before=measurement(env);receipt=compile_independently(env,source['statement'],source['proof'])
   state=env.observe(source['statement'],[{'kind':'intro','argument':'h'+str(i)} for i in range(5)])['states'][-1]
   checked.append({**source,'receipt':receipt,'state':state,'cost':delta(before,measurement(env))})
  proposal=propose(checked);screen=counterexample_search();counter=compile_independently(env,COUNTEREXAMPLE,screen['proof'])
  repair={'reason':'constant function erases endpoint distinctions; equality-chain transport needs injectivity','counterexample':{'domain':'Nat','codomain':'Nat','function':'fun _ => 0','endpoints':[0,0,1]},'statement':REPAIRED,'counterexample_search':screen,'counterexample_receipt':counter}
  admitted=env.admit('PCSAbstractL0',REPAIRED,REPAIR_ACTIONS,source={'protocol_sha256':digest(protocol),'proposal_sha256':digest(proposal),'source_goal_sha256':[s['receipt']['goal_sha256'] for s in checked]},license='CC0-1.0')
  discovery_cost=delta(start,measurement(env));library_sha256=env.library_sha256;library=env.library
  write(folder/'discovery.json',{'sources':checked,'proposal':proposal,'repair':repair,'admission':admitted,'library_sha256':library_sha256,'cost':discovery_cost,'construction':construction})
  rows=[]
  # Baseline receiver contains no discovered declaration at all.
  baseline=MathlibEnvironmentV4(timeout=12)
  try:
   baseline_construction=measurement(baseline)
   for task in transfers:
    print(json.dumps({'task':task['id'],'stage':'no_library'}),flush=True)
    bare=baseline.solve(task['statement'],**{'budget':48,'depth':18,'beam':4,'premises':8,'wall':45})
    print(json.dumps({'task':task['id'],'stage':'strongest_portfolio'}),flush=True)
    strong=baseline.portfolio(task['statement'])
    print(json.dumps({'task':task['id'],'stage':'discovered_library'}),flush=True)
    learned=env.solve(task['statement'],**{'budget':48,'depth':18,'beam':4,'premises':8,'wall':45})
    row={**task,'no_library':bare,'strongest_portfolio':strong,'discovered_library':learned};rows.append(row);write(folder/'partial.json',{'rows':rows})
  finally:baseline.close()
  result={'format':'pcs-verified-abstraction-results-v4','protocol_sha256':digest(protocol),'library_sha256':library_sha256,'library':library,'rows':rows,'discovery_cost':discovery_cost,'construction':{'discovery':construction,'baseline':baseline_construction},'total_wall_seconds':time.monotonic()-total,'novel_mathematics_claim':False,'pcs_authority':False}
  result['metrics']={mode:{'verified':sum(r[mode]['status']=='verified' for r in rows),'tasks':len(rows),'physical_Lean_calls':sum(r[mode]['physical_lean_calls'] for r in rows),'wall_seconds':sum(r[mode]['wall_seconds'] for r in rows)} for mode in ['no_library','strongest_portfolio','discovered_library']}
  result['unique_beyond_strongest']=[r['id'] for r in rows if r['discovered_library']['status']=='verified' and r['strongest_portfolio']['status']!='verified']
  result['proofs_using_discovered_lemma']=[r['id'] for r in rows if r['discovered_library'].get('receipt') and any(a.get('argument')=='PCSAbstractL0' for a in r['discovered_library']['receipt']['actions'])]
  write(folder/'results.json',result);print(json.dumps(result['metrics']),flush=True)
 finally:env.close()

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['freeze','execute','freeze-diagnostic']);parser.add_argument('folder');parser.add_argument('--parent');args=parser.parse_args();freeze_diagnostic(args.folder,args.parent) if args.command=='freeze-diagnostic' else (freeze if args.command=='freeze' else execute)(args.folder)
