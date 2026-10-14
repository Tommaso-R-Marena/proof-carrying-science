#!/usr/bin/env python3
"""Finite actual Python/Node/extracted-Lean receipt comparison; hashes abstracted.

The digest functions remain explicit theorem hypotheses; replace only two digest
fields with DIGEST on all sides. This experiment is not a native semantics proof.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from pcs.experimental import conditional as C
from verify_conditional_runtime_refinement import check_sources, sha


def encoded(value):
 if isinstance(value, dict): return {'__obj__': [[key, encoded(v)] for key, v in value.items()]}
 if isinstance(value, list): return [encoded(v) for v in value]
 return value


def normalize(receipt):
 receipt['task_sha256'] = 'DIGEST'
 receipt['receipt_sha256'] = 'DIGEST'
 return receipt


def ordered(value):
 if isinstance(value, dict): return ('object', tuple((k, ordered(v)) for k, v in value.items()))
 if isinstance(value, list): return ('array', tuple(ordered(v) for v in value))
 return value


def execute(command, cwd, *, timeout=600):
 start = time.monotonic()
 result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout)
 if result.returncode: raise RuntimeError(result.stdout + result.stderr)
 return result.stdout, round(time.monotonic() - start, 6)


def verify(site: Path, output: Path, count: int = 90, seed: int = 614):
 if output.exists(): raise ValueError('evidence output directory must be new')
 source = check_sources(site)
 rng = random.Random(seed)
 tasks = []
 initial = [('A', 'A', ''), ('A', '!A', ''), ('A', 'B', 'A\n!A'),
            ('A & B', 'A', 'B'), ('A | B', 'B | A', ''), ('A', 'B', 'A -> B')]
 def formula(depth):
  if depth == 0 or rng.random() < .35: return rng.choice(['A', 'B', 'C', 'TRUE', 'FALSE'])
  if rng.random() < .25: return '!' + formula(depth - 1)
  return '(' + formula(depth - 1) + rng.choice([' & ', ' | ', ' -> ']) + formula(depth - 1) + ')'
 while len(initial) * 3 < count:
  initial.append((formula(2), formula(2), '\n'.join(formula(1) for _ in range(rng.randrange(3)))))
 for src, candidate, assumptions in initial:
  task = C.from_text(src, candidate, assumptions)
  for limits in [{'nodes':4096,'operations':100000}, {'nodes':2,'operations':100000},
                 {'nodes':4096,'operations':1}]:
   tasks.append({'task':task, 'limits':limits})
 tasks = tasks[:count]
 python = [normalize(C.check(row['task'], row['limits'])) for row in tasks]
 output.mkdir(parents=True)
 (output / 'tasks.json').write_text(json.dumps({'cases':tasks},indent=2)+'\n')
 (output / 'python.json').write_text(json.dumps(python,indent=2)+'\n')
 with tempfile.TemporaryDirectory(prefix='pcs-conditional-node-') as directory:
  runner = Path(directory) / 'run.mjs'
  runner.write_text("import {readFileSync} from 'node:fs';\nimport {checkConditional} from " +
                    json.dumps((site / 'public/conditional-core.mjs').resolve().as_uri()) + ";\n" +
                    "const cases=JSON.parse(readFileSync(process.argv[2],'utf8')).cases;\n" +
                    "for(const c of cases){const r=await checkConditional(c.task,{limits:c.limits});" +
                    "r.task_sha256='DIGEST';r.receipt_sha256='DIGEST';console.log(JSON.stringify(r));}\n")
  stdout, node_wall = execute(['node',str(runner),str(output / 'tasks.json')],site)
 javascript = [json.loads(line) for line in stdout.splitlines()]
 (output / 'javascript.json').write_text(json.dumps(javascript,indent=2)+'\n')
 encoded_cases = {'cases': [{'task':encoded(row['task']), 'limits':encoded(row['limits'])} for row in tasks]}
 (output / 'encoded-tasks.json').write_text(json.dumps(encoded_cases)+'\n')
 lean_results = {}
 times = {'node_wall_seconds':node_wall}
 for language, stem in [('python','PyConditionalCompare'), ('javascript','JsConditionalCompare')]:
  stdout, wall = execute(['lake','env','lean','--run',str(ROOT/'formal/tools'/(stem+'.lean')),
                          str(output/'encoded-tasks.json')],ROOT/'formal')
  values = [json.loads(line) for line in stdout.splitlines()]
  if any(not isinstance(value,dict) for value in values): raise ValueError('Lean extraction exhausted or failed')
  lean_results[language] = values
  times[language+'_lean_wall_seconds'] = wall
  (output/(language+'-lean.json')).write_text(json.dumps(values,indent=2)+'\n')
 if len(javascript) != count or any(len(v) != count for v in lean_results.values()):
  raise ValueError('runtime case inventory differs')
 mismatches=[i for i in range(count) if not ordered(python[i])==ordered(javascript[i])==
             ordered(lean_results['python'][i])==ordered(lean_results['javascript'][i])]
 kinds={}
 for receipt in python: kinds[receipt['decision']]=kinds.get(receipt['decision'],0)+1
 if check_sources(site) != source: raise ValueError('source identity changed during finite comparison')
 report={'format':'pcs-conditional-runtime-parity-v1','cases':count,'seed':seed,'mismatches':mismatches,
         'decisions':kinds,'source_identity':source['source_files'], 'cost':times,
         'digest_fields_abstracted':True,'universal_native_correspondence_proved':False,
         'scientific_acceptance':False,
         'evidence_sha256':{p.name:sha(p) for p in output.glob('*.json')}}
 (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 if mismatches: raise ValueError('runtime/extracted-reference mismatches: '+str(mismatches))
 return report


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--site',type=Path,required=True)
 parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--cases',type=int,default=90)
 parser.add_argument('--seed',type=int,default=614)
 args=parser.parse_args()
 if not 18 <= args.cases <= 300 or args.cases % 3: parser.error('cases must be multiple of three in [18,300]')
 print(json.dumps(verify(args.site.resolve(),args.output.resolve(),args.cases,args.seed)))

if __name__=='__main__':main()
