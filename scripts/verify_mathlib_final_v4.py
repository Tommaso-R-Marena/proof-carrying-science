import gzip,hashlib,json,time
from pathlib import Path
from pcs.experimental.prover.mathlib_environment_v4 import MathlibEnvironmentV4,same_kernel_type
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'research/mathlib-generalization-v4'
summary=json.loads((OUT/'summary.json').read_text()); rows=json.load(gzip.open(OUT/'matrix.json.gz','rt'))
tasks=json.loads((ROOT/'benchmarks/mathlib-v4/tasks.json').read_text()); by_id={t['id']:t for t in tasks}
methods=json.loads((OUT/'protocol.json').read_text())['methods']
assert len(rows)==220 and len({(r['task_id'],r['method']) for r in rows})==220
assert {r['method'] for r in rows}==set(methods)
env=MathlibEnvironmentV4(timeout=60); replays=[]; tick=time.monotonic()
try:
 for i,r in enumerate(rows):
  assert r['result']['status'] in {'verified','unknown'} and r['result']['pcs_authority'] is False
  if r['result']['status']!='verified': continue
  receipt=r['result']['receipt']; statement=by_id[r['task_id']]['statement']; assert receipt['statement']==statement
  # Stored proof is developer-local output from the frozen bounded action/tactic receiver.
  print(json.dumps({'replay_task':r['task_id'],'method':r['method']}),flush=True)
  actual=env._record(f'theorem pcs_post_evaluation_replay_{i} : {statement} := by\n{receipt["proof"]}\n#pcs_audit pcs_post_evaluation_replay_{i}\n','PCS_KERNEL:')
  assert same_kernel_type(receipt['kernel'],actual)
  replays.append({'task_id':r['task_id'],'method':r['method'],'kernel':actual,'proof_sha256':hashlib.sha256(receipt['proof'].encode()).hexdigest()})
 (OUT/'fresh-kernel-replays.json').write_text(json.dumps({'wall_limit_seconds':60,'cpu_limit_seconds':30,'original_30_second_attempt':'Failed with resource exhaustion; log retained; no original evaluation score changed','proofs':replays},indent=2)+'\n')
 metrics={}
 for method in methods:
  selected=[r for r in rows if r['method']==method]
  metrics[method]={'solved':sum(r['result']['status']=='verified' for r in selected),'tasks':len(selected),
    **{k:sum(r['measured'][k] for r in selected) for k in ['wall_seconds','cpu_seconds','compiler_invocations','structured_worker_requests','physical_lean_calls','model_inference_seconds','model_inference_calls']},
    'recorded_expansions':sum(r['result'].get('expansions') or 0 for r in selected),
    'replayed_prefix_action_upper_bound':sum(len(t['prefix'])+1 for r in selected for t in r['result'].get('transitions',[])),
    'max_child_rss_cumulative_upper_bound_kib':max(r['measured']['max_child_rss_kib'] for r in selected)}
 result={'format':'pcs-post-evaluation-independent-replay-v4','matrix_sha256':hashlib.sha256((OUT/'matrix.json.gz').read_bytes()).hexdigest(),
  'complete_comparisons':len(rows),'fresh_kernel_replays':replays,'metrics':metrics,'post_evaluation_compiler_invocations':env.calls,
  'post_evaluation_wall_seconds':time.monotonic()-tick,'prefix_accounting':'Upper bound; every resident request reconstructs its entire prefix, cached requests may do less. Full resource failures have no trace.',
  'memory_scope':'ru_maxrss is cumulative child high-water mark, not exact per-task peak or Python/model memory',
  'original_summary':summary,'training_authorization':False,'promotion':False}
 (OUT/'independent-replay-and-accounting.json').write_text(json.dumps(result,indent=2)+'\n')
 # Post-evaluation bottleneck diagnosis: theorem dependency NAMES only, never bodies into a policy.
 commands='''open Lean Elab Command Meta
syntax "#pcs_dependencies_v4" : command
elab_rules : command
 | `(#pcs_dependencies_v4) => do
  liftTermElabM do
   let mut rows := #[]
'''
 for t in tasks:
  commands+=f'''   let info ← getConstInfo `{t['declaration']}
   let names := match info with | .thmInfo info => info.value.getUsedConstants.toList.map toString | _ => []
   rows := rows.push <| Json.mkObj [("declaration", toJson "{t['declaration']}"), ("dependencies", toJson names)]
'''
 commands+='   IO.println s!"PCS_DEPENDENCIES:{(toJson rows).compress}"\n#pcs_dependencies_v4\n'
 dependencies=env._record(commands,'PCS_DEPENDENCIES:')
 for d in dependencies:
  d['indexed_dependencies']=[n for n in d['dependencies'] if n in env.by_name]
  d['unindexed_dependencies']=[n for n in d['dependencies'] if n not in env.by_name]
 (OUT/'post-evaluation-dependency-diagnostic.json').write_text(json.dumps({'scope':'Post-final developer diagnosis only; names from existing Mathlib proof values; no training or final-set reevaluation authorized','rows':dependencies},indent=2)+'\n')
 print(json.dumps({'rows':len(rows),'independent_final_proofs':len(replays),'metrics':metrics}),flush=True)
finally:env.close()
